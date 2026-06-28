"""Admin/debug helpers for redacted prompt runtime traces."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_SOURCE_ORDER = {
    "answer_evaluation": 0,
    "stage_assessment": 1,
    "project_report": 2,
}


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _clean_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _clean_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _sort_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_prompt_task_trace_rows(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        source_type = _clean_string(row.get("source_type"))
        if source_type not in _SOURCE_ORDER:
            continue

        traces = row.get("prompt_task_traces")
        if not isinstance(traces, Mapping):
            continue

        for trace_name, trace_payload in traces.items():
            if not isinstance(trace_payload, Mapping):
                continue
            task_key = _clean_string(trace_payload.get("task_key"))
            if not task_key and isinstance(trace_name, str):
                task_key = trace_name.strip() or None
            if not task_key:
                continue
            records.append(
                {
                    "source_type": source_type,
                    "source_id": row.get("source_id"),
                    "stage": _clean_string(row.get("stage")),
                    "task_key": task_key,
                    "provider": _clean_string(trace_payload.get("provider")),
                    "model": _clean_string(trace_payload.get("model")),
                    "failure_reason": _clean_string(
                        trace_payload.get("failure_reason")
                    ),
                    "timeout_ms": _clean_int(trace_payload.get("timeout_ms")),
                    "latency_ms": _clean_int(trace_payload.get("latency_ms")),
                    "parse_status": _clean_string(trace_payload.get("parse_status")),
                    "allowed_mutation": _clean_string(
                        trace_payload.get("allowed_mutation")
                    ),
                    "redacted": _clean_bool(trace_payload.get("redacted")),
                    "created_at": row.get("created_at"),
                }
            )

    return sorted(
        records,
        key=lambda item: (
            _sort_datetime(item.get("created_at")),
            _SOURCE_ORDER.get(str(item.get("source_type")), 99),
            str(item.get("source_id") or ""),
            str(item.get("task_key") or ""),
        ),
    )


async def fetch_project_prompt_task_traces(
    session: AsyncSession,
    project_id: UUID,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT "
            "'answer_evaluation' AS source_type, "
            "ae.id AS source_id, "
            "qbq.stage AS stage, "
            "ae.created_at AS created_at, "
            "ae.scores_json -> 'prompt_task_traces' AS prompt_task_traces "
            "FROM answer_evaluations ae "
            "LEFT JOIN project_question_instances pqi "
            "ON pqi.id = ae.question_instance_id "
            "AND pqi.project_id = ae.project_id "
            "AND pqi.org_id = ae.org_id "
            "LEFT JOIN question_bank_questions qbq "
            "ON qbq.id = pqi.question_bank_question_id "
            "WHERE ae.project_id = :project_id "
            "AND ae.org_id = app_org_id() "
            "AND ae.deleted_at IS NULL "
            "AND jsonb_typeof(ae.scores_json -> 'prompt_task_traces') = 'object' "
            "UNION ALL "
            "SELECT "
            "'stage_assessment' AS source_type, "
            "psa.id AS source_id, "
            "psa.stage AS stage, "
            "psa.created_at AS created_at, "
            "psa.scores_json -> 'prompt_task_traces' AS prompt_task_traces "
            "FROM project_stage_assessments psa "
            "WHERE psa.project_id = :project_id "
            "AND psa.org_id = app_org_id() "
            "AND psa.deleted_at IS NULL "
            "AND jsonb_typeof(psa.scores_json -> 'prompt_task_traces') = 'object' "
            "UNION ALL "
            "SELECT "
            "'project_report' AS source_type, "
            "pr.id AS source_id, "
            "'report' AS stage, "
            "pr.created_at AS created_at, "
            "pr.content_json -> 'prompt_task_traces' AS prompt_task_traces "
            "FROM project_reports pr "
            "WHERE pr.project_id = :project_id "
            "AND pr.org_id = app_org_id() "
            "AND pr.deleted_at IS NULL "
            "AND jsonb_typeof(pr.content_json -> 'prompt_task_traces') = 'object'"
        ),
        {"project_id": str(project_id)},
    )
    return normalize_prompt_task_trace_rows(result.mappings().all())
