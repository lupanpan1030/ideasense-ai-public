"""Helpers for question-level verification priority."""

from __future__ import annotations

from typing import Any

from .constants import _VERIFICATION_PRIORITY_BY_QID

_PRIORITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def normalize_priority(value: str | None) -> str:
    if not value:
        return "none"
    normalized = str(value).strip().lower()
    return normalized if normalized in _PRIORITY_ORDER else "none"


def extract_verification_priority(question_detail: dict[str, Any] | None) -> str:
    if not isinstance(question_detail, dict):
        return "none"
    question_id = question_detail.get("question_id")
    prompt_meta = question_detail.get("prompt_meta")
    if not isinstance(prompt_meta, dict):
        if isinstance(question_id, str):
            return normalize_priority(_VERIFICATION_PRIORITY_BY_QID.get(question_id))
        return "none"
    verification_meta = prompt_meta.get("verification")
    if isinstance(verification_meta, dict):
        return normalize_priority(verification_meta.get("priority"))
    priority = normalize_priority(prompt_meta.get("verification_priority"))
    if priority != "none":
        return priority
    if isinstance(question_id, str):
        return normalize_priority(_VERIFICATION_PRIORITY_BY_QID.get(question_id))
    return "none"


def priority_at_least(value: str, threshold: str) -> bool:
    return _PRIORITY_ORDER.get(normalize_priority(value), 0) >= _PRIORITY_ORDER.get(
        normalize_priority(threshold), 0
    )
