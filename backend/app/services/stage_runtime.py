"""Database writers for stage transition decisions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.services.stage_transition import (
    STAGE_STATUS_PASSED,
    StageTransitionDecision,
)


def _row_updated(result: Any) -> bool:
    rowcount = getattr(result, "rowcount", None)
    return rowcount is None or rowcount > 0


async def update_project_runtime_missing_paths_from_decision(
    session,
    *,
    project_id: str,
    org_id: str,
    decision: StageTransitionDecision,
) -> bool:
    result = await session.execute(
        text(
            "UPDATE project_runtime "
            "SET missing_paths = :missing_paths, "
            "updated_at = now() "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "project_id": project_id,
            "org_id": org_id,
            "missing_paths": decision.missing_paths,
        },
    )
    return _row_updated(result)


async def update_project_stage_status_from_decision(
    session,
    *,
    project_id: str,
    org_id: str,
    decision: StageTransitionDecision,
    current_stage: str | None = None,
    require_allowed: bool = False,
) -> bool:
    if require_allowed and not decision.allowed:
        return False

    current_stage_clause = "AND current_stage = :current_stage " if current_stage else ""
    params: dict[str, Any] = {
        "project_id": project_id,
        "org_id": org_id,
        "stage_status": decision.next_stage_status,
    }
    if current_stage:
        params["current_stage"] = current_stage

    result = await session.execute(
        text(
            "UPDATE projects "
            "SET stage_status = :stage_status, "
            "updated_at = now() "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            f"{current_stage_clause}"
            "AND deleted_at IS NULL"
        ),
        params,
    )
    return _row_updated(result)


async def advance_project_stage_from_decision(
    session,
    *,
    project_id: str,
    org_id: str,
    decision: StageTransitionDecision,
    next_variant: str,
) -> bool:
    if not decision.allowed or not decision.current_stage_update:
        raise ValueError("Stage transition decision does not allow stage advancement.")

    result = await session.execute(
        text(
            "UPDATE projects "
            "SET current_stage = :next_stage, "
            "current_variant = :next_variant, "
            "stage_status = :stage_status, "
            "updated_at = now() "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {
            "next_stage": decision.current_stage_update,
            "next_variant": next_variant,
            "stage_status": decision.next_stage_status,
            "project_id": project_id,
            "org_id": org_id,
        },
    )
    return _row_updated(result)


async def mark_project_stage_passed_from_decision(
    session,
    *,
    project_id: str,
    org_id: str,
    decision: StageTransitionDecision,
) -> bool:
    if not decision.allowed or decision.next_stage_status != STAGE_STATUS_PASSED:
        raise ValueError("Stage transition decision does not mark the stage passed.")

    return await update_project_stage_status_from_decision(
        session,
        project_id=project_id,
        org_id=org_id,
        decision=decision,
        current_stage=decision.stage,
        require_allowed=True,
    )


__all__ = [
    "advance_project_stage_from_decision",
    "mark_project_stage_passed_from_decision",
    "update_project_runtime_missing_paths_from_decision",
    "update_project_stage_status_from_decision",
]
