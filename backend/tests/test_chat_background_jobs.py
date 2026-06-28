import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.answer_extraction_jobs import ANSWER_EXTRACTION_JOB_TYPE
from app.services.chat_background_jobs import (
    build_answer_extraction_queued_payload,
    enqueue_chat_pass_background_jobs,
    should_enqueue_pass_answer_background_jobs,
)


def test_should_enqueue_pass_answer_background_jobs_requires_pass() -> None:
    assert should_enqueue_pass_answer_background_jobs(
        {"final_verdict": "pass"},
        skip_requested=False,
        schema_paths=["problem.one_line"],
    )
    assert not should_enqueue_pass_answer_background_jobs(
        {"final_verdict": "needs_info"},
        skip_requested=False,
        schema_paths=["problem.one_line"],
    )
    assert not should_enqueue_pass_answer_background_jobs(
        {"final_verdict": "pass"},
        skip_requested=True,
        schema_paths=["problem.one_line"],
    )
    assert not should_enqueue_pass_answer_background_jobs(
        {"final_verdict": "pass"},
        skip_requested=False,
        schema_paths=[],
    )


def test_build_answer_extraction_queued_payload_preserves_turn_meta() -> None:
    payload = build_answer_extraction_queued_payload(
        turn_event_meta={"project_id": "project-1", "request_id": "req-1"},
        extract_job_id=uuid4(),
        question_instance_id="question-instance-1",
    )

    assert payload["project_id"] == "project-1"
    assert payload["request_id"] == "req-1"
    assert payload["job_type"] == ANSWER_EXTRACTION_JOB_TYPE
    assert payload["extract_job_id"]
    assert payload["question_instance_id"] == "question-instance-1"


def test_enqueue_chat_pass_background_jobs_enqueues_extract_and_verification() -> None:
    extract_job_id = uuid4()
    session = object()
    enqueue_extract = AsyncMock(return_value={"id": extract_job_id})
    enqueue_verification = AsyncMock(return_value={"id": uuid4()})
    gate_context = {
        "project_id": uuid4(),
        "current_question_instance_id": uuid4(),
        "current_question_id": uuid4(),
        "user_message_id": uuid4(),
        "request_id": "req-1",
        "client_message_id": uuid4(),
        "question_detail": {"verification_priority": "high"},
    }

    with (
        patch(
            "app.services.chat_background_jobs.enqueue_authoritative_answer_extraction_job",
            enqueue_extract,
        ),
        patch(
            "app.services.chat_background_jobs.enqueue_answer_question_verification_job",
            enqueue_verification,
        ),
        patch("app.services.chat_background_jobs.verification_enabled", return_value=True),
        patch(
            "app.services.chat_background_jobs.verification_min_priority",
            return_value="low",
        ),
        patch(
            "app.services.chat_background_jobs.extract_verification_priority",
            return_value="high",
        ),
        patch("app.services.chat_background_jobs.priority_at_least", return_value=True),
    ):
        result = asyncio.run(
            enqueue_chat_pass_background_jobs(
                session,
                decision={"final_verdict": "pass"},
                skip_requested=False,
                schema_paths=["problem.one_line"],
                gate_context=gate_context,
                turn_event_meta={"project_id": str(gate_context["project_id"])},
            )
        )

    assert result.queued_extract_job
    assert result.extract_queued_payload == {
        "project_id": str(gate_context["project_id"]),
        "job_type": ANSWER_EXTRACTION_JOB_TYPE,
        "extract_job_id": str(extract_job_id),
        "question_instance_id": str(gate_context["current_question_instance_id"]),
    }
    assert set(result.latency_spans) == {
        "db_commit.background_extract_job",
        "db_commit.background_verification_job",
    }
    enqueue_extract.assert_awaited_once_with(
        session,
        project_id=gate_context["project_id"],
        question_instance_id=str(gate_context["current_question_instance_id"]),
        user_message_id=gate_context["user_message_id"],
        request_id="req-1",
        client_message_id=gate_context["client_message_id"],
    )
    enqueue_verification.assert_awaited_once_with(
        session,
        project_id=gate_context["project_id"],
        question_instance_id=str(gate_context["current_question_instance_id"]),
        question_bank_question_id=str(gate_context["current_question_id"]),
        user_message_id=gate_context["user_message_id"],
        priority="high",
    )


def test_enqueue_chat_pass_background_jobs_skips_when_not_applicable() -> None:
    enqueue_extract = AsyncMock()

    with patch(
        "app.services.chat_background_jobs.enqueue_authoritative_answer_extraction_job",
        enqueue_extract,
    ):
        result = asyncio.run(
            enqueue_chat_pass_background_jobs(
                object(),
                decision={"final_verdict": "pass"},
                skip_requested=True,
                schema_paths=["problem.one_line"],
                gate_context={},
                turn_event_meta={},
            )
        )

    assert not result.queued_extract_job
    assert result.extract_queued_payload is None
    assert result.latency_spans == {}
    enqueue_extract.assert_not_awaited()


def test_enqueue_chat_pass_background_jobs_respects_verification_threshold() -> None:
    enqueue_extract = AsyncMock(return_value={"id": uuid4()})
    enqueue_verification = AsyncMock()
    gate_context = {
        "project_id": uuid4(),
        "current_question_instance_id": uuid4(),
        "current_question_id": uuid4(),
        "user_message_id": uuid4(),
        "question_detail": {"verification_priority": "low"},
    }

    with (
        patch(
            "app.services.chat_background_jobs.enqueue_authoritative_answer_extraction_job",
            enqueue_extract,
        ),
        patch(
            "app.services.chat_background_jobs.enqueue_answer_question_verification_job",
            enqueue_verification,
        ),
        patch("app.services.chat_background_jobs.verification_enabled", return_value=True),
        patch(
            "app.services.chat_background_jobs.extract_verification_priority",
            return_value="low",
        ),
        patch("app.services.chat_background_jobs.priority_at_least", return_value=False),
    ):
        result = asyncio.run(
            enqueue_chat_pass_background_jobs(
                object(),
                decision={"final_verdict": "pass"},
                skip_requested=False,
                schema_paths=["problem.one_line"],
                gate_context=gate_context,
                turn_event_meta={},
            )
        )

    assert result.queued_extract_job
    assert set(result.latency_spans) == {"db_commit.background_extract_job"}
    enqueue_verification.assert_not_awaited()
