from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.localization import (
    OutputLocale,
    apply_summary_locale_update,
    normalize_output_locale,
    normalize_summary_locale_map,
    output_language_label,
)
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    serialize_prompt_task_trace,
)
from app.services.stage_drafts import can_reuse_stage_draft_cache
from app.services.stage_payloads import build_stage_payload
from app.services.stage_summary_fallbacks import build_stage_summary_fallback


STAGE_SUMMARY_FALLBACK_MODEL = "deterministic-stage-summary-fallback"
SUMMARY_STAGES = {"problem", "market", "tech"}
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()
WorkerContextSetter = Callable[[Any, str | None], Awaitable[None]]


async def _commit_if_transaction_open(session) -> None:
    if session.in_transaction():
        await session.commit()


async def generate_stage_summary_v0(
    session,
    stage: str,
    payload: dict[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
    trace_sink: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    stage_key = stage.strip().lower()
    if stage_key not in SUMMARY_STAGES:
        raise ValueError(f"Unsupported stage for summary: {stage}")
    context = PROMPT_CONTEXT_BUILDER.stage_summary(
        stage_key,
        payload,
        output_language=output_language_label(output_locale),
    )
    try:
        result = await execute_prompt_task(
            session,
            context,
            project_settings=project_settings,
            expected_mutation=PromptMutationClass.REPORT_ARTIFACT,
        )
    except Exception as exc:
        if trace_sink is not None:
            trace_sink[f"stage_summary_{stage_key}"] = {
                "task_key": f"stage_summary_{stage_key}",
                "status": "fallback",
                "failure_reason": str(exc) or exc.__class__.__name__,
                "model": STAGE_SUMMARY_FALLBACK_MODEL,
                "provider": "deterministic",
            }
        return (
            build_stage_summary_fallback(
                stage_key,
                payload,
                output_locale=output_locale,
            ),
            STAGE_SUMMARY_FALLBACK_MODEL,
        )
    if trace_sink is not None:
        trace_sink[f"stage_summary_{stage_key}"] = serialize_prompt_task_trace(result)
    if not result.ok:
        if trace_sink is not None:
            trace_sink[f"stage_summary_{stage_key}"]["fallback_used"] = True
        return (
            build_stage_summary_fallback(
                stage_key,
                payload,
                output_locale=output_locale,
            ),
            STAGE_SUMMARY_FALLBACK_MODEL,
        )
    summary = (result.content or "").strip()
    if not summary:
        if trace_sink is not None:
            trace_sink[f"stage_summary_{stage_key}"]["fallback_used"] = True
            trace_sink[f"stage_summary_{stage_key}"]["failure_reason"] = (
                "empty_summary"
            )
        return (
            build_stage_summary_fallback(
                stage_key,
                payload,
                output_locale=output_locale,
            ),
            STAGE_SUMMARY_FALLBACK_MODEL,
        )
    return summary, result.model


async def run_stage_summary_v0(
    session,
    payload: dict[str, Any],
    *,
    job_org_id: str | None = None,
    set_worker_context_fn: WorkerContextSetter | None = None,
) -> None:
    project_id = payload.get("project_id")
    stage = payload.get("stage")
    raw_context_version = payload.get("context_version")
    if not project_id or not isinstance(stage, str) or raw_context_version is None:
        raise ValueError("Job payload missing stage summary identifiers.")

    normalized_stage = stage.strip().lower()
    if normalized_stage not in SUMMARY_STAGES:
        raise ValueError(f"Unsupported stage for summary: {stage}")
    try:
        context_version = int(raw_context_version)
    except (TypeError, ValueError) as exc:
        raise ValueError("Stage summary payload has invalid context_version.") from exc
    raw_output_locale = payload.get("output_locale")
    output_locale = normalize_output_locale(
        raw_output_locale if isinstance(raw_output_locale, str) else None
    )

    org_id: Any = None
    owner_user_id: Any = None
    bank_id: Any = None
    current_variant = "default"
    project_settings: dict[str, Any] | None = None
    stage_payload: dict[str, Any] | None = None

    async with session.begin():
        if set_worker_context_fn is not None:
            await set_worker_context_fn(session, job_org_id)
        project_result = await session.execute(
            text(
                "SELECT id, org_id, owner_user_id, current_stage, current_variant, "
                "stage_status, question_bank_version_id, settings "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id)},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            raise ValueError("Project not found for stage summary job.")

        org_id = project_row.get("org_id")
        owner_user_id = project_row.get("owner_user_id")
        if not org_id or not owner_user_id:
            raise ValueError("Project missing org or owner for stage summary job.")

        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(owner_user_id)},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )

        if project_row.get("current_stage") != normalized_stage:
            return
        if project_row.get("stage_status") != "awaiting_confirm":
            return
        bank_id = project_row.get("question_bank_version_id")
        if not bank_id:
            raise ValueError("Project question bank missing for stage summary job.")
        current_variant = project_row.get("current_variant") or "default"
        settings = project_row.get("settings")
        project_settings = settings if isinstance(settings, dict) else None

        state_result = await session.execute(
            text(
                "SELECT state_json, state_meta, state_version "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id), "org_id": str(org_id)},
        )
        state_row = state_result.mappings().first()
        if not state_row:
            raise ValueError("Project state not found for stage summary job.")
        state_json = state_row.get("state_json")
        if not isinstance(state_json, dict):
            state_json = {}
        state_meta = state_row.get("state_meta")
        if not isinstance(state_meta, dict):
            state_meta = {}
        current_state_version = state_row.get("state_version") or 0
        if int(current_state_version) != context_version:
            return

        summary_locale_map = normalize_summary_locale_map(state_meta)
        existing_draft_locale = (
            summary_locale_map.get(normalized_stage, {}).get("draft")
        )
        assessment_result = await session.execute(
            text(
                "SELECT draft_summary_markdown, generated_from_state_version "
                "FROM project_stage_assessments "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND stage = :stage "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "project_id": str(project_id),
                "org_id": str(org_id),
                "stage": normalized_stage,
            },
        )
        assessment_row = assessment_result.mappings().first()
        if can_reuse_stage_draft_cache(
            existing_summary=assessment_row.get("draft_summary_markdown")
            if assessment_row
            else None,
            existing_version=assessment_row.get("generated_from_state_version")
            if assessment_row
            else None,
            state_version=context_version,
            existing_draft_locale=existing_draft_locale,
            requested_output_locale=output_locale,
        ):
            return

        stage_payload = await build_stage_payload(
            session,
            bank_id,
            normalized_stage,
            current_variant,
            state_json,
            state_meta,
        )

    if stage_payload is None:
        return

    trace_sink: dict[str, Any] = {}
    summary_markdown, summary_model = await generate_stage_summary_v0(
        session,
        normalized_stage,
        stage_payload,
        output_locale=output_locale,
        project_settings=project_settings,
        trace_sink=trace_sink,
    )
    await _commit_if_transaction_open(session)

    async with session.begin():
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(owner_user_id)},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )
        project_result = await session.execute(
            text(
                "SELECT current_stage, stage_status, question_bank_version_id "
                "FROM projects "
                "WHERE id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1 "
                "FOR UPDATE"
            ),
            {"project_id": str(project_id), "org_id": str(org_id)},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            return
        if project_row.get("current_stage") != normalized_stage:
            return
        if project_row.get("stage_status") != "awaiting_confirm":
            return
        if str(project_row.get("question_bank_version_id")) != str(bank_id):
            return

        state_result = await session.execute(
            text(
                "SELECT state_meta, state_version "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id), "org_id": str(org_id)},
        )
        state_row = state_result.mappings().first()
        if not state_row:
            return
        state_meta = state_row.get("state_meta")
        if not isinstance(state_meta, dict):
            state_meta = {}
        current_state_version = state_row.get("state_version") or 0
        if int(current_state_version) != context_version:
            return

        summary_locale_map = normalize_summary_locale_map(state_meta)
        existing_draft_locale = (
            summary_locale_map.get(normalized_stage, {}).get("draft")
        )
        assessment_result = await session.execute(
            text(
                "SELECT draft_summary_markdown, generated_from_state_version "
                "FROM project_stage_assessments "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND stage = :stage "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "project_id": str(project_id),
                "org_id": str(org_id),
                "stage": normalized_stage,
            },
        )
        assessment_row = assessment_result.mappings().first()
        if can_reuse_stage_draft_cache(
            existing_summary=assessment_row.get("draft_summary_markdown")
            if assessment_row
            else None,
            existing_version=assessment_row.get("generated_from_state_version")
            if assessment_row
            else None,
            state_version=context_version,
            existing_draft_locale=existing_draft_locale,
            requested_output_locale=output_locale,
        ):
            return

        await session.execute(
            text(
                "INSERT INTO project_stage_assessments ("
                "org_id, project_id, stage, draft_summary_markdown, "
                "generated_from_state_version, generator_model, scores_json"
                ") VALUES ("
                ":org_id, :project_id, :stage, :summary, :state_version, "
                ":generator_model, :scores_json"
                ") "
                "ON CONFLICT (project_id, stage) WHERE deleted_at IS NULL DO UPDATE SET "
                "draft_summary_markdown = EXCLUDED.draft_summary_markdown, "
                "generated_from_state_version = EXCLUDED.generated_from_state_version, "
                "generator_model = EXCLUDED.generator_model, "
                "scores_json = COALESCE(project_stage_assessments.scores_json, '{}'::jsonb) "
                "|| EXCLUDED.scores_json, "
                "updated_at = now()"
            ).bindparams(bindparam("scores_json", type_=JSONB)),
            {
                "org_id": str(org_id),
                "project_id": str(project_id),
                "stage": normalized_stage,
                "summary": summary_markdown,
                "state_version": context_version,
                "generator_model": summary_model,
                "scores_json": {"prompt_task_traces": trace_sink}
                if trace_sink
                else {},
            },
        )
        next_state_meta = apply_summary_locale_update(
            state_meta,
            stage=normalized_stage,
            draft_output_locale=output_locale,
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
                "project_id": str(project_id),
                "org_id": str(org_id),
            },
        )


__all__ = [
    "STAGE_SUMMARY_FALLBACK_MODEL",
    "generate_stage_summary_v0",
    "run_stage_summary_v0",
]
