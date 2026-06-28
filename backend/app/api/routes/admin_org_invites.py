import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability, require_org_not_private
from app.services.org_invite_links import (
    InviteLinkConfigurationError,
    build_invite_link,
)

router = APIRouter(prefix="/admin-api/org", tags=["admin"])

InviteRole = Literal["admin", "mentor", "student"]
InviteStatus = Literal["pending", "accepted", "expired", "revoked"]


class InviteUser(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None


class OrgInvite(BaseModel):
    id: UUID
    invitee_email: str
    invited_role: InviteRole
    status: InviteStatus
    token: str
    invite_link: str
    expires_at: datetime | None = None
    created_at: datetime


class OrgInvitesResponse(BaseModel):
    invites: list[OrgInvite]
    total: int
    page: int
    limit: int


class OrgInviteCreateRequest(BaseModel):
    email: str
    role: InviteRole


class OrgInviteCreateResponse(BaseModel):
    status: Literal["created", "restored"]
    invite_link: str | None = None
    token: str | None = None
    user: InviteUser | None = None


def _normalize_email(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required.",
        )
    if any(ch.isspace() for ch in cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email must not contain spaces.",
        )
    return cleaned


def _invite_link_or_http_error(token: str) -> str:
    try:
        return build_invite_link(token)
    except InviteLinkConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


async def _refresh_expired_invites(session: AsyncSession) -> None:
    await session.execute(
        text(
            "UPDATE organization_invitations "
            "SET status = 'expired' "
            "WHERE org_id = app_org_id() "
            "AND status = 'pending' "
            "AND expires_at IS NOT NULL "
            "AND expires_at < now() "
            "AND deleted_at IS NULL"
        )
    )


async def _find_pending_invite(
    session: AsyncSession, email: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, token "
            "FROM organization_invitations "
            "WHERE org_id = app_org_id() "
            "AND invitee_email = :email "
            "AND status = 'pending' "
            "AND deleted_at IS NULL"
        ),
        {"email": email},
    )
    return result.mappings().first()


async def _find_user_by_email(session: AsyncSession, email: str) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, email, display_name "
            "FROM users "
            "WHERE email = :email "
            "AND deleted_at IS NULL"
        ),
        {"email": email},
    )
    return result.mappings().first()


async def _find_membership(
    session: AsyncSession, user_id: UUID
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, status, org_role "
            "FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND user_id = :user_id "
            "AND deleted_at IS NULL"
        ),
        {"user_id": str(user_id)},
    )
    return result.mappings().first()


async def _generate_unique_token(session: AsyncSession) -> str:
    for _ in range(6):
        token = secrets.token_urlsafe(20)
        result = await session.execute(
            text(
                "SELECT 1 "
                "FROM organization_invitations "
                "WHERE org_id = app_org_id() "
                "AND token = :token "
                "AND deleted_at IS NULL"
            ),
            {"token": token},
        )
        if not result.first():
            return token
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate invite token.",
    )


@router.get("/invites", response_model=OrgInvitesResponse)
async def list_org_invites(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: InviteStatus | Literal["all"] = Query(
        "pending", alias="status"
    ),
    role: InviteRole | Literal["all"] | None = Query(default=None),
    q: str | None = Query(default=None),
) -> OrgInvitesResponse:
    await require_org_capability(session, "can_manage_invites")
    await _refresh_expired_invites(session)

    filters = ["oi.org_id = app_org_id()", "oi.deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": (page - 1) * limit}

    if status_filter != "all":
        filters.append("oi.status = :status")
        params["status"] = status_filter

    if role and role != "all":
        filters.append("oi.invited_role = :role")
        params["role"] = role

    if q:
        search_value = q.strip()
        if search_value:
            filters.append("oi.invitee_email ILIKE :search")
            params["search"] = f"%{search_value}%"

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM organization_invitations oi "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    invites_result = await session.execute(
        text(
            "SELECT "
            "oi.id, oi.invitee_email, oi.invited_role, oi.status, "
            "oi.token, oi.expires_at, oi.created_at "
            "FROM organization_invitations oi "
            f"WHERE {where_clause} "
            "ORDER BY oi.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    invites = []
    for row in invites_result.mappings().all():
        token = row.get("token")
        invites.append(
            {
                "id": row.get("id"),
                "invitee_email": row.get("invitee_email"),
                "invited_role": row.get("invited_role"),
                "status": row.get("status"),
                "token": token,
                "invite_link": _invite_link_or_http_error(token),
                "expires_at": row.get("expires_at"),
                "created_at": row.get("created_at"),
            }
        )

    return OrgInvitesResponse(
        invites=invites, total=total, page=page, limit=limit
    )


@router.post("/invites", response_model=OrgInviteCreateResponse)
async def create_org_invite(
    payload: OrgInviteCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> OrgInviteCreateResponse:
    await require_org_capability(session, "can_manage_invites")
    await require_org_not_private(
        session, detail="Private organizations do not allow invitations."
    )

    email = _normalize_email(payload.email)

    user = await _find_user_by_email(session, email)
    if user:
        membership = await _find_membership(session, user.get("id"))
        if membership:
            status_value = membership.get("status")
            if status_value == "removed":
                await session.execute(
                    text(
                        "UPDATE organization_memberships "
                        "SET status = 'active', org_role = :role "
                        "WHERE id = :membership_id "
                        "AND org_id = app_org_id() "
                        "AND deleted_at IS NULL"
                    ),
                    {
                        "membership_id": membership.get("id"),
                        "role": payload.role,
                    },
                )
                return OrgInviteCreateResponse(
                    status="restored",
                    user=InviteUser(
                        id=user.get("id"),
                        email=user.get("email"),
                        display_name=user.get("display_name"),
                    ),
                )
            if status_value in {"active", "invited"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a member.",
                )

    pending_invite = await _find_pending_invite(session, email)
    if pending_invite:
        await session.execute(
            text(
                "UPDATE organization_invitations "
                "SET invited_role = :role, "
                "expires_at = now() + interval '7 days', "
                "invited_by = app_user_id(), "
                "status = 'pending' "
                "WHERE id = :invite_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL"
            ),
            {"invite_id": pending_invite.get("id"), "role": payload.role},
        )
        token = pending_invite.get("token")
        return OrgInviteCreateResponse(
            status="created",
            token=token,
            invite_link=_invite_link_or_http_error(token),
        )

    token = await _generate_unique_token(session)
    result = await session.execute(
        text(
            "INSERT INTO organization_invitations "
            "(org_id, invitee_email, invited_role, invited_by, token, "
            "expires_at, status) "
            "VALUES (app_org_id(), :email, :role, app_user_id(), :token, "
            "now() + interval '7 days', 'pending') "
            "RETURNING id"
        ),
        {"email": email, "role": payload.role, "token": token},
    )
    invite = result.mappings().first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create invite.",
        )

    return OrgInviteCreateResponse(
        status="created",
        token=token,
        invite_link=_invite_link_or_http_error(token),
    )


@router.patch(
    "/invites/{invite_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrgInvite,
)
async def revoke_org_invite(
    invite_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> OrgInvite:
    await require_org_capability(session, "can_manage_invites")

    result = await session.execute(
        text(
            "SELECT id, invitee_email, invited_role, status, token, "
            "expires_at, created_at "
            "FROM organization_invitations "
            "WHERE id = :invite_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"invite_id": str(invite_id)},
    )
    invite = result.mappings().first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found.",
        )

    if invite.get("status") == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invite is already accepted.",
        )

    await session.execute(
        text(
            "UPDATE organization_invitations "
            "SET status = 'revoked' "
            "WHERE id = :invite_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"invite_id": str(invite_id)},
    )

    token = invite.get("token")
    return OrgInvite(
        id=invite.get("id"),
        invitee_email=invite.get("invitee_email"),
        invited_role=invite.get("invited_role"),
        status="revoked",
        token=token,
        invite_link=_invite_link_or_http_error(token),
        expires_at=invite.get("expires_at"),
        created_at=invite.get("created_at"),
    )
