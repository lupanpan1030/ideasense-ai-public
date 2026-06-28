from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


def _is_report_value_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_is_report_value_non_empty(item) for item in value)
    if isinstance(value, dict):
        return any(_is_report_value_non_empty(item) for item in value.values())
    return True


def normalize_report_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        items = [item for item in value if _is_report_value_non_empty(item)]
        if not items:
            return None
        if all(isinstance(item, str) for item in items):
            return "; ".join(item.strip() for item in items if item.strip())
        return json.dumps(items, ensure_ascii=True)
    if isinstance(value, dict):
        if not _is_report_value_non_empty(value):
            return None
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def to_report_score(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def scoreboard_has_scores(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(
        to_report_score(value.get(key)) is not None
        for key in ("desirability", "viability", "feasibility", "total_score")
    )


def compact_report_text(value: Any, *, max_len: int = 220) -> str | None:
    text_value = normalize_report_value(value)
    if not text_value:
        return None
    compacted = " ".join(text_value.replace("#", "").split())
    if len(compacted) > max_len:
        return f"{compacted[: max_len - 3].rstrip()}..."
    return compacted


def assessment_summary_by_stage(
    assessments: Any,
) -> dict[str, str]:
    if not isinstance(assessments, list):
        return {}
    summaries: dict[str, str] = {}
    for item in assessments:
        if not isinstance(item, Mapping):
            continue
        stage = item.get("stage")
        if not isinstance(stage, str) or not stage.strip():
            continue
        summary = compact_report_text(
            item.get("summary_text") or item.get("draft_summary_text"),
            max_len=260,
        )
        if summary:
            summaries[stage.strip().lower()] = summary
    return summaries


def fallback_dimension_score(
    confidence: Mapping[str, Any],
    dimension: str,
) -> int:
    dimensions = confidence.get("dimensions")
    raw_score = None
    if isinstance(dimensions, Mapping):
        raw_score = to_report_score(dimensions.get(dimension))
    if raw_score is None:
        raw_score = to_report_score(confidence.get("coverage"))
    if raw_score is None:
        raw_score = 0
    score = round(30 + (max(0, min(100, raw_score)) * 0.45))
    return max(30, min(75, score))


def fallback_decision_band(total_score: int) -> str:
    if total_score >= 70:
        return "Validate next"
    if total_score >= 50:
        return "Needs validation"
    return "High uncertainty"


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        text_value = compact_report_text(value, max_len=240)
        if text_value:
            return text_value
    return None


def _collect_context_cards(report_payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    diagnosis = as_mapping(report_payload.get("diagnosis"))
    cards = diagnosis.get("context_cards")
    if isinstance(cards, Mapping) and cards:
        return {
            str(stage).strip().lower(): as_mapping(card)
            for stage, card in cards.items()
            if str(stage).strip() and isinstance(card, Mapping)
        }

    collected: dict[str, Mapping[str, Any]] = {}
    for assessment in as_list(report_payload.get("assessments")):
        if not isinstance(assessment, Mapping):
            continue
        stage = assessment.get("stage")
        card = assessment.get("context_card")
        if isinstance(stage, str) and stage.strip() and isinstance(card, Mapping) and card:
            collected[stage.strip().lower()] = card
    return collected


def _evidence_item_label(item: Any) -> str | None:
    if isinstance(item, Mapping):
        return compact_report_text(
            item.get("label") or item.get("path") or item.get("claim") or item.get("value"),
            max_len=140,
        )
    return compact_report_text(item, max_len=140)


def _collect_evidence_layer_items(
    context_cards: Mapping[str, Mapping[str, Any]],
    layer: str,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for stage, card in context_cards.items():
        for entry in as_list(card.get(layer)):
            label = _evidence_item_label(entry)
            if not label:
                continue
            item: dict[str, Any] = {
                "stage": stage,
                "layer": layer,
                "label": label,
            }
            if isinstance(entry, Mapping):
                for key in (
                    "path",
                    "value",
                    "resolution_status",
                    "claim_type",
                    "evidence_level",
                    "reason",
                    "source",
                    "note",
                    "pending",
                ):
                    if entry.get(key) is not None:
                        item[key] = entry.get(key)
            items.append(item)
            if len(items) >= limit:
                return items
    return items


def _collect_verification_items(
    context_cards: Mapping[str, Mapping[str, Any]],
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for stage, card in context_cards.items():
        summary = card.get("verification_summary")
        if not isinstance(summary, Mapping):
            continue
        for entry in as_list(summary.get("items")):
            if not isinstance(entry, Mapping):
                continue
            claim = compact_report_text(entry.get("claim") or entry.get("text"), max_len=180)
            if not claim:
                continue
            items.append(
                {
                    "stage": stage,
                    "layer": "verification_summary",
                    "label": claim,
                    "claim": claim,
                    "verdict": entry.get("verdict") or summary.get("status"),
                    "confidence": entry.get("confidence"),
                    "source": "verification",
                }
            )
            if len(items) >= limit:
                return items
    return items


def _build_evidence_index(
    report_payload: Mapping[str, Any],
) -> dict[str, Any]:
    context_cards = _collect_context_cards(report_payload)
    layers = [
        "user_confirmed_inputs",
        "founder_assumptions",
        "ai_inferences",
        "unknowns",
        "evidence_gaps",
    ]
    counts: dict[str, int] = {}
    items: list[dict[str, Any]] = []
    for layer in layers:
        layer_count = 0
        for card in context_cards.values():
            layer_count += len(as_list(card.get(layer)))
        counts[layer] = layer_count
        items.extend(_collect_evidence_layer_items(context_cards, layer, limit=12))
    verification_items = _collect_verification_items(context_cards, limit=6)
    if verification_items:
        counts["verification_summary"] = len(verification_items)
        items.extend(verification_items)
    verification_summary = {
        stage: dict(card.get("verification_summary"))
        for stage, card in context_cards.items()
        if isinstance(card.get("verification_summary"), Mapping)
    }
    return {
        "counts": counts,
        "items": items[:40],
        "verification_summary": verification_summary,
    }


def _gap_label_text(item: Mapping[str, Any]) -> str | None:
    reason = compact_report_text(item.get("reason"), max_len=180)
    label = compact_report_text(item.get("label") or item.get("path"), max_len=140)
    if reason and label and label.lower() not in reason.lower():
        return f"{label}: {reason}"
    return reason or label


def _build_top_gaps(report_payload: Mapping[str, Any]) -> list[str]:
    context_cards = _collect_context_cards(report_payload)
    gaps: list[str] = []
    for layer in ("evidence_gaps", "unknowns"):
        for item in _collect_evidence_layer_items(context_cards, layer, limit=5):
            label = _gap_label_text(item)
            if label and label not in gaps:
                gaps.append(label)
            if len(gaps) >= 5:
                return gaps
    for item in _collect_verification_items(context_cards, limit=5):
        verdict = compact_report_text(item.get("verdict"), max_len=80)
        label = compact_report_text(item.get("label"), max_len=180)
        if not label:
            continue
        gap_text = f"{label}: verification {verdict or 'needs review'}"
        if gap_text not in gaps:
            gaps.append(gap_text)
        if len(gaps) >= 5:
            return gaps
    data_quality = as_mapping(report_payload.get("data_quality"))
    missing_paths = as_list(data_quality.get("missing_paths"))
    for path in missing_paths:
        text = compact_report_text(path, max_len=120)
        if text and text not in gaps:
            gaps.append(text)
        if len(gaps) >= 5:
            break
    return gaps


def _build_top_findings(report_payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for stage, summary in assessment_summary_by_stage(
        report_payload.get("assessments")
    ).items():
        if summary:
            findings.append(f"{stage}: {summary}")
        if len(findings) >= 3:
            return findings
    market_evidence = as_mapping(report_payload.get("market_evidence"))
    for value in (
        market_evidence.get("signals"),
        market_evidence.get("channel_tests"),
        market_evidence.get("channel_test_success"),
    ):
        text = compact_report_text(value, max_len=180)
        if text:
            findings.append(text)
        if len(findings) >= 3:
            break
    return findings


def _build_decision_snapshot(
    report_payload: Mapping[str, Any],
) -> dict[str, Any]:
    existing = as_mapping(report_payload.get("decision_snapshot"))
    scoreboard = as_mapping(report_payload.get("dvf_scoreboard"))
    diagnosis = as_mapping(report_payload.get("diagnosis"))
    confidence = as_mapping(report_payload.get("dvf_confidence"))
    validation_plan = as_list(report_payload.get("validation_plan"))
    first_action = next(
        (item for item in validation_plan if isinstance(item, Mapping)),
        {},
    )
    rationale = _first_text(
        [
            existing.get("rationale"),
            diagnosis.get("summary"),
            diagnosis.get("diagnosis_summary"),
            report_payload.get("overall_summary"),
        ]
    )
    return {
        "verdict": existing.get("verdict")
        or scoreboard.get("decision_band")
        or fallback_decision_band(
            int(to_report_score(scoreboard.get("total_score")) or 0)
        ),
        "total_score": to_report_score(
            existing.get("total_score") or scoreboard.get("total_score")
        ),
        "confidence": existing.get("confidence") or confidence.get("level"),
        "rationale": rationale,
        "top_findings": as_list(existing.get("top_findings"))
        or _build_top_findings(report_payload),
        "top_gaps": as_list(existing.get("top_gaps"))
        or _build_top_gaps(report_payload),
        "next_action": existing.get("next_action")
        or (first_action.get("action") if isinstance(first_action, Mapping) else None),
    }


def _build_dimension_rationale(
    report_payload: Mapping[str, Any],
    dimension: str,
) -> dict[str, Any]:
    existing = as_mapping(report_payload.get("score_rationales")).get(dimension)
    if isinstance(existing, Mapping) and existing:
        return dict(existing)

    assessment = as_mapping(report_payload.get("dvf_assessment"))
    detail = as_mapping(assessment.get(dimension))
    scoreboard = as_mapping(report_payload.get("dvf_scoreboard"))
    context_cards = _collect_context_cards(report_payload)
    evidence_refs = _collect_evidence_layer_items(
        context_cards,
        "user_confirmed_inputs",
        limit=4,
    )
    gaps = _build_top_gaps(report_payload)
    return {
        "score": to_report_score(detail.get("score") or scoreboard.get(dimension)),
        "confidence": detail.get("confidence"),
        "rationale": compact_report_text(detail.get("comment"), max_len=260),
        "evidence_references": evidence_refs,
        "evidence_gaps": gaps[:4],
    }


def _build_score_rationales(
    report_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        dimension: _build_dimension_rationale(report_payload, dimension)
        for dimension in ("desirability", "viability", "feasibility")
    }


def _build_risk_register(
    report_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing = report_payload.get("risk_register")
    risks = existing if isinstance(existing, list) and existing else report_payload.get("key_risks")
    register: list[dict[str, Any]] = []
    for item in as_list(risks):
        if not isinstance(item, Mapping):
            continue
        risk_text = compact_report_text(item.get("risk") or item.get("label"), max_len=220)
        if not risk_text:
            continue
        register.append(
            {
                "risk": risk_text,
                "severity": item.get("severity") or "medium",
                "likelihood": item.get("likelihood") or "medium",
                "category": item.get("category") or "General",
                "linked_evidence": item.get("linked_evidence")
                or item.get("linked_risk"),
                "early_warning_signal": item.get("early_warning_signal"),
                "mitigation_suggestion": item.get("mitigation_suggestion")
                or item.get("mitigation"),
            }
        )
    return register


def _build_experiment_plan(
    report_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing = report_payload.get("experiment_plan")
    plan = existing if isinstance(existing, list) and existing else report_payload.get("validation_plan")
    experiments: list[dict[str, Any]] = []
    for item in as_list(plan):
        if not isinstance(item, Mapping):
            continue
        action = compact_report_text(item.get("action"), max_len=220)
        if not action:
            continue
        experiments.append(
            {
                "action": action,
                "target": item.get("target"),
                "success_signal": item.get("success_signal"),
                "linked_risk": item.get("linked_risk"),
                "priority": item.get("priority") or "medium",
                "time_horizon": item.get("time_horizon") or "14 days",
            }
        )
    return experiments


def build_report_v2_sections(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    decision_snapshot = _build_decision_snapshot(report_payload)
    score_rationales = _build_score_rationales(report_payload)
    risk_register = _build_risk_register(report_payload)
    experiment_plan = _build_experiment_plan(report_payload)
    evidence_index = _build_evidence_index(report_payload)
    return {
        "artifact_schema_version": "report_v2",
        "decision_snapshot": decision_snapshot,
        "score_rationales": score_rationales,
        "risk_register": risk_register,
        "experiment_plan": experiment_plan,
        "evidence_index": dict(evidence_index),
    }
