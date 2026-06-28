"""Canonical helpers for project context path mutation."""

from typing import Any


KNOWN_STAGE_PREFIXES = frozenset({"problem", "market", "tech", "report"})


def split_context_path(path: str) -> list[str]:
    if not isinstance(path, str):
        return []
    trimmed = path.strip()
    if not trimmed:
        return []
    parts = [part.strip() for part in trimmed.split(".") if part.strip()]
    return [part[:-2] if part.endswith("[]") else part for part in parts]


def get_context_path_value(data: Any, path: str | list[str]) -> Any:
    parts = split_context_path(path) if isinstance(path, str) else path
    cursor = data
    for key in parts:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def set_context_path_value(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = target
    for idx, raw_part in enumerate(parts):
        is_last = idx == len(parts) - 1
        is_list = raw_part.endswith("[]")
        key = raw_part[:-2] if is_list else raw_part
        if is_last:
            if is_list and value is not None and not isinstance(value, list):
                cursor[key] = [value]
            else:
                cursor[key] = value
            return
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]


def pop_context_path_value(target: dict[str, Any], path: str) -> Any | None:
    parts = split_context_path(path)
    if not parts:
        return None
    cursor: Any = target
    stack: list[tuple[dict[str, Any], str]] = []
    for key in parts[:-1]:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        stack.append((cursor, key))
        cursor = cursor[key]
    if not isinstance(cursor, dict) or parts[-1] not in cursor:
        return None
    value = cursor.pop(parts[-1], None)
    for parent, key in reversed(stack):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)
        else:
            break
    return value


def infer_context_path_stage(path: str, current_stage: str) -> str:
    prefix = path.split(".", maxsplit=1)[0]
    if prefix in KNOWN_STAGE_PREFIXES:
        return prefix
    return current_stage
