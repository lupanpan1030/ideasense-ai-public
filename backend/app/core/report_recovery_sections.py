from __future__ import annotations

from typing import Any, Mapping

from app.core.report_sections import (
    assessment_summary_by_stage,
    compact_report_text,
    fallback_decision_band,
    fallback_dimension_score,
    scoreboard_has_scores,
    to_report_score,
)


def _build_fallback_overall_summary(report_payload: Mapping[str, Any]) -> str:
    project = report_payload.get("project")
    if not isinstance(project, Mapping):
        project = {}
    lean_canvas = report_payload.get("lean_canvas")
    if not isinstance(lean_canvas, Mapping):
        lean_canvas = {}
    market_evidence = report_payload.get("market_evidence")
    if not isinstance(market_evidence, Mapping):
        market_evidence = {}
    summaries = assessment_summary_by_stage(report_payload.get("assessments"))

    title = compact_report_text(project.get("title"), max_len=80) or "This idea"
    problem = compact_report_text(lean_canvas.get("problem"))
    segment = compact_report_text(lean_canvas.get("customer_segments"), max_len=140)
    value_prop = compact_report_text(
        lean_canvas.get("unique_value_proposition"),
        max_len=180,
    )
    market_signals = compact_report_text(market_evidence.get("signals"), max_len=160)

    lines = [f"{title} is assessed from the confirmed staged interview context."]
    if problem:
        lines.append(f"Problem focus: {problem}")
    if segment:
        lines.append(f"Primary segment: {segment}")
    if value_prop:
        lines.append(f"Value proposition: {value_prop}")
    if market_signals:
        lines.append(f"Validation signals to check next: {market_signals}")
    for stage in ("problem", "market", "tech"):
        summary = summaries.get(stage)
        if summary:
            lines.append(f"{stage.title()} summary: {summary}")
    lines.append(
        "Use the validation plan and risk register before treating the score as a final decision."
    )
    return " ".join(lines)


def _build_fallback_key_risks(
    report_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing = report_payload.get("key_risks")
    if isinstance(existing, list) and existing:
        return []

    data_quality = report_payload.get("data_quality")
    missing_count = 0
    if isinstance(data_quality, Mapping):
        raw_missing_count = to_report_score(data_quality.get("missing_count"))
        if raw_missing_count is not None:
            missing_count = int(raw_missing_count)

    risks: list[dict[str, Any]] = []
    if missing_count:
        risks.append(
            {
                "risk": "Some required interview context is still missing.",
                "severity": "Medium",
                "likelihood": "Medium",
                "category": "Data quality",
                "mitigation_suggestion": "Resolve the missing questions before making a final go/no-go decision.",
            }
        )

    risks.append(
        {
            "risk": "Founder assumptions still need external validation.",
            "severity": "Medium",
            "likelihood": "Medium",
            "category": "Validation",
            "mitigation_suggestion": "Run the recommended customer, pricing, and MVP tests before committing build effort.",
        }
    )
    return risks


def build_report_recovery_sections(
    report_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Fill missing report artifact fields from already-confirmed local context."""
    updates: dict[str, Any] = {}
    confidence = report_payload.get("dvf_confidence")
    if not isinstance(confidence, Mapping):
        confidence = {}

    if not scoreboard_has_scores(report_payload.get("dvf_scoreboard")):
        desirability = fallback_dimension_score(confidence, "desirability")
        viability = fallback_dimension_score(confidence, "viability")
        feasibility = fallback_dimension_score(confidence, "feasibility")
        total_score = round((desirability + viability + feasibility) / 3)
        updates["dvf_scoreboard"] = {
            "desirability": desirability,
            "viability": viability,
            "feasibility": feasibility,
            "total_score": total_score,
            "decision_band": fallback_decision_band(total_score),
        }
        updates["dvf_assessment"] = {
            "desirability": {
                "score": desirability,
                "comment": "Recovery score based on confirmed problem and customer-context coverage.",
                "subscores": None,
            },
            "viability": {
                "score": viability,
                "comment": "Recovery score based on confirmed market and business-model context coverage.",
                "subscores": None,
            },
            "feasibility": {
                "score": feasibility,
                "comment": "Recovery score based on confirmed MVP, architecture, team, and risk context coverage.",
                "subscores": None,
            },
            "total_score": total_score,
        }
    elif not isinstance(report_payload.get("dvf_assessment"), Mapping):
        scoreboard = report_payload.get("dvf_scoreboard")
        if isinstance(scoreboard, Mapping):
            total_score = to_report_score(scoreboard.get("total_score"))
            updates["dvf_assessment"] = {
                "desirability": {
                    "score": to_report_score(scoreboard.get("desirability")),
                    "comment": None,
                    "subscores": None,
                },
                "viability": {
                    "score": to_report_score(scoreboard.get("viability")),
                    "comment": None,
                    "subscores": None,
                },
                "feasibility": {
                    "score": to_report_score(scoreboard.get("feasibility")),
                    "comment": None,
                    "subscores": None,
                },
                "total_score": total_score,
            }

    if not compact_report_text(report_payload.get("overall_summary")):
        updates["overall_summary"] = _build_fallback_overall_summary(report_payload)

    fallback_risks = _build_fallback_key_risks(report_payload)
    if fallback_risks:
        updates["key_risks"] = fallback_risks

    return updates


__all__ = ["build_report_recovery_sections"]
