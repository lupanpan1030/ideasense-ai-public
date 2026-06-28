from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.services.context_paths import (
    get_context_path_value,
    set_context_path_value,
)


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


def _normalize_stage_path_map(
    state_meta: dict[str, Any] | None,
    key: str,
) -> dict[str, list[str]]:
    if not isinstance(state_meta, dict):
        return {}
    raw = state_meta.get(key)
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for stage, paths in raw.items():
        if not isinstance(stage, str) or not isinstance(paths, list):
            continue
        stage_key = stage.strip().lower()
        if not stage_key:
            continue
        cleaned = [path for path in paths if isinstance(path, str) and path.strip()]
        if cleaned:
            normalized[stage_key] = cleaned
    return normalized


def normalize_ai_assisted_map(
    state_meta: dict[str, Any] | None,
) -> dict[str, list[str]]:
    return _normalize_stage_path_map(state_meta, "ai_assisted_paths")


def normalize_user_edited_map(
    state_meta: dict[str, Any] | None,
) -> dict[str, list[str]]:
    return _normalize_stage_path_map(state_meta, "user_edited_paths")


def resolve_ai_assisted_paths(
    state_meta: dict[str, Any] | None,
    stage: str,
) -> list[str]:
    return normalize_ai_assisted_map(state_meta).get(stage.strip().lower(), [])


async def resolve_stage_paths(
    session,
    bank_id: Any,
    stage: str,
    variant: str,
) -> list[str]:
    result = await session.execute(
        text(
            "SELECT COALESCE(array_agg(DISTINCT path ORDER BY path), ARRAY[]::text[]) "
            "AS paths "
            "FROM ( "
            "SELECT unnest(COALESCE(schema_paths, ARRAY[]::text[])) AS path "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            ") AS stage_paths "
            "WHERE path IS NOT NULL "
            "AND btrim(path) <> ''"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    row = result.mappings().first()
    return list(row.get("paths") or [])


async def build_stage_payload(
    session,
    bank_id: Any,
    stage: str,
    variant: str,
    state_json: dict[str, Any],
    state_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_payload: dict[str, Any] = {}
    stage_paths = await resolve_stage_paths(session, bank_id, stage, variant)
    for path in stage_paths:
        value = get_context_path_value(state_json, path)
        if _is_non_empty(value):
            set_context_path_value(stage_payload, path, value)
    return {
        "data": stage_payload,
        "ai_assisted_paths": resolve_ai_assisted_paths(state_meta, stage),
    }


__all__ = [
    "build_stage_payload",
    "normalize_ai_assisted_map",
    "normalize_user_edited_map",
    "resolve_ai_assisted_paths",
    "resolve_stage_paths",
]
