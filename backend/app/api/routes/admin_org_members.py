from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import is_private_org, require_org_capability

router = APIRouter(prefix="/admin-api/org", tags=["admin"])

OrgRole = Literal["owner", "admin", "mentor", "student"]
MutableOrgRole = Literal["admin", "mentor", "student"]
MembershipStatus = Literal["active", "invited", "removed"]


class MemberUser(BaseModel):
    id: UUID | None = None
    display_name: str | None = None
    email: str | None = None


class OrgMember(BaseModel):
    id: UUID
    org_role: OrgRole
    status: MembershipStatus
    created_at: datetime
    user: MemberUser | None = None


class OrgMembersResponse(BaseModel):
    members: list[OrgMember]
    total: int
    limit: int
    offset: int


class OrgMemberUpdate(BaseModel):
    role: MutableOrgRole | None = None
    status: MembershipStatus | None = None


class OwnershipTransferRequest(BaseModel):
    new_owner_user_id: UUID
    transfer_projects: bool = False


class OwnershipTransferResponse(BaseModel):
    previous_owner_user_id: UUID
    new_owner_user_id: UUID
    transfer_projects: bool
    updated_projects: int = 0


def _serialize_member(row: dict) -> dict:
    user_id = row.get("user_id")
    user = None
    if user_id:
        user = {
            "id": user_id,
            "display_name": row.get("display_name"),
            "email": row.get("email"),
        }
    return {
        "id": row.get("id"),
        "org_role": row.get("org_role"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "user": user,
    }


async def _get_membership(
    session: AsyncSession, membership_id: UUID
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, org_role, status "
            "FROM organization_memberships "
            "WHERE id = :membership_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"membership_id": str(membership_id)},
    )
    return result.mappings().first()


@router.get("/members", response_model=OrgMembersResponse)
async def list_org_members(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role: MutableOrgRole | Literal["owner"] | None = Query(default=None),
    status_filter: MembershipStatus | None = Query(default=None, alias="status"),
    roles: str | None = Query(default=None),
    exclude_cohort_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
) -> OrgMembersResponse:
    await require_org_capability(session, "can_manage_members")

    filters = ["om.org_id = app_org_id()", "om.deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": offset}

    allowed_roles = {"owner", "admin", "mentor", "student"}
    role_values: list[str] = []
    if roles:
        role_values = [value.strip() for value in roles.split(",") if value.strip()]
    if role:
        role_values.append(role)
    if role_values:
        invalid_roles = [value for value in role_values if value not in allowed_roles]
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid role filter.",
            )
        placeholders = []
        for index, value in enumerate(role_values):
            key = f"role_{index}"
            params[key] = value
            placeholders.append(f":{key}")
        filters.append(f"om.org_role IN ({', '.join(placeholders)})")

    if status_filter:
        filters.append("om.status = :status")
        params["status"] = status_filter

    if exclude_cohort_id:
        filters.append(
            "NOT EXISTS ("
            "SELECT 1 FROM cohort_memberships cm "
            "WHERE cm.org_id = om.org_id "
            "AND cm.cohort_id = :exclude_cohort_id "
            "AND cm.user_id = om.user_id "
            "AND cm.status = 'active' "
            "AND cm.deleted_at IS NULL)"
        )
        params["exclude_cohort_id"] = str(exclude_cohort_id)

    if q:
        search_value = q.strip()
        if search_value:
            filters.append("(u.display_name ILIKE :search OR u.email ILIKE :search)")
            params["search"] = f"%{search_value}%"

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM organization_memberships om "
            "LEFT JOIN users u ON u.id = om.user_id AND u.deleted_at IS NULL "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT "
            "om.id, om.org_role, om.status, om.created_at, "
            "u.id AS user_id, u.display_name, u.email "
            "FROM organization_memberships om "
            "LEFT JOIN users u ON u.id = om.user_id AND u.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY COALESCE(u.display_name, u.email, '') ASC, om.created_at ASC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    members = [_serialize_member(row) for row in result.mappings().all()]

    return OrgMembersResponse(
        members=members, total=total, limit=limit, offset=offset
    )


@router.patch("/members/{membership_id}", response_model=OrgMember)
async def update_org_member(
    membership_id: UUID,
    payload: OrgMemberUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> OrgMember:
    await require_org_capability(session, "can_manage_members")

    if payload.role is None and payload.status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field is required.",
        )

    membership = await _get_membership(session, membership_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )

    if membership.get("org_role") == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner membership cannot be modified.",
        )

    await session.execute(
        text(
            "UPDATE organization_memberships "
            "SET org_role = COALESCE(:role, org_role), "
            "status = COALESCE(:status, status) "
            "WHERE id = :membership_id AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "membership_id": str(membership_id),
            "role": payload.role,
            "status": payload.status,
        },
    )

    result = await session.execute(
        text(
            "SELECT "
            "om.id, om.org_role, om.status, om.created_at, "
            "u.id AS user_id, u.display_name, u.email "
            "FROM organization_memberships om "
            "LEFT JOIN users u ON u.id = om.user_id AND u.deleted_at IS NULL "
            "WHERE om.id = :membership_id "
            "AND om.org_id = app_org_id() "
            "AND om.deleted_at IS NULL"
        ),
        {"membership_id": str(membership_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )
    return OrgMember(**_serialize_member(row))


@router.delete("/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    membership_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await require_org_capability(session, "can_manage_members")

    membership = await _get_membership(session, membership_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )

    if membership.get("org_role") == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner membership cannot be removed.",
        )

    await session.execute(
        text(
            "UPDATE organization_memberships "
            "SET status = 'removed' "
            "WHERE id = :membership_id AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"membership_id": str(membership_id)},
    )


@router.post("/transfer-ownership", response_model=OwnershipTransferResponse)
async def transfer_ownership(
    payload: OwnershipTransferRequest,
    session: AsyncSession = Depends(get_db_session),
) -> OwnershipTransferResponse:
    await require_org_capability(session, "can_transfer_ownership")
    private_org = await is_private_org(session)

    if not payload.new_owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="new_owner_user_id is required",
        )

    owner_result = await session.execute(
        text(
            "SELECT id, user_id "
            "FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND org_role = 'owner' "
            "AND status = 'active' "
            "AND deleted_at IS NULL "
            "FOR UPDATE"
        )
    )
    owners = owner_result.mappings().all()
    if len(owners) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization must have exactly one active owner.",
        )
    current_owner = owners[0]
    current_owner_user_id = current_owner.get("user_id")

    target_result = await session.execute(
        text(
            "SELECT id, user_id, status "
            "FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND user_id = :user_id "
            "AND deleted_at IS NULL "
            "FOR UPDATE"
        ),
        {"user_id": str(payload.new_owner_user_id)},
    )
    target = target_result.mappings().first()
    if not target or target.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user is not an active organization member.",
        )

    if str(current_owner_user_id) == str(payload.new_owner_user_id):
        return OwnershipTransferResponse(
            previous_owner_user_id=current_owner_user_id,
            new_owner_user_id=payload.new_owner_user_id,
            transfer_projects=payload.transfer_projects,
            updated_projects=0,
        )

    if private_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Private organizations do not support ownership transfer.",
        )

    await session.execute(
        text(
            "UPDATE organization_memberships "
            "SET org_role = 'admin', updated_at = now() "
            "WHERE id = :membership_id"
        ),
        {"membership_id": str(current_owner.get("id"))},
    )

    await session.execute(
        text(
            "UPDATE organization_memberships "
            "SET org_role = 'owner', updated_at = now() "
            "WHERE id = :membership_id"
        ),
        {"membership_id": str(target.get("id"))},
    )

    updated_projects = 0
    if payload.transfer_projects:
        project_result = await session.execute(
            text(
                "UPDATE projects "
                "SET owner_user_id = :new_owner_user_id, updated_at = now() "
                "WHERE org_id = app_org_id() "
                "AND owner_user_id = :current_owner_user_id "
                "AND deleted_at IS NULL"
            ),
            {
                "new_owner_user_id": str(payload.new_owner_user_id),
                "current_owner_user_id": str(current_owner_user_id),
            },
        )
        updated_projects = project_result.rowcount or 0

    return OwnershipTransferResponse(
        previous_owner_user_id=current_owner_user_id,
        new_owner_user_id=payload.new_owner_user_id,
        transfer_projects=payload.transfer_projects,
        updated_projects=updated_projects,
    )
