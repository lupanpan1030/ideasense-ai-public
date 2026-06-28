"""Evidence-layered diagnosis helpers for staged assessments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from app.services.answer_meta import extract_answer_value_and_meta, get_answer_meta_map


STAGE_ROOT_KEYS: dict[str, tuple[str, ...]] = {
    "problem": (
        "problem_user",
        "problem",
        "target_user",
        "impact",
        "alternatives",
        "evidence",
    ),
    "market": ("market_strategy",),
    "tech": ("tech_execution",),
}

UNKNOWN_STATUSES = {"unknown", "undecided", "not_applicable", "partial"}
LOW_EVIDENCE_LEVELS = {"E0", "E1"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_is_non_empty(item) for item in value)
    if isinstance(value, dict):
        return any(_is_non_empty(item) for item in value.values())
    return True


def _normalize_stage(stage: Any) -> str:
    if isinstance(stage, str) and stage.strip():
        return stage.strip().lower()
    return "problem"


def _stage_roots(stage: str) -> tuple[str, ...]:
    return STAGE_ROOT_KEYS.get(_normalize_stage(stage), ())


def _format_label(path: str) -> str:
    raw = path.split(".")[-1].replace("[]", "")
    return raw.replace("_", " ").strip().title() or path


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return "; ".join(item.strip() for item in value if item.strip())
        return str(value)
    if isinstance(value, dict):
        return str(value)
    return str(value)


def _iter_state_values(
    value: Any,
    *,
    prefix: str = "",
) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                continue
            next_prefix = f"{prefix}.{key}" if prefix else key
            yield from _iter_state_values(item, prefix=next_prefix)
        return
    if isinstance(value, list):
        if not _is_non_empty(value):
            return
        yield prefix, value
        return
    if _is_non_empty(value):
        yield prefix, value


def _iter_pending_values(value: Any, *, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        if "value" in value or "suggested_value" in value or "suggested" in value:
            yield prefix, value
            return
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                continue
            next_prefix = f"{prefix}.{key}" if prefix else key
            yield from _iter_pending_values(item, prefix=next_prefix)
        return
    if _is_non_empty(value):
        yield prefix, value


def _path_stage(path: str, fallback_stage: str) -> str:
    root = path.split(".", 1)[0]
    for stage, roots in STAGE_ROOT_KEYS.items():
        if root in roots:
            return stage
    return fallback_stage


def _meta_for_path(
    answer_meta: Mapping[str, Mapping[str, Any]],
    path: str,
) -> dict[str, Any]:
    candidates = [path]
    if path.endswith("[]"):
        candidates.append(path[:-2])
    else:
        candidates.append(f"{path}[]")
    for candidate in candidates:
        entry = answer_meta.get(candidate)
        if isinstance(entry, Mapping):
            return dict(entry)
    return {
        "resolution_status": "answered",
        "claim_type": "hypothesis",
        "evidence_level": "E1",
        "source": "user",
    }


def _diagnosis_entry(
    path: str,
    value: Any,
    meta: Mapping[str, Any],
    *,
    pending: bool = False,
) -> dict[str, Any]:
    return {
        "path": path,
        "label": _format_label(path),
        "value": _format_value(value),
        "resolution_status": str(meta.get("resolution_status") or "answered"),
        "claim_type": str(meta.get("claim_type") or "hypothesis"),
        "evidence_level": str(meta.get("evidence_level") or "E1").upper(),
        "source": str(meta.get("source") or "user"),
        "note": meta.get("note") if isinstance(meta.get("note"), str) else None,
        "pending": pending,
    }


def _pending_value_and_meta(value: Any) -> tuple[Any, dict[str, Any]]:
    resolved_value, meta = extract_answer_value_and_meta(value, default_source="ai")
    if not (isinstance(value, Mapping) and value.get("resolution_status")):
        meta["resolution_status"] = "suggested"
    if not (isinstance(value, Mapping) and value.get("evidence_level")):
        meta["evidence_level"] = "E0"
    if not meta.get("note"):
        meta["note"] = "Pending confirmation."
    return resolved_value, meta


def summarize_verification_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or not payload.get("enabled"):
        return {
            "status": "not_checked",
            "supported_claims": 0,
            "unsupported_claims": 0,
            "uncertain_claims": 0,
            "supported_ratio": None,
            "items": [],
        }

    counts = payload.get("verdict_counts_overall")
    counts = counts if isinstance(counts, Mapping) else {}
    supported_items = payload.get("verified_facts")
    unsupported_items = payload.get("unsupported_claims")
    items: list[dict[str, Any]] = []
    for bucket, verdict in ((supported_items, "supported"), (unsupported_items, "uncertain")):
        if not isinstance(bucket, list):
            continue
        for item in bucket[:5]:
            if not isinstance(item, Mapping):
                continue
            claim = item.get("claim") or item.get("text")
            if not isinstance(claim, str) or not claim.strip():
                continue
            items.append(
                {
                    "claim": claim.strip(),
                    "verdict": item.get("verdict") or verdict,
                    "confidence": item.get("confidence"),
                    "section": item.get("section"),
                }
            )

    supported = int(counts.get("supported") or 0)
    unsupported = int(counts.get("unsupported") or counts.get("contradicted") or 0)
    uncertain = int(counts.get("uncertain") or 0)
    supported_ratio = counts.get("supported_ratio")
    return {
        "status": "checked",
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "uncertain_claims": uncertain,
        "supported_ratio": supported_ratio if isinstance(supported_ratio, (int, float)) else None,
        "items": items,
    }


def summarize_verification_claim_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    supported = 0
    unsupported = 0
    uncertain = 0
    items: list[dict[str, Any]] = []
    for row in rows:
        verdict = str(row.get("verdict") or "uncertain").lower()
        if verdict == "supported":
            supported += 1
        elif verdict == "contradicted":
            unsupported += 1
        else:
            uncertain += 1
        claim = row.get("claim")
        if isinstance(claim, str) and claim.strip() and len(items) < 5:
            items.append(
                {
                    "claim": claim.strip(),
                    "verdict": verdict,
                    "confidence": row.get("confidence"),
                    "section": row.get("stage"),
                }
            )
    total = supported + unsupported + uncertain
    return {
        "status": "checked" if total else "not_checked",
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "uncertain_claims": uncertain,
        "supported_ratio": round(supported / total, 3) if total else None,
        "items": items,
    }


def build_context_card(
    *,
    stage: str,
    state_json: Mapping[str, Any] | None,
    state_meta: Mapping[str, Any] | None = None,
    missing_paths: list[str] | None = None,
    verification_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    stage_key = _normalize_stage(stage)
    state = dict(state_json or {})
    meta = dict(state_meta or {})
    answer_meta = get_answer_meta_map(meta)
    roots = _stage_roots(stage_key)

    card = {
        "stage": stage_key,
        "generated_at": _now_iso(),
        "user_confirmed_inputs": [],
        "founder_assumptions": [],
        "ai_inferences": [],
        "unknowns": [],
        "evidence_gaps": [],
        "verification_summary": dict(verification_summary or summarize_verification_payload(None)),
    }

    for path, value in _iter_state_values(state):
        if roots and _path_stage(path, stage_key) != stage_key:
            continue
        entry_meta = _meta_for_path(answer_meta, path)
        entry = _diagnosis_entry(path, value, entry_meta)
        resolution_status = str(entry["resolution_status"]).lower()
        claim_type = str(entry["claim_type"]).lower()
        evidence_level = str(entry["evidence_level"]).upper()
        source = str(entry["source"]).lower()

        if resolution_status in UNKNOWN_STATUSES:
            card["unknowns"].append(entry)
        elif source in {"ai", "system"}:
            card["ai_inferences"].append(entry)
        elif claim_type == "fact":
            card["user_confirmed_inputs"].append(entry)
        else:
            card["founder_assumptions"].append(entry)

        if evidence_level in LOW_EVIDENCE_LEVELS and resolution_status != "not_applicable":
            card["evidence_gaps"].append(
                {
                    "path": path,
                    "label": _format_label(path),
                    "reason": "Needs stronger evidence before this should drive a high-confidence score.",
                    "evidence_level": evidence_level,
                }
            )

    pending_confirm = meta.get("pending_confirm")
    if isinstance(pending_confirm, Mapping):
        for path, raw_value in _iter_pending_values(pending_confirm):
            if not path or (roots and _path_stage(path, stage_key) != stage_key):
                continue
            value, pending_meta = _pending_value_and_meta(raw_value)
            if not _is_non_empty(value):
                continue
            entry = _diagnosis_entry(
                path,
                value,
                pending_meta,
                pending=True,
            )
            card["ai_inferences"].append(entry)
            card["evidence_gaps"].append(
                {
                    "path": path,
                    "label": _format_label(path),
                    "reason": "Pending suggestion must be accepted or rejected before scoring relies on it.",
                    "evidence_level": "E0",
                }
            )

    for path in list(missing_paths or []):
        if not isinstance(path, str) or not path.strip():
            continue
        if roots and _path_stage(path, stage_key) != stage_key:
            continue
        card["unknowns"].append(
            {
                "path": path,
                "label": _format_label(path),
                "value": "Unknown",
                "resolution_status": "unknown",
                "claim_type": "hypothesis",
                "evidence_level": "E0",
                "source": "system",
                "note": "Required input is still missing.",
                "pending": False,
            }
        )
        card["evidence_gaps"].append(
            {
                "path": path,
                "label": _format_label(path),
                "reason": "Required input is missing.",
                "evidence_level": "E0",
            }
        )

    for key in (
        "user_confirmed_inputs",
        "founder_assumptions",
        "ai_inferences",
        "unknowns",
        "evidence_gaps",
    ):
        card[key] = card[key][:12]

    return card


def build_validation_plan(
    *,
    stage: str,
    context_card: Mapping[str, Any] | None,
    key_risks: list[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    stage_key = _normalize_stage(stage)
    card = context_card if isinstance(context_card, Mapping) else {}
    unknowns = card.get("unknowns") if isinstance(card.get("unknowns"), list) else []
    gaps = card.get("evidence_gaps") if isinstance(card.get("evidence_gaps"), list) else []
    risks = key_risks if isinstance(key_risks, list) else []
    items: list[dict[str, Any]] = []

    stage_defaults = {
        "problem": (
            "Interview 5 P0 users about the #1 problem.",
            "P0 user segment",
            "At least 3 users describe the same painful scenario without prompting.",
            "Problem evidence gap",
        ),
        "market": (
            "Run a willingness-to-pay test with the target buyer.",
            "Initial buyer segment",
            "At least 2 buyers agree to a price range or next sales step.",
            "Viability evidence gap",
        ),
        "tech": (
            "Build a narrow technical spike for the riskiest integration or workflow.",
            "MVP technical path",
            "Spike proves the core path works with realistic data and constraints.",
            "Feasibility evidence gap",
        ),
        "report": (
            "Run the highest-priority validation experiment before expanding scope.",
            "Highest-risk assumption",
            "Evidence changes a go/hold/stop decision within two weeks.",
            "Overall confidence gap",
        ),
    }

    for entry in unknowns[:2]:
        if not isinstance(entry, Mapping):
            continue
        label = entry.get("label") or entry.get("path") or "Unknown"
        items.append(
            {
                "action": f"Resolve the unknown: {label}.",
                "target": label,
                "success_signal": "A specific answer is captured and confirmed by the user.",
                "linked_risk": "Unknown input",
                "priority": "high",
            }
        )

    for entry in gaps[:2]:
        if not isinstance(entry, Mapping):
            continue
        label = entry.get("label") or entry.get("path") or "Evidence gap"
        items.append(
            {
                "action": f"Collect stronger evidence for {label}.",
                "target": label,
                "success_signal": "Evidence level improves from E0/E1 to a concrete user, market, or technical signal.",
                "linked_risk": entry.get("reason") or "Evidence gap",
                "priority": "medium",
            }
        )

    for risk in risks[:2]:
        if not isinstance(risk, Mapping):
            continue
        risk_label = risk.get("risk") or risk.get("label")
        mitigation = risk.get("mitigation_suggestion") or risk.get("mitigationSuggestion")
        if not isinstance(risk_label, str) or not risk_label.strip():
            continue
        items.append(
            {
                "action": mitigation if isinstance(mitigation, str) and mitigation.strip() else f"Design a validation test for {risk_label}.",
                "target": risk.get("category") or "Risk register",
                "success_signal": "The risk can be downgraded or a pivot decision is made.",
                "linked_risk": risk_label.strip(),
                "priority": "high" if str(risk.get("severity")).lower() == "high" else "medium",
            }
        )

    default_action, default_target, default_signal, default_risk = stage_defaults.get(
        stage_key, stage_defaults["report"]
    )
    while len(items) < 3:
        items.append(
            {
                "action": default_action,
                "target": default_target,
                "success_signal": default_signal,
                "linked_risk": default_risk,
                "priority": "medium" if items else "high",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("action") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 5:
            break
    return deduped


def build_report_diagnosis(
    *,
    assessments: list[Mapping[str, Any]],
    dvf_confidence: Mapping[str, Any] | None,
    key_risks: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    context_cards: dict[str, Any] = {}
    stage_validation_plans: dict[str, Any] = {}
    for assessment in assessments:
        stage = assessment.get("stage")
        if not isinstance(stage, str) or not stage.strip():
            continue
        stage_key = stage.strip().lower()
        card = assessment.get("context_card")
        if isinstance(card, Mapping) and card:
            context_cards[stage_key] = dict(card)
        plan = assessment.get("validation_plan")
        if isinstance(plan, list) and plan:
            stage_validation_plans[stage_key] = plan

    return {
        "generated_at": _now_iso(),
        "context_cards": context_cards,
        "dvf_confidence": dict(dvf_confidence or {}),
        "risk_register": list(key_risks or []),
        "stage_validation_plans": stage_validation_plans,
    }


def merge_validation_plans(
    *plans: Iterable[Mapping[str, Any]] | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for plan in plans:
        if not plan:
            continue
        for item in plan:
            if not isinstance(item, Mapping):
                continue
            action = item.get("action")
            if not isinstance(action, str) or not action.strip():
                continue
            key = action.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
            if len(merged) >= limit:
                return merged
    return merged
