from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CANONICAL_FIXTURE = (
    REPO_ROOT / "backend" / "tests" / "fixtures" / "assessment_quality_cases.json"
)

EVIDENCE_LAYERS = (
    "user_confirmed_inputs",
    "founder_assumptions",
    "ai_inferences",
    "unknowns",
    "evidence_gaps",
    "verification_summary",
)
DIMENSIONS = ("desirability", "viability", "feasibility")


def load_canonical_cases(path: Path | None = None) -> dict[str, Any]:
    fixture_path = path or DEFAULT_CANONICAL_FIXTURE
    with fixture_path.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if not isinstance(fixture, dict) or not isinstance(fixture.get("cases"), list):
        raise ValueError("Canonical assessment fixture must contain cases[].")
    return fixture


def build_observation_from_artifact_dir(
    artifact_dir: Path,
    *,
    canonical_fixture_path: Path | None = None,
    require_canonical_match: bool = False,
) -> dict[str, Any]:
    report_payload, source = load_report_payload_from_artifact_dir(artifact_dir)
    return build_assessment_quality_observation(
        report_payload,
        canonical_fixture=load_canonical_cases(canonical_fixture_path),
        source={
            "artifact_dir": str(artifact_dir),
            "report_source": source,
        },
        require_canonical_match=require_canonical_match,
    )


def load_report_payload_from_artifact_dir(
    artifact_dir: Path,
) -> tuple[dict[str, Any], str]:
    report_api_path = artifact_dir / "report-api.json"
    if report_api_path.exists():
        report_payload = _read_json_object(report_api_path)
        db_payload = _load_latest_db_report_payload(artifact_dir)
        if db_payload:
            for key in (
                "id",
                "report_id",
                "report_version",
                "status",
                "generated_from_state_version",
            ):
                if report_payload.get(key) is None and db_payload.get(key) is not None:
                    report_payload[key] = db_payload.get(key)
            return report_payload, "report-api.json+db-report-v2.json"
        return report_payload, "report-api.json"

    db_payload = _load_latest_db_report_payload(artifact_dir)
    if db_payload:
        return db_payload, "db-report-v2.json"
    raise FileNotFoundError(
        "Expected report-api.json or db-report-v2.json in smoke artifact directory."
    )


def _load_latest_db_report_payload(artifact_dir: Path) -> dict[str, Any] | None:
    db_report_path = artifact_dir / "db-report-v2.json"
    if not db_report_path.exists():
        return None
    export_payload = _read_json_object(db_report_path)
    latest_report = export_payload.get("latest_report")
    if isinstance(latest_report, dict) and latest_report:
        return latest_report
    reports = export_payload.get("reports")
    if isinstance(reports, list) and reports and isinstance(reports[0], dict):
        return reports[0]
    return None


def build_assessment_quality_observation(
    report_payload: Mapping[str, Any],
    *,
    canonical_fixture: Mapping[str, Any] | None = None,
    source: Mapping[str, Any] | None = None,
    require_canonical_match: bool = False,
) -> dict[str, Any]:
    normalized = _normalize_report_payload(report_payload)
    canonical = canonical_fixture or load_canonical_cases()
    scores = _extract_scores(normalized)
    evidence_summary = _build_evidence_summary(normalized)
    dimensions = _build_dimension_summaries(normalized)
    canonical_comparison = _compare_with_canonical_cases(
        scores=scores,
        evidence_counts=evidence_summary["counts"],
        canonical_fixture=canonical,
    )
    invariants = _build_invariants(
        normalized=normalized,
        scores=scores,
        evidence_summary=evidence_summary,
        dimensions=dimensions,
        canonical_comparison=canonical_comparison,
        require_canonical_match=require_canonical_match,
    )
    status = _summarize_status(invariants)
    return {
        "artifact_schema_version": "assessment_quality_observation_v1",
        "source": {
            "canonical_version": canonical.get("version"),
            **dict(source or {}),
        },
        "report": {
            "project_id": normalized.get("project_id"),
            "report_id": normalized.get("report_id") or normalized.get("id"),
            "report_version": normalized.get("report_version"),
            "status": normalized.get("status"),
            "artifact_schema_version": normalized.get("artifact_schema_version"),
            "scores": scores,
            "decision_confidence": _decision_confidence(normalized),
        },
        "dimensions": dimensions,
        "evidence": evidence_summary,
        "unknowns": {
            "count": evidence_summary["counts"].get("unknowns", 0),
            "items": evidence_summary["items_by_layer"].get("unknowns", []),
            "top_gaps": _as_list(_decision_snapshot(normalized).get("top_gaps")),
        },
        "canonical_boundaries": canonical_comparison,
        "invariants": invariants,
        "summary": {
            "status": status,
            "failed": [item["id"] for item in invariants if item["status"] == "fail"],
            "warnings": [item["id"] for item in invariants if item["status"] == "warn"],
        },
    }


def write_observation_artifact(
    artifact_dir: Path,
    *,
    canonical_fixture_path: Path | None = None,
    require_canonical_match: bool = False,
) -> dict[str, Any]:
    observation = build_observation_from_artifact_dir(
        artifact_dir,
        canonical_fixture_path=canonical_fixture_path,
        require_canonical_match=require_canonical_match,
    )
    output_path = artifact_dir / "assessment-quality-observation.json"
    output_path.write_text(
        json.dumps(observation, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return observation


def _read_json_object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _normalize_report_payload(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(report_payload)
    for export_key, report_key in (
        ("decision_snapshot_json", "decision_snapshot"),
        ("score_rationales_json", "score_rationales"),
        ("risk_register_json", "risk_register"),
        ("experiment_plan_json", "experiment_plan"),
        ("evidence_index_json", "evidence_index"),
    ):
        if report_key not in normalized and isinstance(normalized.get(export_key), (dict, list)):
            normalized[report_key] = normalized.get(export_key)
    return normalized


def _extract_scores(report_payload: Mapping[str, Any]) -> dict[str, float | None]:
    snapshot = _decision_snapshot(report_payload)
    scoreboard = _as_mapping(report_payload.get("dvf_scoreboard"))
    rationales = _as_mapping(report_payload.get("score_rationales"))
    scores: dict[str, float | None] = {}
    for dimension in DIMENSIONS:
        rationale = _as_mapping(rationales.get(dimension))
        scores[dimension] = _to_score(rationale.get("score") or scoreboard.get(dimension))
    scores["total_score"] = _to_score(
        snapshot.get("total_score") or scoreboard.get("total_score")
    )
    return scores


def _build_dimension_summaries(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    rationales = _as_mapping(report_payload.get("score_rationales"))
    summaries: dict[str, Any] = {}
    for dimension in DIMENSIONS:
        rationale = _as_mapping(rationales.get(dimension))
        evidence_references = _as_list(rationale.get("evidence_references"))
        evidence_gaps = _as_list(rationale.get("evidence_gaps"))
        summaries[dimension] = {
            "score": _to_score(rationale.get("score")),
            "confidence": rationale.get("confidence"),
            "rationale_present": bool(_compact_text(rationale.get("rationale"))),
            "evidence_reference_count": len(evidence_references),
            "evidence_gap_count": len(evidence_gaps),
            "has_evidence_or_gap": bool(evidence_references or evidence_gaps),
        }
    return summaries


def _build_evidence_summary(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    evidence_index = _as_mapping(report_payload.get("evidence_index"))
    raw_counts = _as_mapping(evidence_index.get("counts"))
    counts = {
        layer: _safe_int(raw_counts.get(layer))
        for layer in EVIDENCE_LAYERS
    }
    raw_items = _as_list(evidence_index.get("items"))
    items_by_layer: dict[str, list[dict[str, Any]]] = {layer: [] for layer in EVIDENCE_LAYERS}
    paths_by_layer: dict[str, set[str]] = {layer: set() for layer in EVIDENCE_LAYERS}
    pending_paths: set[str] = set()
    ai_or_assumption_paths: set[str] = set()

    for item in raw_items:
        if not isinstance(item, Mapping):
            continue
        layer = str(item.get("layer") or "").strip()
        if layer not in items_by_layer:
            continue
        compact_item = _compact_evidence_item(item)
        if len(items_by_layer[layer]) < 10:
            items_by_layer[layer].append(compact_item)
        path = _compact_text(item.get("path"), max_len=240)
        if path:
            paths_by_layer[layer].add(path)
            if layer in {"ai_inferences", "founder_assumptions"}:
                ai_or_assumption_paths.add(path)
        if item.get("pending") is True and path:
            pending_paths.add(path)

    promoted_paths = sorted(
        (pending_paths | ai_or_assumption_paths)
        & paths_by_layer["user_confirmed_inputs"]
    )
    return {
        "counts": counts,
        "items_by_layer": items_by_layer,
        "promoted_paths": promoted_paths,
        "total_items": len(raw_items),
    }


def _compare_with_canonical_cases(
    *,
    scores: Mapping[str, float | None],
    evidence_counts: Mapping[str, int],
    canonical_fixture: Mapping[str, Any],
) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    nearest: dict[str, Any] | None = None
    for case in _as_list(canonical_fixture.get("cases")):
        if not isinstance(case, Mapping):
            continue
        expectations = _as_mapping(case.get("expectations"))
        ranges = _as_mapping(expectations.get("score_ranges"))
        distances = _score_boundary_distances(scores, ranges)
        score_distance = round(sum(distances.values()), 3)
        evidence_expectations = _as_mapping(expectations.get("min_evidence_counts"))
        evidence_met = {
            str(layer): _safe_int(evidence_counts.get(str(layer))) >= _safe_int(minimum)
            for layer, minimum in evidence_expectations.items()
        }
        case_summary = {
            "id": case.get("id"),
            "categories": _as_list(case.get("categories")),
            "score_distance": score_distance,
            "dimension_distances": distances,
            "evidence_expectations_met": evidence_met,
        }
        if score_distance == 0:
            matched.append(case_summary)
        if nearest is None or score_distance < nearest["score_distance"]:
            nearest = case_summary

    return {
        "within_any_score_boundary": bool(matched),
        "matched_cases": matched,
        "nearest_case": nearest,
    }


def _build_invariants(
    *,
    normalized: Mapping[str, Any],
    scores: Mapping[str, float | None],
    evidence_summary: Mapping[str, Any],
    dimensions: Mapping[str, Any],
    canonical_comparison: Mapping[str, Any],
    require_canonical_match: bool,
) -> list[dict[str, Any]]:
    invariants: list[dict[str, Any]] = []
    required_sections = (
        "decision_snapshot",
        "score_rationales",
        "evidence_index",
        "risk_register",
        "experiment_plan",
    )
    missing_sections = [
        section for section in required_sections if section not in normalized
    ]
    invariants.append(
        _invariant(
            "report_v2_sections_present",
            "fail" if missing_sections else "pass",
            {"missing_sections": missing_sections},
        )
    )

    missing_scores = [key for key, value in scores.items() if value is None]
    invariants.append(
        _invariant(
            "dvf_scores_present",
            "fail" if missing_scores else "pass",
            {"missing_scores": missing_scores},
        )
    )

    incomplete_dimensions = [
        dimension
        for dimension, summary in dimensions.items()
        if not (
            isinstance(summary, Mapping)
            and summary.get("score") is not None
            and summary.get("confidence") is not None
            and summary.get("rationale_present") is True
            and summary.get("has_evidence_or_gap") is True
        )
    ]
    invariants.append(
        _invariant(
            "score_rationales_complete",
            "fail" if incomplete_dimensions else "pass",
            {"incomplete_dimensions": incomplete_dimensions},
        )
    )

    counts = _as_mapping(evidence_summary.get("counts"))
    missing_count_layers = [
        layer for layer in EVIDENCE_LAYERS if layer not in counts
    ]
    invariants.append(
        _invariant(
            "evidence_index_counts_present",
            "fail" if missing_count_layers else "pass",
            {"missing_layers": missing_count_layers},
        )
    )

    unknown_gap_pressure = _safe_int(counts.get("unknowns")) + _safe_int(
        counts.get("evidence_gaps")
    )
    top_gaps = _as_list(_decision_snapshot(normalized).get("top_gaps"))
    invariants.append(
        _invariant(
            "top_gaps_cover_unknowns",
            "fail" if unknown_gap_pressure > 0 and not top_gaps else "pass",
            {"unknown_or_gap_count": unknown_gap_pressure, "top_gap_count": len(top_gaps)},
        )
    )

    promoted_paths = _as_list(evidence_summary.get("promoted_paths"))
    invariants.append(
        _invariant(
            "source_layers_not_promoted",
            "fail" if promoted_paths else "pass",
            {"promoted_paths": promoted_paths},
        )
    )

    confidence = str(_decision_confidence(normalized) or "").strip().lower()
    confidence_overstated = confidence == "high" and unknown_gap_pressure >= 5
    invariants.append(
        _invariant(
            "confidence_not_overstated",
            "fail" if confidence_overstated else "pass",
            {
                "decision_confidence": confidence or None,
                "unknown_or_gap_count": unknown_gap_pressure,
            },
        )
    )

    within_boundary = bool(canonical_comparison.get("within_any_score_boundary"))
    invariants.append(
        _invariant(
            "canonical_score_boundary",
            "fail" if require_canonical_match and not within_boundary else "pass"
            if within_boundary
            else "warn",
            {
                "within_any_score_boundary": within_boundary,
                "nearest_case": canonical_comparison.get("nearest_case"),
            },
        )
    )
    return invariants


def _score_boundary_distances(
    scores: Mapping[str, float | None],
    ranges: Mapping[str, Any],
) -> dict[str, float]:
    distances: dict[str, float] = {}
    for key in (*DIMENSIONS, "total_score"):
        score = scores.get(key)
        raw_range = ranges.get(key)
        if score is None or not isinstance(raw_range, list) or len(raw_range) != 2:
            distances[key] = 100.0
            continue
        lower = _to_score(raw_range[0])
        upper = _to_score(raw_range[1])
        if lower is None or upper is None:
            distances[key] = 100.0
        elif score < lower:
            distances[key] = round(lower - score, 3)
        elif score > upper:
            distances[key] = round(score - upper, 3)
        else:
            distances[key] = 0.0
    return distances


def _decision_snapshot(report_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(report_payload.get("decision_snapshot"))


def _decision_confidence(report_payload: Mapping[str, Any]) -> Any:
    snapshot = _decision_snapshot(report_payload)
    if snapshot.get("confidence") is not None:
        return snapshot.get("confidence")
    confidence = _as_mapping(report_payload.get("dvf_confidence"))
    return confidence.get("level")


def _compact_evidence_item(item: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in (
        "stage",
        "layer",
        "path",
        "label",
        "resolution_status",
        "claim_type",
        "evidence_level",
        "source",
        "note",
        "pending",
        "verdict",
        "confidence",
    ):
        value = item.get(key)
        if value is not None:
            output[key] = value
    return output


def _invariant(
    invariant_id: str,
    status: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": invariant_id,
        "status": status,
        "details": dict(details or {}),
    }


def _summarize_status(invariants: list[dict[str, Any]]) -> str:
    if any(item.get("status") == "fail" for item in invariants):
        return "fail"
    if any(item.get("status") == "warn" for item in invariants):
        return "warn"
    return "pass"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return 0
    return 0


def _to_score(value: Any) -> float | None:
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


def _compact_text(value: Any, *, max_len: int = 220) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = " ".join(value.split())
    else:
        text = " ".join(json.dumps(value, ensure_ascii=True, sort_keys=True).split())
    if not text:
        return None
    if len(text) > max_len:
        return f"{text[: max_len - 3].rstrip()}..."
    return text
