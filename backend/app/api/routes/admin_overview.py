from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability
from app.services.admin_overview import build_admin_overview_payload
from app.services.localization import normalize_output_locale

router = APIRouter(prefix="/admin-api", tags=["admin"])

MetricTone = Literal["primary", "success", "warning"]
TrendTone = Literal["success", "warning", "info"]

class OverviewMetric(BaseModel):
    label: str
    value: str
    delta: str
    tone: MetricTone
    series: list[int]


class EnrollmentTrend(BaseModel):
    label: str
    sublabel: str
    total: str
    change: str
    tone: TrendTone
    series: list[int]


class CohortProgressItem(BaseModel):
    id: str
    name: str
    progress: int
    meta: str


class PendingAction(BaseModel):
    title: str
    detail: str
    tone: MetricTone


class UpcomingDeadline(BaseModel):
    title: str
    due_at: datetime | None = None


class ActivityItem(BaseModel):
    title: str
    detail: str
    created_at: datetime


class InsightHighlight(BaseModel):
    title: str
    detail: str


class AdminOverviewResponse(BaseModel):
    overview_metrics: list[OverviewMetric]
    enrollment_trend: EnrollmentTrend
    cohort_progress: list[CohortProgressItem]
    pending_actions: list[PendingAction]
    upcoming_deadlines: list[UpcomingDeadline]
    activity_feed: list[ActivityItem]
    insight_highlights: list[InsightHighlight]


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    output_locale: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> AdminOverviewResponse:
    await require_org_capability(session, "is_org_admin")
    locale = normalize_output_locale(output_locale)
    payload = await build_admin_overview_payload(session, locale)
    return AdminOverviewResponse.model_validate(payload, from_attributes=True)
