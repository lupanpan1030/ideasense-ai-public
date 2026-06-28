from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text

from app.services.background_jobs import background_job_sort_time
from app.services.assessment_summaries import (
    SUMMARY_STAGES,
    resolve_verification_provider_unavailable_reason,
)
from app.services.verification.config import (
    verification_enabled,
    verification_min_priority,
    verification_stage_max_questions,
)
from app.services.verification.question_instances import (
    is_verifiable_question_instance,
)
from app.services.verification.priority import (
    extract_verification_priority,
    normalize_priority,
    priority_at_least,
)
from app.services.verification_jobs import (
    VERIFY_QUESTION_CLAIMS_JOB_TYPE,
    enqueue_summary_question_verification_job,
    requeue_question_verification_job,
)


PrepareWriteActor = Callable[[Any], Awaitable[None]]


@dataclass(frozen=True)
class VerificationRefreshJobResult:
    project_exists: bool
    enqueued: int = 0
    skipped: int = 0


class VerificationRefreshProjectNotFoundError(RuntimeError):
    pass


class VerificationRefreshStageUnsupportedError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerificationRefreshWorkflowResult:
    normalized_stage: str | None
    enqueued: int = 0
    skipped: int = 0


async def refresh_project_stage_verification_workflow(
    session,
    *,
    project_id: str,
    stage: str | None,
    prepare_write_actor: PrepareWriteActor | None = None,
) -> VerificationRefreshWorkflowResult:
    normalized_stage = stage.strip().lower() if isinstance(stage, str) else None
    disabled_response_stage = stage if isinstance(stage, str) else None
    if not verification_enabled():
        return VerificationRefreshWorkflowResult(
            normalized_stage=disabled_response_stage
        )
    if resolve_verification_provider_unavailable_reason():
        return VerificationRefreshWorkflowResult(
            normalized_stage=disabled_response_stage
        )
    if normalized_stage and normalized_stage not in SUMMARY_STAGES:
        raise VerificationRefreshStageUnsupportedError("Stage not supported.")

    stage_filter = [normalized_stage] if normalized_stage else sorted(SUMMARY_STAGES)
    refresh_result = await schedule_project_stage_verification_refresh(
        session,
        project_id=project_id,
        stages=stage_filter,
        prepare_write_actor=prepare_write_actor,
    )
    if not refresh_result.project_exists:
        raise VerificationRefreshProjectNotFoundError("Project not found.")
    return VerificationRefreshWorkflowResult(
        normalized_stage=normalized_stage,
        enqueued=refresh_result.enqueued,
        skipped=refresh_result.skipped,
    )


async def schedule_project_stage_verification_refresh(
    session,
    *,
    project_id: str,
    stages: Sequence[str],
    prepare_write_actor: PrepareWriteActor | None = None,
) -> VerificationRefreshJobResult:
    project_result = await session.execute(
        text(
            "SELECT id "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id},
    )
    if not project_result.mappings().first():
        return VerificationRefreshJobResult(project_exists=False)
    if not stages:
        return VerificationRefreshJobResult(project_exists=True)

    question_result = await session.execute(
        text(
            "SELECT qi.id AS question_instance_id, qi.answered_at, "
            "qi.status, qi.final_answer_text, "
            "q.id AS question_bank_question_id, q.question_id, q.title, "
            "q.stage, q.order_index, q.prompt_meta "
            "FROM project_question_instances qi "
            "JOIN question_bank_questions q "
            "ON q.id = qi.question_bank_question_id "
            "WHERE qi.project_id = :project_id "
            "AND qi.org_id = app_org_id() "
            "AND qi.deleted_at IS NULL "
            "AND q.deleted_at IS NULL "
            "AND q.stage IN :stages "
            "ORDER BY CASE q.stage "
            "WHEN 'problem' THEN 1 "
            "WHEN 'market' THEN 2 "
            "WHEN 'tech' THEN 3 "
            "ELSE 4 END, q.order_index ASC"
        ).bindparams(bindparam("stages", expanding=True)),
        {"project_id": project_id, "stages": list(stages)},
    )
    question_rows = [
        row
        for row in question_result.mappings().all()
        if is_verifiable_question_instance(
            row.get("status"),
            row.get("final_answer_text"),
        )
    ]

    min_priority = verification_min_priority()
    candidates: list[dict[str, Any]] = []
    for row in question_rows:
        prompt_meta = row.get("prompt_meta") or {}
        priority = extract_verification_priority(
            {"prompt_meta": prompt_meta, "question_id": row.get("question_id")}
        )
        priority = normalize_priority(priority)
        if not priority_at_least(priority, min_priority):
            continue
        candidates.append({**row, "priority": priority})

    question_ids = [
        row.get("question_bank_question_id")
        for row in candidates
        if row.get("question_bank_question_id")
    ]
    latest_claim_by_question: dict[str, datetime] = {}
    if question_ids:
        claim_result = await session.execute(
            text(
                "SELECT question_bank_question_id, created_at "
                "FROM project_stage_verification_claims "
                "WHERE project_id = :project_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL "
                "AND question_bank_question_id IN :question_ids "
                "ORDER BY created_at DESC"
            ).bindparams(bindparam("question_ids", expanding=True)),
            {"project_id": project_id, "question_ids": question_ids},
        )
        for row in claim_result.mappings().all():
            question_key = str(row.get("question_bank_question_id"))
            created_at = row.get("created_at")
            if question_key and created_at:
                latest_claim_by_question.setdefault(question_key, created_at)

    job_result = await session.execute(
        text(
            "SELECT id, payload, status, created_at, updated_at, completed_at "
            "FROM background_jobs "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND job_type = :job_type "
            "AND status IN ('queued','running','failed','cancelled') "
            "AND deleted_at IS NULL"
        ),
        {"project_id": project_id, "job_type": VERIFY_QUESTION_CLAIMS_JOB_TYPE},
    )
    pending_question_ids: set[str] = set()
    retry_job_by_question: dict[str, dict[str, Any]] = {}
    for row in job_result.mappings().all():
        payload = row.get("payload")
        if isinstance(payload, dict):
            qid = payload.get("question_bank_question_id")
            if isinstance(qid, str) and qid:
                job_status = str(row.get("status") or "").strip().lower()
                if job_status in {"queued", "running"}:
                    pending_question_ids.add(qid)
                elif job_status in {"failed", "cancelled"}:
                    existing = retry_job_by_question.get(qid)
                    candidate = dict(row)
                    min_time = datetime.min.replace(tzinfo=timezone.utc)
                    if (
                        background_job_sort_time(candidate) or min_time
                    ) >= (background_job_sort_time(existing) or min_time):
                        retry_job_by_question[qid] = candidate

    max_per_stage = verification_stage_max_questions()
    enqueued = 0
    skipped = 0

    for stage_key in stages:
        stage_candidates = [c for c in candidates if c.get("stage") == stage_key]
        stage_candidates.sort(
            key=lambda row: (
                0
                if row.get("priority") == "high"
                else 1
                if row.get("priority") == "medium"
                else 2,
                row.get("order_index") or 0,
            )
        )
        scheduled = 0
        for row in stage_candidates:
            if scheduled >= max_per_stage:
                break
            question_bank_id = row.get("question_bank_question_id")
            if not question_bank_id:
                skipped += 1
                continue
            question_key = str(question_bank_id)
            if question_key in pending_question_ids:
                skipped += 1
                continue
            answered_at = row.get("answered_at")
            latest_claim_at = latest_claim_by_question.get(question_key)
            is_stale = bool(
                answered_at and latest_claim_at and answered_at > latest_claim_at
            )
            has_claim = latest_claim_at is not None and not is_stale
            if has_claim:
                skipped += 1
                continue

            retry_job = retry_job_by_question.get(question_key)
            if prepare_write_actor:
                await prepare_write_actor(session)
            if retry_job:
                requeued = await requeue_question_verification_job(
                    session,
                    job_id=retry_job.get("id"),
                )
                if requeued:
                    enqueued += 1
                    scheduled += 1
                else:
                    skipped += 1
                continue

            inserted = await enqueue_summary_question_verification_job(
                session,
                project_id=project_id,
                question_instance_id=str(row.get("question_instance_id")),
                question_bank_question_id=str(question_bank_id),
                answered_at=answered_at,
                priority=row.get("priority"),
            )
            if inserted:
                enqueued += 1
                scheduled += 1
            else:
                skipped += 1

    return VerificationRefreshJobResult(
        project_exists=True,
        enqueued=enqueued,
        skipped=skipped,
    )


__all__ = [
    "VerificationRefreshJobResult",
    "VerificationRefreshProjectNotFoundError",
    "VerificationRefreshStageUnsupportedError",
    "VerificationRefreshWorkflowResult",
    "refresh_project_stage_verification_workflow",
    "schedule_project_stage_verification_refresh",
]
