from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectRuntimeMissingError(RuntimeError):
    pass


async def fetch_project_detail(
    session: AsyncSession,
    project_id: Any,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT "
            "p.id, p.org_id, p.owner_user_id, p.title, p.description, "
            "p.question_bank_version_id, p.current_stage, p.current_variant, "
            "p.stage_status, p.settings, p.is_archived, p.archived_at, "
            "p.created_at, p.updated_at, "
            "pr.project_id AS runtime_project_id, pr.org_id AS runtime_org_id, "
            "pr.stage AS runtime_stage, pr.variant AS runtime_variant, "
            "pr.current_question_bank_question_id, "
            "pr.next_question_bank_question_id, pr.missing_paths, "
            "pr.turn_state, pr.runtime_version, "
            "pr.created_at AS runtime_created_at, "
            "pr.updated_at AS runtime_updated_at, "
            "qi.id AS current_question_instance_id "
            "FROM projects p "
            "LEFT JOIN project_runtime pr "
            "ON pr.project_id = p.id "
            "AND pr.org_id = p.org_id "
            "AND pr.deleted_at IS NULL "
            "LEFT JOIN project_question_instances qi "
            "ON qi.project_id = p.id "
            "AND qi.question_bank_question_id = pr.current_question_bank_question_id "
            "AND qi.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    row = result.mappings().first()
    if not row:
        return None
    if not row.get("runtime_project_id"):
        raise ProjectRuntimeMissingError("Project runtime is not initialized.")

    return {
        "project": {
            "id": row.get("id"),
            "org_id": row.get("org_id"),
            "owner_user_id": row.get("owner_user_id"),
            "title": row.get("title"),
            "description": row.get("description"),
            "question_bank_version_id": row.get("question_bank_version_id"),
            "current_stage": row.get("current_stage"),
            "current_variant": row.get("current_variant"),
            "stage_status": row.get("stage_status"),
            "settings": row.get("settings") or {},
            "is_archived": row.get("is_archived"),
            "archived_at": row.get("archived_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        },
        "runtime": {
            "project_id": row.get("runtime_project_id"),
            "org_id": row.get("runtime_org_id"),
            "stage": row.get("runtime_stage"),
            "variant": row.get("runtime_variant"),
            "current_question_bank_question_id": row.get(
                "current_question_bank_question_id"
            ),
            "next_question_bank_question_id": row.get(
                "next_question_bank_question_id"
            ),
            "missing_paths": list(row.get("missing_paths") or []),
            "turn_state": row.get("turn_state"),
            "runtime_version": row.get("runtime_version"),
            "created_at": row.get("runtime_created_at"),
            "updated_at": row.get("runtime_updated_at"),
        },
        "current_question_instance_id": row.get("current_question_instance_id"),
    }


__all__ = ["ProjectRuntimeMissingError", "fetch_project_detail"]
