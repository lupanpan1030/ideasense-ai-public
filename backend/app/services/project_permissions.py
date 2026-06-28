from __future__ import annotations

from sqlalchemy import text


async def can_mutate_project(
    session,
    *,
    project_id: str,
    org_id: str,
    user_id: str,
) -> bool:
    result = await session.execute(
        text(
            "SELECT 1 "
            "FROM projects p "
            "LEFT JOIN organization_memberships om "
            "ON om.org_id = p.org_id "
            "AND om.user_id = :user_id "
            "AND om.status = 'active' "
            "AND om.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = :org_id "
            "AND p.deleted_at IS NULL "
            "AND ("
            "p.owner_user_id = :user_id "
            "OR om.org_role IN ('owner', 'admin')"
            ") "
            "LIMIT 1"
        ),
        {
            "project_id": project_id,
            "org_id": org_id,
            "user_id": user_id,
        },
    )
    return bool(result.first())


__all__ = ["can_mutate_project"]
