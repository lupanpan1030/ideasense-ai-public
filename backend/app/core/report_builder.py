import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Mapping

from app.core.report_sections import (
    _is_report_value_non_empty as _is_non_empty,
    normalize_report_value as _normalize_report_value,
)
from app.services.localization import OutputLocale


def _get_value_by_path(data: dict[str, Any], path: str) -> Any:
    cursor: Any = data
    for raw_part in path.split("."):
        key = raw_part[:-2] if raw_part.endswith("[]") else raw_part
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _coalesce_state_value(state_json: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        value = _get_value_by_path(state_json, path)
        if _is_non_empty(value):
            return value
    return None


_DVF_CONFIDENCE_PATHS: dict[str, list[list[str]]] = {
    "desirability": [
        ["problem.main_problems", "problem.main_problems[]"],
        ["problem.one_line"],
        ["target_user.priority_segment", "target_user.core"],
        ["problem.scenarios", "problem.scenarios[]"],
        ["problem.severity_score"],
        ["impact.time_impact", "impact.money_impact"],
        ["alternatives.current_solutions", "alternatives.current_solutions[]"],
    ],
    "viability": [
        ["market_strategy.uvp.one_line"],
        ["market_strategy.business_model.revenue_model"],
        ["market_strategy.business_model.pricing_unit"],
        [
            "market_strategy.business_model.initial_price_point_raw",
            "market_strategy.business_model.initial_price_point_normalized",
        ],
        ["market_strategy.market_size.initial_segment_definition"],
        ["market_strategy.competition.positioning_summary"],
        ["market_strategy.go_to_market.primary_channels", "market_strategy.go_to_market.primary_channels[]"],
        ["market_strategy.validation.signals", "market_strategy.validation.signals[]"],
    ],
    "feasibility": [
        ["tech_execution.product_scope.mvp_definition"],
        [
            "tech_execution.architecture.architecture_style",
            "tech_execution.architecture.high_level_components",
        ],
        ["tech_execution.architecture.tech_stack_choices"],
        ["tech_execution.team_process.execution_team_type", "tech_execution.team_process.team_composition"],
        ["tech_execution.roadmap_risks.top_technical_risks"],
        ["tech_execution.security_compliance.data_types", "tech_execution.security_compliance.compliance_requirements"],
    ],
}


def _count_confidence_coverage(
    state_json: dict[str, Any], groups: list[list[str]]
) -> tuple[int, int]:
    total = len(groups)
    if total == 0:
        return 0, 0
    covered = 0
    for group in groups:
        for path in group:
            value = _get_value_by_path(state_json, path)
            if _is_non_empty(value):
                covered += 1
                break
    return covered, total


def _build_dvf_confidence(state_json: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state_json, dict):
        state_json = {}

    dimension_coverage: dict[str, int] = {}
    total_groups = 0
    total_covered = 0

    for dimension, groups in _DVF_CONFIDENCE_PATHS.items():
        covered, total = _count_confidence_coverage(state_json, groups)
        total_groups += total
        total_covered += covered
        coverage = round((covered / total) * 100) if total else 0
        dimension_coverage[dimension] = coverage

    overall = round((total_covered / total_groups) * 100) if total_groups else 0
    if overall >= 80:
        level = "high"
    elif overall >= 50:
        level = "medium"
    else:
        level = "low"

    return {
        "coverage": overall,
        "level": level,
        "dimensions": dimension_coverage,
    }


def build_lean_canvas(state_json: dict[str, Any]) -> dict[str, str | None]:
    if not isinstance(state_json, dict):
        state_json = {}

    return {
        "problem": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                ["problem.main_problems", "problem.main_problems[]"],
            )
        ),
        "customer_segments": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                ["target_user.priority_segment", "target_user.core"],
            )
        ),
        "unique_value_proposition": _normalize_report_value(
            _coalesce_state_value(state_json, ["market_strategy.uvp.one_line"])
        ),
        "solution": _normalize_report_value(
            _coalesce_state_value(state_json, ["problem_user.idea.raw"])
        ),
        "channels": _normalize_report_value(
            _coalesce_state_value(
                state_json, ["market_strategy.go_to_market.primary_channels"]
            )
        ),
        "revenue_streams": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                [
                    "market_strategy.business_model.revenue_model",
                    "market_strategy.business_model.secondary_revenue_streams",
                ],
            )
        ),
        "cost_structure": _normalize_report_value(
            _coalesce_state_value(
                state_json, ["market_strategy.unit_economics.main_cost_drivers"]
            )
        ),
        "key_metrics": None,
        "unfair_advantage": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                ["market_strategy.unfair_advantage", "market_strategy.moat.switching_costs"],
            )
        ),
    }


def build_market_evidence(state_json: dict[str, Any]) -> dict[str, str | None]:
    if not isinstance(state_json, dict):
        state_json = {}

    return {
        "signals": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                [
                    "market_strategy.validation.signals",
                    "market_strategy.validation.signals[]",
                ],
            )
        ),
        "channel_tests": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                [
                    "market_strategy.go_to_market.channel_tests",
                    "market_strategy.go_to_market.channel_tests[]",
                ],
            )
        ),
        "channel_test_success": _normalize_report_value(
            _coalesce_state_value(
                state_json,
                [
                    "market_strategy.go_to_market.channel_test_success",
                    "market_strategy.go_to_market.channel_test_success[]",
                ],
            )
        ),
    }


def _isoformat(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def build_assessment_snapshots(
    rows: Iterable[Mapping[str, Any]],
    summary_locales: Mapping[str, Mapping[str, OutputLocale]] | None = None,
) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for row in rows:
        stage = row.get("stage")
        assessment_id = row.get("id")
        if not stage or not assessment_id:
            continue
        confirmed = bool(row.get("confirmed"))
        summary_text = row.get("final_summary_markdown")
        draft_text = row.get("draft_summary_markdown")
        score_status = "confirmed" if confirmed else "draft"
        total_score = row.get("total_score")
        if isinstance(total_score, Decimal):
            total_score = float(total_score)
        stage_key = stage.strip().lower() if isinstance(stage, str) else ""
        locale_payload = (
            summary_locales.get(stage_key)
            if isinstance(summary_locales, Mapping) and stage_key
            else None
        )
        draft_output_locale = (
            locale_payload.get("draft")
            if isinstance(locale_payload, Mapping)
            else None
        )
        final_output_locale = (
            locale_payload.get("final")
            if isinstance(locale_payload, Mapping)
            else None
        )
        snapshots.append(
            {
                "id": str(assessment_id),
                "stage": stage,
                "summary_text": summary_text,
                "draft_summary_text": draft_text,
                "draft_output_locale": draft_output_locale,
                "final_output_locale": final_output_locale,
                "score_status": score_status,
                "total_score": total_score,
                "decision_band": None,
                "computed_at": _isoformat(row.get("confirmed_at")),
                "created_at": _isoformat(row.get("created_at")),
                "updated_at": _isoformat(row.get("updated_at")),
                "context_card": row.get("context_card_json")
                if isinstance(row.get("context_card_json"), dict)
                else {},
                "validation_plan": row.get("validation_plan_json")
                if isinstance(row.get("validation_plan_json"), list)
                else [],
            }
        )
    return snapshots


def build_stage_summary_map(
    assessments: list[dict[str, Any]],
) -> dict[str, str]:
    stage_map: dict[str, str] = {}
    for item in assessments:
        if not isinstance(item, dict):
            continue
        stage = item.get("stage")
        if not isinstance(stage, str) or not stage:
            continue
        summary = item.get("summary_text") or item.get("draft_summary_text") or ""
        if isinstance(summary, str) and summary.strip():
            stage_map[stage] = summary.strip()
    return stage_map


def build_report_input(
    project_payload: Mapping[str, Any],
    lean_canvas: Mapping[str, Any],
    market_evidence: Mapping[str, Any],
    assessments: list[dict[str, Any]],
    ai_assisted_paths: dict[str, list[str]] | None = None,
    user_edited_paths: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    context_cards = {
        item["stage"]: item.get("context_card") or {}
        for item in assessments
        if isinstance(item, dict)
        and isinstance(item.get("stage"), str)
        and isinstance(item.get("context_card"), dict)
        and item.get("context_card")
    }
    validation_plans = {
        item["stage"]: item.get("validation_plan") or []
        for item in assessments
        if isinstance(item, dict)
        and isinstance(item.get("stage"), str)
        and isinstance(item.get("validation_plan"), list)
        and item.get("validation_plan")
    }
    return {
        "project": {
            "title": project_payload.get("title"),
            "description": project_payload.get("description"),
        },
        "lean_canvas": dict(lean_canvas),
        "market_evidence": dict(market_evidence),
        "stage_summaries": build_stage_summary_map(assessments),
        "context_cards": context_cards,
        "validation_plans": validation_plans,
        "ai_assisted_paths": ai_assisted_paths or {},
        "user_edited_paths": user_edited_paths or {},
    }


def parse_report_json(content: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def normalize_report_sections(raw: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    scoreboard = raw.get("dvf_scoreboard") or raw.get("dvfScoreboard")
    if isinstance(scoreboard, dict):
        normalized["dvf_scoreboard"] = scoreboard

    assessment = raw.get("dvf_assessment") or raw.get("dvfAssessment")
    if isinstance(assessment, dict):
        normalized["dvf_assessment"] = assessment

    key_risks = raw.get("key_risks") or raw.get("keyRisks")
    if isinstance(key_risks, list):
        normalized["key_risks"] = key_risks

    risk_matrix = raw.get("risk_matrix") or raw.get("riskMatrix")
    if isinstance(risk_matrix, dict):
        normalized["risk_matrix"] = risk_matrix

    overall_summary = (
        raw.get("overall_summary")
        or raw.get("overallSummary")
        or raw.get("overall_report")
    )
    if isinstance(overall_summary, dict):
        overall_summary = (
            overall_summary.get("summary")
            or overall_summary.get("executive_summary")
            or overall_summary.get("executiveSummary")
        )
    if isinstance(overall_summary, str) and overall_summary.strip():
        normalized["overall_summary"] = overall_summary.strip()

    architecture_diagram = raw.get("architecture_diagram") or raw.get(
        "architectureDiagram"
    )
    if architecture_diagram is not None:
        normalized["architecture_diagram"] = architecture_diagram

    diagnosis = raw.get("diagnosis") or raw.get("diagnosis_summary") or raw.get(
        "diagnosisSummary"
    )
    if isinstance(diagnosis, dict):
        normalized["diagnosis"] = diagnosis
    elif isinstance(diagnosis, str) and diagnosis.strip():
        normalized["diagnosis"] = {"summary": diagnosis.strip()}

    validation_plan = (
        raw.get("validation_plan")
        or raw.get("next_validation_steps")
        or raw.get("validationPlan")
        or raw.get("nextValidationSteps")
    )
    if isinstance(validation_plan, list):
        normalized["validation_plan"] = validation_plan

    for source_key, normalized_key in (
        ("decision_snapshot", "decision_snapshot"),
        ("decisionSnapshot", "decision_snapshot"),
        ("score_rationales", "score_rationales"),
        ("scoreRationales", "score_rationales"),
        ("evidence_index", "evidence_index"),
        ("evidenceIndex", "evidence_index"),
    ):
        value = raw.get(source_key)
        if isinstance(value, dict):
            normalized[normalized_key] = value

    risk_register = raw.get("risk_register") or raw.get("riskRegister")
    if isinstance(risk_register, list):
        normalized["risk_register"] = risk_register

    experiment_plan = (
        raw.get("experiment_plan")
        or raw.get("experimentPlan")
        or raw.get("experiments")
    )
    if isinstance(experiment_plan, list):
        normalized["experiment_plan"] = experiment_plan

    return normalized


def merge_report_payload(
    base_payload: dict[str, Any],
    updates: dict[str, Any] | None,
) -> dict[str, Any]:
    if not updates:
        return base_payload
    merged = dict(base_payload)
    for key in (
        "dvf_scoreboard",
        "dvf_assessment",
        "dvf_confidence",
        "key_risks",
        "risk_matrix",
        "diagnosis",
        "validation_plan",
        "architecture_diagram",
        "overall_summary",
        "decision_snapshot",
        "score_rationales",
        "risk_register",
        "experiment_plan",
        "evidence_index",
        "artifact_schema_version",
    ):
        if key in updates:
            merged[key] = updates[key]
    return merged


def build_report_payload(
    project_row: Mapping[str, Any],
    state_json: dict[str, Any],
    assessments: list[dict[str, Any]],
    generated_at: datetime | str | None = None,
    artifact_locale: OutputLocale | None = None,
    ai_assisted_paths: dict[str, list[str]] | None = None,
    user_edited_paths: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    project_id = project_row.get("id")
    generated_value = generated_at
    if isinstance(generated_at, datetime):
        generated_value = generated_at.isoformat()
    elif isinstance(generated_at, str):
        generated_value = generated_at
    else:
        generated_value = datetime.now(timezone.utc).isoformat()

    project_payload = {
        "id": str(project_id) if project_id else None,
        "title": project_row.get("title") or "Untitled project",
        "description": project_row.get("description"),
        "current_stage": project_row.get("current_stage") or "unknown",
        "updated_at": _isoformat(project_row.get("updated_at")),
    }

    return {
        "project_id": str(project_id) if project_id else None,
        "generated_at": generated_value,
        "artifact_locale": artifact_locale,
        "project": project_payload,
        "lean_canvas": build_lean_canvas(state_json),
        "market_evidence": build_market_evidence(state_json),
        "dvf_confidence": _build_dvf_confidence(state_json),
        "dvf_scoreboard": {
            "desirability": None,
            "viability": None,
            "feasibility": None,
            "total_score": None,
            "decision_band": None,
        },
        "dvf_assessment": None,
        "key_risks": [],
        "risk_matrix": None,
        "diagnosis": {},
        "validation_plan": [],
        "architecture_diagram": None,
        "overall_summary": None,
        "ai_assisted_paths": ai_assisted_paths or {},
        "user_edited_paths": user_edited_paths or {},
        "assessments": assessments,
    }


def build_report_markdown(report_payload: dict[str, Any]) -> str:
    project = report_payload.get("project") or {}
    title = project.get("title") or "Untitled project"
    generated_at = report_payload.get("generated_at") or ""
    assessments = report_payload.get("assessments") or []
    summary_map = {
        (item.get("stage") or ""): (
            item.get("summary_text")
            or item.get("draft_summary_text")
            or "Summary unavailable."
        )
        for item in assessments
        if isinstance(item, dict)
    }

    lines = [
        f"# {title}",
        f"Generated: {generated_at}",
        "",
        "## Problem",
        summary_map.get("problem", "Summary unavailable."),
        "",
        "## Market",
        summary_map.get("market", "Summary unavailable."),
        "",
        "## Tech",
        summary_map.get("tech", "Summary unavailable."),
    ]
    market_evidence = report_payload.get("market_evidence") or {}
    if isinstance(market_evidence, dict):
        signals = market_evidence.get("signals")
        tests = market_evidence.get("channel_tests")
        success = market_evidence.get("channel_test_success")
        if any(value for value in (signals, tests, success)):
            lines.extend(
                [
                    "",
                    "## Market Evidence",
                    f"- Signals: {signals or '-'}",
                    f"- Channel tests: {tests or '-'}",
                    f"- Success criteria: {success or '-'}",
                ]
            )
    lines.extend(
        [
            "",
            "## Overall summary",
            report_payload.get("overall_summary") or "Summary unavailable.",
        ]
    )
    diagnosis = report_payload.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis_summary = diagnosis.get("summary") or diagnosis.get("diagnosis_summary")
        context_cards = diagnosis.get("context_cards")
        diagnosis_lines: list[str] = []
        if isinstance(diagnosis_summary, str) and diagnosis_summary.strip():
            diagnosis_lines.append(diagnosis_summary.strip())
        if isinstance(context_cards, dict):
            for stage, card in context_cards.items():
                if not isinstance(card, dict):
                    continue
                counts = {
                    "confirmed": len(card.get("user_confirmed_inputs") or []),
                    "assumptions": len(card.get("founder_assumptions") or []),
                    "ai_inferences": len(card.get("ai_inferences") or []),
                    "unknowns": len(card.get("unknowns") or []),
                    "evidence_gaps": len(card.get("evidence_gaps") or []),
                }
                diagnosis_lines.append(
                    f"- {stage}: "
                    f"{counts['confirmed']} confirmed, "
                    f"{counts['assumptions']} assumptions, "
                    f"{counts['ai_inferences']} AI inferences, "
                    f"{counts['unknowns']} unknowns, "
                    f"{counts['evidence_gaps']} evidence gaps"
                )
        if diagnosis_lines:
            lines.extend(["", "## Diagnosis", "\n".join(diagnosis_lines)])
    validation_plan = report_payload.get("validation_plan")
    if isinstance(validation_plan, list) and validation_plan:
        lines.extend(["", "## Validation plan"])
        for item in validation_plan:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            target = item.get("target")
            signal = item.get("success_signal")
            if not isinstance(action, str) or not action.strip():
                continue
            suffix = []
            if isinstance(target, str) and target.strip():
                suffix.append(f"Target: {target.strip()}")
            if isinstance(signal, str) and signal.strip():
                suffix.append(f"Success signal: {signal.strip()}")
            detail = f" ({'; '.join(suffix)})" if suffix else ""
            lines.append(f"- {action.strip()}{detail}")
    ai_paths = report_payload.get("ai_assisted_paths")
    if isinstance(ai_paths, dict):
        flattened = []
        for stage, paths in ai_paths.items():
            if not isinstance(paths, list):
                continue
            for path in paths:
                if isinstance(path, str) and path.strip():
                    flattened.append(f"{stage}: {path}")
        if flattened:
            lines.extend(
                [
                    "",
                    "## AI-assisted inputs",
                    "\n".join(f"- {item}" for item in flattened),
                ]
            )
    user_paths = report_payload.get("user_edited_paths")
    if isinstance(user_paths, dict):
        flattened = []
        for stage, paths in user_paths.items():
            if not isinstance(paths, list):
                continue
            for path in paths:
                if isinstance(path, str) and path.strip():
                    flattened.append(f"{stage}: {path}")
        if flattened:
            lines.extend(
                [
                    "",
                    "## User-edited inputs",
                    "\n".join(f"- {item}" for item in flattened),
                ]
            )
    return "\n".join(lines).strip()
