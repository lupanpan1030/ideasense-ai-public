from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.background_jobs import normalize_background_job_status
from app.services.localization import DEFAULT_OUTPUT_LOCALE


STAGE_SUMMARY_JOB_TYPE = "stage_summary_v0"
STAGE_SUMMARY_PENDING_STATUSES = {"queued", "running"}
STAGE_SUMMARY_FAILED_STATUSES = {"failed", "cancelled"}


def stage_summary_job_idempotency_key(
    project_id: UUID | str,
    stage: str,
    context_version: int,
    output_locale: str,
) -> str:
    stage_key = stage.strip().lower()
    locale_key = output_locale.strip().lower() or DEFAULT_OUTPUT_LOCALE
    return f"stage-summary:{project_id}:{stage_key}:{context_version}:{locale_key}"


async def fetch_stage_summary_job(
    session,
    *,
    project_id: UUID,
    idempotency_key: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT id, status, last_error, created_at, updated_at, completed_at "
            "FROM background_jobs "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND job_type = :job_type "
            "AND idempotency_key = :idempotency_key "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {
            "project_id": str(project_id),
            "job_type": STAGE_SUMMARY_JOB_TYPE,
            "idempotency_key": idempotency_key,
        },
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def enqueue_stage_summary_job(
    session,
    *,
    project_id: UUID,
    stage: str,
    context_version: int,
    output_locale: str,
    retry: bool = False,
) -> dict[str, Any] | None:
    idempotency_key = stage_summary_job_idempotency_key(
        project_id,
        stage,
        context_version,
        output_locale,
    )
    existing_job = await fetch_stage_summary_job(
        session,
        project_id=project_id,
        idempotency_key=idempotency_key,
    )
    existing_status = normalize_background_job_status(
        existing_job.get("status") if existing_job else None
    )
    if existing_status in STAGE_SUMMARY_PENDING_STATUSES:
        return existing_job
    retryable_statuses = STAGE_SUMMARY_FAILED_STATUSES | {"succeeded"}
    if existing_status in STAGE_SUMMARY_FAILED_STATUSES and not retry:
        return existing_job
    if existing_status in retryable_statuses and retry and existing_job:
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
                "AND status IN ('failed','cancelled','succeeded') "
                "AND deleted_at IS NULL "
                "RETURNING id, status, last_error, created_at, updated_at, completed_at"
            ),
            {"job_id": existing_job.get("id")},
        )
        row = result.mappings().first()
        return dict(row) if row else existing_job
    if existing_job and existing_status == "succeeded":
        return existing_job

    await session.execute(
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
            "project_id": str(project_id),
            "job_type": STAGE_SUMMARY_JOB_TYPE,
            "idempotency_key": idempotency_key,
            "payload": {
                "project_id": str(project_id),
                "stage": stage,
                "context_version": context_version,
                "output_locale": output_locale,
            },
        },
    )
    return await fetch_stage_summary_job(
        session,
        project_id=project_id,
        idempotency_key=idempotency_key,
    )


__all__ = [
    "STAGE_SUMMARY_FAILED_STATUSES",
    "STAGE_SUMMARY_JOB_TYPE",
    "STAGE_SUMMARY_PENDING_STATUSES",
    "enqueue_stage_summary_job",
    "fetch_stage_summary_job",
    "stage_summary_job_idempotency_key",
]
