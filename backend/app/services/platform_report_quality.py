from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PlatformReportQualityValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PlatformReportQualityNotFoundError(LookupError):
    pass


def normalize_quality_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized or normalized == "all":
        return None
    if normalized not in {"pass", "warn", "fail"}:
        raise PlatformReportQualityValidationError("Invalid report quality status")
    return normalized


def build_quality_observation_filters(
    *,
    quality_status: str | None,
    org_id: UUID | None,
    project_id: UUID | None,
    report_id: UUID | None,
    observed_from: datetime | None,
    observed_to: datetime | None,
    q: str | None,
) -> tuple[str, dict[str, object]]:
    filters = ["rqo.deleted_at IS NULL"]
    params: dict[str, object] = {}
    normalized_status = normalize_quality_status(quality_status)
    if normalized_status:
        filters.append("rqo.status = :quality_status")
        params["quality_status"] = normalized_status
    if org_id:
        filters.append("rqo.org_id = :org_id")
        params["org_id"] = str(org_id)
    if project_id:
        filters.append("rqo.project_id = :project_id")
        params["project_id"] = str(project_id)
    if report_id:
        filters.append("rqo.report_id = :report_id")
        params["report_id"] = str(report_id)
    if observed_from:
        filters.append("rqo.observed_at >= :observed_from")
        params["observed_from"] = observed_from
    if observed_to:
        filters.append("rqo.observed_at <= :observed_to")
        params["observed_to"] = observed_to
    if q:
        search = q.strip()
        if search:
            filters.append(
                "("
                "rqo.project_title ILIKE :search OR "
                "CAST(rqo.project_id AS TEXT) ILIKE :search OR "
                "CAST(rqo.report_id AS TEXT) ILIKE :search OR "
                "o.name ILIKE :search OR "
                "o.slug ILIKE :search"
                ")"
            )
            params["search"] = f"%{search}%"
    return " AND ".join(filters), params


def row_to_report_quality_item_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "org_id": row.get("org_id"),
        "org_name": row.get("org_name"),
        "org_slug": row.get("org_slug"),
        "project_id": row.get("project_id"),
        "project_title": row.get("project_title"),
        "report_id": row.get("report_id"),
        "report_version": int(row.get("report_version") or 1),
        "generated_from_state_version": int(
            row.get("generated_from_state_version") or 1
        ),
        "observation_schema_version": (
            row.get("observation_schema_version")
            or "assessment_quality_observation_v1"
        ),
        "status": row.get("status") or "fail",
        "failed_invariants": json_string_list(row.get("failed_invariants_json")),
        "warning_invariants": json_string_list(row.get("warning_invariants_json")),
        "score_snapshot": json_object(row.get("score_snapshot_json")),
        "evidence_counts": json_object(row.get("evidence_counts_json")),
        "canonical_boundaries": json_object(row.get("canonical_boundaries_json")),
        "observed_at": row.get("observed_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def row_to_report_quality_detail_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row_to_report_quality_item_payload(row)
    payload["observation"] = json_object(row.get("observation_json"))
    return payload


def json_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def json_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


async def fetch_report_quality_summary_payload(
    session: AsyncSession,
    *,
    quality_status: str | None,
    org_id: UUID | None,
    project_id: UUID | None,
    report_id: UUID | None,
    observed_from: datetime | None,
    observed_to: datetime | None,
    q: str | None,
) -> dict[str, Any]:
    where_clause, params = build_quality_observation_filters(
        quality_status=quality_status,
        org_id=org_id,
        project_id=project_id,
        report_id=report_id,
        observed_from=observed_from,
        observed_to=observed_to,
        q=q,
    )
    status_result = await session.execute(
        text(
            "SELECT rqo.status, COUNT(*) AS count "
            "FROM report_quality_observations rqo "
            "JOIN organizations o ON o.id = rqo.org_id AND o.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "GROUP BY rqo.status "
            "ORDER BY rqo.status"
        ),
        params,
    )
    status_counts = [
        {
            "status": row.get("status") or "fail",
            "count": int(row.get("count") or 0),
        }
        for row in status_result.mappings().all()
    ]
    total = sum(item["count"] for item in status_counts)

    invariant_result = await session.execute(
        text(
            "WITH filtered AS ("
            "  SELECT rqo.failed_invariants_json, rqo.warning_invariants_json "
            "  FROM report_quality_observations rqo "
            "  JOIN organizations o ON o.id = rqo.org_id AND o.deleted_at IS NULL "
            f"  WHERE {where_clause} "
            "), expanded AS ("
            "  SELECT jsonb_array_elements_text(failed_invariants_json) AS invariant_id, "
            "  'fail' AS severity FROM filtered "
            "  UNION ALL "
            "  SELECT jsonb_array_elements_text(warning_invariants_json) AS invariant_id, "
            "  'warn' AS severity FROM filtered"
            ") "
            "SELECT invariant_id, severity, COUNT(*) AS count "
            "FROM expanded "
            "GROUP BY invariant_id, severity "
            "ORDER BY count DESC, severity, invariant_id "
            "LIMIT 20"
        ),
        params,
    )
    invariant_counts = [
        {
            "invariant_id": row.get("invariant_id") or "",
            "severity": row.get("severity") or "fail",
            "count": int(row.get("count") or 0),
        }
        for row in invariant_result.mappings().all()
        if row.get("invariant_id")
    ]
    return {
        "total": total,
        "status_counts": status_counts,
        "invariant_counts": invariant_counts,
    }


async def list_report_quality_observation_payloads(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    quality_status: str | None,
    org_id: UUID | None,
    project_id: UUID | None,
    report_id: UUID | None,
    observed_from: datetime | None,
    observed_to: datetime | None,
    q: str | None,
) -> dict[str, Any]:
    where_clause, params = build_quality_observation_filters(
        quality_status=quality_status,
        org_id=org_id,
        project_id=project_id,
        report_id=report_id,
        observed_from=observed_from,
        observed_to=observed_to,
        q=q,
    )
    count_result = await session.execute(
        text(
            "SELECT COUNT(*) AS total "
            "FROM report_quality_observations rqo "
            "JOIN organizations o ON o.id = rqo.org_id AND o.deleted_at IS NULL "
            f"WHERE {where_clause}"
        ),
        params,
    )
    total = int((count_result.mappings().first() or {}).get("total") or 0)

    list_params = {**params, "limit": limit, "offset": offset}
    result = await session.execute(
        text(
            "SELECT rqo.id, rqo.org_id, o.name AS org_name, o.slug AS org_slug, "
            "rqo.project_id, rqo.project_title, rqo.report_id, "
            "rqo.report_version, rqo.generated_from_state_version, "
            "rqo.observation_schema_version, rqo.status, "
            "rqo.failed_invariants_json, rqo.warning_invariants_json, "
            "rqo.score_snapshot_json, rqo.evidence_counts_json, "
            "rqo.canonical_boundaries_json, rqo.observed_at, "
            "rqo.created_at, rqo.updated_at "
            "FROM report_quality_observations rqo "
            "JOIN organizations o ON o.id = rqo.org_id AND o.deleted_at IS NULL "
            f"WHERE {where_clause} "
            "ORDER BY "
            "CASE rqo.status WHEN 'fail' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END, "
            "rqo.observed_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        list_params,
    )
    return {
        "observations": [
            row_to_report_quality_item_payload(row) for row in result.mappings().all()
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_report_quality_observation_payload(
    session: AsyncSession,
    *,
    observation_id: UUID,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            "SELECT rqo.id, rqo.org_id, o.name AS org_name, o.slug AS org_slug, "
            "rqo.project_id, rqo.project_title, rqo.report_id, "
            "rqo.report_version, rqo.generated_from_state_version, "
            "rqo.observation_schema_version, rqo.status, "
            "rqo.failed_invariants_json, rqo.warning_invariants_json, "
            "rqo.score_snapshot_json, rqo.evidence_counts_json, "
            "rqo.canonical_boundaries_json, rqo.observation_json, "
            "rqo.observed_at, rqo.created_at, rqo.updated_at "
            "FROM report_quality_observations rqo "
            "JOIN organizations o ON o.id = rqo.org_id AND o.deleted_at IS NULL "
            "WHERE rqo.id = :observation_id "
            "AND rqo.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"observation_id": str(observation_id)},
    )
    row = result.mappings().first()
    if not row:
        raise PlatformReportQualityNotFoundError("Report quality observation not found")
    return row_to_report_quality_detail_payload(row)
