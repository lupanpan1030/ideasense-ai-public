from typing import Any

from app.services.answer_meta import get_answer_meta_map, set_answer_meta_entry
from app.services.context_paths import get_context_path_value, set_context_path_value


IDEA_RAW_PATH = "problem_user.idea.raw"

UNKNOWN_LIKE_VALUES = {
    "unknown",
    "unsure",
    "not sure",
    "i'm not sure",
    "i am not sure",
    "dont know",
    "don't know",
    "undecided",
    "n/a",
    "na",
    "none",
    "no idea",
    "未知",
    "不确定",
    "不知道",
    "未决定",
    "无",
}


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


def _is_unknown_like_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = " ".join(value.strip().lower().split())
    return cleaned in UNKNOWN_LIKE_VALUES


def _first_context_text(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned and not _is_unknown_like_text(cleaned):
            return cleaned
        return None
    if isinstance(value, list):
        for item in value:
            candidate = _first_context_text(item)
            if candidate:
                return candidate
        return None
    if isinstance(value, dict):
        for key in ("snapshot", "one_line", "raw", "value", "text", "summary"):
            candidate = _first_context_text(value.get(key))
            if candidate:
                return candidate
        for item in value.values():
            candidate = _first_context_text(item)
            if candidate:
                return candidate
    return None


def _derive_idea_raw_from_problem_context(state_json: dict[str, Any]) -> str | None:
    candidates = [
        get_context_path_value(state_json, ["problem_user", "idea", "snapshot"]),
        get_context_path_value(state_json, ["problem", "one_line"]),
        get_context_path_value(state_json, ["problem", "main_problems"]),
    ]
    for value in candidates:
        candidate = _first_context_text(value)
        if candidate:
            return candidate
    return None


def backfill_problem_idea_raw(
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    *,
    source: str = "user",
) -> bool:
    if not isinstance(state_json, dict) or not isinstance(state_meta, dict):
        return False

    current = get_context_path_value(state_json, IDEA_RAW_PATH)
    current_is_concrete = _is_non_empty(current) and not _is_unknown_like_text(current)
    answer_meta = get_answer_meta_map(state_meta)
    meta_entry = answer_meta.get(IDEA_RAW_PATH)
    meta_status = (
        meta_entry.get("resolution_status") if isinstance(meta_entry, dict) else None
    )
    meta_is_unknown = meta_status in {"unknown", "undecided"}

    if current_is_concrete:
        if meta_is_unknown:
            set_answer_meta_entry(
                state_meta,
                IDEA_RAW_PATH,
                resolution_status="answered",
                claim_type="hypothesis",
                evidence_level="E1",
                source=source,
                note="Marked answered because the field now contains a concrete user-provided value.",
            )
            return True
        return False

    if not (_is_unknown_like_text(current) or meta_is_unknown):
        return False

    candidate = _derive_idea_raw_from_problem_context(state_json)
    if not candidate:
        return False

    set_context_path_value(state_json, IDEA_RAW_PATH, candidate)
    set_answer_meta_entry(
        state_meta,
        IDEA_RAW_PATH,
        resolution_status="answered",
        claim_type="hypothesis",
        evidence_level="E1",
        source=source,
        note="Backfilled from later problem-stage context after the initial idea answer was unknown.",
    )
    return True
