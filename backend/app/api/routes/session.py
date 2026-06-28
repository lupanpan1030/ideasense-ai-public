from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ActorContext,
    get_actor_context,
    get_admin_db_session,
    normalize_org_header,
    resolve_org_membership,
)
from app.core.permissions import resolve_org_capabilities

router = APIRouter()


def _resolve_capabilities(org_role: str | None, org_settings: dict | None) -> dict:
    return resolve_org_capabilities(org_role, org_settings)


@router.get("/session")
async def get_session(
    session: AsyncSession = Depends(get_admin_db_session),
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> dict:
    user_result = await session.execute(
        text(
            "SELECT id, email, display_name, email_verified_at "
            "FROM users "
            "WHERE id = :user_id "
            "AND deleted_at IS NULL "
            "AND is_active IS TRUE"
        ),
        {"user_id": actor.user_id},
    )
    user = user_result.mappings().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or inactive",
        )

    explicit_org_id = normalize_org_header(x_org_id)
    membership = await resolve_org_membership(
        session, user_id=actor.user_id, explicit_org_id=explicit_org_id
    )

    org_result = await session.execute(
        text(
            "SELECT id, name, settings "
            "FROM organizations "
            "WHERE id = :org_id AND deleted_at IS NULL"
        ),
        {"org_id": membership.get("org_id")},
    )
    org = org_result.mappings().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found or inactive",
        )

    org_role = membership.get("org_role")
    org_settings = org.get("settings") if org else None
    capabilities = _resolve_capabilities(org_role, org_settings)

    platform_result = await session.execute(
        text(
            "SELECT 1 "
            "FROM platform_admins "
            "WHERE user_id = :user_id "
            "AND status = 'active' "
            "AND deleted_at IS NULL"
        ),
        {"user_id": actor.user_id},
    )
    is_platform_admin = platform_result.first() is not None

    orgs_result = await session.execute(
        text(
            "SELECT "
            "om.org_id AS id, om.org_role, om.status, o.name "
            "FROM organization_memberships om "
            "JOIN organizations o ON o.id = om.org_id AND o.deleted_at IS NULL "
            "WHERE om.user_id = :user_id "
            "AND om.deleted_at IS NULL "
            "AND om.status <> 'removed' "
            "ORDER BY om.created_at DESC"
        ),
        {"user_id": actor.user_id},
    )
    orgs = [
        {
            "id": row.get("id"),
            "name": row.get("name"),
            "org_role": row.get("org_role"),
            "status": row.get("status"),
        }
        for row in orgs_result.mappings().all()
    ]

    return {
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "display_name": user.get("display_name"),
            "email_verified": bool(user.get("email_verified_at")),
        },
        "org": {
            "id": org.get("id"),
            "name": org.get("name"),
            "settings": org.get("settings") or {},
        },
        "membership": {
            "id": membership.get("id"),
            "org_role": org_role,
            "status": membership.get("status"),
        },
        "capabilities": capabilities,
        "orgs": orgs,
        "actor_type": actor.actor_type,
        "is_platform_admin": is_platform_admin,
    }
