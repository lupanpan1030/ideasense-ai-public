from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability
from app.services.prompt_templates import (
    PromptTemplateRevisionCreateError,
    PromptTemplateRevisionValidationError,
    create_prompt_template_revision,
    normalize_template_key,
    prompt_template_row_to_payload,
)

router = APIRouter(prefix="/admin-api/prompts", tags=["admin"])


class PromptTemplateInfo(BaseModel):
    id: str
    template_key: str
    version: str
    content: str
    purpose: str
    stage: str | None
    variant: str | None
    org_id: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None


class PromptTemplateListResponse(BaseModel):
    templates: list[PromptTemplateInfo]


class PromptTemplateCreateRequest(BaseModel):
    content: str
    purpose: str | None = None
    stage: str | None = None
    variant: str | None = None
    version: str | None = None


class PromptTemplateRevertResponse(BaseModel):
    reverted: bool
    effective_template: PromptTemplateInfo | None


@router.get("", response_model=PromptTemplateListResponse)
async def list_prompt_templates(
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateListResponse:
    await require_org_capability(session, "can_manage_prompts")
    result = await session.execute(
        text(
            "SELECT id, template_key, version, content, purpose, stage, variant, "
            "org_id, is_active, created_at, updated_at "
            "FROM prompt_templates "
            "WHERE deleted_at IS NULL "
            "AND is_active "
            "AND (org_id = app_org_id() OR org_id IS NULL) "
            "ORDER BY template_key, CASE WHEN org_id IS NULL THEN 1 ELSE 0 END"
        )
    )
    templates = [
        PromptTemplateInfo(**prompt_template_row_to_payload(row, include_org_id=True))
        for row in result.mappings().all()
    ]
    return PromptTemplateListResponse(templates=templates)


@router.post("/{template_key}", response_model=PromptTemplateInfo)
async def create_prompt_template(
    template_key: str,
    payload: PromptTemplateCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateInfo:
    await require_org_capability(session, "can_manage_prompts")
    try:
        created = await create_prompt_template_revision(
            session,
            template_key=template_key,
            content=payload.content,
            purpose=payload.purpose,
            stage=payload.stage,
            variant=payload.variant,
            version=payload.version,
            scope="org",
            include_org_id=True,
        )
    except PromptTemplateRevisionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except PromptTemplateRevisionCreateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return PromptTemplateInfo(**created)


@router.post("/{template_key}/revert", response_model=PromptTemplateRevertResponse)
async def revert_prompt_template(
    template_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateRevertResponse:
    await require_org_capability(session, "can_manage_prompts")
    normalized_key = normalize_template_key(template_key)
    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="template_key is required",
        )
    result = await session.execute(
        text(
            "UPDATE prompt_templates "
            "SET is_active = false, updated_at = now() "
            "WHERE template_key = :template_key "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "AND is_active"
        ),
        {"template_key": normalized_key},
    )
    reverted = bool(result.rowcount)

    effective_result = await session.execute(
        text(
            "SELECT id, template_key, version, content, purpose, stage, variant, "
            "org_id, is_active, created_at, updated_at "
            "FROM prompt_templates "
            "WHERE template_key = :template_key "
            "AND org_id IS NULL "
            "AND deleted_at IS NULL "
            "AND is_active "
            "LIMIT 1"
        ),
        {"template_key": normalized_key},
    )
    row = effective_result.mappings().first()
    effective_template = (
        PromptTemplateInfo(**prompt_template_row_to_payload(row, include_org_id=True))
        if row
        else None
    )

    return PromptTemplateRevertResponse(
        reverted=reverted,
        effective_template=effective_template,
    )
