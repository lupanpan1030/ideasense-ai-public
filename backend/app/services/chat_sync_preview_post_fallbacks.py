from __future__ import annotations

import re
from typing import Any

from app.services.answer_meta import set_answer_meta_entry
from app.services.context_paths import (
    set_context_path_value as _set_path,
)
from app.services.extraction_transforms import (
    get_nested_state_value as _get_nested_state_value,
    is_non_empty as _is_non_empty,
)

PreviewExtractionUpdate = tuple[str, str, Any]

FREQUENCY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:multiple|several|a few|two|three|\d+(?:-\d+)?)\s+times?\s+per\s+day\b",
            re.IGNORECASE,
        ),
        "multiple times per day",
    ),
    (
        re.compile(r"\b(?:daily|every\s+day|once\s+per\s+day)\b", re.IGNORECASE),
        "daily",
    ),
    (
        re.compile(
            r"\b(?:weekly|every\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|\d+(?:-\d+)?\s+times?\s+per\s+week|per\s+week)\b",
            re.IGNORECASE,
        ),
        "weekly",
    ),
    (
        re.compile(
            r"\b(?:monthly|every\s+month|per\s+month|planning\s+cycle)\b",
            re.IGNORECASE,
        ),
        "monthly",
    ),
    (
        re.compile(r"\b(?:quarterly|every\s+quarter|per\s+quarter)\b", re.IGNORECASE),
        "quarterly",
    ),
)


def infer_problem_frequency_from_answer(answer: str) -> str | None:
    cleaned = answer.strip()
    if not cleaned:
        return None
    matches: list[str] = []
    for pattern, label in FREQUENCY_PATTERNS:
        if pattern.search(cleaned):
            matches.append(label)
    if not matches:
        return None
    ordered = list(dict.fromkeys(matches))
    return ", with ".join(ordered) if len(ordered) > 1 else ordered[0]


def _source(ai_assisted: bool) -> str:
    return "ai" if ai_assisted else "user"


def apply_mvp_boundary_preview_fallbacks(
    fallback_values: dict[str, Any],
    *,
    resolved_paths: list[str],
    extraction_updates: list[PreviewExtractionUpdate],
    next_state_json: dict[str, Any],
    next_state_meta: dict[str, Any],
    ai_assisted: bool,
) -> None:
    existing_update_paths = {
        path for target, path, _value in extraction_updates if target == "state"
    }
    for path, value in fallback_values.items():
        if not _is_non_empty(value):
            continue
        if path not in resolved_paths:
            resolved_paths.append(path)
        if path not in existing_update_paths:
            extraction_updates.append(("state", path, value))
            existing_update_paths.add(path)
        _set_path(next_state_json, path, value)
        set_answer_meta_entry(
            next_state_meta,
            path,
            resolution_status="answered",
            claim_type="hypothesis",
            evidence_level="E1",
            source=_source(ai_assisted),
        )


def apply_problem_frequency_preview_fallback(
    answer: str,
    *,
    resolved_paths: list[str],
    extraction_updates: list[PreviewExtractionUpdate],
    next_state_json: dict[str, Any],
    next_state_meta: dict[str, Any],
    ai_assisted: bool,
) -> None:
    existing_frequency = _get_nested_state_value(
        next_state_json,
        ["problem", "frequency"],
    )
    if _is_non_empty(existing_frequency):
        return
    inferred_frequency = infer_problem_frequency_from_answer(answer)
    if not inferred_frequency:
        return

    frequency_path = "problem.frequency"
    resolved_paths.append(frequency_path)
    extraction_updates.append(("state", frequency_path, inferred_frequency))
    _set_path(next_state_json, frequency_path, inferred_frequency)
    set_answer_meta_entry(
        next_state_meta,
        frequency_path,
        resolution_status="answered",
        claim_type="hypothesis",
        evidence_level="E1",
        source=_source(ai_assisted),
    )
