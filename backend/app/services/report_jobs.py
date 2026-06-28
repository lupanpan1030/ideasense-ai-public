from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.services.background_jobs import (
    enqueue_background_job,
    normalize_background_job_status,
)
from app.services.localization import DEFAULT_OUTPUT_LOCALE, normalize_output_locale


REPORT_GENERATION_JOB_TYPE = "report_generation_v0"
REPORT_PENDING_STATUSES = {"queued", "running"}
REPORT_FAILED_STATUSES = {"failed", "cancelled"}
REPORT_DEFAULT_NEXT_POLL_MS = 2000


def report_generation_idempotency_key(
    project_id: str,
    context_version: int,
    output_locale: str | None,
) -> str:
    locale = normalize_output_locale(output_locale)
    return f"report-generation:{project_id}:{context_version}:{locale}"


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _isoformat(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def build_ready_report_job_status(
    *,
    project_id: str,
    current_stage: Any,
    stage_status: Any,
    report_id: Any,
    report_version: Any,
    generated_at: Any,
    context_version: int,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "current_stage": current_stage,
        "stage_status": stage_status,
        "job_type": REPORT_GENERATION_JOB_TYPE,
        "status": "ready",
        "retryable": False,
        "report_id": str(report_id),
        "report_version": report_version,
        "generated_at": _isoformat(generated_at),
        "context_version": context_version,
        "next_poll_ms": 0,
    }


def build_queued_report_job_status(
    *,
    project_id: str,
    current_stage: Any,
    stage_status: Any,
    status: Any,
    context_version: int,
    next_poll_ms: int = REPORT_DEFAULT_NEXT_POLL_MS,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "current_stage": current_stage,
        "stage_status": stage_status,
        "job_type": REPORT_GENERATION_JOB_TYPE,
        "status": status or "queued",
        "retryable": False,
        "report_id": None,
        "report_version": None,
        "generated_at": None,
        "context_version": context_version,
        "next_poll_ms": next_poll_ms,
    }


async def enqueue_report_generation_job(
    session,
    *,
    org_id: str,
    project_id: str,
    context_version: int,
    output_locale: str | None,
    requested_by_user_id: str,
) -> dict[str, Any]:
    locale = normalize_output_locale(output_locale)
    idempotency_key = report_generation_idempotency_key(
        project_id,
        context_version,
        locale,
    )
    payload = {
        "project_id": project_id,
        "context_version": context_version,
        "output_locale": locale,
        "requested_by_user_id": requested_by_user_id,
        "mode": "finalize",
        "phase": "queued",
    }
    return await enqueue_background_job(
        session,
        org_id=org_id,
        project_id=project_id,
        job_type=REPORT_GENERATION_JOB_TYPE,
        payload=payload,
        idempotency_key=idempotency_key,
        requeue_statuses=("failed", "cancelled", "succeeded"),
    )


async def resolve_report_generation_status(
    session,
    *,
    project_id: str,
    output_locale: str | None = None,
) -> dict[str, Any]:
    locale = normalize_output_locale(output_locale)
    project_result = await session.execute(
        text(
            "SELECT p.id, p.current_stage, p.stage_status, ps.state_version "
            "FROM projects p "
            "LEFT JOIN project_states ps "
            "ON ps.project_id = p.id "
            "AND ps.org_id = p.org_id "
            "AND ps.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id},
    )
    project_row = project_result.mappings().first()
    if not project_row:
        return {
            "project_id": project_id,
            "current_stage": None,
            "stage_status": None,
            "job_type": None,
            "status": "not_started",
            "retryable": False,
            "report_id": None,
            "report_version": None,
            "generated_at": None,
            "context_version": None,
            "next_poll_ms": REPORT_DEFAULT_NEXT_POLL_MS,
        }

    context_version = int(project_row.get("state_version") or 0)
    report_result = await session.execute(
        text(
            "SELECT id, report_version, generated_from_state_version, created_at "
            "FROM project_reports "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "AND status = 'final' "
            "AND COALESCE(NULLIF(content_json->>'artifact_locale', ''), "
            ":default_output_locale) = :output_locale "
            "ORDER BY report_version DESC "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "output_locale": locale,
            "default_output_locale": DEFAULT_OUTPUT_LOCALE,
        },
    )
    report_row = report_result.mappings().first()
    if report_row:
        report_context_version = int(
            report_row.get("generated_from_state_version") or 0
        )
        if report_context_version == context_version:
            return build_ready_report_job_status(
                project_id=project_id,
                current_stage=project_row.get("current_stage"),
                stage_status=project_row.get("stage_status"),
                report_id=report_row.get("id"),
                report_version=report_row.get("report_version"),
                generated_at=report_row.get("created_at"),
                context_version=context_version,
            )

    job_result = await session.execute(
        text(
            "SELECT id, status, payload, last_error, created_at, updated_at, completed_at "
            "FROM background_jobs "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND job_type = :job_type "
            "AND COALESCE(NULLIF(payload->>'output_locale', ''), "
            ":default_output_locale) = :output_locale "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "job_type": REPORT_GENERATION_JOB_TYPE,
            "output_locale": locale,
            "default_output_locale": DEFAULT_OUTPUT_LOCALE,
        },
    )
    job_row = job_result.mappings().first()
    if not job_row:
        return {
            "project_id": project_id,
            "current_stage": project_row.get("current_stage"),
            "stage_status": project_row.get("stage_status"),
            "job_type": REPORT_GENERATION_JOB_TYPE,
            "status": "not_started",
            "retryable": True,
            "report_id": None,
            "report_version": None,
            "generated_at": None,
            "context_version": context_version,
            "next_poll_ms": REPORT_DEFAULT_NEXT_POLL_MS,
        }

    payload = job_row.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    job_context_version = _safe_int(payload.get("context_version"))
    if job_context_version is not None and job_context_version != context_version:
        status_value = "stale"
        retryable = True
    else:
        raw_status = normalize_background_job_status(job_row.get("status"))
        phase = payload.get("phase")
        if raw_status == "running" and phase == "finalizing":
            status_value = "finalizing"
        elif raw_status in REPORT_PENDING_STATUSES:
            status_value = raw_status
        elif raw_status in REPORT_FAILED_STATUSES:
            status_value = "failed"
        elif raw_status == "succeeded":
            status_value = "failed"
        else:
            status_value = "queued"
        retryable = status_value in {"failed", "stale", "not_started"}

    return {
        "project_id": project_id,
        "current_stage": project_row.get("current_stage"),
        "stage_status": project_row.get("stage_status"),
        "job_type": REPORT_GENERATION_JOB_TYPE,
        "status": status_value,
        "retryable": retryable,
        "report_id": str(report_row.get("id")) if report_row else None,
        "report_version": report_row.get("report_version") if report_row else None,
        "generated_at": _isoformat(report_row.get("created_at")) if report_row else None,
        "context_version": context_version,
        "next_poll_ms": 1500
        if status_value in {"running", "finalizing"}
        else REPORT_DEFAULT_NEXT_POLL_MS,
    }


def empty_report_status(project_id: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "current_stage": None,
        "stage_status": None,
        "job_type": REPORT_GENERATION_JOB_TYPE,
        "status": "not_started",
        "retryable": True,
        "report_id": None,
        "report_version": None,
        "generated_at": None,
        "context_version": None,
        "next_poll_ms": REPORT_DEFAULT_NEXT_POLL_MS,
    }
