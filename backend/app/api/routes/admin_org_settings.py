import json
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability

router = APIRouter(prefix="/admin-api/org", tags=["admin"])


class OrgSettingsResponse(BaseModel):
    settings: dict[str, Any]


class OrgSettingsUpdate(BaseModel):
    settings: dict[str, Any]
    name: str | None = None


class QuestionBankStatusResponse(BaseModel):
    bank_key: str
    version: str
    source: str | None = None
    activated_at: datetime | None = None
    created_at: datetime | None = None


@router.get("/settings", response_model=OrgSettingsResponse)
async def get_org_settings(
    session: AsyncSession = Depends(get_db_session),
) -> OrgSettingsResponse:
    await require_org_capability(session, "can_manage_org_settings")
    result = await session.execute(
        text(
            "SELECT settings "
            "FROM organizations "
            "WHERE id = app_org_id() AND deleted_at IS NULL"
        )
    )
    org = result.mappings().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found or inactive",
        )
    return OrgSettingsResponse(settings=org.get("settings") or {})


@router.patch("/settings", response_model=OrgSettingsResponse)
async def update_org_settings(
    payload: OrgSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> OrgSettingsResponse:
    await require_org_capability(session, "can_manage_org_settings")
    name_value = payload.name.strip() if payload.name is not None else None
    if name_value is not None and not name_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization name is required",
        )
    result = await session.execute(
        text(
            "UPDATE organizations "
            "SET name = COALESCE(:name, name), "
            "settings = COALESCE(settings, '{}'::jsonb) || CAST(:settings AS jsonb) "
            "WHERE id = app_org_id() AND deleted_at IS NULL "
            "RETURNING settings"
        ),
        {"settings": json.dumps(payload.settings), "name": name_value},
    )
    org = result.mappings().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization not found or inactive",
        )
    return OrgSettingsResponse(settings=org.get("settings") or {})


@router.get("/question-bank", response_model=QuestionBankStatusResponse)
async def get_question_bank_status(
    bank_key: str = "default",
    session: AsyncSession = Depends(get_db_session),
) -> QuestionBankStatusResponse:
    await require_org_capability(session, "can_manage_org_settings")
    normalized_key = bank_key.strip().lower()
    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="bank_key is required",
        )

    result = await session.execute(
        text(
            "SELECT bank_key, version, source, activated_at, created_at "
            "FROM question_bank_versions "
            "WHERE bank_key = :bank_key "
            "AND is_active "
            "AND deleted_at IS NULL "
            "AND (org_id IS NULL OR org_id = app_org_id()) "
            "ORDER BY (org_id IS NULL) ASC, activated_at DESC "
            "LIMIT 1"
        ),
        {"bank_key": normalized_key},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active question bank not found",
        )
    return QuestionBankStatusResponse(
        bank_key=row.get("bank_key") or normalized_key,
        version=row.get("version") or "unknown",
        source=row.get("source"),
        activated_at=row.get("activated_at"),
        created_at=row.get("created_at"),
    )
