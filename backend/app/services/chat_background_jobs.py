from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.services.answer_extraction_jobs import (
    ANSWER_EXTRACTION_JOB_TYPE,
    enqueue_authoritative_answer_extraction_job,
)
from app.services.verification.config import (
    verification_enabled,
    verification_min_priority,
)
from app.services.verification.priority import (
    extract_verification_priority,
    priority_at_least,
)
from app.services.verification_jobs import (
    enqueue_answer_question_verification_job,
)


@dataclass(frozen=True)
class ChatBackgroundJobEnqueueResult:
    queued_extract_job: bool = False
    extract_queued_payload: dict[str, Any] | None = None
    latency_spans: dict[str, float] = field(default_factory=dict)


def should_enqueue_pass_answer_background_jobs(
    decision: dict[str, Any],
    *,
    skip_requested: bool,
    schema_paths: list[Any],
) -> bool:
    return (
        decision.get("final_verdict") == "pass"
        and not skip_requested
        and bool(schema_paths)
    )


def build_answer_extraction_queued_payload(
    *,
    turn_event_meta: dict[str, Any],
    extract_job_id: Any,
    question_instance_id: str,
) -> dict[str, Any]:
    return {
        **turn_event_meta,
        "job_type": ANSWER_EXTRACTION_JOB_TYPE,
        "extract_job_id": str(extract_job_id) if extract_job_id else None,
        "question_instance_id": question_instance_id,
    }


async def enqueue_chat_pass_background_jobs(
    session,
    *,
    decision: dict[str, Any],
    skip_requested: bool,
    schema_paths: list[Any],
    gate_context: dict[str, Any],
    turn_event_meta: dict[str, Any],
) -> ChatBackgroundJobEnqueueResult:
    if not should_enqueue_pass_answer_background_jobs(
        decision,
        skip_requested=skip_requested,
        schema_paths=schema_paths,
    ):
        return ChatBackgroundJobEnqueueResult()

    latencies: dict[str, float] = {}
    question_instance_id = str(gate_context["current_question_instance_id"])

    extract_job_started_at = time.perf_counter()
    extract_job_row = await enqueue_authoritative_answer_extraction_job(
        session,
        project_id=gate_context["project_id"],
        question_instance_id=question_instance_id,
        user_message_id=gate_context["user_message_id"],
        request_id=gate_context.get("request_id"),
        client_message_id=gate_context.get("client_message_id"),
    )
    latencies["db_commit.background_extract_job"] = (
        time.perf_counter() - extract_job_started_at
    )
    extract_job_id = extract_job_row.get("id") if extract_job_row else None
    extract_queued_payload = build_answer_extraction_queued_payload(
        turn_event_meta=turn_event_meta,
        extract_job_id=extract_job_id,
        question_instance_id=question_instance_id,
    )

    verification_priority = extract_verification_priority(
        gate_context.get("question_detail")
    )
    if verification_enabled() and priority_at_least(
        verification_priority,
        verification_min_priority(),
    ):
        verification_job_started_at = time.perf_counter()
        await enqueue_answer_question_verification_job(
            session,
            project_id=gate_context["project_id"],
            question_instance_id=question_instance_id,
            question_bank_question_id=str(gate_context["current_question_id"]),
            user_message_id=gate_context["user_message_id"],
            priority=verification_priority,
        )
        latencies["db_commit.background_verification_job"] = (
            time.perf_counter() - verification_job_started_at
        )

    return ChatBackgroundJobEnqueueResult(
        queued_extract_job=True,
        extract_queued_payload=extract_queued_payload,
        latency_spans=latencies,
    )
