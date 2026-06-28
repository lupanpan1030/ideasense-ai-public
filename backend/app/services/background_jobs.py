from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB


ALLOWED_REQUEUE_STATUSES = {"cancelled", "failed", "succeeded"}


def normalize_background_job_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def background_job_sort_time(job: dict[str, Any] | None) -> datetime | None:
    if not job:
        return None
    for key in ("completed_at", "updated_at", "created_at"):
        value = job.get(key)
        if isinstance(value, datetime):
            return value
    return None


def _status_list_sql(statuses: Iterable[str]) -> str:
    normalized: list[str] = []
    for status in statuses:
        if status not in ALLOWED_REQUEUE_STATUSES:
            raise ValueError(f"Unsupported background job requeue status: {status}")
        normalized.append(status)
    if not normalized:
        return "NULL"
    return ", ".join(f"'{status}'" for status in normalized)


async def enqueue_background_job(
    session,
    *,
    org_id: str,
    project_id: str,
    job_type: str,
    payload: dict[str, Any],
    idempotency_key: str,
    requeue_statuses: Iterable[str],
) -> dict[str, Any]:
    status_list_sql = _status_list_sql(requeue_statuses)
    result = await session.execute(
        text(
            "INSERT INTO background_jobs ("
            "org_id, project_id, job_type, status, payload, idempotency_key"
            ") VALUES ("
            ":org_id, :project_id, :job_type, 'queued', :payload, :idempotency_key"
            ") "
            "ON CONFLICT (org_id, job_type, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL "
            "DO UPDATE SET "
            "payload = EXCLUDED.payload, "
            "status = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN 'queued' "
            "ELSE background_jobs.status "
            "END, "
            "attempts = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN 0 "
            "ELSE background_jobs.attempts "
            "END, "
            "run_at = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN now() "
            "ELSE background_jobs.run_at "
            "END, "
            "locked_at = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.locked_at "
            "END, "
            "lock_expires_at = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.lock_expires_at "
            "END, "
            "locked_by = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.locked_by "
            "END, "
            "started_at = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.started_at "
            "END, "
            "completed_at = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.completed_at "
            "END, "
            "last_error = CASE "
            f"WHEN background_jobs.status IN ({status_list_sql}) THEN NULL "
            "ELSE background_jobs.last_error "
            "END, "
            "updated_at = now() "
            "RETURNING id, status, payload, last_error, created_at, updated_at, completed_at"
        ).bindparams(bindparam("payload", type_=JSONB)),
        {
            "org_id": org_id,
            "project_id": project_id,
            "job_type": job_type,
            "payload": payload,
            "idempotency_key": idempotency_key,
        },
    )
    row = result.mappings().first()
    return dict(row or {})


__all__ = [
    "background_job_sort_time",
    "enqueue_background_job",
    "normalize_background_job_status",
]
