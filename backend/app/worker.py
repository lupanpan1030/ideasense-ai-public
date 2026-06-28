# ruff: noqa: E402
import asyncio
import json
import logging
import os
import uuid
from typing import Any

from app.core.env import load_backend_env, require_dev_flags_disabled_in_production

load_backend_env()
require_dev_flags_disabled_in_production()

from sqlalchemy import text

from app.core.database_async import AdminAsyncSessionLocal
from app.services.report_jobs import REPORT_GENERATION_JOB_TYPE
from app.services.stage_finalize_jobs import STAGE_FINALIZE_JOB_TYPE
from app.services.stage_summary_jobs import STAGE_SUMMARY_JOB_TYPE
from app.services.answer_extraction_worker_handler import run_extract_answer_v0
from app.services.report_generation_worker_handler import run_report_generation_v0
from app.services.stage_finalize_worker_handler import run_stage_finalize_v0
from app.services.stage_summary_worker_handler import run_stage_summary_v0
from app.services.verification_job_handler import (
    run_verify_question_claims_v0,
)

POLL_INTERVAL_SEC = float(os.getenv("WORKER_POLL_INTERVAL_SEC", "2"))
LOCK_TTL_SEC = int(os.getenv("WORKER_LOCK_TTL_SEC", "60"))
REPORT_LOCK_TTL_SEC = int(
    os.getenv("WORKER_REPORT_LOCK_TTL_SEC", str(max(LOCK_TTL_SEC, 300)))
)

WORKER_ID = os.getenv("WORKER_ID") or f"worker-{uuid.uuid4()}"
logger = logging.getLogger("ideasense.worker")

async def _process_job(job_row: dict[str, Any]) -> None:
    if AdminAsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL_ADMIN is required for worker.")

    job_type = job_row.get("job_type")
    job_org_id = str(job_row.get("org_id")) if job_row.get("org_id") else None
    if job_org_id is None:
        raise ValueError("Worker job missing org_id.")
    payload = job_row.get("payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("Job payload must be a JSON object.")

    async with AdminAsyncSessionLocal() as session:
        handler = _worker_job_handlers().get(job_type)
        if handler is None:
            raise ValueError(f"Unsupported job type: {job_type}")
        await handler(session, payload, job_row)


async def _process_extract_answer_job(
    session,
    payload: dict[str, Any],
    job_row: dict[str, Any],
) -> None:
    await run_extract_answer_v0(
        session,
        payload,
        job_org_id=str(job_row["org_id"]),
        set_worker_context_fn=_set_worker_context,
    )


async def _process_stage_summary_job(
    session,
    payload: dict[str, Any],
    job_row: dict[str, Any],
) -> None:
    await run_stage_summary_v0(
        session,
        payload,
        job_org_id=str(job_row["org_id"]),
        set_worker_context_fn=_set_worker_context,
    )


async def _process_stage_finalize_job(
    session,
    payload: dict[str, Any],
    job_row: dict[str, Any],
) -> None:
    await run_stage_finalize_v0(
        session,
        payload,
        job_org_id=str(job_row["org_id"]),
        set_worker_context_fn=_set_worker_context,
    )


async def _process_verify_question_claims_job(
    session,
    payload: dict[str, Any],
    job_row: dict[str, Any],
) -> None:
    await run_verify_question_claims_v0(
        session,
        payload,
        job_org_id=str(job_row["org_id"]),
        set_worker_context_fn=_set_worker_context,
    )


async def _process_report_generation_job(
    session,
    payload: dict[str, Any],
    job_row: dict[str, Any],
) -> None:
    await run_report_generation_v0(
        session,
        payload,
        job_id=job_row.get("id"),
        job_org_id=str(job_row["org_id"]),
        set_worker_context_fn=_set_worker_context,
    )


def _worker_job_handlers() -> dict[str, Any]:
    return {
        "extract_answer_v0": _process_extract_answer_job,
        STAGE_SUMMARY_JOB_TYPE: _process_stage_summary_job,
        "stage_summary_v0": _process_stage_summary_job,
        STAGE_FINALIZE_JOB_TYPE: _process_stage_finalize_job,
        "verify_question_claims_v0": _process_verify_question_claims_job,
        REPORT_GENERATION_JOB_TYPE: _process_report_generation_job,
    }


async def _set_worker_context(session, org_id: str | None = None) -> None:
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )
    if org_id:
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )


async def _claim_job(session) -> dict[str, Any] | None:
    await _set_worker_context(session)
    result = await session.execute(
        text(
            "SELECT id, org_id, project_id, job_type, payload, attempts, max_attempts "
            "FROM background_jobs "
            "WHERE status = 'queued' "
            "AND run_at <= now() "
            "AND deleted_at IS NULL "
            "ORDER BY priority ASC, run_at ASC, id ASC "
            "FOR UPDATE SKIP LOCKED "
            "LIMIT 1"
        )
    )
    job_row = result.mappings().first()
    if not job_row:
        return None

    if job_row.get("attempts", 0) >= job_row.get("max_attempts", 0):
        await session.execute(
            text(
                "UPDATE background_jobs "
                "SET status = 'failed', last_error = :error_message "
                "WHERE id = :job_id"
            ),
            {
                "job_id": job_row.get("id"),
                "error_message": "Max attempts exceeded.",
            },
        )
        return None

    org_id = job_row.get("org_id")
    if org_id:
        await _set_worker_context(session, str(org_id))
    await session.execute(
        text(
            "UPDATE background_jobs "
            "SET status = 'running', "
            "attempts = attempts + 1, "
            "locked_at = now(), "
            "lock_expires_at = now() + (:lock_ttl * interval '1 second'), "
            "locked_by = :worker_id "
            "WHERE id = :job_id"
        ),
        {
            "job_id": job_row.get("id"),
            "lock_ttl": REPORT_LOCK_TTL_SEC
            if job_row.get("job_type")
            in {REPORT_GENERATION_JOB_TYPE, STAGE_FINALIZE_JOB_TYPE}
            else LOCK_TTL_SEC,
            "worker_id": WORKER_ID,
        },
    )
    return job_row


async def _reset_expired_locks(session) -> None:
    await _set_worker_context(session)
    orgs_result = await session.execute(
        text(
            "SELECT DISTINCT org_id "
            "FROM background_jobs "
            "WHERE status = 'running' "
            "AND lock_expires_at IS NOT NULL "
            "AND lock_expires_at < now() "
            "AND deleted_at IS NULL"
        )
    )
    org_ids = [row[0] for row in orgs_result.fetchall() if row[0]]
    for org_id in org_ids:
        await _set_worker_context(session, str(org_id))
        await session.execute(
            text(
                "UPDATE background_jobs "
                "SET status = 'queued', "
                "locked_at = NULL, "
                "lock_expires_at = NULL, "
                "locked_by = NULL "
                "WHERE status = 'running' "
                "AND lock_expires_at IS NOT NULL "
                "AND lock_expires_at < now() "
                "AND deleted_at IS NULL "
                "AND org_id = :org_id"
            ),
            {"org_id": org_id},
        )


async def _finalize_job(
    job_id: int,
    status: str,
    error_message: str | None,
    org_id: str | None,
) -> None:
    if AdminAsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL_ADMIN is required for worker.")

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            await _set_worker_context(session, org_id)
            await session.execute(
                text(
                    "UPDATE background_jobs "
                    "SET status = :status, "
                    "last_error = :error_message, "
                    "completed_at = CASE "
                    "WHEN :status IN ('succeeded','failed','cancelled') THEN now() "
                    "ELSE completed_at END, "
                    "locked_at = NULL, "
                    "lock_expires_at = NULL, "
                    "locked_by = NULL "
                    "WHERE id = :job_id "
                    "AND org_id = :org_id"
                ),
                {
                    "job_id": job_id,
                    "status": status,
                    "error_message": error_message,
                    "org_id": org_id,
                },
            )


async def run_worker() -> None:
    if AdminAsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL_ADMIN is required for worker.")

    logger.info("Worker started polling for jobs.", extra={"worker_id": WORKER_ID})
    while True:
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                await _reset_expired_locks(session)
                job_row = await _claim_job(session)

        if not job_row:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue

        job_id = job_row.get("id")
        job_org_id = str(job_row.get("org_id")) if job_row.get("org_id") else None
        try:
            await _process_job(job_row)
        except Exception as exc:  # noqa: BLE001
            await _finalize_job(job_id, "failed", str(exc), job_org_id)
        else:
            await _finalize_job(job_id, "succeeded", None, job_org_id)


if __name__ == "__main__":
    asyncio.run(run_worker())
