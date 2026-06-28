from __future__ import annotations

from typing import Any

from sqlalchemy import TEXT, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.report_builder import build_assessment_snapshots, build_report_payload
from app.services.diagnostics import (
    build_report_diagnosis,
    build_validation_plan,
    merge_validation_plans,
)
from app.services.localization import DEFAULT_OUTPUT_LOCALE, normalize_summary_locale_map
from app.services.stage_payloads import (
    normalize_ai_assisted_map,
    normalize_user_edited_map,
)


async def fetch_project_report_payload(
    session: AsyncSession,
    project_id: Any,
    *,
    output_locale: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT "
            "p.id, "
            "p.title, "
            "p.description, "
            "p.current_stage, "
            "p.question_bank_version_id, "
            "p.updated_at, "
            "pr.id AS report_id, "
            "pr.content_json, "
            "pr.diagnosis_json, "
            "pr.validation_plan_json, "
            "pr.artifact_schema_version, "
            "pr.decision_snapshot_json, "
            "pr.score_rationales_json, "
            "pr.risk_register_json, "
            "pr.experiment_plan_json, "
            "pr.evidence_index_json, "
            "pr.created_at AS report_created_at "
            "FROM projects p "
            "JOIN project_reports pr "
            "ON pr.project_id = p.id "
            "AND pr.org_id = p.org_id "
            "AND pr.deleted_at IS NULL "
            "AND COALESCE(NULLIF(pr.content_json->>'artifact_locale', ''), "
            ":default_output_locale) = :output_locale "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "ORDER BY pr.report_version DESC "
            "LIMIT 1"
        ),
        {
            "project_id": str(project_id),
            "output_locale": output_locale,
            "default_output_locale": DEFAULT_OUTPUT_LOCALE,
        },
    )
    row = result.mappings().first()
    if not row:
        return None

    state_result = await session.execute(
        text(
            "SELECT state_json, state_meta "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    state_row = state_result.mappings().first()
    state_json = state_row.get("state_json") if state_row else {}
    if not isinstance(state_json, dict):
        state_json = {}
    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    summary_locales = normalize_summary_locale_map(state_meta)

    runtime_result = await session.execute(
        text(
            "SELECT missing_paths "
            "FROM project_runtime "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    runtime_row = runtime_result.mappings().first()
    missing_paths = list(runtime_row.get("missing_paths") or []) if runtime_row else []
    if not isinstance(missing_paths, list):
        missing_paths = list(missing_paths or [])

    skipped_result = await session.execute(
        text(
            "SELECT COUNT(*) AS skipped_count "
            "FROM project_question_instances "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND status = 'skipped' "
            "AND deleted_at IS NULL"
        ),
        {"project_id": str(project_id)},
    )
    skipped_row = skipped_result.mappings().first()
    skipped_count = int(skipped_row.get("skipped_count") or 0) if skipped_row else 0

    missing_questions: list[dict[str, Any]] = []
    bank_version_id = row.get("question_bank_version_id")
    if missing_paths and bank_version_id:
        missing_result = await session.execute(
            text(
                "SELECT DISTINCT question_id, title "
                "FROM question_bank_questions "
                "WHERE bank_version_id = :bank_version_id "
                "AND deleted_at IS NULL "
                "AND schema_paths && :missing_paths "
                "ORDER BY order_index ASC"
            ).bindparams(bindparam("missing_paths", type_=ARRAY(TEXT))),
            {
                "bank_version_id": str(bank_version_id),
                "missing_paths": missing_paths,
            },
        )
        for missing_row in missing_result.mappings().all():
            question_id = missing_row.get("question_id")
            title = missing_row.get("title")
            if question_id or title:
                missing_questions.append(
                    {
                        "question_id": question_id,
                        "title": title,
                    }
                )

    assessments_result = await session.execute(
        text(
            "SELECT id, stage, draft_summary_markdown, final_summary_markdown, "
            "confirmed, total_score, confirmed_at, created_at, updated_at, "
            "context_card_json, validation_plan_json "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {"project_id": str(project_id)},
    )
    assessment_rows = assessments_result.mappings().all()
    assessments = build_assessment_snapshots(
        assessment_rows,
        summary_locales=summary_locales,
    )

    report_created_at = row.get("report_created_at")
    base_payload = build_report_payload(
        row,
        state_json,
        assessments,
        generated_at=report_created_at,
        artifact_locale=None,
        ai_assisted_paths=normalize_ai_assisted_map(state_meta),
        user_edited_paths=normalize_user_edited_map(state_meta),
    )
    base_payload["data_quality"] = {
        "missing_paths": missing_paths,
        "missing_questions": missing_questions,
        "missing_count": len(missing_paths),
        "skipped_questions": {"count": skipped_count},
    }
    base_payload["diagnosis"] = (
        row.get("diagnosis_json") if isinstance(row.get("diagnosis_json"), dict) else {}
    )
    base_payload["validation_plan"] = (
        row.get("validation_plan_json")
        if isinstance(row.get("validation_plan_json"), list)
        else []
    )
    if not base_payload["diagnosis"]:
        base_payload["diagnosis"] = build_report_diagnosis(
            assessments=assessments,
            dvf_confidence=base_payload.get("dvf_confidence")
            if isinstance(base_payload.get("dvf_confidence"), dict)
            else {},
            key_risks=base_payload.get("key_risks")
            if isinstance(base_payload.get("key_risks"), list)
            else [],
        )
    if not base_payload["validation_plan"]:
        stage_validation_plans = [
            item.get("validation_plan")
            for item in assessments
            if isinstance(item, dict) and isinstance(item.get("validation_plan"), list)
        ]
        base_payload["validation_plan"] = merge_validation_plans(
            *stage_validation_plans,
            build_validation_plan(
                stage="report",
                context_card={},
                key_risks=base_payload.get("key_risks")
                if isinstance(base_payload.get("key_risks"), list)
                else [],
            ),
        )

    content_json = row.get("content_json")
    if isinstance(content_json, dict):
        payload: dict[str, Any] = {**base_payload, **content_json}
        if not payload.get("project_id"):
            payload["project_id"] = base_payload.get("project_id")
        if not payload.get("generated_at"):
            payload["generated_at"] = base_payload.get("generated_at")
        if not payload.get("project"):
            payload["project"] = base_payload.get("project")
        if not payload.get("assessments"):
            payload["assessments"] = base_payload.get("assessments")
        if not payload.get("lean_canvas"):
            payload["lean_canvas"] = base_payload.get("lean_canvas")
        if not payload.get("dvf_scoreboard"):
            payload["dvf_scoreboard"] = base_payload.get("dvf_scoreboard")
        if "overall_summary" not in payload:
            payload["overall_summary"] = base_payload.get("overall_summary")
        if "user_edited_paths" not in payload:
            payload["user_edited_paths"] = base_payload.get("user_edited_paths")
        if "data_quality" not in payload:
            payload["data_quality"] = base_payload.get("data_quality")
        if not payload.get("diagnosis"):
            payload["diagnosis"] = base_payload.get("diagnosis")
        if not payload.get("validation_plan"):
            payload["validation_plan"] = base_payload.get("validation_plan")
    else:
        payload = base_payload

    payload["artifact_schema_version"] = (
        row.get("artifact_schema_version") or payload.get("artifact_schema_version")
    )
    payload["decision_snapshot"] = (
        row.get("decision_snapshot_json")
        if isinstance(row.get("decision_snapshot_json"), dict)
        else payload.get("decision_snapshot") or {}
    )
    payload["score_rationales"] = (
        row.get("score_rationales_json")
        if isinstance(row.get("score_rationales_json"), dict)
        else payload.get("score_rationales") or {}
    )
    payload["risk_register"] = (
        row.get("risk_register_json")
        if isinstance(row.get("risk_register_json"), list)
        else payload.get("risk_register") or []
    )
    payload["experiment_plan"] = (
        row.get("experiment_plan_json")
        if isinstance(row.get("experiment_plan_json"), list)
        else payload.get("experiment_plan") or []
    )
    payload["evidence_index"] = (
        row.get("evidence_index_json")
        if isinstance(row.get("evidence_index_json"), dict)
        else payload.get("evidence_index") or {}
    )
    return payload


__all__ = ["fetch_project_report_payload"]
