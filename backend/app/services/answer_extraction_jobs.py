from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB


ANSWER_EXTRACTION_JOB_TYPE = "extract_answer_v0"


def answer_extraction_job_idempotency_key(
    question_instance_id: str,
    user_message_id: int | str,
) -> str:
    return f"extract-answer:{question_instance_id}:{user_message_id}"


async def enqueue_authoritative_answer_extraction_job(
    session,
    *,
    project_id: str,
    question_instance_id: str,
    user_message_id: int | str,
    request_id: str | None,
    client_message_id: Any,
) -> dict[str, Any]:
    idempotency_key = answer_extraction_job_idempotency_key(
        question_instance_id,
        user_message_id,
    )
    message_id = int(user_message_id)
    result = await session.execute(
        text(
            "WITH inserted AS ("
            "INSERT INTO background_jobs ("
            "org_id, project_id, job_type, status, payload, idempotency_key"
            ") VALUES ("
            "app_org_id(), :project_id, :job_type, 'queued', :payload, :idempotency_key"
            ") "
            "ON CONFLICT (org_id, job_type, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL "
            "DO NOTHING "
            "RETURNING id"
            ") "
            "SELECT id FROM inserted "
            "UNION ALL "
            "SELECT id FROM background_jobs "
            "WHERE org_id = app_org_id() "
            "AND project_id = :project_id "
            "AND job_type = :job_type "
            "AND idempotency_key = :idempotency_key "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ).bindparams(bindparam("payload", type_=JSONB)),
        {
            "project_id": project_id,
            "job_type": ANSWER_EXTRACTION_JOB_TYPE,
            "idempotency_key": idempotency_key,
            "payload": {
                "project_id": project_id,
                "question_instance_id": question_instance_id,
                "message_id": message_id,
                "source_message_id": message_id,
                "request_id": request_id,
                "client_message_id": client_message_id,
                "trigger": "authoritative_extract",
            },
        },
    )
    row = result.mappings().first()
    return dict(row or {})


__all__ = [
    "ANSWER_EXTRACTION_JOB_TYPE",
    "answer_extraction_job_idempotency_key",
    "enqueue_authoritative_answer_extraction_job",
]
