from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB


VERIFY_QUESTION_CLAIMS_JOB_TYPE = "verify_question_claims_v0"


def answer_verification_job_idempotency_key(
    question_instance_id: str,
    user_message_id: int | str,
) -> str:
    return f"verify-question:{question_instance_id}:{user_message_id}"


def summary_verification_job_idempotency_key(
    question_instance_id: str,
    answered_at: datetime | str | None,
) -> str:
    return f"verify-question:{question_instance_id}:{answered_at}"


async def _enqueue_question_verification_job(
    session,
    *,
    project_id: str,
    question_instance_id: str,
    question_bank_question_id: str,
    priority: str | None,
    trigger: str,
    idempotency_key: str,
) -> bool:
    result = await session.execute(
        text(
            "INSERT INTO background_jobs ("
            "org_id, project_id, job_type, status, payload, idempotency_key"
            ") VALUES ("
            "app_org_id(), :project_id, :job_type, 'queued', :payload, :idempotency_key"
            ") "
            "ON CONFLICT (org_id, job_type, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL "
            "DO NOTHING"
        ).bindparams(bindparam("payload", type_=JSONB)),
        {
            "project_id": project_id,
            "job_type": VERIFY_QUESTION_CLAIMS_JOB_TYPE,
            "idempotency_key": idempotency_key,
            "payload": {
                "project_id": project_id,
                "question_instance_id": question_instance_id,
                "question_bank_question_id": question_bank_question_id,
                "priority": priority,
                "trigger": trigger,
            },
        },
    )
    return bool(result.rowcount)


async def enqueue_answer_question_verification_job(
    session,
    *,
    project_id: str,
    question_instance_id: str,
    question_bank_question_id: str,
    user_message_id: int | str,
    priority: str | None,
) -> bool:
    return await _enqueue_question_verification_job(
        session,
        project_id=project_id,
        question_instance_id=question_instance_id,
        question_bank_question_id=question_bank_question_id,
        priority=priority,
        trigger="answer",
        idempotency_key=answer_verification_job_idempotency_key(
            question_instance_id,
            user_message_id,
        ),
    )


async def enqueue_summary_question_verification_job(
    session,
    *,
    project_id: str,
    question_instance_id: str,
    question_bank_question_id: str,
    answered_at: datetime | str | None,
    priority: str | None,
) -> bool:
    return await _enqueue_question_verification_job(
        session,
        project_id=project_id,
        question_instance_id=question_instance_id,
        question_bank_question_id=question_bank_question_id,
        priority=priority,
        trigger="summary",
        idempotency_key=summary_verification_job_idempotency_key(
            question_instance_id,
            answered_at,
        ),
    )


async def requeue_question_verification_job(
    session,
    *,
    job_id: Any,
) -> bool:
    result = await session.execute(
        text(
            "UPDATE background_jobs "
            "SET status = 'queued', "
            "attempts = 0, "
            "run_at = now(), "
            "locked_at = NULL, "
            "lock_expires_at = NULL, "
            "locked_by = NULL, "
            "last_error = NULL, "
            "updated_at = now() "
            "WHERE id = :job_id "
            "AND org_id = app_org_id() "
            "AND status IN ('failed','cancelled') "
            "AND deleted_at IS NULL"
        ),
        {"job_id": job_id},
    )
    return bool(result.rowcount)


__all__ = [
    "VERIFY_QUESTION_CLAIMS_JOB_TYPE",
    "answer_verification_job_idempotency_key",
    "enqueue_answer_question_verification_job",
    "enqueue_summary_question_verification_job",
    "requeue_question_verification_job",
    "summary_verification_job_idempotency_key",
]
