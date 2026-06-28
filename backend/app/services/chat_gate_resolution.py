import time
from typing import Any

from app.services.answer_meta import set_answer_meta_entry
from app.services.chat_answer_actions import build_skip_decision
from app.services.chat_followup_compose import build_gate_decision
from app.services.chat_prompt_tasks import run_answer_gate_for_context
from app.services.chat_stream.latency import record_latency_span


async def resolve_gate_and_sync_extraction(
    gate_context: dict[str, Any],
    *,
    schema_paths: list[Any],
    skip_requested: bool,
    skip_reason: str | None,
    skip_resolution_status: str | None,
    latency_spans: dict[str, float] | None = None,
) -> tuple[dict[str, Any], str | None, dict[str, Any], bool, dict[str, Any]]:
    prompt_task_traces: dict[str, Any] = {}

    if skip_requested:
        decision = build_skip_decision(
            skip_reason,
            resolution_status=skip_resolution_status,
        )
        gate_model = "system"
    else:
        gate_started_at = time.perf_counter()
        try:
            gate_result, gate_model, gate_trace = await run_answer_gate_for_context(
                gate_context
            )
        finally:
            record_latency_span(latency_spans, "answer_gate", gate_started_at)
        if gate_trace:
            prompt_task_traces["answer_gate"] = gate_trace
        decision = build_gate_decision(
            gate_context["question_detail"],
            gate_context["gate_answer_text"],
            gate_result,
            gate_context.get("latest_answer"),
        )

    return (
        decision,
        gate_model,
        {},
        False,
        prompt_task_traces,
    )


def mark_partial_unknown_paths(
    state_meta: dict[str, Any],
    paths: list[str],
    *,
    note: str | None = None,
) -> None:
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            continue
        set_answer_meta_entry(
            state_meta,
            path,
            resolution_status="unknown",
            evidence_level="E0",
            source="user",
            note=note
            or "Advanced after repeated follow-up; field remains unknown.",
        )
