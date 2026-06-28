from datetime import datetime, timezone
from typing import Any

VALID_RESOLUTION_STATUSES = {
    "answered",
    "partial",
    "unknown",
    "undecided",
    "not_applicable",
    "suggested",
}
VALID_CLAIM_TYPES = {"fact", "hypothesis", "estimate"}
VALID_EVIDENCE_LEVELS = {"E0", "E1", "E2", "E3", "E4"}
VALID_SOURCES = {"user", "ai", "mixed", "system"}

DEFAULT_RESOLUTION_STATUS = "answered"
DEFAULT_CLAIM_TYPE = "hypothesis"
DEFAULT_EVIDENCE_LEVEL = "E1"
DEFAULT_SOURCE = "user"

ANSWER_VALUE_KEYS = ("value", "suggested_value", "suggested", "current_value")
ANSWER_META_KEYS = (
    "resolution_status",
    "claim_type",
    "evidence_level",
    "source",
    "note",
)

UNKNOWN_TEXT_VALUES = {
    "?",
    "dont know",
    "don't know",
    "i dont know",
    "i don't know",
    "not known",
    "not sure",
    "unknown",
    "unsure",
}
UNDECIDED_TEXT_VALUES = {
    "not decided",
    "not decided yet",
    "tbd",
    "to be decided",
    "undecided",
}
NOT_APPLICABLE_TEXT_VALUES = {
    "n/a",
    "na",
    "no current solution",
    "no current solutions",
    "none",
    "none yet",
    "not applicable",
}

SKIP_ANSWER_ACTIONS = {
    "skip_soft",
    "unknown",
    "undecided",
    "not_applicable",
}


def _normalize_path(path: str | None) -> str | None:
    if not isinstance(path, str):
        return None
    cleaned = path.strip()
    return cleaned if cleaned else None


def _normalize_choice(
    value: str | None,
    allowed: set[str],
    *,
    default: str,
    upper: bool = False,
) -> str:
    if not isinstance(value, str):
        return default
    cleaned = value.strip()
    if upper:
        cleaned = cleaned.upper()
    else:
        cleaned = cleaned.lower()
    return cleaned if cleaned in allowed else default


def _normalize_note(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _clean_answer_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _value_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_clean_answer_text(value)]
    if isinstance(value, list):
        return [_clean_answer_text(item) for item in value if isinstance(item, str)]
    return []


def _infer_resolution_from_value(value: Any) -> str | None:
    if isinstance(value, list) and not value:
        return "not_applicable"
    texts = [text for text in _value_texts(value) if text]
    if not texts:
        return None
    if all(
        text in NOT_APPLICABLE_TEXT_VALUES or text.startswith("none ")
        for text in texts
    ):
        return "not_applicable"
    if all(
        text in UNDECIDED_TEXT_VALUES or text.startswith("undecided")
        for text in texts
    ):
        return "undecided"
    if all(
        text in UNKNOWN_TEXT_VALUES
        or text.startswith("unknown")
        or text.endswith(" unknown")
        for text in texts
    ):
        return "unknown"
    return None


def extract_answer_value_and_meta(
    value: Any,
    *,
    default_source: str = DEFAULT_SOURCE,
) -> tuple[Any, dict[str, Any]]:
    """Return a context value and normalized answer metadata for production writes."""
    raw_payload = value if isinstance(value, dict) else {}
    resolved_value = value
    if isinstance(value, dict):
        for key in ANSWER_VALUE_KEYS:
            if key in value:
                resolved_value = value.get(key)
                break

    source = _normalize_choice(
        raw_payload.get("source") if isinstance(raw_payload, dict) else None,
        VALID_SOURCES,
        default=_normalize_choice(default_source, VALID_SOURCES, default=DEFAULT_SOURCE),
    )
    meta: dict[str, Any] = {
        "resolution_status": DEFAULT_RESOLUTION_STATUS,
        "claim_type": DEFAULT_CLAIM_TYPE,
        "evidence_level": DEFAULT_EVIDENCE_LEVEL,
        "source": source,
    }

    inferred_resolution = _infer_resolution_from_value(resolved_value)
    if inferred_resolution is not None:
        meta["resolution_status"] = inferred_resolution
        meta["evidence_level"] = "E0"
        meta["note"] = build_skip_answer_meta_note(inferred_resolution)
    elif source in {"ai", "system"}:
        meta["evidence_level"] = "E0"

    if isinstance(raw_payload, dict):
        if raw_payload.get("resolution_status") is not None:
            meta["resolution_status"] = raw_payload.get("resolution_status")
        if raw_payload.get("claim_type") is not None:
            meta["claim_type"] = raw_payload.get("claim_type")
        if raw_payload.get("evidence_level") is not None:
            meta["evidence_level"] = raw_payload.get("evidence_level")
        if raw_payload.get("source") is not None:
            meta["source"] = raw_payload.get("source")
        if raw_payload.get("note") is not None:
            meta["note"] = raw_payload.get("note")

    return resolved_value, normalize_answer_meta({"_": meta})["_"]


def _normalize_updated_at(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return datetime.now(timezone.utc).isoformat()


def normalize_answer_meta(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for raw_path, raw_entry in value.items():
        path = _normalize_path(raw_path)
        if path is None or not isinstance(raw_entry, dict):
            continue
        entry = {
            "resolution_status": _normalize_choice(
                raw_entry.get("resolution_status"),
                VALID_RESOLUTION_STATUSES,
                default=DEFAULT_RESOLUTION_STATUS,
            ),
            "claim_type": _normalize_choice(
                raw_entry.get("claim_type"),
                VALID_CLAIM_TYPES,
                default=DEFAULT_CLAIM_TYPE,
            ),
            "evidence_level": _normalize_choice(
                raw_entry.get("evidence_level"),
                VALID_EVIDENCE_LEVELS,
                default=DEFAULT_EVIDENCE_LEVEL,
                upper=True,
            ),
            "source": _normalize_choice(
                raw_entry.get("source"),
                VALID_SOURCES,
                default=DEFAULT_SOURCE,
            ),
            "updated_at": _normalize_updated_at(raw_entry.get("updated_at")),
        }
        note = _normalize_note(raw_entry.get("note"))
        if note is not None:
            entry["note"] = note
        normalized[path] = entry
    return normalized


def normalize_answer_action(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    if cleaned in {
        "skip",
        "skip_soft",
        "skip-soft",
        "skip_later",
        "skip-later",
    }:
        return "skip_soft"
    if cleaned in {
        "cant_answer",
        "cannot_answer",
        "unknown",
        "dont_know",
        "don't_know",
    }:
        return "unknown"
    if cleaned in {
        "undecided",
        "not_decided",
        "not-decided",
        "not_sure_yet",
        "not-sure-yet",
        "need_to_decide",
        "need-to-decide",
    }:
        return "undecided"
    if cleaned in {
        "not_applicable",
        "not-applicable",
        "n/a",
        "na",
        "not_relevant",
        "not-relevant",
    }:
        return "not_applicable"
    if cleaned in {"ai_draft", "ai-draft", "ai_assist", "ai-assist", "assist"}:
        return "ai_draft"
    return None


def is_skip_answer_action(answer_action: str | None) -> bool:
    return answer_action in SKIP_ANSWER_ACTIONS


def resolve_skip_resolution_status(
    answer_action: str | None,
    skip_reason: str | None = None,
) -> str:
    if answer_action in {"unknown", "undecided", "not_applicable"}:
        return answer_action
    if isinstance(skip_reason, str):
        cleaned = skip_reason.strip().lower()
        if cleaned in {
            "undecided",
            "not_decided",
            "not-decided",
            "not_sure_yet",
            "not-sure-yet",
            "need_to_decide",
            "need-to-decide",
        }:
            return "undecided"
        if cleaned in {
            "not_applicable",
            "not-applicable",
            "n/a",
            "na",
            "not_relevant",
            "not-relevant",
        }:
            return "not_applicable"
    return "unknown"


def build_skip_answer_meta_note(
    resolution_status: str,
    skip_reason: str | None = None,
) -> str:
    labels = {
        "unknown": "unknown",
        "undecided": "undecided",
        "not_applicable": "not applicable",
    }
    label = labels.get(resolution_status, "unknown")
    if not isinstance(skip_reason, str):
        return f"User marked this answer as {label}."
    cleaned = skip_reason.strip()
    if not cleaned:
        return f"User marked this answer as {label}."
    generic_reasons = {
        "cant_answer",
        "cannot_answer",
        "unknown",
        "undecided",
        "not_applicable",
        "not-applicable",
        "n/a",
        "na",
    }
    if cleaned.lower() in generic_reasons:
        return f"User marked this answer as {label}."
    return f"User marked this answer as {label}: {cleaned}."


def get_answer_meta_map(state_meta: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(state_meta, dict):
        return {}
    return normalize_answer_meta(state_meta.get("answer_meta"))


def set_answer_meta_entry(
    state_meta: dict[str, Any],
    path: str,
    *,
    resolution_status: str = DEFAULT_RESOLUTION_STATUS,
    claim_type: str = DEFAULT_CLAIM_TYPE,
    evidence_level: str = DEFAULT_EVIDENCE_LEVEL,
    source: str = DEFAULT_SOURCE,
    note: str | None = None,
    updated_at: datetime | str | None = None,
) -> None:
    cleaned_path = _normalize_path(path)
    if cleaned_path is None:
        return

    answer_meta = get_answer_meta_map(state_meta)
    entry = {
        "resolution_status": _normalize_choice(
            resolution_status,
            VALID_RESOLUTION_STATUSES,
            default=DEFAULT_RESOLUTION_STATUS,
        ),
        "claim_type": _normalize_choice(
            claim_type,
            VALID_CLAIM_TYPES,
            default=DEFAULT_CLAIM_TYPE,
        ),
        "evidence_level": _normalize_choice(
            evidence_level,
            VALID_EVIDENCE_LEVELS,
            default=DEFAULT_EVIDENCE_LEVEL,
            upper=True,
        ),
        "source": _normalize_choice(
            source,
            VALID_SOURCES,
            default=DEFAULT_SOURCE,
        ),
        "updated_at": _normalize_updated_at(updated_at),
    }
    normalized_note = _normalize_note(note)
    if normalized_note is not None:
        entry["note"] = normalized_note
    answer_meta[cleaned_path] = entry
    state_meta["answer_meta"] = answer_meta


def remove_answer_meta_entry(state_meta: dict[str, Any], path: str) -> None:
    cleaned_path = _normalize_path(path)
    if cleaned_path is None:
        return
    answer_meta = get_answer_meta_map(state_meta)
    if cleaned_path not in answer_meta:
        return
    answer_meta.pop(cleaned_path, None)
    if answer_meta:
        state_meta["answer_meta"] = answer_meta
    else:
        state_meta.pop("answer_meta", None)
