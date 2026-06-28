from datetime import datetime, timedelta, timezone
from typing import Literal
import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability

router = APIRouter(prefix="/admin-api", tags=["admin"])

ReportStatusFilter = Literal["draft", "final", "archived", "all"]
ConfirmedFilter = Literal["confirmed", "unconfirmed", "all"]


class ReportOwner(BaseModel):
    id: UUID | None = None
    display_name: str | None = None
    email: str | None = None


class ReportCohort(BaseModel):
    id: UUID
    name: str
    is_archived: bool


class ReportProjectSummary(BaseModel):
    id: UUID
    title: str
    current_stage: str | None = None
    stage_status: str | None = None
    is_archived: bool
    owner: ReportOwner
    cohort: ReportCohort | None = None


class ReportSummary(BaseModel):
    id: UUID
    report_version: int
    status: str
    confirmed: bool
    created_at: datetime
    updated_at: datetime
    project: ReportProjectSummary


class ReportsResponse(BaseModel):
    reports: list[ReportSummary]
    total: int
    page: int
    limit: int


class ReportUpdateRequest(BaseModel):
    confirmed: bool | None = None


class ReportBatchUpdateRequest(BaseModel):
    report_ids: list[UUID] = []
    confirmed: bool | None = None


class ReportBatchUpdateResponse(BaseModel):
    updated_count: int


def _resolve_confirmed_filter(value: ConfirmedFilter | None) -> bool | None:
    if not value or value == "all":
        return None
    return value == "confirmed"


def _build_report_filters(
    *,
    status: ReportStatusFilter | None,
    confirmed: ConfirmedFilter | None,
    include_archived: bool,
    cohort_id: UUID | None,
    updated_since_days: int | None,
    query: str | None,
) -> tuple[list[str], dict[str, object]]:
    filters = [
        "pr.org_id = app_org_id()",
        "pr.deleted_at IS NULL",
        "p.deleted_at IS NULL",
    ]
    params: dict[str, object] = {}

    if not include_archived:
        filters.append("p.is_archived = false")

    if status and status != "all":
        filters.append("pr.status = :status")
        params["status"] = status

    confirmed_value = _resolve_confirmed_filter(confirmed)
    if confirmed_value is not None:
        filters.append("pr.confirmed = :confirmed")
        params["confirmed"] = confirmed_value

    if query:
        search_value = query.strip()
        if search_value:
            filters.append(
                "("
                "p.title ILIKE :search "
                "OR owner.display_name ILIKE :search "
                "OR owner.email ILIKE :search"
                ")"
            )
            params["search"] = f"%{search_value}%"

    if cohort_id:
        filters.append("p.cohort_id = :cohort_id")
        params["cohort_id"] = str(cohort_id)

    if updated_since_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=updated_since_days)
        filters.append("pr.updated_at >= :updated_after")
        params["updated_after"] = cutoff

    return filters, params


def _build_report_summary(row: dict) -> ReportSummary:
    cohort_id = row.get("cohort_id")
    cohort = (
        ReportCohort(
            id=cohort_id,
            name=row.get("cohort_name") or "Cohort",
            is_archived=bool(row.get("cohort_archived")),
        )
        if cohort_id
        else None
    )

    project = ReportProjectSummary(
        id=row.get("project_id"),
        title=row.get("project_title") or "Untitled project",
        current_stage=row.get("current_stage"),
        stage_status=row.get("stage_status"),
        is_archived=bool(row.get("project_archived")),
        owner=ReportOwner(
            id=row.get("owner_id"),
            display_name=row.get("owner_name"),
            email=row.get("owner_email"),
        ),
        cohort=cohort,
    )

    return ReportSummary(
        id=row.get("id"),
        report_version=row.get("report_version") or 1,
        status=row.get("status") or "draft",
        confirmed=bool(row.get("confirmed")),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        project=project,
    )


async def _fetch_report_summary(
    session: AsyncSession, report_id: UUID
) -> ReportSummary | None:
    result = await session.execute(
        text(
            "SELECT "
            "pr.id, pr.report_version, pr.status, pr.confirmed, "
            "pr.created_at, pr.updated_at, "
            "p.id AS project_id, p.title AS project_title, "
            "p.current_stage, p.stage_status, p.is_archived AS project_archived, "
            "owner.id AS owner_id, owner.display_name AS owner_name, "
            "owner.email AS owner_email, "
            "c.id AS cohort_id, c.name AS cohort_name, "
            "c.is_archived AS cohort_archived "
            "FROM project_reports pr "
            "JOIN projects p ON p.id = pr.project_id "
            "AND p.org_id = pr.org_id "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = p.cohort_id "
            "AND c.deleted_at IS NULL "
            "WHERE pr.id = :report_id "
            "AND pr.org_id = app_org_id() "
            "AND pr.deleted_at IS NULL"
        ),
        {"report_id": str(report_id)},
    )
    row = result.mappings().first()
    if not row:
        return None
    return _build_report_summary(row)


@router.get("/reports", response_model=ReportsResponse)
async def list_reports(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: ReportStatusFilter | None = Query(default=None, alias="status"),
    confirmed: ConfirmedFilter | None = Query(default=None),
    include_archived: bool = Query(False),
    cohort_id: UUID | None = Query(default=None),
    updated_since_days: int | None = Query(default=None, ge=1, le=365),
    query: str | None = Query(default=None, alias="q"),
) -> ReportsResponse:
    await require_org_capability(session, "can_manage_reports")

    filters, params = _build_report_filters(
        status=status,
        confirmed=confirmed,
        include_archived=include_archived,
        cohort_id=cohort_id,
        updated_since_days=updated_since_days,
        query=query,
    )
    params.update({"limit": limit, "offset": (page - 1) * limit})

    where_clause = " AND ".join(filters)

    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM project_reports pr "
            "JOIN projects p ON p.id = pr.project_id "
            "AND p.org_id = pr.org_id "
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
            "pr.id, pr.report_version, pr.status, pr.confirmed, "
            "pr.created_at, pr.updated_at, "
            "p.id AS project_id, p.title AS project_title, "
            "p.current_stage, p.stage_status, p.is_archived AS project_archived, "
            "owner.id AS owner_id, owner.display_name AS owner_name, "
            "owner.email AS owner_email, "
            "c.id AS cohort_id, c.name AS cohort_name, "
            "c.is_archived AS cohort_archived "
            "FROM project_reports pr "
            "JOIN projects p ON p.id = pr.project_id "
            "AND p.org_id = pr.org_id "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = p.cohort_id "
            "AND c.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY pr.updated_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        params,
    )

    reports = [_build_report_summary(row) for row in result.mappings().all()]

    return ReportsResponse(
        reports=reports,
        total=total,
        page=page,
        limit=limit,
    )


def _format_csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@router.get("/reports/export")
async def export_reports(
    session: AsyncSession = Depends(get_db_session),
    status: ReportStatusFilter | None = Query(default=None, alias="status"),
    confirmed: ConfirmedFilter | None = Query(default=None),
    include_archived: bool = Query(False),
    cohort_id: UUID | None = Query(default=None),
    updated_since_days: int | None = Query(default=None, ge=1, le=365),
    query: str | None = Query(default=None, alias="q"),
) -> Response:
    await require_org_capability(session, "can_manage_reports")

    filters, params = _build_report_filters(
        status=status,
        confirmed=confirmed,
        include_archived=include_archived,
        cohort_id=cohort_id,
        updated_since_days=updated_since_days,
        query=query,
    )
    where_clause = " AND ".join(filters)

    result = await session.execute(
        text(
            "SELECT "
            "pr.id AS report_id, pr.report_version, pr.status, pr.confirmed, "
            "pr.confirmed_at, pr.created_at, pr.updated_at, "
            "p.id AS project_id, p.title AS project_title, "
            "p.current_stage, p.stage_status, p.is_archived AS project_archived, "
            "owner.display_name AS owner_name, owner.email AS owner_email, "
            "c.id AS cohort_id, c.name AS cohort_name, "
            "c.is_archived AS cohort_archived "
            "FROM project_reports pr "
            "JOIN projects p ON p.id = pr.project_id "
            "AND p.org_id = pr.org_id "
            "LEFT JOIN users owner ON owner.id = p.owner_user_id "
            "AND owner.deleted_at IS NULL "
            "LEFT JOIN cohorts c ON c.id = p.cohort_id "
            "AND c.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY pr.updated_at DESC"
        ),
        params,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "report_id",
            "report_version",
            "report_status",
            "confirmed",
            "confirmed_at",
            "report_created_at",
            "report_updated_at",
            "project_id",
            "project_title",
            "project_stage",
            "project_stage_status",
            "project_archived",
            "owner_name",
            "owner_email",
            "cohort_id",
            "cohort_name",
            "cohort_archived",
        ]
    )

    for row in result.mappings().all():
        writer.writerow(
            [
                _format_csv_value(row.get("report_id")),
                _format_csv_value(row.get("report_version")),
                _format_csv_value(row.get("status")),
                _format_csv_value(row.get("confirmed")),
                _format_csv_value(row.get("confirmed_at")),
                _format_csv_value(row.get("created_at")),
                _format_csv_value(row.get("updated_at")),
                _format_csv_value(row.get("project_id")),
                _format_csv_value(row.get("project_title")),
                _format_csv_value(row.get("current_stage")),
                _format_csv_value(row.get("stage_status")),
                _format_csv_value(row.get("project_archived")),
                _format_csv_value(row.get("owner_name")),
                _format_csv_value(row.get("owner_email")),
                _format_csv_value(row.get("cohort_id")),
                _format_csv_value(row.get("cohort_name")),
                _format_csv_value(row.get("cohort_archived")),
            ]
        )

    filename = f"reports_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@router.patch("/reports/{report_id}", response_model=ReportSummary)
async def update_report(
    report_id: UUID,
    payload: ReportUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ReportSummary:
    await require_org_capability(session, "can_manage_reports")

    if payload.confirmed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confirmed is required.",
        )

    updated = await session.execute(
        text(
            "UPDATE project_reports "
            "SET confirmed = :confirmed "
            "WHERE id = :report_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "RETURNING id"
        ),
        {"report_id": str(report_id), "confirmed": payload.confirmed},
    )
    if not updated.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    summary = await _fetch_report_summary(session, report_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return summary


@router.post("/reports/batch", response_model=ReportBatchUpdateResponse)
async def batch_update_reports(
    payload: ReportBatchUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ReportBatchUpdateResponse:
    await require_org_capability(session, "can_manage_reports")

    if not payload.report_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="report_ids is required.",
        )
    if payload.confirmed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confirmed is required.",
        )

    result = await session.execute(
        text(
            "UPDATE project_reports "
            "SET confirmed = :confirmed "
            "WHERE id = ANY(:report_ids) "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "confirmed": payload.confirmed,
            "report_ids": [str(report_id) for report_id in payload.report_ids],
        },
    )
    updated_count = result.rowcount or 0
    return ReportBatchUpdateResponse(updated_count=updated_count)
