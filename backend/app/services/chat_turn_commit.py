import json
import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.chat_followup_compose import (
    build_followup_stream_context,
    build_question_stream_context,
)
from app.services.chat_context_reads import fetch_context_meta
from app.services.chat_question_planning import (
    apply_transition_prefix,
    build_question_group_payload,
    persist_question_plan,
    question_supports_grouping,
    resolve_question_group,
    resolve_question_group_plan,
    should_attempt_question_planner,
)
from app.services.chat_question_runtime import (
    ensure_question_instance,
    fetch_chat_question_detail,
    resolve_askable_question_id,
    resolve_initial_questions,
    resolve_missing_paths,
    resolve_next_question_id,
    resolve_repair_question,
)
from app.services.chat_router_mode import require_router_mode
from app.services.chat_stream.latency import record_latency_span
from app.services.chat_turn_payloads import (
    ChatStateUpdateResult,
    NeedsInfoTurnResult,
    NextQuestionTurnResult,
    RuntimeMetadataUpdateResult,
    StandardNextTurnResult,
    TransitionTurnResult,
)
from app.services.chat_turn_commit_shapers import (
    apply_chat_state_patch,
    build_needs_info_assistant_meta,
    build_router_mode_state_event_patch,
    build_next_question_assistant_meta,
    build_next_question_turn_result,
    build_skip_answer_status_meta,
    build_stage_gate_ready_payload,
    build_stage_transition_assistant_meta,
    build_state_event_patch,
    derive_updated_runtime_missing_paths,
    normalize_project_state_payload,
    resolve_routing_state_json,
    resolve_standard_question_routing,
    select_transition_state_payload,
    should_update_chat_state_meta,
)
from app.services.project_state_events import record_project_state_event
from app.services.stage_runtime import (
    update_project_runtime_missing_paths_from_decision,
    update_project_stage_status_from_decision,
)
from app.services.stage_transition import decide_stage_ready

TRANSITION_MESSAGE = (
    "Thank you. I have gathered enough information for this stage. "
    "I am now analyzing your responses."
)


async def commit_needs_info_turn(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    runtime_row: Any,
    decision: dict[str, Any],
    followup_message: str,
    rolling_summary: str | None,
    key_points: list[str],
    request_id: str,
    turn_event_meta: dict[str, Any],
    latency_spans: dict[str, float] | None = None,
) -> NeedsInfoTurnResult:
    started_at = time.perf_counter()
    await session.execute(
        text(
            "UPDATE project_question_instances "
            "SET status = 'needs_info', "
            "validation_status = 'needs_info', "
            "updated_at = now() "
            "WHERE id = :question_instance_id "
            "AND project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "question_instance_id": gate_context["current_question_instance_id"],
            "project_id": gate_context["project_id"],
            "org_id": org_id,
        },
    )
    await session.execute(
        text(
            "UPDATE project_runtime "
            "SET turn_state = 'needs_info', "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "project_id": gate_context["project_id"],
            "org_id": org_id,
        },
    )

    assistant_meta_payload = build_needs_info_assistant_meta(
        gate_context=gate_context,
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
    )
    question_stream_context = await build_followup_stream_context(
        session,
        project_id=gate_context["project_id"],
        org_id=org_id,
        stage=runtime_row.get("stage"),
        variant=runtime_row.get("variant"),
        question_instance_id=gate_context["current_question_instance_id"],
        question_detail=gate_context["question_detail"],
        decision=decision,
        fallback_content=followup_message,
        meta=assistant_meta_payload.assistant_meta,
        output_locale=gate_context.get("output_locale", "en"),
        latest_answer=gate_context.get("latest_answer"),
        context_summary=gate_context.get("context_summary"),
        message_meta=gate_context.get("message_meta"),
        project_settings=gate_context.get("project_settings"),
        answer_evaluation_request_id=request_id,
    )
    question_stream_context.update(turn_event_meta)
    record_latency_span(latency_spans, "db_commit.needs_info_turn", started_at)
    return NeedsInfoTurnResult(
        assistant_content=followup_message,
        question_meta_payload=assistant_meta_payload.question_meta_payload,
        question_stream_context=question_stream_context,
    )


async def commit_answer_status(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    skip_requested: bool,
    answer_action: str | None,
    skip_resolution_status: str | None,
    skip_reason: str | None,
    latency_spans: dict[str, float] | None = None,
) -> None:
    started_at = time.perf_counter()
    if skip_requested:
        await session.execute(
            text(
                "UPDATE project_question_instances "
                "SET status = 'skipped', "
                "validation_status = 'not_validated', "
                "answered_at = now(), "
                "final_answer_text = NULL, "
                "meta = COALESCE(meta, '{}'::jsonb) || CAST(:meta AS jsonb), "
                "updated_at = now() "
                "WHERE id = :question_instance_id "
                "AND project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ).bindparams(bindparam("meta", type_=JSONB)),
            {
                "question_instance_id": gate_context["current_question_instance_id"],
                "project_id": gate_context["project_id"],
                "org_id": org_id,
                "meta": json.dumps(
                    build_skip_answer_status_meta(
                        answer_action=answer_action,
                        skip_resolution_status=skip_resolution_status,
                        skip_reason=skip_reason,
                    )
                ),
            },
        )
    else:
        await session.execute(
            text(
                "UPDATE project_question_instances "
                "SET status = 'answered', "
                "validation_status = 'valid', "
                "answered_at = now(), "
                "final_answer_text = :answer_text, "
                "updated_at = now() "
                "WHERE id = :question_instance_id "
                "AND project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {
                "question_instance_id": gate_context["current_question_instance_id"],
                "project_id": gate_context["project_id"],
                "org_id": org_id,
                "answer_text": gate_context["extraction_answer_text"],
            },
        )

    record_latency_span(latency_spans, "db_commit.answer_status", started_at)


async def apply_chat_state_updates(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    runtime_stage: str | None,
    runtime_variant: str | None,
    resolved_paths: list[str],
    extraction_updates: list[tuple[str, str, Any]],
    schema_paths: list[Any],
    skip_requested: bool,
    skip_resolution_status: str | None,
    skip_reason: str | None,
    partial_unknown_paths: list[str],
    latency_spans: dict[str, float] | None = None,
) -> ChatStateUpdateResult:
    if not should_update_chat_state_meta(
        extraction_updates=extraction_updates,
        skip_requested=skip_requested,
        schema_paths=schema_paths,
        partial_unknown_paths=partial_unknown_paths,
    ):
        return ChatStateUpdateResult(state_json=None, state_meta=None)

    started_at = time.perf_counter()
    state_result = await session.execute(
        text(
            "SELECT state_json, state_meta, state_version "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {
            "project_id": gate_context["project_id"],
            "org_id": org_id,
        },
    )
    state_row = state_result.mappings().first()
    state_payload = normalize_project_state_payload(state_row)
    patch_result = apply_chat_state_patch(
        gate_context=gate_context,
        state_json=state_payload.state_json,
        state_meta=state_payload.state_meta,
        pending_confirm=state_payload.pending_confirm,
        runtime_stage=runtime_stage,
        resolved_paths=resolved_paths,
        extraction_updates=extraction_updates,
        schema_paths=schema_paths,
        skip_requested=skip_requested,
        skip_resolution_status=skip_resolution_status,
        skip_reason=skip_reason,
        partial_unknown_paths=partial_unknown_paths,
    )
    state_json = patch_result.state_json
    state_meta = patch_result.state_meta

    next_version = state_payload.state_version + 1
    if state_payload.has_existing_state:
        prev_version = state_payload.state_version
        await session.execute(
            text(
                "UPDATE project_states "
                "SET state_json = :state_json, "
                "state_meta = :state_meta, "
                "state_version = :state_version "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ).bindparams(
                bindparam("state_json", type_=JSONB),
                bindparam("state_meta", type_=JSONB),
            ),
            {
                "project_id": gate_context["project_id"],
                "org_id": org_id,
                "state_json": state_json,
                "state_meta": state_meta,
                "state_version": next_version,
            },
        )
    else:
        prev_version = 0
        await session.execute(
            text(
                "INSERT INTO project_states ("
                "project_id, org_id, bank_version_id, "
                "state_json, state_meta, state_version"
                ") VALUES ("
                ":project_id, :org_id, :bank_version_id, "
                ":state_json, :state_meta, :state_version"
                ")"
            ).bindparams(
                bindparam("state_json", type_=JSONB),
                bindparam("state_meta", type_=JSONB),
            ),
            {
                "project_id": gate_context["project_id"],
                "org_id": org_id,
                "bank_version_id": gate_context["bank_version_id"],
                "state_json": state_json,
                "state_meta": state_meta,
                "state_version": next_version,
            },
        )
    await record_project_state_event(
        session,
        org_id=org_id,
        project_id=str(gate_context["project_id"]),
        question_instance_id=str(gate_context["current_question_instance_id"]),
        event_type="apply_patch",
        patch_json=build_state_event_patch(
            runtime_stage=runtime_stage,
            runtime_variant=runtime_variant,
            resolved_paths=resolved_paths,
            extraction_updates=extraction_updates,
            skip_requested=skip_requested,
            partial_unknown_paths=partial_unknown_paths,
        ),
        actor_type="system",
        prev_state_version=prev_version,
        next_state_version=next_version,
        request_id=gate_context.get("request_id"),
    )
    record_latency_span(latency_spans, "db_commit.state_update", started_at)
    return ChatStateUpdateResult(state_json=state_json, state_meta=state_meta)


async def update_runtime_metadata_after_answer(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    runtime_stage: str | None,
    runtime_variant: str | None,
    runtime_missing_paths: list[str],
    resolved_paths: list[str],
    skip_requested: bool,
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
    latency_spans: dict[str, float] | None = None,
) -> RuntimeMetadataUpdateResult:
    started_at = time.perf_counter()
    updated_missing_paths = runtime_missing_paths
    stage_status_ready = None

    missing_paths_result = derive_updated_runtime_missing_paths(
        runtime_stage=runtime_stage,
        runtime_variant=runtime_variant,
        runtime_missing_paths=runtime_missing_paths,
        resolved_paths=resolved_paths,
        skip_requested=skip_requested,
        state_json=state_json,
        state_meta=state_meta,
    )
    updated_missing_paths = missing_paths_result.updated_missing_paths
    if missing_paths_result.changed:
        await session.execute(
            text(
                "UPDATE project_runtime "
                "SET missing_paths = :missing_paths "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {
                "project_id": gate_context["project_id"],
                "org_id": org_id,
                "missing_paths": updated_missing_paths,
            },
        )

    transition_state_json, transition_state_meta = select_transition_state_payload(
        gate_context=gate_context,
        state_json=state_json,
        state_meta=state_meta,
    )
    stage_ready_decision = decide_stage_ready(
        runtime_stage,
        updated_missing_paths,
        state_json=transition_state_json,
        state_meta=transition_state_meta,
        variant=runtime_variant,
    )
    if stage_ready_decision.missing_paths != updated_missing_paths:
        await update_project_runtime_missing_paths_from_decision(
            session,
            project_id=gate_context["project_id"],
            org_id=org_id,
            decision=stage_ready_decision,
        )
    updated_missing_paths = stage_ready_decision.missing_paths
    if stage_ready_decision.allowed:
        await update_project_stage_status_from_decision(
            session,
            project_id=gate_context["project_id"],
            org_id=org_id,
            decision=stage_ready_decision,
            require_allowed=True,
        )
        stage_status_ready = stage_ready_decision.next_stage_status

    record_latency_span(latency_spans, "db_commit.runtime_metadata", started_at)
    return RuntimeMetadataUpdateResult(
        updated_missing_paths=updated_missing_paths,
        stage_status_ready=stage_status_ready,
    )


async def insert_answer_evaluation(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    rubric_id: str,
    scores_payload: dict[str, Any],
    overall_score: Any,
    feedback_markdown: str,
    evaluator_model: str | None,
    request_id: str,
) -> None:
    await session.execute(
        text(
            "INSERT INTO answer_evaluations ("
            "org_id, project_id, question_instance_id, rubric_id, "
            "scores_json, overall_score, feedback_markdown, "
            "evaluator_type, evaluator_model, request_id"
            ") VALUES ("
            ":org_id, :project_id, :question_instance_id, :rubric_id, "
            ":scores_json, :overall_score, :feedback_markdown, "
            "'ai', :evaluator_model, :request_id"
            ")"
        ).bindparams(bindparam("scores_json", type_=JSONB)),
        {
            "org_id": org_id,
            "project_id": gate_context["project_id"],
            "question_instance_id": gate_context["current_question_instance_id"],
            "rubric_id": str(rubric_id),
            "scores_json": scores_payload,
            "overall_score": overall_score,
            "feedback_markdown": feedback_markdown,
            "evaluator_model": evaluator_model,
            "request_id": request_id,
        },
    )


async def commit_stage_transition_turn(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    runtime_stage: str | None,
    runtime_variant: str | None,
    decision: dict[str, Any],
    rolling_summary: str | None,
    key_points: list[str],
    stage_gate_ready_for_review: bool,
) -> TransitionTurnResult:
    await session.execute(
        text(
            "UPDATE project_runtime "
            "SET next_question_bank_question_id = NULL, "
            "turn_state = 'updated', "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "project_id": gate_context["project_id"],
        },
    )
    await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, role, stage, variant, content, meta"
            ") VALUES ("
            "app_org_id(), :project_id, 'assistant', :stage, "
            ":variant, :content, :meta"
            ")"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": gate_context["project_id"],
            "stage": runtime_stage,
            "variant": runtime_variant,
            "content": TRANSITION_MESSAGE,
            "meta": build_stage_transition_assistant_meta(
                gate_context=gate_context,
                decision=decision,
                rolling_summary=rolling_summary,
                key_points=key_points,
            ),
        },
    )

    stage_gate_ready_payload = None
    stage_value = gate_context.get("current_stage") or gate_context.get(
        "runtime_stage"
    )
    if stage_value and stage_gate_ready_for_review:
        context_version, context_updated_at = await fetch_context_meta(
            session,
            gate_context["project_id"],
            org_id,
        )
        stage_gate_ready_payload = build_stage_gate_ready_payload(
            gate_context=gate_context,
            stage=stage_value,
            context_version=context_version,
            context_updated_at=context_updated_at,
        )

    return TransitionTurnResult(
        assistant_content=TRANSITION_MESSAGE,
        stage_gate_ready_payload=stage_gate_ready_payload,
    )


async def commit_router_mode_next_turn(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    decision: dict[str, Any],
    chosen_mode: str | None,
    group_enabled: bool,
    group_max: int,
    transition_enabled: bool,
    planner_settings: dict[str, Any],
    planned_question_id: Any,
    planned_question_prompt: str | None,
    rolling_summary: str | None,
    key_points: list[str],
    request_id: str,
    turn_event_meta: dict[str, Any],
) -> NextQuestionTurnResult:
    bank_version_id = gate_context["bank_version_id"]
    if not bank_version_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project question bank is missing.",
        )
    chosen_mode = require_router_mode(chosen_mode)

    router_state_result = await session.execute(
        text(
            "UPDATE project_states "
            "SET state_json = jsonb_set("
            "COALESCE(state_json, '{}'::jsonb), "
            "'{tech_execution,meta,mode}', "
            "to_jsonb(CAST(:mode AS text))::jsonb, "
            "true"
            "), "
            "state_version = COALESCE(state_version, 0) + 1 "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "RETURNING state_version"
        ),
        {
            "mode": chosen_mode,
            "project_id": gate_context["project_id"],
            "org_id": org_id,
        },
    )
    router_state_row = router_state_result.mappings().first()
    if router_state_row:
        next_router_state_version = router_state_row.get("state_version") or 0
        await record_project_state_event(
            session,
            org_id=org_id,
            project_id=str(gate_context["project_id"]),
            question_instance_id=str(gate_context["current_question_instance_id"]),
            event_type="apply_patch",
            patch_json=build_router_mode_state_event_patch(mode=chosen_mode),
            actor_type="system",
            prev_state_version=next_router_state_version - 1,
            next_state_version=next_router_state_version,
            request_id=gate_context.get("request_id"),
        )

    await session.execute(
        text(
            "UPDATE projects "
            "SET current_variant = :variant, "
            "settings = COALESCE(settings, '{}'::jsonb) "
            "|| CAST(:settings AS jsonb), "
            "updated_at = now() "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "variant": chosen_mode,
            "settings": json.dumps({"tech_mode": chosen_mode}),
            "project_id": gate_context["project_id"],
            "org_id": org_id,
        },
    )

    current_question_id, next_question_id = await resolve_initial_questions(
        session,
        bank_version_id,
        "tech",
        chosen_mode,
    )
    missing_paths = await resolve_missing_paths(
        session,
        bank_version_id,
        "tech",
        chosen_mode,
    )

    await session.execute(
        text(
            "UPDATE project_runtime "
            "SET current_question_bank_question_id = :current_id, "
            "next_question_bank_question_id = :next_id, "
            "missing_paths = :missing_paths, "
            "variant = :variant, "
            "turn_state = 'updated', "
            "runtime_version = runtime_version + 1, "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "project_id": gate_context["project_id"],
            "current_id": current_question_id,
            "next_id": next_question_id,
            "missing_paths": missing_paths,
            "variant": chosen_mode,
        },
    )

    question_instance_id = await ensure_question_instance(
        session,
        gate_context["project_id"],
        current_question_id,
    )

    question_detail = await fetch_chat_question_detail(session, current_question_id)
    assistant_prompt = question_detail.get("prompt")
    if planned_question_prompt and planned_question_id == current_question_id:
        assistant_prompt = planned_question_prompt
    group_meta_payload = None
    group_question_ids: list[str] = []
    group_next_id = None
    grouped = False
    planner_used = False
    plan_meta = None

    if should_attempt_question_planner(
        planner_settings=planner_settings,
        stage="tech",
        question_detail=question_detail,
        missing_paths=missing_paths,
    ):
        plan_result = await resolve_question_group_plan(
            session,
            question_detail,
            assistant_prompt,
            missing_paths,
            gate_context.get("latest_answer"),
            output_locale=gate_context.get("output_locale", "en"),
            max_questions=planner_settings.get("max_questions", 1),
            max_schema=planner_settings.get("max_schema", 1),
            timeout_ms=planner_settings.get("timeout_ms", 1000),
            candidate_limit=planner_settings.get("candidate_limit", 12),
            min_candidates=planner_settings.get("min_candidates", 1),
            project_settings=gate_context.get("project_settings"),
            resolve_next_question_id=resolve_next_question_id,
        )
        if plan_result:
            planner_used = True
            grouped_detail, group_question_ids, group_next_id, plan_meta = plan_result
            question_detail = grouped_detail
            assistant_prompt = grouped_detail.get("prompt") or assistant_prompt
            grouped = len(group_question_ids) > 1

    if not planner_used and (
        group_enabled
        and group_max > 1
        and question_supports_grouping(question_detail)
    ):
        grouped_detail, group_question_ids, group_next_id = await resolve_question_group(
            session,
            question_detail,
            assistant_prompt,
            missing_paths,
            latest_answer=gate_context.get("latest_answer"),
            max_questions=group_max,
            fetch_question_detail=fetch_chat_question_detail,
            resolve_next_question_id=resolve_next_question_id,
        )
        if len(group_question_ids) > 1:
            grouped = True
            question_detail = grouped_detail
            assistant_prompt = grouped_detail.get("prompt") or assistant_prompt

    if not planner_used and (
        not grouped
        and transition_enabled
        and question_supports_grouping(question_detail)
    ):
        assistant_prompt = apply_transition_prefix(
            assistant_prompt,
            question_detail,
            gate_context.get("latest_answer"),
        )

    plan_id = None
    if planner_used and plan_meta:
        try:
            plan_id = await persist_question_plan(
                session,
                org_id=org_id,
                project_id=gate_context["project_id"],
                stage="tech",
                variant=chosen_mode,
                question_instance_id=question_instance_id,
                question_bank_question_ids=plan_meta.get("question_ids", []),
                question_codes=plan_meta.get("question_codes", []),
                schema_paths=question_detail.get("schema_paths") or [],
                prompt=assistant_prompt,
                model=plan_meta.get("model"),
                latency_ms=plan_meta.get("latency_ms"),
                meta=plan_meta,
            )
        except Exception:
            plan_id = None

    if planner_used and group_question_ids:
        group_meta_payload = build_question_group_payload(
            question_detail,
            group_question_ids,
            plan_id=plan_id,
        )
    elif grouped and group_question_ids:
        group_meta_payload = build_question_group_payload(
            question_detail,
            group_question_ids,
        )

    if group_next_id is not None and group_next_id != next_question_id:
        await session.execute(
            text(
                "UPDATE project_runtime "
                "SET next_question_bank_question_id = :next_id, "
                "updated_at = now() "
                "WHERE project_id = :project_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL"
            ),
            {
                "project_id": gate_context["project_id"],
                "next_id": group_next_id,
            },
        )
    assistant_meta = build_next_question_assistant_meta(
        gate_context=gate_context,
        question_detail=question_detail,
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
        group_meta_payload=group_meta_payload,
        planned_question_prompt=planned_question_prompt,
        planner_used=planner_used,
    )
    question_stream_context = await build_question_stream_context(
        session,
        project_id=gate_context["project_id"],
        org_id=org_id,
        stage="tech",
        variant=chosen_mode,
        question_instance_id=question_instance_id,
        question_detail=question_detail,
        fallback_content=assistant_prompt,
        meta=assistant_meta,
        output_locale=gate_context.get("output_locale", "en"),
        latest_answer=gate_context.get("latest_answer"),
        context_summary=gate_context.get("context_summary"),
        message_meta=gate_context.get("message_meta"),
        project_settings=gate_context.get("project_settings"),
        answer_evaluation_request_id=request_id,
    )
    question_stream_context.update(turn_event_meta)
    return build_next_question_turn_result(
        assistant_prompt=assistant_prompt,
        question_detail=question_detail,
        question_stream_context=question_stream_context,
    )


async def commit_standard_next_turn(
    session,
    *,
    org_id: str,
    gate_context: dict[str, Any],
    runtime_row: Any,
    runtime_stage: str | None,
    runtime_variant: str | None,
    next_question_id: Any,
    updated_missing_paths: list[str],
    state_json: dict[str, Any] | None,
    stage_status_ready: str | None,
    schema_paths: list[Any],
    decision: dict[str, Any],
    group_enabled: bool,
    group_max: int,
    transition_enabled: bool,
    planner_settings: dict[str, Any],
    planned_question_id: Any,
    planned_question_prompt: str | None,
    rolling_summary: str | None,
    key_points: list[str],
    request_id: str,
    turn_event_meta: dict[str, Any],
) -> StandardNextTurnResult:
    repair_question_id = None
    routing_state_json = resolve_routing_state_json(
        state_json=state_json,
        gate_context=gate_context,
    )
    routing_result = resolve_standard_question_routing(
        gate_context=gate_context,
        runtime_stage=runtime_stage,
        runtime_variant=runtime_variant,
        next_question_id=next_question_id,
        updated_missing_paths=updated_missing_paths,
        stage_status_ready=stage_status_ready,
    )
    stage_gate_ready_for_review = routing_result.stage_gate_ready_for_review
    next_question_id = routing_result.next_question_id
    updated_missing_paths = routing_result.updated_missing_paths
    if next_question_id:
        next_question_id = await resolve_askable_question_id(
            session,
            next_question_id,
            state_json=routing_state_json,
            missing_paths=updated_missing_paths,
            defer_schema_paths=schema_paths,
            skip_optional=True,
        )
    if not next_question_id and updated_missing_paths:
        bank_version_id = gate_context["bank_version_id"]
        if not bank_version_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Project question bank is missing.",
            )
        repair_question_id = await resolve_repair_question(
            session,
            bank_version_id,
            runtime_stage,
            runtime_variant,
            updated_missing_paths,
            gate_context["project_id"],
        )
        if not repair_question_id:
            repair_question_id = runtime_row.get("current_question_bank_question_id")

    if not next_question_id and not repair_question_id:
        transition_result = await commit_stage_transition_turn(
            session,
            org_id=org_id,
            gate_context=gate_context,
            runtime_stage=runtime_stage,
            runtime_variant=runtime_variant,
            decision=decision,
            rolling_summary=rolling_summary,
            key_points=key_points,
            stage_gate_ready_for_review=stage_gate_ready_for_review,
        )
        return StandardNextTurnResult(
            assistant_content=transition_result.assistant_content,
            question_meta_payload=None,
            question_stream_context=None,
            stage_gate_ready_payload=transition_result.stage_gate_ready_payload,
        )

    question_id = next_question_id or repair_question_id
    question_detail = await fetch_chat_question_detail(session, question_id)
    question_instance_id = await ensure_question_instance(
        session,
        gate_context["project_id"],
        question_id,
    )
    assistant_prompt = question_detail.get("prompt")
    if planned_question_prompt and planned_question_id == question_id:
        assistant_prompt = planned_question_prompt
    group_meta_payload = None
    group_question_ids: list[str] = []
    group_next_id = None
    grouped = False
    planner_used = False
    plan_meta = None
    allow_group = question_id == next_question_id

    if allow_group and should_attempt_question_planner(
        planner_settings=planner_settings,
        stage=runtime_stage,
        question_detail=question_detail,
        missing_paths=updated_missing_paths,
    ):
        plan_result = await resolve_question_group_plan(
            session,
            question_detail,
            assistant_prompt,
            updated_missing_paths,
            gate_context.get("latest_answer"),
            output_locale=gate_context.get("output_locale", "en"),
            max_questions=planner_settings.get("max_questions", 1),
            max_schema=planner_settings.get("max_schema", 1),
            timeout_ms=planner_settings.get("timeout_ms", 1000),
            candidate_limit=planner_settings.get("candidate_limit", 12),
            min_candidates=planner_settings.get("min_candidates", 1),
            resolve_next_question_id=resolve_next_question_id,
        )
        if plan_result:
            planner_used = True
            grouped_detail, group_question_ids, group_next_id, plan_meta = plan_result
            question_detail = grouped_detail
            assistant_prompt = grouped_detail.get("prompt") or assistant_prompt
            grouped = len(group_question_ids) > 1

    if not planner_used and (
        allow_group
        and group_enabled
        and group_max > 1
        and question_supports_grouping(question_detail)
    ):
        grouped_detail, group_question_ids, group_next_id = await resolve_question_group(
            session,
            question_detail,
            assistant_prompt,
            updated_missing_paths,
            latest_answer=gate_context.get("latest_answer"),
            max_questions=group_max,
            fetch_question_detail=fetch_chat_question_detail,
            resolve_next_question_id=resolve_next_question_id,
        )
        if len(group_question_ids) > 1:
            grouped = True
            question_detail = grouped_detail
            assistant_prompt = grouped_detail.get("prompt") or assistant_prompt

    if not planner_used and (
        not grouped
        and transition_enabled
        and question_supports_grouping(question_detail)
    ):
        assistant_prompt = apply_transition_prefix(
            assistant_prompt,
            question_detail,
            gate_context.get("latest_answer"),
        )

    plan_id = None
    if planner_used and plan_meta:
        try:
            plan_id = await persist_question_plan(
                session,
                org_id=org_id,
                project_id=gate_context["project_id"],
                stage=runtime_stage,
                variant=runtime_variant,
                question_instance_id=question_instance_id,
                question_bank_question_ids=plan_meta.get("question_ids", []),
                question_codes=plan_meta.get("question_codes", []),
                schema_paths=question_detail.get("schema_paths") or [],
                prompt=assistant_prompt,
                model=plan_meta.get("model"),
                latency_ms=plan_meta.get("latency_ms"),
                meta=plan_meta,
            )
        except Exception:
            plan_id = None

    if planner_used and group_question_ids:
        group_meta_payload = build_question_group_payload(
            question_detail,
            group_question_ids,
            plan_id=plan_id,
        )
    elif grouped and group_question_ids:
        group_meta_payload = build_question_group_payload(
            question_detail,
            group_question_ids,
        )

    assistant_meta = build_next_question_assistant_meta(
        gate_context=gate_context,
        question_detail=question_detail,
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
        group_meta_payload=group_meta_payload,
        planned_question_prompt=planned_question_prompt,
        planner_used=planner_used,
    )
    question_stream_context = await build_question_stream_context(
        session,
        project_id=gate_context["project_id"],
        org_id=org_id,
        stage=runtime_stage,
        variant=runtime_variant,
        question_instance_id=question_instance_id,
        question_detail=question_detail,
        fallback_content=assistant_prompt,
        meta=assistant_meta,
        output_locale=gate_context.get("output_locale", "en"),
        latest_answer=gate_context.get("latest_answer"),
        context_summary=gate_context.get("context_summary"),
        message_meta=gate_context.get("message_meta"),
        project_settings=gate_context.get("project_settings"),
        answer_evaluation_request_id=request_id,
    )
    question_stream_context.update(turn_event_meta)

    next_next_question_id = None
    if question_id == next_question_id:
        if planner_used:
            next_next_question_id = group_next_id
        elif grouped:
            next_next_question_id = group_next_id
        else:
            next_next_question_id = await resolve_next_question_id(
                session,
                question_detail,
                state_json=routing_state_json,
                missing_paths=updated_missing_paths,
                defer_schema_paths=schema_paths,
                skip_optional=True,
            )
    if next_next_question_id:
        next_next_question_id = await resolve_askable_question_id(
            session,
            next_next_question_id,
            state_json=routing_state_json,
            missing_paths=updated_missing_paths,
            defer_schema_paths=schema_paths,
            skip_optional=True,
        )
    await session.execute(
        text(
            "UPDATE project_runtime "
            "SET current_question_bank_question_id = :current_id, "
            "next_question_bank_question_id = :next_id, "
            "turn_state = 'updated', "
            "runtime_version = runtime_version + 1 "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "project_id": gate_context["project_id"],
            "current_id": question_id,
            "next_id": next_next_question_id,
        },
    )

    next_turn_result = build_next_question_turn_result(
        assistant_prompt=assistant_prompt,
        question_detail=question_detail,
        question_stream_context=question_stream_context,
    )
    return StandardNextTurnResult(
        assistant_content=next_turn_result.assistant_content,
        question_meta_payload=next_turn_result.question_meta_payload,
        question_stream_context=next_turn_result.question_stream_context,
        stage_gate_ready_payload=None,
    )
