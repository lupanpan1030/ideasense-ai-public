from dataclasses import dataclass
from typing import Any

from app.services.answer_meta import build_skip_answer_meta_note, set_answer_meta_entry
from app.services.chat_gate_resolution import mark_partial_unknown_paths
from app.services.chat_market_type_normalization import (
    canonicalize_extracted_value,
    canonicalize_market_type_fields,
)
from app.services.chat_question_filters import adjust_missing_paths_for_market
from app.services.chat_question_planning import build_question_meta_payload
from app.services.chat_stage_gate import (
    resolve_next_stage,
    should_enter_stage_gate_review,
)
from app.services.chat_sync_extraction_preview import update_ai_assisted_paths
from app.services.chat_turn_context import build_assistant_meta
from app.services.chat_turn_payloads import NextQuestionTurnResult
from app.services.context_backfill import backfill_problem_idea_raw
from app.services.context_paths import set_context_path_value
from app.services.extraction_transforms import extract_value_meta
from app.services.localization import DEFAULT_OUTPUT_LOCALE
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths


@dataclass(frozen=True)
class ProjectStatePayload:
    state_json: dict[str, Any]
    state_meta: dict[str, Any]
    pending_confirm: dict[str, Any]
    state_version: int
    has_existing_state: bool


@dataclass(frozen=True)
class ChatStatePatchResult:
    state_json: dict[str, Any]
    state_meta: dict[str, Any]
    pending_confirm: dict[str, Any]


@dataclass(frozen=True)
class RuntimeMissingPathsResult:
    updated_missing_paths: list[str]
    changed: bool


@dataclass(frozen=True)
class StandardQuestionRouting:
    stage_gate_ready_for_review: bool
    next_question_id: Any
    updated_missing_paths: list[str]


@dataclass(frozen=True)
class NeedsInfoAssistantMetaPayload:
    question_meta_payload: dict[str, Any] | None
    assistant_meta: dict[str, Any]


def build_skip_answer_status_meta(
    *,
    answer_action: str | None,
    skip_resolution_status: str | None,
    skip_reason: str | None,
) -> dict[str, Any]:
    return {
        "skip_mode": "soft",
        "answer_action": answer_action or "skip_soft",
        "resolution_status": skip_resolution_status,
        "skip_reason": skip_reason,
    }


def build_router_mode_state_event_patch(*, mode: str) -> dict[str, Any]:
    return {
        "source": "router_mode_selection",
        "stage": "tech",
        "variant": "router",
        "state_paths": ["tech_execution.meta.mode"],
        "mode": mode,
    }


def build_stage_gate_ready_payload(
    *,
    gate_context: dict[str, Any],
    stage: str | None,
    context_version: Any,
    context_updated_at: Any,
) -> dict[str, Any] | None:
    if not stage:
        return None
    payload = {
        "project_id": gate_context["project_id"],
        "stage": stage,
        "next_stage": resolve_next_stage(stage),
        "stage_status": "awaiting_confirm",
    }
    if context_version is not None:
        payload["context_version"] = context_version
    if context_updated_at:
        payload["context_updated_at"] = context_updated_at
    return payload


def resolve_routing_state_json(
    *,
    state_json: dict[str, Any] | None,
    gate_context: dict[str, Any],
) -> dict[str, Any] | None:
    if isinstance(state_json, dict):
        return state_json
    gate_state_json = gate_context.get("state_json")
    if isinstance(gate_state_json, dict):
        return gate_state_json
    return None


def should_update_chat_state_meta(
    *,
    extraction_updates: list[tuple[str, str, Any]],
    skip_requested: bool,
    schema_paths: list[Any],
    partial_unknown_paths: list[str],
) -> bool:
    return (
        bool(extraction_updates)
        or (skip_requested and bool(schema_paths))
        or bool(partial_unknown_paths)
    )


def normalize_project_state_payload(state_row: Any) -> ProjectStatePayload:
    state_json = state_row.get("state_json") if state_row else {}
    if not isinstance(state_json, dict):
        state_json = {}

    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}

    pending_confirm = state_meta.get("pending_confirm")
    if not isinstance(pending_confirm, dict):
        pending_confirm = {}

    return ProjectStatePayload(
        state_json=state_json,
        state_meta=state_meta,
        pending_confirm=pending_confirm,
        state_version=(state_row.get("state_version") if state_row else 0) or 0,
        has_existing_state=bool(state_row),
    )


def apply_chat_state_patch(
    *,
    gate_context: dict[str, Any],
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    pending_confirm: dict[str, Any],
    runtime_stage: str | None,
    resolved_paths: list[str],
    extraction_updates: list[tuple[str, str, Any]],
    schema_paths: list[Any],
    skip_requested: bool,
    skip_resolution_status: str | None,
    skip_reason: str | None,
    partial_unknown_paths: list[str],
) -> ChatStatePatchResult:
    if skip_requested:
        skip_note = build_skip_answer_meta_note(skip_resolution_status, skip_reason)
        for path in schema_paths:
            if not isinstance(path, str) or not path.strip():
                continue
            set_answer_meta_entry(
                state_meta,
                path,
                resolution_status=skip_resolution_status or "unknown",
                evidence_level="E0",
                source="user",
                note=skip_note,
            )

    if partial_unknown_paths:
        mark_partial_unknown_paths(state_meta, partial_unknown_paths)

    ai_assisted = bool(gate_context.get("ai_assisted"))
    for target, path, value in extraction_updates:
        default_source = "ai" if ai_assisted or target == "pending" else "user"
        value, meta_update = extract_value_meta(
            value,
            default_source=default_source,
        )
        value = canonicalize_extracted_value(path, value)
        if target == "state":
            set_context_path_value(state_json, path, value)
            set_answer_meta_entry(
                state_meta,
                path,
                **meta_update,
            )
        else:
            set_context_path_value(
                pending_confirm,
                path,
                {"value": value, **meta_update},
            )

    state_meta["pending_confirm"] = pending_confirm
    update_ai_assisted_paths(
        state_meta,
        resolved_paths,
        runtime_stage,
        ai_assisted,
    )
    backfill_problem_idea_raw(
        state_json,
        state_meta,
        source="ai" if ai_assisted else "user",
    )
    canonicalize_market_type_fields(state_json)

    return ChatStatePatchResult(
        state_json=state_json,
        state_meta=state_meta,
        pending_confirm=pending_confirm,
    )


def build_state_event_patch(
    *,
    runtime_stage: str | None,
    runtime_variant: str | None,
    resolved_paths: list[str],
    extraction_updates: list[tuple[str, str, Any]],
    skip_requested: bool,
    partial_unknown_paths: list[str],
) -> dict[str, Any]:
    return {
        "source": "chat_sync_extraction",
        "stage": runtime_stage,
        "variant": runtime_variant,
        "resolved_paths": resolved_paths,
        "state_paths": [
            path for target, path, _ in extraction_updates if target == "state"
        ],
        "pending_paths": [
            path for target, path, _ in extraction_updates if target != "state"
        ],
        "skip_requested": skip_requested,
        "partial_unknown_paths": partial_unknown_paths,
    }


def derive_updated_runtime_missing_paths(
    *,
    runtime_stage: str | None,
    runtime_variant: str | None,
    runtime_missing_paths: list[str],
    resolved_paths: list[str],
    skip_requested: bool,
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
) -> RuntimeMissingPathsResult:
    updated_missing_paths = runtime_missing_paths
    if resolved_paths or skip_requested:
        updated_missing_paths = [
            path for path in runtime_missing_paths if path not in resolved_paths
        ]
        updated_missing_paths = filter_stage_blocking_missing_paths(
            runtime_stage,
            updated_missing_paths,
            state_json=state_json,
            state_meta=state_meta,
        )
        if state_json and runtime_stage == "market":
            updated_missing_paths = adjust_missing_paths_for_market(
                state_json,
                updated_missing_paths,
                resolved_paths,
            )

    return RuntimeMissingPathsResult(
        updated_missing_paths=updated_missing_paths,
        changed=updated_missing_paths != runtime_missing_paths,
    )


def select_transition_state_payload(
    *,
    gate_context: dict[str, Any],
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    transition_state_json = (
        state_json
        if isinstance(state_json, dict)
        else (
            gate_context.get("state_json")
            if isinstance(gate_context.get("state_json"), dict)
            else {}
        )
    )
    transition_state_meta = (
        state_meta
        if isinstance(state_meta, dict)
        else (
            gate_context.get("state_meta")
            if isinstance(gate_context.get("state_meta"), dict)
            else {}
        )
    )
    return transition_state_json, transition_state_meta


def resolve_standard_question_routing(
    *,
    gate_context: dict[str, Any],
    runtime_stage: str | None,
    runtime_variant: str | None,
    next_question_id: Any,
    updated_missing_paths: list[str],
    stage_status_ready: str | None,
) -> StandardQuestionRouting:
    stage_gate_ready_for_review = should_enter_stage_gate_review(
        stage_status_ready=stage_status_ready,
        current_stage_status=gate_context.get("stage_status"),
        stage=runtime_stage,
        variant=runtime_variant,
        missing_paths=updated_missing_paths,
    )
    if stage_gate_ready_for_review:
        return StandardQuestionRouting(
            stage_gate_ready_for_review=True,
            next_question_id=None,
            updated_missing_paths=[],
        )
    return StandardQuestionRouting(
        stage_gate_ready_for_review=False,
        next_question_id=next_question_id,
        updated_missing_paths=updated_missing_paths,
    )


def build_needs_info_assistant_meta(
    *,
    gate_context: dict[str, Any],
    decision: dict[str, Any],
    rolling_summary: str | None,
    key_points: list[str],
) -> NeedsInfoAssistantMetaPayload:
    question_detail = gate_context.get("question_detail") or {}
    question_meta_payload = build_question_meta_payload(question_detail)
    assistant_meta = build_assistant_meta(
        base_meta={
            "schema_version": "v1",
            "question_id": question_detail.get("question_id"),
        },
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
        question_meta=question_meta_payload,
        content_locale=gate_context.get("output_locale", "en"),
    )
    return NeedsInfoAssistantMetaPayload(
        question_meta_payload=question_meta_payload,
        assistant_meta=assistant_meta,
    )


def build_stage_transition_assistant_meta(
    *,
    gate_context: dict[str, Any],
    decision: dict[str, Any],
    rolling_summary: str | None,
    key_points: list[str],
) -> dict[str, Any]:
    return build_assistant_meta(
        base_meta={"schema_version": "v1"},
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
        content_locale=gate_context.get("output_locale", "en"),
    )


def build_next_question_assistant_meta(
    *,
    gate_context: dict[str, Any],
    question_detail: dict[str, Any],
    decision: dict[str, Any],
    rolling_summary: str | None,
    key_points: list[str],
    group_meta_payload: dict[str, Any] | None,
    planned_question_prompt: str | None,
    planner_used: bool,
) -> dict[str, Any]:
    assistant_meta = build_assistant_meta(
        base_meta={
            "schema_version": "v1",
            "question_id": question_detail.get("question_id"),
        },
        decision=decision,
        rolling_summary=rolling_summary,
        key_points=key_points,
        question_meta=build_question_meta_payload(question_detail),
        content_locale=(
            gate_context.get("output_locale", "en")
            if planned_question_prompt or planner_used
            else DEFAULT_OUTPUT_LOCALE
        ),
    )
    if group_meta_payload:
        assistant_meta = {**assistant_meta, "question_group": group_meta_payload}
    return assistant_meta


def build_next_question_turn_result(
    *,
    assistant_prompt: str | None,
    question_detail: dict[str, Any],
    question_stream_context: dict[str, Any],
) -> NextQuestionTurnResult:
    return NextQuestionTurnResult(
        assistant_content=assistant_prompt,
        question_meta_payload=build_question_meta_payload(question_detail),
        question_stream_context=question_stream_context,
    )
