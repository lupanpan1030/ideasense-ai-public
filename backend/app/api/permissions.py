from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import OrgCapabilityKey, resolve_org_capabilities


async def _fetch_active_membership(session: AsyncSession) -> dict:
    result = await session.execute(
        text(
            "SELECT id, org_role, status "
            "FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND user_id = app_user_id() "
            "AND deleted_at IS NULL"
        )
    )
    membership = result.mappings().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership not found",
        )
    if membership.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership is not active",
        )
    return membership


async def require_org_capability(
    session: AsyncSession, capability: OrgCapabilityKey
) -> dict:
    membership = await _fetch_active_membership(session)
    org_result = await session.execute(
        text(
            "SELECT settings "
            "FROM organizations "
            "WHERE id = app_org_id() "
            "AND deleted_at IS NULL"
        )
    )
    org = org_result.mappings().first()
    capabilities = resolve_org_capabilities(
        membership.get("org_role"),
        org.get("settings") if org else None,
    )
    if not capabilities.get(capability, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient organization permissions",
        )
    return membership


async def is_private_org(session: AsyncSession) -> bool:
    result = await session.execute(
        text(
            "SELECT settings "
            "FROM organizations "
            "WHERE id = app_org_id() "
            "AND deleted_at IS NULL"
        )
    )
    org = result.mappings().first()
    settings = org.get("settings") if org else None
    if not isinstance(settings, dict):
        return False
    return settings.get("org_type") == "private"


async def require_org_not_private(
    session: AsyncSession, *, detail: str
) -> None:
    if await is_private_org(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def require_platform_admin(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT 1 "
            "FROM platform_admins "
            "WHERE user_id = app_user_id() "
            "AND status = 'active' "
            "AND deleted_at IS NULL"
        )
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient platform permissions",
        )

    membership_result = await session.execute(
        text(
            "SELECT 1 "
            "FROM organization_memberships "
            "WHERE user_id = app_user_id() "
            "AND org_role IN ('owner', 'admin') "
            "AND status = 'active' "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        )
    )
    if not membership_result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin requires owner/admin membership",
        )
