from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from app.services.answer_meta import extract_answer_value_and_meta
from app.services.context_paths import infer_context_path_stage


NONE_PATTERNS = [
    re.compile(r"\bnone\b", re.IGNORECASE),
    re.compile(r"\bno (?:data|evidence|metrics|numbers?)\b", re.IGNORECASE),
    re.compile(r"\bnot yet\b", re.IGNORECASE),
    re.compile("暂无"),
    re.compile("没有"),
    re.compile("无数据"),
]


def normalize_extraction_key(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("[]", "")
    cleaned = cleaned.replace("/", ".")
    cleaned = re.sub(r"[^\w.]+", "_", cleaned)
    cleaned = re.sub(r"\.+", ".", cleaned)
    cleaned = cleaned.strip("._")
    return cleaned


def flatten_extraction_payload(
    payload: dict[str, Any],
    prefix: str = "",
) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        next_prefix = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened[next_prefix] = value
            flattened.update(flatten_extraction_payload(value, next_prefix))
        else:
            flattened[next_prefix] = value
    return flattened


def build_schema_key_map(schema_paths: list[str]) -> dict[str, str]:
    candidates: dict[str, list[str]] = {}
    for path in schema_paths:
        normalized = normalize_extraction_key(path)
        if not normalized:
            continue
        segments = normalized.split(".")
        for index in range(len(segments)):
            suffix = ".".join(segments[index:])
            if not suffix:
                continue
            candidates.setdefault(suffix, []).append(path)
    return {key: paths[0] for key, paths in candidates.items() if len(paths) == 1}


def is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(is_non_empty(item) for item in value)
    if isinstance(value, dict):
        return any(is_non_empty(item) for item in value.values())
    return True


def has_explicit_none(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    return any(pattern.search(cleaned) for pattern in NONE_PATTERNS)


def get_nested_state_value(state_json: Any, path: list[str]) -> Any:
    cursor = state_json
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def split_state_path(path: str) -> list[str]:
    parts: list[str] = []
    for raw_part in path.split("."):
        cleaned = raw_part[:-2] if raw_part.endswith("[]") else raw_part
        if cleaned:
            parts.append(cleaned)
    return parts


def extract_value_meta(
    value: Any,
    *,
    default_source: str = "user",
) -> tuple[Any, dict[str, Any]]:
    return extract_answer_value_and_meta(value, default_source=default_source)


def canonicalize_extraction_update_value(
    path: str,
    value: Any,
    *,
    canonicalize_value: Callable[[str, Any], Any] | None = None,
) -> Any:
    actual_value, _meta = extract_value_meta(value)
    canonical = (
        canonicalize_value(path, actual_value)
        if canonicalize_value is not None
        else actual_value
    )
    if isinstance(value, dict):
        explicit_meta = {
            key: value.get(key)
            for key in (
                "resolution_status",
                "claim_type",
                "evidence_level",
                "source",
                "note",
            )
            if value.get(key) is not None
        }
        if explicit_meta:
            return {"value": canonical, **explicit_meta}
    return canonical


def build_extraction_targets(
    remapped: dict[str, Any],
    current_stage: str,
    *,
    canonicalize_value: Callable[[str, Any], Any] | None = None,
) -> tuple[list[str], list[tuple[str, str, Any]]]:
    resolved_paths: list[str] = []
    updates: list[tuple[str, str, Any]] = []
    for path, value in remapped.items():
        value = canonicalize_extraction_update_value(
            path,
            value,
            canonicalize_value=canonicalize_value,
        )
        if not is_non_empty(value):
            continue
        resolved_paths.append(path)
        path_stage = infer_context_path_stage(path, current_stage)
        if path_stage == current_stage:
            updates.append(("state", path, value))
        else:
            updates.append(("pending", path, value))
    return resolved_paths, updates


def remap_extracted(
    extracted: dict[str, Any],
    schema_paths: list[str],
    *,
    canonicalize_value: Callable[[str, Any], Any] | None = None,
) -> dict[str, Any]:
    flattened = flatten_extraction_payload(extracted)
    key_map = build_schema_key_map(schema_paths)
    remapped: dict[str, Any] = {}
    for raw_key, value in flattened.items():
        normalized_key = normalize_extraction_key(raw_key)
        if not normalized_key:
            continue
        schema_path = key_map.get(normalized_key)
        if not schema_path:
            continue
        if (
            schema_path.endswith("[]")
            and value is not None
            and not isinstance(value, list)
        ):
            value = [value]
        if canonicalize_value is not None:
            value = canonicalize_value(schema_path, value)
        remapped[schema_path] = value
    return remapped
