from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.usage_limits import enforce_llm_usage_limits
from app.services.stage_drafts import can_reuse_stage_draft_cache
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths
from app.services.localization import (
    DEFAULT_OUTPUT_LOCALE,
    OutputLocale,
    apply_summary_locale_update,
    normalize_summary_locale_map,
)
from app.services.project_permissions import can_mutate_project
from app.services.report_jobs import (
    build_queued_report_job_status,
    enqueue_report_generation_job,
)
from app.services.stage_confirmation_preparation import (
    build_prepared_stage_confirmation_payload,
    extract_stage_prompt_task_traces,
    normalize_stage_state_snapshot,
    resolve_stage_confirmation_defaults,
)
from app.services.stage_confirmation_persistence_payloads import (
    build_confirmed_stage_artifact_payload,
)
from app.services.stage_confirmation_types import (
    ConfirmedStagePersistenceResult,
    PreparedStageConfirmation,
    STAGE_CONFIRMATION_NEXT_MAP,
    StageConfirmationCommitResult,
    StageConfirmationConflictError,
    StageConfirmationNotFoundError,
    StageConfirmationPermissionError,
    StageConfirmationRuntimeError,
)
from app.services.stage_finalize_jobs import enqueue_stage_finalize_job
from app.services.stage_question_setup import (
    StageQuestionPromptMissingError,
    StageStarterQuestionMissingError,
    build_stage_question_meta_payload,
    fetch_stage_question_detail,
    resolve_stage_initial_questions,
    resolve_stage_missing_paths,
    resolve_tech_entry_variant,
)
from app.services.stage_runtime import advance_project_stage_from_decision
from app.services.stage_transition import (
    STAGE_STATUS_IN_PROGRESS,
    decide_next_stage_after_confirmation,
    decide_stage_confirmation_advance,
    next_stage_starts_in_review,
)


async def prepare_stage_confirmation_workflow(
    session,
    *,
    org_id: str,
    project_id: str,
    user_id: str,
    stage: str,
    client_context_version: int | None,
    output_locale: OutputLocale,
    is_verified: bool,
) -> PreparedStageConfirmation:
    defaults = resolve_stage_confirmation_defaults(
        stage=stage,
        next_stage_map=STAGE_CONFIRMATION_NEXT_MAP,
    )
    if defaults is None:
        raise StageConfirmationNotFoundError("Stage not supported for confirmation.")

    next_stage = defaults.next_stage
    next_variant = defaults.next_variant
    project_result = await session.execute(
        text(
            "SELECT id, org_id, current_stage, current_variant, stage_status, "
            "question_bank_version_id, title, description, settings "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    project_row = project_result.mappings().first()
    if not project_row:
        raise StageConfirmationNotFoundError("Project not found.")

    initial_confirmation_decision = decide_stage_confirmation_advance(
        requested_stage=stage,
        current_stage=project_row.get("current_stage"),
        stage_status=project_row.get("stage_status"),
        next_stage=next_stage,
        next_stage_status=STAGE_STATUS_IN_PROGRESS,
    )
    if initial_confirmation_decision.reason == "stage_mismatch":
        raise StageConfirmationConflictError(
            "Project stage changed. Refresh and try again."
        )
    if initial_confirmation_decision.reason == "stage_not_awaiting_confirm":
        raise StageConfirmationConflictError("Stage is not ready for confirmation.")

    await enforce_llm_usage_limits(session, user_id=user_id, is_verified=is_verified)

    state_result = await session.execute(
        text(
            "SELECT state_json, state_meta, state_version "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    state_row = state_result.mappings().first()
    state_snapshot = normalize_stage_state_snapshot(state_row)
    state_json = state_snapshot.state_json
    state_meta = state_snapshot.state_meta
    state_version = state_snapshot.state_version

    if client_context_version is not None and client_context_version != state_version:
        raise StageConfirmationConflictError(
            "Context updated while you were away. Refresh and try again."
        )

    bank_id = project_row.get("question_bank_version_id")
    if not bank_id:
        raise StageConfirmationRuntimeError("Project question bank is missing.")
    current_variant = project_row.get("current_variant") or "default"
    if next_stage == "tech":
        next_variant = await resolve_tech_entry_variant(session, bank_id=bank_id)

    current_required_paths = await resolve_stage_missing_paths(
        session,
        bank_id=bank_id,
        stage=stage,
        variant=current_variant,
    )
    current_stage_missing_paths = filter_stage_blocking_missing_paths(
        stage,
        current_required_paths,
        state_json=state_json,
        state_meta=state_meta,
    )
    summary_locale_map = normalize_summary_locale_map(state_meta)
    existing_draft_locale = summary_locale_map.get(stage, {}).get("draft")
    assessment_result = await session.execute(
        text(
            "SELECT id, draft_summary_markdown, generated_from_state_version, "
            "generator_model, scores_json "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND stage = :stage "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "org_id": org_id,
            "stage": stage,
        },
    )
    assessment_row = assessment_result.mappings().first()
    existing_summary = assessment_row.get("draft_summary_markdown") if assessment_row else None
    existing_version = (
        assessment_row.get("generated_from_state_version") if assessment_row else None
    )
    if not can_reuse_stage_draft_cache(
        existing_summary=existing_summary,
        existing_version=existing_version,
        state_version=state_version,
        existing_draft_locale=existing_draft_locale,
        requested_output_locale=output_locale,
    ):
        raise StageConfirmationConflictError(
            "Stage summary is still being prepared. Refresh and try again."
        )

    prompt_task_traces = extract_stage_prompt_task_traces(assessment_row)

    next_stage_status = defaults.next_stage_status
    current_question_id = None
    next_question_id = None
    missing_paths: list[str] = []
    question_detail: dict[str, Any] | None = None

    if next_stage != "report":
        try:
            current_question_id, next_question_id = await resolve_stage_initial_questions(
                session,
                bank_id=bank_id,
                stage=next_stage,
                variant=next_variant,
            )
            missing_paths = await resolve_stage_missing_paths(
                session,
                bank_id=bank_id,
                stage=next_stage,
                variant=next_variant,
            )
        except StageStarterQuestionMissingError as exc:
            raise StageConfirmationRuntimeError(str(exc)) from exc
        next_stage_decision = decide_next_stage_after_confirmation(
            next_stage,
            missing_paths,
            state_json=state_json,
            state_meta=state_meta,
            variant=next_variant,
        )
        missing_paths = next_stage_decision.missing_paths
        next_stage_status = next_stage_decision.next_stage_status
        if not next_stage_starts_in_review(next_stage, next_stage_status):
            try:
                question_detail = await fetch_stage_question_detail(
                    session,
                    current_question_id,
                )
            except StageQuestionPromptMissingError as exc:
                raise StageConfirmationRuntimeError(str(exc)) from exc
    else:
        next_stage_decision = decide_next_stage_after_confirmation(
            next_stage,
            [],
            state_json=state_json,
            state_meta=state_meta,
            variant=next_variant,
        )
        next_stage_status = next_stage_decision.next_stage_status

    return PreparedStageConfirmation(
        **build_prepared_stage_confirmation_payload(
            org_id=org_id,
            project_id=project_id,
            user_id=user_id,
            stage=stage,
            bank_id=bank_id,
            current_variant=current_variant,
            defaults=defaults,
            next_variant=next_variant,
            next_stage_status=next_stage_status,
            state_snapshot=state_snapshot,
            current_stage_missing_paths=current_stage_missing_paths,
            assessment_row=assessment_row,
            prompt_task_traces=prompt_task_traces,
            output_locale=output_locale,
            current_question_id=current_question_id,
            next_question_id=next_question_id,
            missing_paths=missing_paths,
            question_detail=question_detail,
        )
    )


async def commit_prepared_stage_confirmation_workflow(
    session,
    *,
    prepared: PreparedStageConfirmation,
    report_ready_message: str,
) -> StageConfirmationCommitResult:
    return await commit_stage_confirmation_workflow(
        session,
        org_id=prepared.org_id,
        project_id=prepared.project_id,
        user_id=prepared.user_id,
        stage=prepared.stage,
        bank_id=prepared.bank_id,
        current_variant=prepared.current_variant,
        next_stage=prepared.next_stage,
        next_variant=prepared.next_variant,
        next_stage_status=prepared.next_stage_status,
        state_version=prepared.state_version,
        current_stage_missing_paths=prepared.current_stage_missing_paths,
        summary_markdown=prepared.summary_markdown,
        summary_model=prepared.summary_model,
        prompt_task_traces=prepared.prompt_task_traces,
        output_locale=prepared.output_locale,
        current_question_id=prepared.current_question_id,
        next_question_id=prepared.next_question_id,
        missing_paths=prepared.missing_paths,
        question_detail=prepared.question_detail,
        report_ready_message=report_ready_message,
    )


async def persist_confirmed_stage_assessment(
    session,
    *,
    org_id: str,
    project_id: str,
    stage: str,
    user_id: str,
    state_version: int,
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    missing_paths: list[str],
    summary_markdown: str | None,
    summary_model: str | None,
    prompt_task_traces: dict[str, Any] | None,
    output_locale: OutputLocale,
    total_score: float | None = None,
    risk_matrix: dict[str, Any] | None = None,
) -> ConfirmedStagePersistenceResult:
    artifact_payload = build_confirmed_stage_artifact_payload(
        stage=stage,
        state_json=state_json,
        state_meta=state_meta,
        missing_paths=missing_paths,
        prompt_task_traces=prompt_task_traces,
    )

    assessment_result = await session.execute(
        text(
            "INSERT INTO project_stage_assessments ("
            "org_id, project_id, stage, final_summary_markdown, confirmed, "
            "confirmed_by_user_id, generated_from_state_version, generator_model, "
            "scores_json, total_score, risk_matrix, context_card_json, "
            "validation_plan_json"
            ") VALUES ("
            ":org_id, :project_id, :stage, :summary, true, :user_id, "
            ":state_version, :generator_model, :scores_json, :total_score, "
            ":risk_matrix, :context_card, :validation_plan"
            ") "
            "ON CONFLICT (project_id, stage) WHERE deleted_at IS NULL DO UPDATE SET "
            "final_summary_markdown = EXCLUDED.final_summary_markdown, "
            "confirmed = EXCLUDED.confirmed, "
            "confirmed_by_user_id = EXCLUDED.confirmed_by_user_id, "
            "confirmed_at = now(), "
            "generated_from_state_version = EXCLUDED.generated_from_state_version, "
            "generator_model = EXCLUDED.generator_model, "
            "scores_json = EXCLUDED.scores_json, "
            "total_score = EXCLUDED.total_score, "
            "risk_matrix = EXCLUDED.risk_matrix, "
            "context_card_json = EXCLUDED.context_card_json, "
            "validation_plan_json = EXCLUDED.validation_plan_json, "
            "updated_at = now() "
            "RETURNING id"
        ).bindparams(
            bindparam("scores_json", type_=JSONB),
            bindparam("risk_matrix", type_=JSONB),
            bindparam("context_card", type_=JSONB),
            bindparam("validation_plan", type_=JSONB),
        ),
        {
            "org_id": org_id,
            "project_id": project_id,
            "stage": stage,
            "summary": summary_markdown,
            "user_id": user_id,
            "state_version": state_version,
            "generator_model": summary_model,
            "scores_json": artifact_payload.scores_json_payload,
            "total_score": total_score,
            "risk_matrix": risk_matrix,
            "context_card": artifact_payload.context_card,
            "validation_plan": artifact_payload.validation_plan,
        },
    )
    assessment_row = assessment_result.mappings().first()
    next_state_meta = apply_summary_locale_update(
        state_meta,
        stage=stage,
        final_output_locale=output_locale,
    )
    await session.execute(
        text(
            "UPDATE project_states "
            "SET state_meta = :state_meta, "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ).bindparams(bindparam("state_meta", type_=JSONB)),
        {
            "state_meta": next_state_meta,
            "project_id": project_id,
            "org_id": org_id,
        },
    )

    return ConfirmedStagePersistenceResult(
        assessment_id=assessment_row.get("id") if assessment_row else None,
        context_card=artifact_payload.context_card,
        validation_plan=artifact_payload.validation_plan,
        scores_json_payload=artifact_payload.scores_json_payload,
    )


async def initialize_stage_confirmation_runtime(
    session,
    *,
    org_id: str,
    project_id: str,
    next_stage: str,
    next_variant: str,
    next_stage_status: str,
    current_question_id: Any | None,
    next_question_id: Any | None,
    missing_paths: list[str],
    assistant_prompt: str | None,
    question_detail: dict[str, Any] | None,
    report_ready_message: str,
) -> None:
    if next_stage != "report":
        if not current_question_id:
            raise StageConfirmationRuntimeError("Next stage question is missing.")
        await session.execute(
            text(
                "UPDATE project_runtime "
                "SET current_question_bank_question_id = :current_question_id, "
                "next_question_bank_question_id = :next_question_id, "
                "missing_paths = :missing_paths, "
                "turn_state = 'draft', "
                "runtime_version = runtime_version + 1, "
                "updated_at = now() "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {
                "current_question_id": current_question_id,
                "next_question_id": next_question_id,
                "missing_paths": missing_paths,
                "project_id": project_id,
                "org_id": org_id,
            },
        )

        if next_stage_starts_in_review(next_stage, next_stage_status):
            return

        question_instance_result = await session.execute(
            text(
                "INSERT INTO project_question_instances ("
                "org_id, project_id, question_bank_question_id"
                ") VALUES ("
                ":org_id, :project_id, :question_id"
                ") "
                "ON CONFLICT (project_id, question_bank_question_id) "
                "WHERE deleted_at IS NULL "
                "DO UPDATE SET updated_at = project_question_instances.updated_at "
                "RETURNING id"
            ),
            {
                "org_id": org_id,
                "project_id": project_id,
                "question_id": current_question_id,
            },
        )
        question_instance_row = question_instance_result.mappings().first()
        if not question_instance_row:
            raise StageConfirmationRuntimeError(
                "Unable to initialize question instance."
            )

        if not assistant_prompt or not question_detail:
            raise StageConfirmationRuntimeError("Question prompt is missing.")

        await session.execute(
            text(
                "INSERT INTO conversation_messages ("
                "org_id, project_id, role, stage, variant, "
                "question_instance_id, content, meta"
                ") VALUES ("
                ":org_id, :project_id, 'assistant', :stage, :variant, "
                ":question_instance_id, :content, :meta"
                ")"
            ).bindparams(bindparam("meta", type_=JSONB)),
            {
                "org_id": org_id,
                "project_id": project_id,
                "stage": next_stage,
                "variant": next_variant,
                "question_instance_id": question_instance_row.get("id"),
                "content": assistant_prompt,
                "meta": {
                    "schema_version": "v1",
                    "question_id": question_detail.get("question_id"),
                    "content_locale": DEFAULT_OUTPUT_LOCALE,
                    "question_meta": build_stage_question_meta_payload(
                        question_detail
                    ),
                },
            },
        )
        return

    await session.execute(
        text(
            "UPDATE project_runtime "
            "SET current_question_bank_question_id = :current_question_id, "
            "next_question_bank_question_id = NULL, "
            "missing_paths = :missing_paths, "
            "turn_state = 'draft', "
            "runtime_version = runtime_version + 1, "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "current_question_id": None,
            "missing_paths": [],
            "project_id": project_id,
            "org_id": org_id,
        },
    )
    await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, role, stage, variant, content, meta"
            ") VALUES ("
            ":org_id, :project_id, 'assistant', :stage, :variant, :content, :meta"
            ")"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "org_id": org_id,
            "project_id": project_id,
            "stage": next_stage,
            "variant": next_variant,
            "content": report_ready_message,
            "meta": {"schema_version": "v1"},
        },
    )


async def commit_stage_confirmation_workflow(
    session,
    *,
    org_id: str,
    project_id: str,
    user_id: str,
    stage: str,
    bank_id: Any,
    current_variant: str,
    next_stage: str,
    next_variant: str,
    next_stage_status: str,
    state_version: int,
    current_stage_missing_paths: list[str],
    summary_markdown: str | None,
    summary_model: str | None,
    prompt_task_traces: dict[str, Any],
    output_locale: OutputLocale,
    current_question_id: Any | None,
    next_question_id: Any | None,
    missing_paths: list[str],
    question_detail: dict[str, Any] | None,
    report_ready_message: str,
    total_score: float | None = None,
    risk_matrix: dict[str, Any] | None = None,
) -> StageConfirmationCommitResult:
    project_result = await session.execute(
        text(
            "SELECT id, org_id, current_stage, current_variant, stage_status, "
            "question_bank_version_id, settings "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1 "
            "FOR UPDATE"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    project_row = project_result.mappings().first()
    if not project_row:
        raise StageConfirmationNotFoundError("Project not found.")

    allowed = await can_mutate_project(
        session,
        project_id=project_id,
        org_id=org_id,
        user_id=user_id,
    )
    if not allowed:
        raise StageConfirmationPermissionError("Insufficient project permissions.")

    locked_confirmation_decision = decide_stage_confirmation_advance(
        requested_stage=stage,
        current_stage=project_row.get("current_stage"),
        stage_status=project_row.get("stage_status"),
        next_stage=next_stage,
        next_stage_status=next_stage_status,
    )
    if locked_confirmation_decision.reason == "stage_mismatch":
        raise StageConfirmationConflictError(
            "Project stage changed. Refresh and try again."
        )
    if locked_confirmation_decision.reason == "stage_not_awaiting_confirm":
        raise StageConfirmationConflictError("Stage is not ready for confirmation.")
    if str(project_row.get("question_bank_version_id")) != str(bank_id):
        raise StageConfirmationConflictError(
            "Project question bank changed. Refresh and try again."
        )

    state_result = await session.execute(
        text(
            "SELECT state_json, state_version, state_meta "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    state_row = state_result.mappings().first()
    current_state_snapshot = normalize_stage_state_snapshot(state_row)
    if current_state_snapshot.state_version != state_version:
        raise StageConfirmationConflictError(
            "Context updated while you were away. Refresh and try again."
        )

    confirmed_stage = await persist_confirmed_stage_assessment(
        session,
        org_id=org_id,
        project_id=project_id,
        stage=stage,
        user_id=user_id,
        state_version=int(state_version),
        state_json=current_state_snapshot.state_json,
        state_meta=current_state_snapshot.state_meta,
        missing_paths=current_stage_missing_paths,
        summary_markdown=summary_markdown,
        summary_model=summary_model,
        prompt_task_traces=prompt_task_traces,
        output_locale=output_locale,
        total_score=total_score,
        risk_matrix=risk_matrix,
    )

    await advance_project_stage_from_decision(
        session,
        project_id=project_id,
        org_id=org_id,
        decision=locked_confirmation_decision,
        next_variant=next_variant,
    )

    report_job_status: dict[str, Any] | None = None
    if next_stage == "report":
        job_row = await enqueue_report_generation_job(
            session,
            org_id=org_id,
            project_id=project_id,
            context_version=int(current_state_snapshot.state_version),
            output_locale=output_locale,
            requested_by_user_id=user_id,
        )
        report_job_status = build_queued_report_job_status(
            project_id=project_id,
            current_stage="report",
            stage_status=next_stage_status,
            status=job_row.get("status"),
            context_version=int(current_state_snapshot.state_version),
        )

    await enqueue_stage_finalize_job(
        session,
        org_id=org_id,
        project_id=project_id,
        stage=stage,
        context_version=int(current_state_snapshot.state_version),
        output_locale=output_locale,
        requested_by_user_id=user_id,
        question_bank_version_id=str(bank_id),
        variant=current_variant,
    )

    assistant_prompt = question_detail.get("prompt") if question_detail else None
    await initialize_stage_confirmation_runtime(
        session,
        org_id=org_id,
        project_id=project_id,
        next_stage=next_stage,
        next_variant=next_variant,
        next_stage_status=next_stage_status,
        current_question_id=current_question_id,
        next_question_id=next_question_id,
        missing_paths=missing_paths,
        assistant_prompt=assistant_prompt,
        question_detail=question_detail,
        report_ready_message=report_ready_message,
    )

    return StageConfirmationCommitResult(
        assessment_id=confirmed_stage.assessment_id,
        next_stage=next_stage,
        stage_status=next_stage_status,
        score_status="queued",
        scores_json=confirmed_stage.scores_json_payload,
        total_score=total_score,
        risk_matrix=risk_matrix,
        context_card=confirmed_stage.context_card,
        validation_plan=confirmed_stage.validation_plan,
        report_job_status=report_job_status,
    )


__all__ = [
    "ConfirmedStagePersistenceResult",
    "PreparedStageConfirmation",
    "StageConfirmationCommitResult",
    "StageConfirmationConflictError",
    "STAGE_CONFIRMATION_NEXT_MAP",
    "StageConfirmationNotFoundError",
    "StageConfirmationPermissionError",
    "StageConfirmationRuntimeError",
    "commit_prepared_stage_confirmation_workflow",
    "commit_stage_confirmation_workflow",
    "initialize_stage_confirmation_runtime",
    "persist_confirmed_stage_assessment",
    "prepare_stage_confirmation_workflow",
]
