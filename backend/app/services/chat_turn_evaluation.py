from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.services.answer_meta import set_answer_meta_entry
from app.services.chat_followup_compose import (
    apply_repeated_followup_cap,
    build_followup_message,
    focus_followup_on_unresolved_paths,
)
from app.services.chat_gate_resolution import (
    mark_partial_unknown_paths,
    resolve_gate_and_sync_extraction,
)
from app.services.chat_output_locale import resolve_followup_output_locale
from app.services.chat_router_mode import apply_router_mode_selection_guard
from app.services.chat_sync_extraction_preview import (
    build_sync_extraction_preview,
    infer_frequency_from_answer,
)
from app.services.chat_turn_context import collect_key_points
from app.services.context_paths import set_context_path_value
from app.services.extraction_transforms import get_nested_state_value, is_non_empty


@dataclass(frozen=True)
class ChatTurnEvaluation:
    decision: dict[str, Any]
    gate_model: str | None
    extracted_payload: dict[str, Any]
    resolved_paths: list[str]
    extraction_updates: list[tuple[str, str, Any]]
    schema_paths: list[Any]
    partial_unknown_paths: list[str]
    followup_message: str
    prompt_task_traces: dict[str, Any]
    rolling_summary: str | None
    key_points: list[str]
    chosen_mode: str | None
    gate_context: dict[str, Any]


async def evaluate_chat_turn(
    gate_context: dict[str, Any],
    *,
    previous_answer_count: int,
    skip_requested: bool,
    skip_reason: str | None,
    skip_resolution_status: str | None,
    latency_spans: dict[str, float] | None = None,
) -> ChatTurnEvaluation:
    schema_paths = gate_context["question_detail"].get("schema_paths") or []
    if not isinstance(schema_paths, list):
        schema_paths = list(schema_paths)

    (
        decision,
        gate_model,
        extracted_payload,
        _did_sync_extract,
        prompt_task_traces,
    ) = await resolve_gate_and_sync_extraction(
        gate_context,
        schema_paths=schema_paths,
        skip_requested=skip_requested,
        skip_reason=skip_reason,
        skip_resolution_status=skip_resolution_status,
        latency_spans=latency_spans,
    )

    preview_resolved_paths: list[str] = []
    preview_extraction_updates: list[tuple[str, str, Any]] = []
    preview_state_json = gate_context.get("state_json")
    preview_state_meta = gate_context.get("state_meta")
    if not skip_requested and schema_paths:
        (
            preview_resolved_paths,
            preview_extraction_updates,
            preview_state_json,
            preview_state_meta,
        ) = build_sync_extraction_preview(
            gate_context["question_detail"],
            extracted_payload,
            current_stage=gate_context["runtime_stage"],
            answer=gate_context["extraction_answer_text"],
            latest_answer=gate_context.get("latest_answer"),
            state_json=gate_context.get("state_json"),
            state_meta=gate_context.get("state_meta"),
            ai_assisted=bool(gate_context.get("ai_assisted")),
        )

    partial_unknown_paths: list[str] = []
    if decision["final_verdict"] != "pass" and not skip_requested:
        decision, partial_unknown_paths = apply_repeated_followup_cap(
            decision,
            gate_context["question_detail"],
            gate_context.get("latest_answer") or gate_context["gate_answer_text"],
            schema_paths=schema_paths,
            resolved_paths=preview_resolved_paths,
            previous_answer_count=previous_answer_count,
        )
    if (
        decision["final_verdict"] != "pass"
        and not skip_requested
        and preview_resolved_paths
    ):
        decision = focus_followup_on_unresolved_paths(
            decision,
            schema_paths=schema_paths,
            resolved_paths=preview_resolved_paths,
        )

    resolved_paths: list[str] = []
    extraction_updates: list[tuple[str, str, Any]] = []
    if decision["final_verdict"] == "pass" and not skip_requested and schema_paths:
        resolved_paths = list(preview_resolved_paths)
        extraction_updates = list(preview_extraction_updates)
        if partial_unknown_paths:
            preview_state_meta = (
                deepcopy(preview_state_meta)
                if isinstance(preview_state_meta, dict)
                else {}
            )
            mark_partial_unknown_paths(preview_state_meta, partial_unknown_paths)
            for path in partial_unknown_paths:
                if path not in resolved_paths:
                    resolved_paths.append(path)
        gate_context = {
            **gate_context,
            "state_json": preview_state_json,
            "state_meta": preview_state_meta,
        }

    followup_message = ""
    if decision["final_verdict"] != "pass":
        followup_output_locale = resolve_followup_output_locale(
            gate_context.get("latest_answer"),
            gate_context.get("output_locale", "en"),
            context_summary=gate_context.get("context_summary"),
            message_meta=gate_context.get("message_meta"),
        )
        followup_message = build_followup_message(
            gate_context["question_detail"],
            decision,
            gate_context.get("latest_answer"),
            output_locale=followup_output_locale,
        )

    if (
        decision["final_verdict"] == "pass"
        and gate_context["question_detail"].get("question_id") == "S1Q5"
    ):
        heuristic_state_json = (
            deepcopy(gate_context.get("state_json"))
            if isinstance(gate_context.get("state_json"), dict)
            else {}
        )
        heuristic_state_meta = (
            deepcopy(gate_context.get("state_meta"))
            if isinstance(gate_context.get("state_meta"), dict)
            else {}
        )
        existing_frequency = get_nested_state_value(
            heuristic_state_json, ["problem", "frequency"]
        )
        if not is_non_empty(existing_frequency):
            inferred_frequency = infer_frequency_from_answer(
                gate_context["extraction_answer_text"]
            )
            if inferred_frequency:
                frequency_path = "problem.frequency"
                if frequency_path not in resolved_paths:
                    resolved_paths.append(frequency_path)
                if not any(
                    target == "state" and path == frequency_path
                    for target, path, _value in extraction_updates
                ):
                    extraction_updates.append(
                        ("state", frequency_path, inferred_frequency)
                    )
                set_context_path_value(
                    heuristic_state_json,
                    frequency_path,
                    inferred_frequency,
                )
                set_answer_meta_entry(
                    heuristic_state_meta,
                    frequency_path,
                    resolution_status="answered",
                    claim_type="hypothesis",
                    evidence_level="E1",
                    source="ai" if bool(gate_context.get("ai_assisted")) else "user",
                )
                gate_context = {
                    **gate_context,
                    "state_json": heuristic_state_json,
                    "state_meta": heuristic_state_meta,
                }

    rolling_summary = gate_context.get("context_summary")
    key_points = collect_key_points(extracted_payload)

    chosen_mode = None
    if (
        decision["final_verdict"] == "pass"
        and gate_context["runtime_stage"] == "tech"
        and gate_context["runtime_variant"] == "router"
    ):
        decision, chosen_mode, router_followup_message = (
            apply_router_mode_selection_guard(
                gate_context["question_detail"],
                decision,
                state_json=gate_context.get("router_state_json"),
                message_meta=gate_context.get("message_meta"),
                latest_answer=gate_context.get("latest_answer"),
                output_locale=gate_context.get("output_locale", "en"),
            )
        )
        if router_followup_message:
            followup_message = router_followup_message

    return ChatTurnEvaluation(
        decision=decision,
        gate_model=gate_model,
        extracted_payload=extracted_payload,
        resolved_paths=resolved_paths,
        extraction_updates=extraction_updates,
        schema_paths=schema_paths,
        partial_unknown_paths=partial_unknown_paths,
        followup_message=followup_message,
        prompt_task_traces=prompt_task_traces,
        rolling_summary=rolling_summary,
        key_points=key_points,
        chosen_mode=chosen_mode,
        gate_context=gate_context,
    )
