from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


STAGE_FILTERS = {"problem", "market", "tech", "report", "all"}
ARCHIVED_FILTERS = {"active", "archived", "all"}
SORT_FIELDS: dict[str, str] = {
    "updated_at": "p.updated_at",
    "created_at": "p.created_at",
    "title": "LOWER(p.title)",
}
SORT_ORDERS = {"asc", "desc"}


@dataclass(frozen=True)
class ProjectListFilters:
    stage: str | None
    archived: str
    sort: str
    order: str


def normalize_project_list_filters(
    *,
    stage: str | None,
    archived: str | None,
    sort: str | None,
    order: str | None,
) -> ProjectListFilters:
    stage_filter = stage.strip().lower() if stage else None
    if stage_filter and stage_filter not in STAGE_FILTERS:
        raise ValueError("Invalid stage filter.")
    if stage_filter == "all":
        stage_filter = None

    archived_filter = archived.strip().lower() if archived else "active"
    if archived_filter not in ARCHIVED_FILTERS:
        raise ValueError("Invalid archived filter.")

    sort_field = sort.strip().lower() if sort else "updated_at"
    if sort_field not in SORT_FIELDS:
        raise ValueError("Invalid sort field.")

    sort_order = order.strip().lower() if order else "desc"
    if sort_order not in SORT_ORDERS:
        raise ValueError("Invalid sort order.")

    return ProjectListFilters(
        stage=stage_filter,
        archived=archived_filter,
        sort=sort_field,
        order=sort_order,
    )


async def fetch_project_list(
    session: AsyncSession,
    *,
    owner_user_id: Any,
    limit: int,
    offset: int,
    stage: str | None = None,
    archived: str | None = None,
    sort: str | None = None,
    order: str | None = None,
) -> dict[str, Any]:
    filters = normalize_project_list_filters(
        stage=stage,
        archived=archived,
        sort=sort,
        order=order,
    )
    stage_clause = " AND p.current_stage = :stage" if filters.stage else ""
    if filters.archived == "archived":
        archived_clause = " AND p.is_archived = true"
    elif filters.archived == "active":
        archived_clause = " AND p.is_archived = false"
    else:
        archived_clause = ""
    order_clause = (
        f" ORDER BY {SORT_FIELDS[filters.sort]} {filters.order.upper()}, "
        "p.updated_at DESC, p.id DESC "
    )
    params: dict[str, Any] = {"owner_user_id": owner_user_id}
    if filters.stage:
        params["stage"] = filters.stage

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM projects p "
            "WHERE p.org_id = app_org_id() "
            "AND p.owner_user_id = :owner_user_id "
            "AND p.deleted_at IS NULL"
            f"{stage_clause}"
            f"{archived_clause}"
        ),
        params,
    )
    count_row = count_result.mappings().first()
    total = count_row.get("total") if count_row else 0

    result = await session.execute(
        text(
            "SELECT "
            "p.id, p.org_id, p.owner_user_id, p.title, p.description, "
            "p.question_bank_version_id, p.current_stage, p.current_variant, "
            "p.stage_status, p.is_archived, p.created_at, p.updated_at "
            "FROM projects p "
            "WHERE p.org_id = app_org_id() "
            "AND p.owner_user_id = :owner_user_id "
            "AND p.deleted_at IS NULL "
            f"{stage_clause} "
            f"{archived_clause} "
            f"{order_clause} "
            "LIMIT :limit OFFSET :offset"
        ),
        {
            "limit": limit,
            "offset": offset,
            **params,
        },
    )
    projects = [dict(row) for row in result.mappings().all()]
    return {
        "projects": projects,
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }


__all__ = [
    "ProjectListFilters",
    "fetch_project_list",
    "normalize_project_list_filters",
]
