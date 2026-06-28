from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectMutationValidationError(ValueError):
    pass


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


async def update_project_summary(
    session: AsyncSession,
    *,
    project_id: Any,
    fields_set: set[str],
    title: str | None = None,
    description: str | None = None,
    is_archived: bool | None = None,
) -> dict[str, Any] | None:
    if not fields_set:
        raise ProjectMutationValidationError("No project fields provided.")

    updates: list[str] = []
    params: dict[str, Any] = {"project_id": str(project_id)}

    if "title" in fields_set:
        normalized_title = _normalize_optional_string(title)
        if not normalized_title:
            raise ProjectMutationValidationError("Project title is required.")
        updates.append("title = :title")
        params["title"] = normalized_title

    if "description" in fields_set:
        updates.append("description = :description")
        params["description"] = _normalize_optional_string(description)

    if "is_archived" in fields_set:
        if is_archived is None:
            raise ProjectMutationValidationError("is_archived is required.")
        updates.append("is_archived = :is_archived")
        updates.append(
            "archived_at = CASE WHEN :is_archived THEN now() ELSE NULL END"
        )
        params["is_archived"] = is_archived

    if not updates:
        raise ProjectMutationValidationError("No valid project updates provided.")

    result = await session.execute(
        text(
            "UPDATE projects "
            "SET " + ", ".join(updates) + " "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "RETURNING "
            "id, org_id, owner_user_id, title, description, "
            "question_bank_version_id, current_stage, current_variant, "
            "stage_status, is_archived, created_at, updated_at"
        ),
        params,
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def soft_delete_project(
    session: AsyncSession,
    *,
    project_id: Any,
) -> bool:
    result = await session.execute(
        text(
            "UPDATE projects "
            "SET deleted_at = now() "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "RETURNING id"
        ),
        {"project_id": str(project_id)},
    )
    return bool(result.mappings().first())


__all__ = [
    "ProjectMutationValidationError",
    "soft_delete_project",
    "update_project_summary",
]
