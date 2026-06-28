from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stage_runtime import (
    update_project_runtime_missing_paths_from_decision,
    update_project_stage_status_from_decision,
)
from app.services.stage_transition import decide_stage_ready


async def sync_runtime_gate_state(
    session: AsyncSession,
    *,
    project_id: str,
    org_id: str,
    current_stage: str,
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
) -> None:
    runtime_result = await session.execute(
        text(
            "SELECT stage, variant, missing_paths "
            "FROM project_runtime "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    runtime_row = runtime_result.mappings().first()
    if not runtime_row:
        return

    runtime_stage = runtime_row.get("stage") or current_stage
    runtime_variant = runtime_row.get("variant")
    current_missing_paths = list(runtime_row.get("missing_paths") or [])
    transition_decision = decide_stage_ready(
        runtime_stage,
        current_missing_paths,
        state_json=state_json,
        state_meta=state_meta,
        variant=runtime_variant,
    )
    updated_missing_paths = transition_decision.missing_paths

    if updated_missing_paths != current_missing_paths:
        await update_project_runtime_missing_paths_from_decision(
            session,
            project_id=project_id,
            org_id=org_id,
            decision=transition_decision,
        )

    if runtime_stage == current_stage:
        await update_project_stage_status_from_decision(
            session,
            project_id=project_id,
            org_id=org_id,
            decision=transition_decision,
            current_stage=current_stage,
        )


__all__ = ["sync_runtime_gate_state"]
