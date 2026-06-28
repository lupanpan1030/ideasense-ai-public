from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.core.usage_limits import enforce_llm_usage_limits, enforce_report_daily_limit
from app.services.diagnostics import merge_validation_plans
from app.services.project_permissions import can_mutate_project
from app.services.report_jobs import (
    build_queued_report_job_status,
    build_ready_report_job_status,
    enqueue_report_generation_job,
)
from app.services.stage_transition import decide_report_confirmation_complete


REPORT_CONFIRMATION_REQUIRED_STAGES = frozenset({"problem", "market", "tech"})


class ReportConfirmationConflictError(RuntimeError):
    pass


class ReportConfirmationNotFoundError(RuntimeError):
    pass


class ReportConfirmationPermissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportConfirmationPrerequisites:
    state_version: int
    validation_plan: list[dict[str, Any]]


@dataclass(frozen=True)
class ReportConfirmationWorkflowResult:
    stage_status: Any
    validation_plan: list[dict[str, Any]]
    report_job_status: dict[str, Any]


def _is_report_recovery(*, current_stage: Any, stage_status: Any) -> bool:
    return (
        str(current_stage or "").strip().lower() == "report"
        and str(stage_status or "").strip().lower() == "passed"
    )


def _raise_for_report_decision(*, current_stage: Any, stage_status: Any) -> bool:
    decision = decide_report_confirmation_complete(
        current_stage=current_stage,
        stage_status=stage_status,
    )
    is_recovery = _is_report_recovery(
        current_stage=current_stage,
        stage_status=stage_status,
    )
    if decision.reason == "stage_mismatch":
        raise ReportConfirmationConflictError(
            "Project stage changed. Refresh and try again."
        )
    if decision.reason == "stage_not_awaiting_confirm" and not is_recovery:
        raise ReportConfirmationConflictError(
            "Report stage is not ready for confirmation."
        )
    return is_recovery


async def resolve_report_confirmation_prerequisites(
    session,
    *,
    project_id: str,
    org_id: str,
    client_context_version: int | None,
) -> ReportConfirmationPrerequisites:
    state_result = await session.execute(
        text(
            "SELECT state_version "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    state_row = state_result.mappings().first()
    state_version = state_row.get("state_version") if state_row else 0
    if state_version is None:
        state_version = 0

    if client_context_version is not None and client_context_version != state_version:
        raise ReportConfirmationConflictError(
            "Context updated while you were away. Refresh and try again."
        )

    assessments_result = await session.execute(
        text(
            "SELECT id, stage, draft_summary_markdown, final_summary_markdown, "
            "confirmed, total_score, confirmed_at, created_at, updated_at, "
            "context_card_json, validation_plan_json "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND stage IN ('problem','market','tech') "
            "AND deleted_at IS NULL"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    assessment_rows = assessments_result.mappings().all()
    confirmed_stages = {
        row.get("stage") for row in assessment_rows if row.get("confirmed")
    }
    missing_stages = REPORT_CONFIRMATION_REQUIRED_STAGES - confirmed_stages
    if missing_stages:
        raise ReportConfirmationConflictError(
            "All stage summaries must be confirmed before generating report."
        )
    stage_validation_plans = [
        row.get("validation_plan_json")
        for row in assessment_rows
        if isinstance(row.get("validation_plan_json"), list)
    ]
    return ReportConfirmationPrerequisites(
        state_version=int(state_version),
        validation_plan=merge_validation_plans(*stage_validation_plans),
    )


async def fetch_report_confirmation_recovery_report(
    session,
    *,
    project_id: str,
    org_id: str,
    state_version: int,
    output_locale: str,
    default_output_locale: str,
) -> dict[str, Any] | None:
    existing_report_result = await session.execute(
        text(
            "SELECT id, report_version, created_at "
            "FROM project_reports "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "AND status = 'final' "
            "AND generated_from_state_version = :state_version "
            "AND COALESCE(NULLIF(content_json->>'artifact_locale', ''), "
            ":default_output_locale) = :output_locale "
            "ORDER BY report_version DESC "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "org_id": org_id,
            "state_version": int(state_version),
            "output_locale": output_locale,
            "default_output_locale": default_output_locale,
        },
    )
    existing_report = existing_report_result.mappings().first()
    return dict(existing_report) if existing_report else None


async def fetch_report_confirmation_project_row(
    session,
    *,
    project_id: str,
    org_id: str,
) -> dict[str, Any]:
    project_result = await session.execute(
        text(
            "SELECT id, org_id, title, description, current_stage, stage_status, "
            "updated_at, settings "
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
        raise ReportConfirmationNotFoundError("Project not found.")
    return dict(project_row)


async def confirm_project_report_stage_workflow(
    session,
    *,
    project_id: str,
    org_id: str,
    user_id: str,
    client_context_version: int | None,
    output_locale: str,
    default_output_locale: str,
) -> ReportConfirmationWorkflowResult:
    project_row = await fetch_report_confirmation_project_row(
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
        raise ReportConfirmationPermissionError("Insufficient project permissions.")
    return await confirm_report_stage_workflow(
        session,
        project_id=project_id,
        org_id=org_id,
        user_id=user_id,
        client_context_version=client_context_version,
        output_locale=output_locale,
        default_output_locale=default_output_locale,
        current_stage=project_row.get("current_stage"),
        stage_status=project_row.get("stage_status"),
    )


async def confirm_report_stage_workflow(
    session,
    *,
    project_id: str,
    org_id: str,
    user_id: str,
    client_context_version: int | None,
    output_locale: str,
    default_output_locale: str,
    current_stage: Any,
    stage_status: Any,
) -> ReportConfirmationWorkflowResult:
    _raise_for_report_decision(
        current_stage=current_stage,
        stage_status=stage_status,
    )
    report_prerequisites = await resolve_report_confirmation_prerequisites(
        session,
        project_id=project_id,
        org_id=org_id,
        client_context_version=client_context_version,
    )
    state_version = int(report_prerequisites.state_version)
    validation_plan = report_prerequisites.validation_plan

    lock_result = await session.execute(
        text(
            "SELECT current_stage, stage_status "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1 "
            "FOR UPDATE"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    lock_row = lock_result.mappings().first()
    if not lock_row:
        raise ReportConfirmationNotFoundError("Project not found.")

    locked_recovery = _raise_for_report_decision(
        current_stage=lock_row.get("current_stage"),
        stage_status=lock_row.get("stage_status"),
    )
    if locked_recovery:
        existing_report = await fetch_report_confirmation_recovery_report(
            session,
            project_id=project_id,
            org_id=org_id,
            state_version=state_version,
            output_locale=output_locale,
            default_output_locale=default_output_locale,
        )
        if existing_report:
            return ReportConfirmationWorkflowResult(
                stage_status=lock_row.get("stage_status"),
                validation_plan=validation_plan,
                report_job_status=build_ready_report_job_status(
                    project_id=project_id,
                    current_stage=lock_row.get("current_stage"),
                    stage_status=lock_row.get("stage_status"),
                    report_id=existing_report.get("id"),
                    report_version=existing_report.get("report_version"),
                    generated_at=existing_report.get("created_at"),
                    context_version=state_version,
                ),
            )

    await enforce_report_daily_limit(session, user_id=user_id)
    await enforce_llm_usage_limits(session, user_id=user_id, is_verified=True)
    job_row = await enqueue_report_generation_job(
        session,
        org_id=org_id,
        project_id=project_id,
        context_version=state_version,
        output_locale=output_locale,
        requested_by_user_id=user_id,
    )
    return ReportConfirmationWorkflowResult(
        stage_status=lock_row.get("stage_status"),
        validation_plan=validation_plan,
        report_job_status=build_queued_report_job_status(
            project_id=project_id,
            current_stage=lock_row.get("current_stage"),
            stage_status=lock_row.get("stage_status"),
            status=job_row.get("status"),
            context_version=state_version,
        ),
    )


__all__ = [
    "REPORT_CONFIRMATION_REQUIRED_STAGES",
    "ReportConfirmationConflictError",
    "ReportConfirmationNotFoundError",
    "ReportConfirmationPermissionError",
    "ReportConfirmationPrerequisites",
    "ReportConfirmationWorkflowResult",
    "confirm_project_report_stage_workflow",
    "confirm_report_stage_workflow",
    "fetch_report_confirmation_project_row",
    "fetch_report_confirmation_recovery_report",
    "resolve_report_confirmation_prerequisites",
]
