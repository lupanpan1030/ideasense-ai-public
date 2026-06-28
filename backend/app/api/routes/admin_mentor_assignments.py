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

AssignmentStatus = Literal["pending", "active", "revoked"]


class AssignmentUser(BaseModel):
    id: UUID
    display_name: str | None = None
    email: str | None = None


class AssignmentCohort(BaseModel):
    id: UUID
    name: str


class MentorAssignment(BaseModel):
    id: UUID
    status: AssignmentStatus
    can_view_messages: bool
    can_view_facts: bool
    can_comment: bool
    created_at: datetime
    updated_at: datetime
    mentor: AssignmentUser
    student: AssignmentUser
    cohort: AssignmentCohort | None = None


class MentorAssignmentsResponse(BaseModel):
    assignments: list[MentorAssignment]
    total: int
    page: int
    limit: int


class MentorAssignmentCreateRequest(BaseModel):
    mentor_user_id: UUID
    student_user_id: UUID
    cohort_id: UUID | None = None
    can_view_messages: bool = False
    can_view_facts: bool = False
    can_comment: bool = True


class MentorAssignmentUpdateRequest(BaseModel):
    status: Literal["active", "revoked"] | None = None
    can_view_messages: bool | None = None
    can_view_facts: bool | None = None
    can_comment: bool | None = None


def _normalize_flags(
    can_view_messages: bool, can_view_facts: bool
) -> tuple[bool, bool]:
    if can_view_messages and not can_view_facts:
        return can_view_messages, True
    return can_view_messages, can_view_facts


async def _ensure_active_org_member(
    session: AsyncSession, user_id: UUID, label: str
) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM organization_memberships "
            "WHERE org_id = app_org_id() "
            "AND user_id = :user_id "
            "AND status = 'active' "
            "AND deleted_at IS NULL"
        ),
        {"user_id": str(user_id)},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} must be an active organization member.",
        )


async def _ensure_active_cohort_member(
    session: AsyncSession, cohort_id: UUID, user_id: UUID, label: str
) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM cohort_memberships "
            "WHERE org_id = app_org_id() "
            "AND cohort_id = :cohort_id "
            "AND user_id = :user_id "
            "AND status = 'active' "
            "AND deleted_at IS NULL"
        ),
        {"cohort_id": str(cohort_id), "user_id": str(user_id)},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} must be an active member of the selected cohort.",
        )


async def _ensure_cohort(session: AsyncSession, cohort_id: UUID) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM cohorts "
            "WHERE id = :cohort_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"cohort_id": str(cohort_id)},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )


async def _fetch_assignment(
    session: AsyncSession, assignment_id: UUID
) -> MentorAssignment:
    result = await session.execute(
        text(
            "SELECT "
            "msa.id, msa.status, msa.can_view_messages, msa.can_view_facts, "
            "msa.can_comment, msa.created_at, msa.updated_at, "
            "mentor.id AS mentor_id, mentor.display_name AS mentor_name, "
            "mentor.email AS mentor_email, "
            "student.id AS student_id, student.display_name AS student_name, "
            "student.email AS student_email, "
            "c.id AS cohort_id, c.name AS cohort_name "
            "FROM mentor_student_assignments msa "
            "LEFT JOIN users mentor ON mentor.id = msa.mentor_user_id "
            "AND mentor.deleted_at IS NULL "
            "LEFT JOIN users student ON student.id = msa.student_user_id "
            "AND student.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = msa.cohort_id "
            "AND c.org_id = msa.org_id "
            "AND c.deleted_at IS NULL "
            "WHERE msa.id = :assignment_id "
            "AND msa.org_id = app_org_id() "
            "AND msa.deleted_at IS NULL"
        ),
        {"assignment_id": str(assignment_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )
    cohort = None
    if row.get("cohort_id"):
        cohort = AssignmentCohort(
            id=row.get("cohort_id"),
            name=row.get("cohort_name"),
        )
    return MentorAssignment(
        id=row.get("id"),
        status=row.get("status"),
        can_view_messages=row.get("can_view_messages"),
        can_view_facts=row.get("can_view_facts"),
        can_comment=row.get("can_comment"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        mentor=AssignmentUser(
            id=row.get("mentor_id"),
            display_name=row.get("mentor_name"),
            email=row.get("mentor_email"),
        ),
        student=AssignmentUser(
            id=row.get("student_id"),
            display_name=row.get("student_name"),
            email=row.get("student_email"),
        ),
        cohort=cohort,
    )


@router.get("/mentor-assignments", response_model=MentorAssignmentsResponse)
async def list_mentor_assignments(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Literal["pending", "active", "revoked", "all"] = Query(
        "active", alias="status"
    ),
    cohort_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
) -> MentorAssignmentsResponse:
    await require_org_capability(session, "can_manage_assignments")

    filters = ["msa.org_id = app_org_id()", "msa.deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": (page - 1) * limit}

    if status_filter != "all":
        filters.append("msa.status = :status")
        params["status"] = status_filter

    if cohort_id:
        filters.append("msa.cohort_id = :cohort_id")
        params["cohort_id"] = str(cohort_id)

    if q:
        search_value = q.strip()
        if search_value:
            filters.append(
                "(mentor.display_name ILIKE :search OR mentor.email ILIKE :search "
                "OR student.display_name ILIKE :search OR student.email ILIKE :search)"
            )
            params["search"] = f"%{search_value}%"

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM mentor_student_assignments msa "
            "LEFT JOIN users mentor ON mentor.id = msa.mentor_user_id "
            "AND mentor.deleted_at IS NULL "
            "LEFT JOIN users student ON student.id = msa.student_user_id "
            "AND student.deleted_at IS NULL "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT "
            "msa.id, msa.status, msa.can_view_messages, msa.can_view_facts, "
            "msa.can_comment, msa.created_at, msa.updated_at, "
            "mentor.id AS mentor_id, mentor.display_name AS mentor_name, "
            "mentor.email AS mentor_email, "
            "student.id AS student_id, student.display_name AS student_name, "
            "student.email AS student_email, "
            "c.id AS cohort_id, c.name AS cohort_name "
            "FROM mentor_student_assignments msa "
            "LEFT JOIN users mentor ON mentor.id = msa.mentor_user_id "
            "AND mentor.deleted_at IS NULL "
            "LEFT JOIN users student ON student.id = msa.student_user_id "
            "AND student.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = msa.cohort_id "
            "AND c.org_id = msa.org_id "
            "AND c.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY msa.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    assignments: list[MentorAssignment] = []
    for row in result.mappings().all():
        cohort = None
        if row.get("cohort_id"):
            cohort = AssignmentCohort(
                id=row.get("cohort_id"),
                name=row.get("cohort_name"),
            )
        assignments.append(
            MentorAssignment(
                id=row.get("id"),
                status=row.get("status"),
                can_view_messages=row.get("can_view_messages"),
                can_view_facts=row.get("can_view_facts"),
                can_comment=row.get("can_comment"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                mentor=AssignmentUser(
                    id=row.get("mentor_id"),
                    display_name=row.get("mentor_name"),
                    email=row.get("mentor_email"),
                ),
                student=AssignmentUser(
                    id=row.get("student_id"),
                    display_name=row.get("student_name"),
                    email=row.get("student_email"),
                ),
                cohort=cohort,
            )
        )

    return MentorAssignmentsResponse(
        assignments=assignments,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/mentor-assignments", response_model=MentorAssignment)
async def create_mentor_assignment(
    payload: MentorAssignmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MentorAssignment:
    await require_org_capability(session, "can_manage_assignments")

    if payload.mentor_user_id == payload.student_user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mentor and student must be different users.",
        )

    await _ensure_active_org_member(session, payload.mentor_user_id, "Mentor")
    await _ensure_active_org_member(session, payload.student_user_id, "Student")

    if payload.cohort_id:
        await _ensure_cohort(session, payload.cohort_id)
        await _ensure_active_cohort_member(
            session, payload.cohort_id, payload.mentor_user_id, "Mentor"
        )
        await _ensure_active_cohort_member(
            session, payload.cohort_id, payload.student_user_id, "Student"
        )

    can_view_messages, can_view_facts = _normalize_flags(
        payload.can_view_messages, payload.can_view_facts
    )

    existing_result = await session.execute(
        text(
            "SELECT id FROM mentor_student_assignments "
            "WHERE org_id = app_org_id() "
            "AND mentor_user_id = :mentor_user_id "
            "AND student_user_id = :student_user_id "
            "AND cohort_id IS NOT DISTINCT FROM :cohort_id "
            "AND deleted_at IS NULL"
        ),
        {
            "mentor_user_id": str(payload.mentor_user_id),
            "student_user_id": str(payload.student_user_id),
            "cohort_id": str(payload.cohort_id) if payload.cohort_id else None,
        },
    )
    existing = existing_result.mappings().first()

    if existing:
        await session.execute(
            text(
                "UPDATE mentor_student_assignments "
                "SET status = 'active', "
                "can_view_messages = :can_view_messages, "
                "can_view_facts = :can_view_facts, "
                "can_comment = :can_comment "
                "WHERE id = :assignment_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL"
            ),
            {
                "assignment_id": existing.get("id"),
                "can_view_messages": can_view_messages,
                "can_view_facts": can_view_facts,
                "can_comment": payload.can_comment,
            },
        )
        return await _fetch_assignment(session, existing.get("id"))

    result = await session.execute(
        text(
            "INSERT INTO mentor_student_assignments "
            "(org_id, cohort_id, mentor_user_id, student_user_id, status, "
            "can_view_messages, can_view_facts, can_comment, created_by) "
            "VALUES (app_org_id(), :cohort_id, :mentor_user_id, :student_user_id, "
            "'active', :can_view_messages, :can_view_facts, :can_comment, "
            "app_user_id()) "
            "RETURNING id"
        ),
        {
            "cohort_id": str(payload.cohort_id) if payload.cohort_id else None,
            "mentor_user_id": str(payload.mentor_user_id),
            "student_user_id": str(payload.student_user_id),
            "can_view_messages": can_view_messages,
            "can_view_facts": can_view_facts,
            "can_comment": payload.can_comment,
        },
    )
    assignment_id = result.scalar()
    if not assignment_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create assignment.",
        )
    return await _fetch_assignment(session, assignment_id)


@router.patch("/mentor-assignments/{assignment_id}", response_model=MentorAssignment)
async def update_mentor_assignment(
    assignment_id: UUID,
    payload: MentorAssignmentUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MentorAssignment:
    await require_org_capability(session, "can_manage_assignments")

    current = await _fetch_assignment(session, assignment_id)

    next_status = payload.status or current.status
    if next_status not in ("active", "revoked"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status update.",
        )

    next_can_view_messages = (
        payload.can_view_messages
        if payload.can_view_messages is not None
        else current.can_view_messages
    )
    next_can_view_facts = (
        payload.can_view_facts
        if payload.can_view_facts is not None
        else current.can_view_facts
    )
    next_can_comment = (
        payload.can_comment
        if payload.can_comment is not None
        else current.can_comment
    )

    next_can_view_messages, next_can_view_facts = _normalize_flags(
        next_can_view_messages, next_can_view_facts
    )

    await session.execute(
        text(
            "UPDATE mentor_student_assignments "
            "SET status = :status, "
            "can_view_messages = :can_view_messages, "
            "can_view_facts = :can_view_facts, "
            "can_comment = :can_comment "
            "WHERE id = :assignment_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "assignment_id": str(assignment_id),
            "status": next_status,
            "can_view_messages": next_can_view_messages,
            "can_view_facts": next_can_view_facts,
            "can_comment": next_can_comment,
        },
    )

    return await _fetch_assignment(session, assignment_id)
