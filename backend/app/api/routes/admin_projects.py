from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability
from app.services.prompt_trace_debug import fetch_project_prompt_task_traces

router = APIRouter(prefix="/admin-api", tags=["admin"])

StageFilter = Literal["problem", "market", "tech", "report", "all"]
StageStatusFilter = Literal["in_progress", "awaiting_confirm", "passed", "all"]


class ProjectOwner(BaseModel):
    id: UUID | None = None
    display_name: str | None = None
    email: str | None = None


class ProjectCohort(BaseModel):
    id: UUID
    name: str
    is_archived: bool


class ProjectSummary(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    current_stage: str | None = None
    stage_status: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    owner: ProjectOwner
    cohort: ProjectCohort | None = None


class ProjectsResponse(BaseModel):
    projects: list[ProjectSummary]
    total: int
    page: int
    limit: int


class ProjectDetail(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    current_stage: str | None = None
    stage_status: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    owner: ProjectOwner
    cohort: ProjectCohort | None = None


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    current_stage: Literal["problem", "market", "tech", "report"] | None = None
    stage_status: Literal["in_progress", "awaiting_confirm", "passed"] | None = None


class ProjectReportItem(BaseModel):
    id: UUID
    report_version: int
    status: str
    created_at: datetime
    updated_at: datetime
    confirmed: bool
    content_markdown: str | None = None


class ProjectReportsResponse(BaseModel):
    reports: list[ProjectReportItem]


class ProjectPromptTaskTraceItem(BaseModel):
    source_type: Literal[
        "answer_evaluation",
        "stage_assessment",
        "project_report",
    ]
    source_id: UUID
    stage: str | None = None
    task_key: str
    provider: str | None = None
    model: str | None = None
    failure_reason: str | None = None
    timeout_ms: int | None = None
    latency_ms: int | None = None
    parse_status: str | None = None
    allowed_mutation: str | None = None
    redacted: bool | None = None
    created_at: datetime


class ProjectPromptTaskTracesResponse(BaseModel):
    project_id: UUID
    traces: list[ProjectPromptTaskTraceItem]


class ProjectCommentAuthor(BaseModel):
    id: UUID | None = None
    display_name: str | None = None
    email: str | None = None


class ProjectCommentItem(BaseModel):
    id: UUID
    content: str
    visibility: str
    created_at: datetime
    author: ProjectCommentAuthor


class ProjectCommentsResponse(BaseModel):
    comments: list[ProjectCommentItem]
    total: int
    page: int
    limit: int


class ProjectCommentCreateRequest(BaseModel):
    content: str
    visibility: Literal["student_and_mentors", "mentors_only", "private"] | None = None


def _normalize_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} cannot be empty.",
        )
    return cleaned


async def _ensure_project(session: AsyncSession, project_id: UUID) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM projects "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"project_id": str(project_id)},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )


@router.get("/projects", response_model=ProjectsResponse)
async def list_projects(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    cohort_id: UUID | None = Query(default=None),
    stage: StageFilter | None = Query(default=None),
    status_filter: StageStatusFilter | None = Query(default=None, alias="status"),
    owner_user_id: UUID | None = Query(default=None),
    owner_query: str | None = Query(default=None, alias="owner"),
    include_archived: bool = Query(False),
) -> ProjectsResponse:
    await require_org_capability(session, "can_manage_projects")

    filters = ["p.org_id = app_org_id()", "p.deleted_at IS NULL"]
    params: dict[str, object] = {"limit": limit, "offset": (page - 1) * limit}

    if not include_archived:
        filters.append("p.is_archived = false")

    if stage and stage != "all":
        filters.append("p.current_stage = :stage")
        params["stage"] = stage

    if status_filter and status_filter != "all":
        filters.append("p.stage_status = :stage_status")
        params["stage_status"] = status_filter

    if cohort_id:
        filters.append("p.cohort_id = :cohort_id")
        params["cohort_id"] = str(cohort_id)

    if owner_user_id:
        filters.append("p.owner_user_id = :owner_user_id")
        params["owner_user_id"] = str(owner_user_id)

    if owner_query:
        search_value = owner_query.strip()
        if search_value:
            filters.append(
                "(owner.display_name ILIKE :owner_search OR owner.email ILIKE :owner_search)"
            )
            params["owner_search"] = f"%{search_value}%"

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM projects p "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT "
            "p.id, p.title, p.description, p.current_stage, p.stage_status, "
            "p.is_archived, p.created_at, p.updated_at, "
            "owner.id AS owner_id, owner.display_name AS owner_name, "
            "owner.email AS owner_email, "
            "c.id AS cohort_id, c.name AS cohort_name, c.is_archived AS cohort_archived "
            "FROM projects p "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = p.cohort_id "
            "AND c.org_id = p.org_id "
            "AND c.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY p.updated_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    projects: list[ProjectSummary] = []
    for row in result.mappings().all():
        cohort = None
        if row.get("cohort_id"):
            cohort = ProjectCohort(
                id=row.get("cohort_id"),
                name=row.get("cohort_name"),
                is_archived=row.get("cohort_archived") or False,
            )
        projects.append(
            ProjectSummary(
                id=row.get("id"),
                title=row.get("title"),
                description=row.get("description"),
                current_stage=row.get("current_stage"),
                stage_status=row.get("stage_status"),
                is_archived=row.get("is_archived"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                owner=ProjectOwner(
                    id=row.get("owner_id"),
                    display_name=row.get("owner_name"),
                    email=row.get("owner_email"),
                ),
                cohort=cohort,
            )
        )

    return ProjectsResponse(
        projects=projects,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_detail(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectDetail:
    await require_org_capability(session, "can_manage_projects")

    result = await session.execute(
        text(
            "SELECT "
            "p.id, p.title, p.description, p.current_stage, p.stage_status, "
            "p.is_archived, p.created_at, p.updated_at, "
            "owner.id AS owner_id, owner.display_name AS owner_name, "
            "owner.email AS owner_email, "
            "c.id AS cohort_id, c.name AS cohort_name, c.is_archived AS cohort_archived "
            "FROM projects p "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = p.cohort_id "
            "AND c.org_id = p.org_id "
            "AND c.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL"
        ),
        {"project_id": str(project_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    cohort = None
    if row.get("cohort_id"):
        cohort = ProjectCohort(
            id=row.get("cohort_id"),
            name=row.get("cohort_name"),
            is_archived=row.get("cohort_archived") or False,
        )

    return ProjectDetail(
        id=row.get("id"),
        title=row.get("title"),
        description=row.get("description"),
        current_stage=row.get("current_stage"),
        stage_status=row.get("stage_status"),
        is_archived=row.get("is_archived"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        owner=ProjectOwner(
            id=row.get("owner_id"),
            display_name=row.get("owner_name"),
            email=row.get("owner_email"),
        ),
        cohort=cohort,
    )


@router.patch("/projects/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectDetail:
    await require_org_capability(session, "can_manage_projects")

    title = _normalize_text(payload.title, "Title")
    description = None
    if payload.description is not None:
        trimmed_description = payload.description.strip()
        description = trimmed_description or None

    updates = []
    params: dict[str, object] = {"project_id": str(project_id)}

    if title is not None:
        updates.append("title = :title")
        params["title"] = title
    if payload.description is not None:
        updates.append("description = :description")
        params["description"] = description
    # Admin-only repair override. Normal stage engine writes go through stage_runtime.
    if payload.current_stage is not None:
        updates.append("current_stage = :current_stage")
        params["current_stage"] = payload.current_stage
    if payload.stage_status is not None:
        updates.append("stage_status = :stage_status")
        params["stage_status"] = payload.stage_status

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No updates provided.",
        )

    await session.execute(
        text(
            "UPDATE projects "
            f"SET {', '.join(updates)} "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        params,
    )

    return await get_project_detail(project_id, session)


@router.get("/projects/{project_id}/reports", response_model=ProjectReportsResponse)
async def list_project_reports(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectReportsResponse:
    await require_org_capability(session, "can_manage_projects")
    await _ensure_project(session, project_id)

    result = await session.execute(
        text(
            "SELECT id, report_version, status, created_at, updated_at, "
            "confirmed, content_markdown "
            "FROM project_reports "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"project_id": str(project_id)},
    )
    reports = [
        ProjectReportItem(
            id=row.get("id"),
            report_version=row.get("report_version"),
            status=row.get("status"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            confirmed=row.get("confirmed"),
            content_markdown=row.get("content_markdown"),
        )
        for row in result.mappings().all()
    ]
    return ProjectReportsResponse(reports=reports)


@router.get(
    "/projects/{project_id}/prompt-task-traces",
    response_model=ProjectPromptTaskTracesResponse,
)
async def list_project_prompt_task_traces(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectPromptTaskTracesResponse:
    await require_org_capability(session, "is_org_admin")
    await _ensure_project(session, project_id)
    traces = await fetch_project_prompt_task_traces(session, project_id)
    return ProjectPromptTaskTracesResponse(project_id=project_id, traces=traces)


@router.get("/projects/{project_id}/comments", response_model=ProjectCommentsResponse)
async def list_project_comments(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ProjectCommentsResponse:
    await require_org_capability(session, "can_manage_projects")
    await _ensure_project(session, project_id)

    params = {"project_id": str(project_id), "limit": limit, "offset": (page - 1) * limit}

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM project_comments pc "
            "WHERE pc.project_id = :project_id "
            "AND pc.org_id = app_org_id() "
            "AND pc.deleted_at IS NULL"
        ),
        params,
    )
    total = count_result.mappings().first().get("total") or 0

    result = await session.execute(
        text(
            "SELECT pc.id, pc.content, pc.visibility, pc.created_at, "
            "u.id AS author_id, u.display_name AS author_name, "
            "u.email AS author_email "
            "FROM project_comments pc "
            "LEFT JOIN users u ON u.id = pc.author_user_id "
            "AND u.deleted_at IS NULL "
            "WHERE pc.project_id = :project_id "
            "AND pc.org_id = app_org_id() "
            "AND pc.deleted_at IS NULL "
            "ORDER BY pc.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    comments = [
        ProjectCommentItem(
            id=row.get("id"),
            content=row.get("content"),
            visibility=row.get("visibility"),
            created_at=row.get("created_at"),
            author=ProjectCommentAuthor(
                id=row.get("author_id"),
                display_name=row.get("author_name"),
                email=row.get("author_email"),
            ),
        )
        for row in result.mappings().all()
    ]
    return ProjectCommentsResponse(
        comments=comments, total=total, page=page, limit=limit
    )


@router.post("/projects/{project_id}/comments", response_model=ProjectCommentItem)
async def create_project_comment(
    project_id: UUID,
    payload: ProjectCommentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectCommentItem:
    await require_org_capability(session, "can_manage_projects")
    await _ensure_project(session, project_id)

    content = _normalize_text(payload.content, "Comment")
    visibility = payload.visibility or "student_and_mentors"

    result = await session.execute(
        text(
            "INSERT INTO project_comments "
            "(org_id, project_id, author_user_id, visibility, content) "
            "VALUES (app_org_id(), :project_id, app_user_id(), :visibility, :content) "
            "RETURNING id"
        ),
        {
            "project_id": str(project_id),
            "visibility": visibility,
            "content": content,
        },
    )
    comment_id = result.scalar()
    if not comment_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create comment.",
        )

    row = await session.execute(
        text(
            "SELECT pc.id, pc.content, pc.visibility, pc.created_at, "
            "u.id AS author_id, u.display_name AS author_name, "
            "u.email AS author_email "
            "FROM project_comments pc "
            "LEFT JOIN users u ON u.id = pc.author_user_id "
            "AND u.deleted_at IS NULL "
            "WHERE pc.id = :comment_id "
            "AND pc.org_id = app_org_id() "
            "AND pc.deleted_at IS NULL"
        ),
        {"comment_id": str(comment_id)},
    )
    record = row.mappings().first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load created comment.",
        )
    return ProjectCommentItem(
        id=record.get("id"),
        content=record.get("content"),
        visibility=record.get("visibility"),
        created_at=record.get("created_at"),
        author=ProjectCommentAuthor(
            id=record.get("author_id"),
            display_name=record.get("author_name"),
            email=record.get("author_email"),
        ),
    )


@router.delete("/projects/{project_id}/comments/{comment_id}")
async def delete_project_comment(
    project_id: UUID,
    comment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await require_org_capability(session, "can_manage_projects")
    await _ensure_project(session, project_id)

    result = await session.execute(
        text(
            "UPDATE project_comments "
            "SET deleted_at = now() "
            "WHERE id = :comment_id "
            "AND project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "RETURNING id"
        ),
        {"comment_id": str(comment_id), "project_id": str(project_id)},
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )
    return {"status": "deleted"}
