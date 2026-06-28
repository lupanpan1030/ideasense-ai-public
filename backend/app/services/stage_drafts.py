from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.core.usage_limits import enforce_llm_usage_limits
from app.services.background_jobs import normalize_background_job_status
from app.services.localization import DEFAULT_OUTPUT_LOCALE
from app.services.localization import normalize_summary_locale_map
from app.services.project_permissions import can_mutate_project
from app.services.stage_summary_jobs import (
    STAGE_SUMMARY_FAILED_STATUSES,
    STAGE_SUMMARY_PENDING_STATUSES,
    enqueue_stage_summary_job,
)
from app.services.stage_transition import decide_stage_draft_generation


STAGE_DRAFT_STAGE_CHANGED = "stage_changed"
STAGE_DRAFT_NOT_READY = "stage_not_ready"
STAGE_DRAFT_CONTEXT_CONFLICT = "context_conflict"
STAGE_DRAFT_MISSING_QUESTION_BANK = "missing_question_bank"


class StageDraftNotFoundError(RuntimeError):
    pass


class StageDraftPermissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageDraftWorkflowResult:
    error: str | None = None
    assessment_id: Any = None
    stage_status: str | None = None
    draft_summary_text: str = ""
    draft_output_locale: str | None = None
    context_version: int | None = None
    context_updated_at: Any = None
    generation_status: str = "queued"
    retryable: bool = False
    last_error: str | None = None


def can_reuse_stage_draft_cache(
    *,
    existing_summary: str | None,
    existing_version: int | None,
    state_version: int,
    existing_draft_locale: str | None,
    requested_output_locale: str,
) -> bool:
    if not existing_summary or existing_version != state_version:
        return False
    if existing_draft_locale:
        return existing_draft_locale == requested_output_locale
    return requested_output_locale == DEFAULT_OUTPUT_LOCALE


def resolve_stage_summary_generation_status(
    *,
    has_ready_summary: bool,
    job_status: Any = None,
    stale: bool = False,
) -> str:
    if has_ready_summary:
        return "ready"
    if stale:
        return "stale"
    normalized = normalize_background_job_status(job_status)
    if normalized in STAGE_SUMMARY_PENDING_STATUSES:
        return normalized
    if normalized in STAGE_SUMMARY_FAILED_STATUSES:
        return "failed"
    if normalized == "succeeded":
        return "failed"
    return "queued"


def stage_summary_retryable(generation_status: str) -> bool:
    return generation_status in {"failed", "stale"}


async def prepare_stage_draft_workflow(
    session,
    *,
    project_id: str,
    org_id: str,
    user_id: str,
    stage: str,
    project_row: dict[str, Any],
    client_context_version: int | None,
    output_locale: str,
    retry: bool = False,
) -> StageDraftWorkflowResult:
    draft_decision = decide_stage_draft_generation(
        requested_stage=stage,
        current_stage=project_row.get("current_stage"),
        stage_status=project_row.get("stage_status"),
    )
    if draft_decision.reason == "stage_mismatch":
        return StageDraftWorkflowResult(error=STAGE_DRAFT_STAGE_CHANGED)
    if draft_decision.reason == "stage_not_awaiting_confirm":
        return StageDraftWorkflowResult(error=STAGE_DRAFT_NOT_READY)
    stage_status = draft_decision.next_stage_status

    state_result = await session.execute(
        text(
            "SELECT state_meta, state_version, updated_at "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    state_row = state_result.mappings().first()
    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    state_version = state_row.get("state_version") if state_row else 0
    if state_version is None:
        state_version = 0
    summary_locale_map = normalize_summary_locale_map(state_meta)
    existing_draft_locale = summary_locale_map.get(stage, {}).get("draft")
    context_updated_at = state_row.get("updated_at") if state_row else None

    if client_context_version is not None and client_context_version != state_version:
        return StageDraftWorkflowResult(
            error=STAGE_DRAFT_CONTEXT_CONFLICT,
            stage_status=stage_status,
            context_version=state_version,
            context_updated_at=context_updated_at,
        )

    bank_id = project_row.get("question_bank_version_id")
    if not bank_id:
        return StageDraftWorkflowResult(
            error=STAGE_DRAFT_MISSING_QUESTION_BANK,
            stage_status=stage_status,
            context_version=state_version,
            context_updated_at=context_updated_at,
        )

    assessment_result = await session.execute(
        text(
            "SELECT id, draft_summary_markdown, generated_from_state_version "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND stage = :stage "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "org_id": org_id,
            "stage": stage,
        },
    )
    assessment_row = assessment_result.mappings().first()
    existing_summary = (
        assessment_row.get("draft_summary_markdown") if assessment_row else None
    )
    existing_version = (
        assessment_row.get("generated_from_state_version") if assessment_row else None
    )
    assessment_id = assessment_row.get("id") if assessment_row else None
    if can_reuse_stage_draft_cache(
        existing_summary=existing_summary,
        existing_version=existing_version,
        state_version=state_version,
        existing_draft_locale=existing_draft_locale,
        requested_output_locale=output_locale,
    ):
        return StageDraftWorkflowResult(
            assessment_id=assessment_id,
            stage_status=stage_status,
            draft_summary_text=existing_summary or "",
            draft_output_locale=existing_draft_locale or DEFAULT_OUTPUT_LOCALE,
            context_version=state_version,
            context_updated_at=context_updated_at,
            generation_status="ready",
            retryable=False,
            last_error=None,
        )

    await enforce_llm_usage_limits(session, user_id=user_id, is_verified=True)
    job_row = await enqueue_stage_summary_job(
        session,
        project_id=project_id,
        stage=stage,
        context_version=state_version,
        output_locale=output_locale,
        retry=retry,
    )
    job_status = job_row.get("status") if job_row else None
    generation_status = resolve_stage_summary_generation_status(
        has_ready_summary=False,
        job_status=job_status,
    )
    last_error = job_row.get("last_error") if job_row else None
    if generation_status == "failed" and not last_error:
        last_error = "Stage summary job completed without a reusable draft summary."
    return StageDraftWorkflowResult(
        assessment_id=assessment_id,
        stage_status=stage_status,
        draft_summary_text="",
        draft_output_locale=output_locale,
        context_version=state_version,
        context_updated_at=context_updated_at,
        generation_status=generation_status,
        retryable=stage_summary_retryable(generation_status),
        last_error=last_error if generation_status == "failed" else None,
    )


async def fetch_stage_draft_project_row(
    session,
    *,
    project_id: str,
    org_id: str,
) -> dict[str, Any]:
    project_result = await session.execute(
        text(
            "SELECT id, current_stage, current_variant, stage_status, "
            "question_bank_version_id, settings "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    project_row = project_result.mappings().first()
    if not project_row:
        raise StageDraftNotFoundError("Project not found.")
    return dict(project_row)


async def prepare_project_stage_draft_workflow(
    session,
    *,
    project_id: str,
    org_id: str,
    user_id: str,
    stage: str,
    client_context_version: int | None,
    output_locale: str,
    retry: bool = False,
) -> StageDraftWorkflowResult:
    project_row = await fetch_stage_draft_project_row(
        session,
        project_id=project_id,
        org_id=org_id,
    )
    allowed = await can_mutate_project(
        session,
        project_id=project_id,
        org_id=org_id,
        user_id=user_id,
    )
    if not allowed:
        raise StageDraftPermissionError("Insufficient project permissions.")
    return await prepare_stage_draft_workflow(
        session,
        project_id=project_id,
        org_id=org_id,
        user_id=user_id,
        stage=stage,
        project_row=project_row,
        client_context_version=client_context_version,
        output_locale=output_locale,
        retry=retry,
    )


__all__ = [
    "can_reuse_stage_draft_cache",
    "fetch_stage_draft_project_row",
    "prepare_project_stage_draft_workflow",
    "prepare_stage_draft_workflow",
    "resolve_stage_summary_generation_status",
    "StageDraftNotFoundError",
    "StageDraftPermissionError",
    "StageDraftWorkflowResult",
    "STAGE_DRAFT_CONTEXT_CONFLICT",
    "STAGE_DRAFT_MISSING_QUESTION_BANK",
    "STAGE_DRAFT_NOT_READY",
    "STAGE_DRAFT_STAGE_CHANGED",
    "stage_summary_retryable",
]
