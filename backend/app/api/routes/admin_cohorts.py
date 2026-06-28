from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability

router = APIRouter(prefix="/admin-api", tags=["admin"])

CohortStatusFilter = Literal["active", "archived", "all"]
CohortMemberStatus = Literal["active", "removed", "all"]
CohortMemberRole = Literal["student", "mentor"]
DetailTab = Literal["members", "mentors", "projects"]


class CohortSummary(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    students_count: int
    mentors_count: int
    projects_count: int


class CohortsResponse(BaseModel):
    cohorts: list[CohortSummary]
    total: int
    page: int
    limit: int


class CohortCreateRequest(BaseModel):
    name: str
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class CohortUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_archived: bool | None = None


class CohortMemberItem(BaseModel):
    membership_id: UUID
    user_id: UUID
    display_name: str | None = None
    email: str | None = None
    status: Literal["active", "removed"]
    joined_at: datetime
    role_in_cohort: CohortMemberRole


class CohortProjectItem(BaseModel):
    id: UUID
    title: str | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    current_stage: str | None = None
    stage_status: str | None = None
    is_archived: bool


class CohortDetailResponse(BaseModel):
    cohort: CohortSummary
    list_type: DetailTab
    items: list[CohortMemberItem | CohortProjectItem]
    total: int
    page: int
    limit: int


class CohortMembersAddRequest(BaseModel):
    role_in_cohort: CohortMemberRole
    user_ids: list[UUID]


class CohortMembersAddResponse(BaseModel):
    added: int
    updated: int
    restored: int


def _normalize_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cohort name is required.",
        )
    return cleaned


async def _get_cohort(session: AsyncSession, cohort_id: UUID) -> dict:
    result = await session.execute(
        text(
            "SELECT id, name, description, start_at, end_at, is_archived, "
            "created_at, updated_at "
            "FROM cohorts "
            "WHERE id = :cohort_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"cohort_id": str(cohort_id)},
    )
    cohort = result.mappings().first()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )
    return cohort


async def _get_cohort_counts(session: AsyncSession, cohort_id: UUID) -> dict:
    result = await session.execute(
        text(
            "SELECT "
            "(SELECT COUNT(*) FROM cohort_memberships cm "
            " WHERE cm.cohort_id = :cohort_id "
            " AND cm.role_in_cohort = 'student' "
            " AND cm.status = 'active' "
            " AND cm.deleted_at IS NULL) AS students_count, "
            "(SELECT COUNT(*) FROM cohort_memberships cm "
            " WHERE cm.cohort_id = :cohort_id "
            " AND cm.role_in_cohort = 'mentor' "
            " AND cm.status = 'active' "
            " AND cm.deleted_at IS NULL) AS mentors_count, "
            "(SELECT COUNT(*) FROM projects p "
            " WHERE p.cohort_id = :cohort_id "
            " AND p.deleted_at IS NULL) AS projects_count"
        ),
        {"cohort_id": str(cohort_id)},
    )
    return result.mappings().first() or {}


@router.get("/cohorts", response_model=CohortsResponse)
async def list_cohorts(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: CohortStatusFilter = Query("active", alias="status"),
    q: str | None = Query(default=None),
) -> CohortsResponse:
    await require_org_capability(session, "can_manage_cohorts")

    filters = ["c.org_id = app_org_id()", "c.deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": (page - 1) * limit}

    if status_filter == "active":
        filters.append("c.is_archived IS FALSE")
    elif status_filter == "archived":
        filters.append("c.is_archived IS TRUE")

    if q:
        search_value = q.strip()
        if search_value:
            filters.append("c.name ILIKE :search")
            params["search"] = f"%{search_value}%"

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM cohorts c "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT "
            "c.id, c.name, c.description, c.start_at, c.end_at, c.is_archived, "
            "c.created_at, c.updated_at, "
            "(SELECT COUNT(*) FROM cohort_memberships cm "
            " WHERE cm.cohort_id = c.id "
            " AND cm.role_in_cohort = 'student' "
            " AND cm.status = 'active' "
            " AND cm.deleted_at IS NULL) AS students_count, "
            "(SELECT COUNT(*) FROM cohort_memberships cm "
            " WHERE cm.cohort_id = c.id "
            " AND cm.role_in_cohort = 'mentor' "
            " AND cm.status = 'active' "
            " AND cm.deleted_at IS NULL) AS mentors_count, "
            "(SELECT COUNT(*) FROM projects p "
            " WHERE p.cohort_id = c.id "
            " AND p.deleted_at IS NULL) AS projects_count "
            "FROM cohorts c "
            f"WHERE {where_clause} "
            "ORDER BY c.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    cohorts = []
    for row in result.mappings().all():
        cohorts.append(
            CohortSummary(
                id=row.get("id"),
                name=row.get("name"),
                description=row.get("description"),
                start_at=row.get("start_at"),
                end_at=row.get("end_at"),
                is_archived=row.get("is_archived"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                students_count=row.get("students_count") or 0,
                mentors_count=row.get("mentors_count") or 0,
                projects_count=row.get("projects_count") or 0,
            )
        )

    return CohortsResponse(
        cohorts=cohorts,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/cohorts", response_model=CohortSummary)
async def create_cohort(
    payload: CohortCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CohortSummary:
    await require_org_capability(session, "can_manage_cohorts")
    name = _normalize_name(payload.name)

    existing = await session.execute(
        text(
            "SELECT 1 FROM cohorts "
            "WHERE org_id = app_org_id() "
            "AND name = :name "
            "AND deleted_at IS NULL"
        ),
        {"name": name},
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cohort name is already in use.",
        )

    result = await session.execute(
        text(
            "INSERT INTO cohorts "
            "(org_id, name, description, start_at, end_at, is_archived) "
            "VALUES (app_org_id(), :name, :description, :start_at, :end_at, false) "
            "RETURNING id, name, description, start_at, end_at, is_archived, "
            "created_at, updated_at"
        ),
        {
            "name": name,
            "description": payload.description,
            "start_at": payload.start_at,
            "end_at": payload.end_at,
        },
    )
    cohort = result.mappings().first()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create cohort.",
        )

    return CohortSummary(
        id=cohort.get("id"),
        name=cohort.get("name"),
        description=cohort.get("description"),
        start_at=cohort.get("start_at"),
        end_at=cohort.get("end_at"),
        is_archived=cohort.get("is_archived"),
        created_at=cohort.get("created_at"),
        updated_at=cohort.get("updated_at"),
        students_count=0,
        mentors_count=0,
        projects_count=0,
    )


@router.patch("/cohorts/{cohort_id}", response_model=CohortSummary)
async def update_cohort(
    cohort_id: UUID,
    payload: CohortUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CohortSummary:
    await require_org_capability(session, "can_manage_cohorts")

    if payload.name is not None:
        name = _normalize_name(payload.name)
        existing = await session.execute(
            text(
                "SELECT 1 FROM cohorts "
                "WHERE org_id = app_org_id() "
                "AND name = :name "
                "AND id <> :cohort_id "
                "AND deleted_at IS NULL"
            ),
            {"name": name, "cohort_id": str(cohort_id)},
        )
        if existing.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cohort name is already in use.",
            )
    else:
        name = None

    result = await session.execute(
        text(
            "UPDATE cohorts "
            "SET name = COALESCE(:name, name), "
            "description = COALESCE(:description, description), "
            "start_at = COALESCE(:start_at, start_at), "
            "end_at = COALESCE(:end_at, end_at), "
            "is_archived = COALESCE(:is_archived, is_archived) "
            "WHERE id = :cohort_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "RETURNING id, name, description, start_at, end_at, is_archived, "
            "created_at, updated_at"
        ),
        {
            "name": name,
            "description": payload.description,
            "start_at": payload.start_at,
            "end_at": payload.end_at,
            "is_archived": payload.is_archived,
            "cohort_id": str(cohort_id),
        },
    )
    cohort = result.mappings().first()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    counts = await _get_cohort_counts(session, cohort_id)
    return CohortSummary(
        id=cohort.get("id"),
        name=cohort.get("name"),
        description=cohort.get("description"),
        start_at=cohort.get("start_at"),
        end_at=cohort.get("end_at"),
        is_archived=cohort.get("is_archived"),
        created_at=cohort.get("created_at"),
        updated_at=cohort.get("updated_at"),
        students_count=counts.get("students_count") or 0,
        mentors_count=counts.get("mentors_count") or 0,
        projects_count=counts.get("projects_count") or 0,
    )


@router.get("/cohorts/{cohort_id}", response_model=CohortDetailResponse)
async def get_cohort_detail(
    cohort_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    tab: DetailTab = Query("members"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: CohortMemberStatus = Query("active", alias="status"),
    q: str | None = Query(default=None),
) -> CohortDetailResponse:
    await require_org_capability(session, "can_manage_cohorts")
    cohort = await _get_cohort(session, cohort_id)
    counts = await _get_cohort_counts(session, cohort_id)

    offset = (page - 1) * limit
    params: dict[str, object] = {
        "cohort_id": str(cohort_id),
        "limit": limit,
        "offset": offset,
    }

    if tab in {"members", "mentors"}:
        role = "student" if tab == "members" else "mentor"
        filters = [
            "cm.cohort_id = :cohort_id",
            "cm.org_id = app_org_id()",
            "cm.deleted_at IS NULL",
            "cm.role_in_cohort = :role",
        ]
        params["role"] = role
        if status_filter != "all":
            filters.append("cm.status = :status")
            params["status"] = status_filter
        if q:
            search_value = q.strip()
            if search_value:
                filters.append("(u.display_name ILIKE :search OR u.email ILIKE :search)")
                params["search"] = f"%{search_value}%"

        where_clause = " AND ".join(filters)
        count_result = await session.execute(
            text(
                "SELECT COUNT(*) AS total "
                "FROM cohort_memberships cm "
                "LEFT JOIN users u ON u.id = cm.user_id AND u.deleted_at IS NULL "
                f"WHERE {where_clause}"
            ),
            params,
        )
        total = count_result.mappings().first().get("total") or 0

        result = await session.execute(
            text(
                "SELECT cm.id AS membership_id, cm.user_id, cm.status, "
                "cm.joined_at, cm.role_in_cohort, "
                "u.display_name, u.email "
                "FROM cohort_memberships cm "
                "LEFT JOIN users u ON u.id = cm.user_id AND u.deleted_at IS NULL "
                f"WHERE {where_clause} "
                "ORDER BY COALESCE(u.display_name, u.email, '') ASC, cm.joined_at ASC "
                "LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        items = [
            CohortMemberItem(
                membership_id=row.get("membership_id"),
                user_id=row.get("user_id"),
                display_name=row.get("display_name"),
                email=row.get("email"),
                status=row.get("status"),
                joined_at=row.get("joined_at"),
                role_in_cohort=row.get("role_in_cohort"),
            )
            for row in result.mappings().all()
        ]
    else:
        filters = [
            "p.cohort_id = :cohort_id",
            "p.org_id = app_org_id()",
            "p.deleted_at IS NULL",
        ]
        if q:
            search_value = q.strip()
            if search_value:
                filters.append(
                    "(p.title ILIKE :search OR u.display_name ILIKE :search "
                    "OR u.email ILIKE :search)"
                )
                params["search"] = f"%{search_value}%"
        where_clause = " AND ".join(filters)

        count_result = await session.execute(
            text(
                "SELECT COUNT(*) AS total "
                "FROM projects p "
                "LEFT JOIN users u ON u.id = p.owner_user_id "
                "AND u.deleted_at IS NULL "
                f"WHERE {where_clause}"
            ),
            params,
        )
        total = count_result.mappings().first().get("total") or 0

        result = await session.execute(
            text(
                "SELECT p.id, p.title, p.current_stage, p.stage_status, "
                "p.is_archived, "
                "u.display_name AS owner_name, u.email AS owner_email "
                "FROM projects p "
                "LEFT JOIN users u ON u.id = p.owner_user_id "
                "AND u.deleted_at IS NULL "
                f"WHERE {where_clause} "
                "ORDER BY p.created_at DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        items = [
            CohortProjectItem(
                id=row.get("id"),
                title=row.get("title"),
                owner_name=row.get("owner_name"),
                owner_email=row.get("owner_email"),
                current_stage=row.get("current_stage"),
                stage_status=row.get("stage_status"),
                is_archived=row.get("is_archived"),
            )
            for row in result.mappings().all()
        ]

    cohort_summary = CohortSummary(
        id=cohort.get("id"),
        name=cohort.get("name"),
        description=cohort.get("description"),
        start_at=cohort.get("start_at"),
        end_at=cohort.get("end_at"),
        is_archived=cohort.get("is_archived"),
        created_at=cohort.get("created_at"),
        updated_at=cohort.get("updated_at"),
        students_count=counts.get("students_count") or 0,
        mentors_count=counts.get("mentors_count") or 0,
        projects_count=counts.get("projects_count") or 0,
    )

    return CohortDetailResponse(
        cohort=cohort_summary,
        list_type=tab,
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/cohorts/{cohort_id}/members", response_model=CohortMembersAddResponse)
async def add_cohort_members(
    cohort_id: UUID,
    payload: CohortMembersAddRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CohortMembersAddResponse:
    await require_org_capability(session, "can_manage_cohorts")
    await _get_cohort(session, cohort_id)

    if not payload.user_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one user is required.",
        )

    active_result = await session.execute(
        text(
            "SELECT user_id "
            "FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND status = 'active' "
            "AND deleted_at IS NULL"
        )
    )
    active_users = {row.get("user_id") for row in active_result.mappings().all()}
    for user_id in payload.user_ids:
        if user_id not in active_users:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All users must be active organization members.",
            )

    added = 0
    updated = 0
    restored = 0
    for user_id in payload.user_ids:
        existing_result = await session.execute(
            text(
                "SELECT id, status, role_in_cohort "
                "FROM cohort_memberships "
                "WHERE cohort_id = :cohort_id "
                "AND user_id = :user_id "
                "AND deleted_at IS NULL"
            ),
            {"cohort_id": str(cohort_id), "user_id": str(user_id)},
        )
        existing = existing_result.mappings().first()
        if existing:
            status_value = existing.get("status")
            if status_value == "removed":
                restored += 1
            else:
                updated += 1
            await session.execute(
                text(
                    "UPDATE cohort_memberships "
                    "SET status = 'active', role_in_cohort = :role "
                    "WHERE id = :membership_id "
                    "AND org_id = app_org_id() "
                    "AND deleted_at IS NULL"
                ),
                {
                    "membership_id": existing.get("id"),
                    "role": payload.role_in_cohort,
                },
            )
        else:
            added += 1
            await session.execute(
                text(
                    "INSERT INTO cohort_memberships "
                    "(org_id, cohort_id, user_id, role_in_cohort, status) "
                    "VALUES (app_org_id(), :cohort_id, :user_id, :role, 'active')"
                ),
                {
                    "cohort_id": str(cohort_id),
                    "user_id": str(user_id),
                    "role": payload.role_in_cohort,
                },
            )

    return CohortMembersAddResponse(
        added=added,
        updated=updated,
        restored=restored,
    )


@router.delete(
    "/cohorts/{cohort_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_cohort_member(
    cohort_id: UUID,
    membership_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await require_org_capability(session, "can_manage_cohorts")
    await _get_cohort(session, cohort_id)

    result = await session.execute(
        text(
            "SELECT id "
            "FROM cohort_memberships "
            "WHERE id = :membership_id "
            "AND cohort_id = :cohort_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"membership_id": str(membership_id), "cohort_id": str(cohort_id)},
    )
    membership = result.mappings().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort membership not found.",
        )

    await session.execute(
        text(
            "UPDATE cohort_memberships "
            "SET status = 'removed' "
            "WHERE id = :membership_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"membership_id": str(membership_id)},
    )
