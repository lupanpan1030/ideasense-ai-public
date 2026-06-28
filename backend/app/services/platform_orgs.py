from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PlatformOrgValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PlatformOrgNotFoundError(LookupError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def row_to_platform_org_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "name": row.get("name") or "",
        "slug": row.get("slug") or "",
        "settings": row.get("settings") or {},
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def build_platform_org_filters(
    *,
    limit: int,
    offset: int,
    q: str | None,
) -> tuple[str, dict[str, object]]:
    filters = ["deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if q:
        search = q.strip()
        if search:
            filters.append("(name ILIKE :search OR slug ILIKE :search)")
            params["search"] = f"%{search}%"

    return " AND ".join(filters), params


async def fetch_platform_orgs_payload(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    q: str | None,
) -> dict[str, Any]:
    where_clause, params = build_platform_org_filters(
        limit=limit,
        offset=offset,
        q=q,
    )

    count_result = await session.execute(
        text(f"SELECT COUNT(*) AS total FROM organizations WHERE {where_clause}"),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT id, name, slug, settings, created_at, updated_at "
            "FROM organizations "
            f"WHERE {where_clause} "
            "ORDER BY created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return {
        "orgs": [row_to_platform_org_payload(row) for row in result.mappings().all()],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def update_platform_org_payload(
    session: AsyncSession,
    *,
    org_id: UUID,
    name: str | None,
    settings: dict[str, Any] | None,
) -> dict[str, Any]:
    name_value = name.strip() if name is not None else None
    if name_value is not None and not name_value:
        raise PlatformOrgValidationError("Organization name is required")

    settings_value = settings or {}
    if settings is not None and not isinstance(settings, dict):
        raise PlatformOrgValidationError("settings must be an object")

    result = await session.execute(
        text(
            "UPDATE organizations "
            "SET name = COALESCE(:name, name), "
            "settings = COALESCE(settings, '{}'::jsonb) || CAST(:settings AS jsonb) "
            "WHERE id = :org_id AND deleted_at IS NULL "
            "RETURNING id, name, slug, settings, created_at, updated_at"
        ),
        {
            "org_id": str(org_id),
            "name": name_value,
            "settings": settings_value,
        },
    )
    row = result.mappings().first()
    if not row:
        raise PlatformOrgNotFoundError("Organization not found")
    return row_to_platform_org_payload(row)
