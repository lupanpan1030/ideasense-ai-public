from __future__ import annotations

from typing import Any

from app.services.context_paths import set_context_path_value as _set_path
from app.services.extraction_transforms import (
    get_nested_state_value as _get_nested_state_value,
    is_non_empty as _is_non_empty,
)

MARKET_TYPE_ENUM_PATHS = {
    "target_user.market_type_inferred",
    "market_strategy.meta.market_type_override",
}


def canonicalize_market_type_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        return value
    normalized = cleaned.lower()
    if normalized in {
        "unknown",
        "unsure",
        "not sure",
        "undecided",
        "n/a",
        "na",
    }:
        return "Unknown"

    has_b2b = any(
        token in normalized
        for token in (
            "b2b",
            "business",
            "businesses",
            "company",
            "companies",
            "enterprise",
            "team",
            "teams",
            "saas",
            "smb",
            "organization",
            "organizations",
        )
    )
    has_b2c = any(
        token in normalized
        for token in (
            "b2c",
            "consumer",
            "consumers",
            "individual",
            "individuals",
            "student",
            "students",
            "prosumer",
        )
    )
    if "hybrid" in normalized or "b2b2c" in normalized or (has_b2b and has_b2c):
        return "Hybrid"
    if has_b2b:
        return "B2B"
    if has_b2c:
        return "B2C"
    return "Unknown"


def canonicalize_extracted_value(path: str, value: Any) -> Any:
    if path in MARKET_TYPE_ENUM_PATHS:
        return canonicalize_market_type_value(value)
    return value


def collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(collect_strings(item))
        return items
    if isinstance(value, dict):
        items = []
        for item in value.values():
            items.extend(collect_strings(item))
        return items
    return []


def infer_market_type_enum_from_state(state_json: Any) -> str | None:
    if not isinstance(state_json, dict):
        return None
    candidates = [
        _get_nested_state_value(state_json, ["target_user", "market_type_inferred"]),
        _get_nested_state_value(
            state_json,
            ["market_strategy", "meta", "market_type_override"],
        ),
        _get_nested_state_value(state_json, ["target_user", "core"]),
        _get_nested_state_value(state_json, ["target_user", "segments"]),
        _get_nested_state_value(state_json, ["target_user", "priority_segment"]),
        _get_nested_state_value(state_json, ["target_user", "decision_vs_end_user"]),
        _get_nested_state_value(
            state_json,
            ["market_strategy", "business_model", "payer_role"],
        ),
        _get_nested_state_value(
            state_json,
            ["market_strategy", "business_model", "end_user_role"],
        ),
    ]
    combined = " ".join(
        item for value in candidates for item in collect_strings(value) if item
    )
    if not combined:
        return None
    canonical = canonicalize_market_type_value(combined)
    if canonical in {"B2B", "B2C", "Hybrid"}:
        return canonical
    return None


def canonicalize_market_type_fields(state_json: dict[str, Any]) -> bool:
    changed = False
    for path in MARKET_TYPE_ENUM_PATHS:
        current = _get_nested_state_value(state_json, path.split("."))
        canonical = canonicalize_market_type_value(current)
        if canonical != current:
            _set_path(state_json, path, canonical)
            changed = True
    current_target_market = _get_nested_state_value(
        state_json,
        ["target_user", "market_type_inferred"],
    )
    if not _is_non_empty(current_target_market):
        inferred = infer_market_type_enum_from_state(state_json)
        if inferred:
            _set_path(state_json, "target_user.market_type_inferred", inferred)
            changed = True
    return changed
