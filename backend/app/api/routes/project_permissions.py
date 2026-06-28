from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectPermissionsResponse(BaseModel):
    can_view_project: bool
    can_view_messages: bool
    can_view_facts: bool
    can_comment: bool


@router.get("/{project_id}/permissions", response_model=ProjectPermissionsResponse)
async def get_project_permissions(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectPermissionsResponse:
    result = await session.execute(
        text(
            "SELECT id FROM projects "
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

    permissions_result = await session.execute(
        text(
            "SELECT "
            "can_view_project(:project_id, app_org_id()) AS can_view_project, "
            "can_view_project_messages(:project_id, app_org_id()) "
            "AS can_view_messages, "
            "can_view_project_facts(:project_id, app_org_id()) "
            "AS can_view_facts, "
            "can_comment_on_project(:project_id, app_org_id()) AS can_comment"
        ),
        {"project_id": str(project_id)},
    )
    row = permissions_result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return ProjectPermissionsResponse(
        can_view_project=row.get("can_view_project", False),
        can_view_messages=row.get("can_view_messages", False),
        can_view_facts=row.get("can_view_facts", False),
        can_comment=row.get("can_comment", False),
    )
