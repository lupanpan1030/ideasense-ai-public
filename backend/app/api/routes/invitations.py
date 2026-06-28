from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ActorContext, get_actor_context, get_admin_db_session

router = APIRouter(prefix="/invitations", tags=["invitations"])


class InvitationAcceptRequest(BaseModel):
    token: str


class InvitationAcceptResponse(BaseModel):
    status: Literal["accepted"]
    org_id: str


class InvitationDetailsResponse(BaseModel):
    invitee_email: str


def _normalize_token(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invitation token is required",
        )
    return cleaned


@router.get("/details", response_model=InvitationDetailsResponse)
async def invitation_details(
    token: str,
    session: AsyncSession = Depends(get_admin_db_session),
) -> InvitationDetailsResponse:
    normalized = _normalize_token(token)

    invite_result = await session.execute(
        text(
            "SELECT invitee_email, status, expires_at "
            "FROM organization_invitations "
            "WHERE token = :token "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"token": normalized},
    )
    invite = invite_result.mappings().first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    status_value = invite.get("status")
    if status_value == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation already accepted",
        )
    if status_value != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invitation is {status_value}",
        )

    expires_at = invite.get("expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    invitee_email = invite.get("invitee_email")
    if not invitee_email:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation is missing invitee email",
        )

    return InvitationDetailsResponse(invitee_email=invitee_email)


@router.post("/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    payload: InvitationAcceptRequest,
    session: AsyncSession = Depends(get_admin_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> InvitationAcceptResponse:
    token = _normalize_token(payload.token)

    user_result = await session.execute(
        text(
            "SELECT id, email "
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

    invite_result = await session.execute(
        text(
            "SELECT id, org_id, invitee_email, invited_role, invited_by, "
            "status, expires_at, accepted_user_id "
            "FROM organization_invitations "
            "WHERE token = :token "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"token": token},
    )
    invite = invite_result.mappings().first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    status_value = invite.get("status")
    if status_value == "accepted":
        accepted_user_id = invite.get("accepted_user_id")
        if accepted_user_id and str(accepted_user_id) != str(user.get("id")):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invitation already accepted by another user",
            )
    elif status_value != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invitation is {status_value}",
        )

    expires_at = invite.get("expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    invitee_email = invite.get("invitee_email")
    user_email = user.get("email")
    if not invitee_email or not user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation email mismatch",
        )
    if invitee_email.strip().lower() != str(user_email).strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation email mismatch",
        )

    org_id = invite.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation is missing organization",
        )

    org_result = await session.execute(
        text(
            "SELECT settings "
            "FROM organizations "
            "WHERE id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {"org_id": str(org_id)},
    )
    org = org_result.mappings().first()
    settings = org.get("settings") if org else None
    if isinstance(settings, dict) and settings.get("org_type") == "private":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Private organizations do not allow invitations.",
        )

    await session.execute(
        text(
            "INSERT INTO organization_memberships "
            "(org_id, user_id, org_role, status, created_by) "
            "VALUES (:org_id, :user_id, :org_role, 'active', :created_by) "
            "ON CONFLICT (org_id, user_id) "
            "WHERE deleted_at IS NULL DO NOTHING"
        ),
        {
            "org_id": str(org_id),
            "user_id": str(user.get("id")),
            "org_role": invite.get("invited_role"),
            "created_by": invite.get("invited_by"),
        },
    )

    if status_value == "pending":
        await session.execute(
            text(
                "UPDATE organization_invitations "
                "SET status = 'accepted', accepted_user_id = :user_id "
                "WHERE id = :invite_id "
                "AND status = 'pending' "
                "AND deleted_at IS NULL"
            ),
            {"invite_id": invite.get("id"), "user_id": str(user.get("id"))},
        )

    return InvitationAcceptResponse(status="accepted", org_id=str(org_id))
