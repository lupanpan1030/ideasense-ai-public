from __future__ import annotations

from typing import Any

from app.services.background_jobs import enqueue_background_job
from app.services.localization import DEFAULT_OUTPUT_LOCALE, normalize_output_locale


STAGE_FINALIZE_JOB_TYPE = "stage_finalize_v0"


def stage_finalize_idempotency_key(
    project_id: str,
    stage: str,
    context_version: int,
    output_locale: str | None,
) -> str:
    stage_key = stage.strip().lower()
    locale = normalize_output_locale(output_locale)
    return f"stage-finalize:{project_id}:{stage_key}:{context_version}:{locale}"


async def enqueue_stage_finalize_job(
    session,
    *,
    org_id: str,
    project_id: str,
    stage: str,
    context_version: int,
    output_locale: str | None,
    requested_by_user_id: str,
    question_bank_version_id: str | None = None,
    variant: str | None = None,
) -> dict[str, Any]:
    stage_key = stage.strip().lower()
    locale = normalize_output_locale(output_locale)
    idempotency_key = stage_finalize_idempotency_key(
        project_id,
        stage_key,
        context_version,
        locale,
    )
    payload = {
        "project_id": project_id,
        "stage": stage_key,
        "context_version": context_version,
        "output_locale": locale or DEFAULT_OUTPUT_LOCALE,
        "requested_by_user_id": requested_by_user_id,
        "question_bank_version_id": question_bank_version_id,
        "variant": variant or "default",
        "mode": "post_confirm",
    }
    return await enqueue_background_job(
        session,
        org_id=org_id,
        project_id=project_id,
        job_type=STAGE_FINALIZE_JOB_TYPE,
        payload=payload,
        idempotency_key=idempotency_key,
        requeue_statuses=("failed", "cancelled"),
    )


__all__ = [
    "STAGE_FINALIZE_JOB_TYPE",
    "enqueue_stage_finalize_job",
    "stage_finalize_idempotency_key",
]
