from __future__ import annotations

from typing import Any

from app.services.chat_market_type_normalization import (
    MARKET_TYPE_ENUM_PATHS,
    canonicalize_extracted_value,
    canonicalize_market_type_fields,
    infer_market_type_enum_from_state,
)
from app.services.extraction_transforms import (
    get_nested_state_value as _get_nested_state_value,
    is_non_empty as _is_non_empty,
    split_state_path as _split_state_path,
)


__all__ = [
    "MARKET_TYPE_ENUM_PATHS",
    "adjust_answer_extraction_market_missing_paths",
    "canonicalize_extracted_value",
    "canonicalize_market_type_fields",
    "infer_market_type_enum_from_state",
]


PATH_EQUIVALENTS = {
    "market_strategy.unit_economics.expected_payback_period_normalized": [
        "market_strategy.unit_economics.expected_payback_period_raw",
    ],
    "market_strategy.business_model.initial_price_point_normalized": [
        "market_strategy.business_model.initial_price_point_raw",
    ],
}


def _path_has_value(state_json: Any, path: str) -> bool:
    if not isinstance(state_json, dict):
        return False
    value = _get_nested_state_value(state_json, _split_state_path(path))
    return _is_non_empty(value)


def _filter_missing_paths_by_state(
    state_json: Any,
    missing_paths: list[str],
) -> list[str]:
    if not missing_paths or not isinstance(state_json, dict):
        return missing_paths
    filtered: list[str] = []
    for path in missing_paths:
        if _path_has_value(state_json, path):
            continue
        equivalents = PATH_EQUIVALENTS.get(path, [])
        if equivalents and any(
            _path_has_value(state_json, item) for item in equivalents
        ):
            continue
        filtered.append(path)
    return filtered


def _normalize_market_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        parts = [_normalize_market_text(item) for item in value]
        return " ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts = [_normalize_market_text(item) for item in value.values()]
        return " ".join(parts)
    return ""


def _infer_market_type(state_json: Any) -> str | None:
    if not isinstance(state_json, dict):
        return None
    inferred_enum = infer_market_type_enum_from_state(state_json)
    if inferred_enum:
        return inferred_enum.strip().lower()
    candidates = [
        _normalize_market_text(
            _get_nested_state_value(state_json, ["target_user", "market_type_inferred"])
        ),
        _normalize_market_text(
            _get_nested_state_value(
                state_json, ["market_strategy", "meta", "market_type_override"]
            )
        ),
        _normalize_market_text(
            _get_nested_state_value(
                state_json, ["market_strategy", "business_model", "payer_role"]
            )
        ),
        _normalize_market_text(
            _get_nested_state_value(
                state_json, ["market_strategy", "business_model", "end_user_role"]
            )
        ),
    ]
    combined = " ".join([value for value in candidates if value])
    if not combined:
        return None
    has_b2b = (
        "b2b" in combined
        or "enterprise" in combined
        or "company" in combined
        or "team" in combined
    )
    has_b2c = (
        "b2c" in combined
        or "consumer" in combined
        or "individual" in combined
        or "founder" in combined
        or "indie" in combined
        or "prosumer" in combined
    )
    if "hybrid" in combined or (has_b2b and has_b2c):
        return "hybrid"
    if has_b2b:
        return "b2b"
    if has_b2c:
        return "b2c"
    return None


def adjust_answer_extraction_market_missing_paths(
    state_json: Any,
    missing_paths: list[str],
    resolved_paths: list[str] | None = None,
) -> list[str]:
    if not missing_paths or not isinstance(state_json, dict):
        return missing_paths
    expected_sales_path = "market_strategy.go_to_market.expected_sales_cycle_length"
    retention_path = "market_strategy.go_to_market.retention_loop"
    if expected_sales_path not in missing_paths and retention_path not in missing_paths:
        return missing_paths

    resolved = set(resolved_paths or [])
    has_retention = (
        _is_non_empty(
            _get_nested_state_value(
                state_json, ["market_strategy", "go_to_market", "retention_loop"]
            )
        )
        or retention_path in resolved
    )
    has_sales_cycle = (
        _is_non_empty(
            _get_nested_state_value(
                state_json,
                ["market_strategy", "go_to_market", "expected_sales_cycle_length"],
            )
        )
        or expected_sales_path in resolved
    )

    adjusted = list(missing_paths)
    if has_retention and expected_sales_path in adjusted:
        adjusted.remove(expected_sales_path)
    if has_sales_cycle and retention_path in adjusted:
        adjusted.remove(retention_path)

    if expected_sales_path in adjusted and retention_path in adjusted:
        market_type = _infer_market_type(state_json)
        if market_type == "b2c" and expected_sales_path in adjusted:
            adjusted.remove(expected_sales_path)
        elif market_type == "b2b" and retention_path in adjusted:
            adjusted.remove(retention_path)

    return adjusted
