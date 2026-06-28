from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_db_session

router = APIRouter(prefix="/sample", tags=["sample"])

STAGE_FILTERS = {"problem", "market", "tech", "report"}


class SampleProjectSummary(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    current_stage: str
    updated_at: datetime | None = None


class SampleProjectsListResponse(BaseModel):
    projects: list[SampleProjectSummary]
    total: int
    limit: int
    offset: int


class SampleConversationMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str | None = None
    stage: str | None = None
    meta: dict[str, Any] | None = None


class SampleConversationResponse(BaseModel):
    messages: list[SampleConversationMessage]


@router.get("/projects", response_model=SampleProjectsListResponse)
async def list_sample_projects(
    session: AsyncSession = Depends(get_admin_db_session),
    stage: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> SampleProjectsListResponse:
    stage_filter = stage.strip().lower() if isinstance(stage, str) else None
    if stage_filter and stage_filter not in STAGE_FILTERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid stage filter.",
        )

    where_clause = "WHERE stage = :stage " if stage_filter else ""
    count_result = await session.execute(
        text(f"SELECT COUNT(*) AS total FROM sample_projects {where_clause}"),
        {"stage": stage_filter},
    )
    total = int(count_result.mappings().first().get("total") or 0)

    result = await session.execute(
        text(
            "SELECT id, title, description, stage, project_updated_at "
            "FROM sample_projects "
            f"{where_clause}"
            "ORDER BY project_updated_at DESC NULLS LAST, updated_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        {"stage": stage_filter, "limit": limit, "offset": offset},
    )
    projects = [
        SampleProjectSummary(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            current_stage=row["stage"],
            updated_at=row["project_updated_at"],
        )
        for row in result.mappings().all()
    ]
    return SampleProjectsListResponse(
        projects=projects, total=total, limit=limit, offset=offset
    )


@router.get(
    "/projects/{sample_id}/chat",
    response_model=SampleConversationResponse,
)
async def get_sample_chat(
    sample_id: UUID,
    session: AsyncSession = Depends(get_admin_db_session),
) -> SampleConversationResponse:
    result = await session.execute(
        text("SELECT messages FROM sample_projects WHERE id = :sample_id"),
        {"sample_id": str(sample_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample project not found.",
        )
    messages = row.get("messages")
    if not isinstance(messages, list):
        messages = []
    return SampleConversationResponse(messages=messages)


@router.get("/projects/{sample_id}/report")
async def get_sample_report(
    sample_id: UUID,
    session: AsyncSession = Depends(get_admin_db_session),
) -> dict[str, Any]:
    result = await session.execute(
        text("SELECT report FROM sample_projects WHERE id = :sample_id"),
        {"sample_id": str(sample_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample project not found.",
        )
    report = row.get("report")
    if not isinstance(report, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return report
