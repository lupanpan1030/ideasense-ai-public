from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.assessment_quality_observability import (
    build_assessment_quality_observation,
)


logger = logging.getLogger(__name__)

OBSERVATION_SCHEMA_VERSION = "assessment_quality_observation_v1"
VALID_STATUSES = {"pass", "warn", "fail"}
UNSAFE_DETAIL_KEYS = {
    "raw_prompt",
    "prompt",
    "prompts",
    "provider_response",
    "provider_payload",
    "provider_key",
    "api_key",
    "token",
    "verification_token",
    "password",
    "password_hash",
    "secret",
    "content_markdown",
    "content_json",
    "raw_user_answer",
    "transcript",
}


def build_report_quality_observation_record(
    report_payload: Mapping[str, Any],
    *,
    org_id: str,
    project_id: str,
    project_title: str | None = None,
    report_id: str,
    report_version: int,
    generated_from_state_version: int,
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(report_payload)
    payload.update(
        {
            "id": report_id,
            "report_id": report_id,
            "project_id": project_id,
            "report_version": report_version,
            "generated_from_state_version": generated_from_state_version,
            "status": payload.get("status") or "final",
        }
    )
    observation = build_assessment_quality_observation(
        payload,
        source={
            "source": "report_quality_observations",
            "org_id": org_id,
            "project_id": project_id,
            "report_id": report_id,
            **dict(source or {}),
        },
    )
    summary = _as_mapping(observation.get("summary"))
    report = _as_mapping(observation.get("report"))
    evidence = _as_mapping(observation.get("evidence"))
    sanitized_observation = _sanitize_observation_detail(observation)
    return {
        "org_id": org_id,
        "project_id": project_id,
        "project_title": _compact_text(project_title, max_len=240),
        "report_id": report_id,
        "report_version": int(report_version),
        "generated_from_state_version": int(generated_from_state_version),
        "observation_schema_version": str(
            observation.get("artifact_schema_version") or OBSERVATION_SCHEMA_VERSION
        ),
        "status": _normalize_status(summary.get("status")),
        "failed_invariants_json": _as_string_list(summary.get("failed")),
        "warning_invariants_json": _as_string_list(summary.get("warnings")),
        "score_snapshot_json": dict(_as_mapping(report.get("scores"))),
        "evidence_counts_json": dict(_as_mapping(evidence.get("counts"))),
        "canonical_boundaries_json": dict(
            _as_mapping(observation.get("canonical_boundaries"))
        ),
        "observation_json": sanitized_observation,
    }


async def persist_report_quality_observation(
    session: AsyncSession,
    report_payload: Mapping[str, Any],
    *,
    org_id: str,
    project_id: str,
    project_title: str | None = None,
    report_id: str,
    report_version: int,
    generated_from_state_version: int,
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    record = build_report_quality_observation_record(
        report_payload,
        org_id=org_id,
        project_id=project_id,
        project_title=project_title,
        report_id=report_id,
        report_version=report_version,
        generated_from_state_version=generated_from_state_version,
        source=source,
    )
    return await upsert_report_quality_observation(session, record)


async def upsert_report_quality_observation(
    session: AsyncSession, record: Mapping[str, Any]
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "INSERT INTO report_quality_observations ("
            "org_id, project_id, report_id, report_version, "
            "project_title, "
            "generated_from_state_version, observation_schema_version, status, "
            "failed_invariants_json, warning_invariants_json, score_snapshot_json, "
            "evidence_counts_json, canonical_boundaries_json, observation_json"
            ") VALUES ("
            ":org_id, :project_id, :report_id, :report_version, "
            ":project_title, "
            ":generated_from_state_version, :observation_schema_version, :status, "
            ":failed_invariants_json, :warning_invariants_json, :score_snapshot_json, "
            ":evidence_counts_json, :canonical_boundaries_json, :observation_json"
            ") "
            "ON CONFLICT (report_id, generated_from_state_version) "
            "WHERE deleted_at IS NULL "
            "DO UPDATE SET "
            "org_id = EXCLUDED.org_id, "
            "project_id = EXCLUDED.project_id, "
            "project_title = EXCLUDED.project_title, "
            "report_version = EXCLUDED.report_version, "
            "observation_schema_version = EXCLUDED.observation_schema_version, "
            "status = EXCLUDED.status, "
            "failed_invariants_json = EXCLUDED.failed_invariants_json, "
            "warning_invariants_json = EXCLUDED.warning_invariants_json, "
            "score_snapshot_json = EXCLUDED.score_snapshot_json, "
            "evidence_counts_json = EXCLUDED.evidence_counts_json, "
            "canonical_boundaries_json = EXCLUDED.canonical_boundaries_json, "
            "observation_json = EXCLUDED.observation_json, "
            "observed_at = now(), "
            "updated_at = now() "
            "RETURNING id, org_id, project_id, project_title, report_id, report_version, "
            "generated_from_state_version, observation_schema_version, status, "
            "failed_invariants_json, warning_invariants_json, score_snapshot_json, "
            "evidence_counts_json, canonical_boundaries_json, observation_json, "
            "observed_at, created_at, updated_at"
        ).bindparams(
            bindparam("failed_invariants_json", type_=JSONB),
            bindparam("warning_invariants_json", type_=JSONB),
            bindparam("score_snapshot_json", type_=JSONB),
            bindparam("evidence_counts_json", type_=JSONB),
            bindparam("canonical_boundaries_json", type_=JSONB),
            bindparam("observation_json", type_=JSONB),
        ),
        dict(record),
    )
    row = result.mappings().first()
    return dict(row) if row else None


def _sanitize_observation_detail(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if key.strip().lower() in UNSAFE_DETAIL_KEYS:
                continue
            sanitized[key] = _sanitize_observation_detail(raw_value)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_observation_detail(item) for item in value]
    return value


def _normalize_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return status if status in VALID_STATUSES else "fail"


def _compact_text(value: Any, *, max_len: int) -> str | None:
    if value is None:
        return None
    text_value = " ".join(str(value).split()).strip()
    if not text_value:
        return None
    return text_value[:max_len]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
