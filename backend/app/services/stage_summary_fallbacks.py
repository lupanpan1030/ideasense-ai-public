from __future__ import annotations

import json
from typing import Any


def stage_summary_label(path: str) -> str:
    return path.replace("_", " ").replace(".", " / ").title()


def stage_summary_value(value: Any, *, max_len: int = 220) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text_value = " ".join(value.split())
    elif isinstance(value, (int, float, bool)):
        text_value = str(value)
    else:
        try:
            text_value = json.dumps(value, ensure_ascii=True, sort_keys=True)
        except TypeError:
            text_value = str(value)
    text_value = text_value.strip()
    if not text_value:
        return None
    if len(text_value) > max_len:
        return f"{text_value[: max_len - 3].rstrip()}..."
    return text_value


def collect_stage_summary_items(
    value: Any,
    *,
    path: str = "",
    items: list[tuple[str, str]] | None = None,
    limit: int = 10,
) -> list[tuple[str, str]]:
    collected = items if items is not None else []
    if len(collected) >= limit:
        return collected
    if isinstance(value, dict):
        for key in sorted(value):
            child_path = f"{path}.{key}" if path else str(key)
            collect_stage_summary_items(
                value.get(key),
                path=child_path,
                items=collected,
                limit=limit,
            )
            if len(collected) >= limit:
                break
        return collected
    if isinstance(value, list):
        scalar_values = [
            stage_summary_value(item, max_len=120)
            for item in value
            if not isinstance(item, (dict, list))
        ]
        scalar_values = [item for item in scalar_values if item]
        if scalar_values:
            joined = "; ".join(scalar_values[:4])
            if len(value) > 4:
                joined = f"{joined}; ..."
            collected.append((stage_summary_label(path), joined))
            return collected
        for index, item in enumerate(value[:4], start=1):
            child_path = f"{path}.{index}" if path else str(index)
            collect_stage_summary_items(
                item,
                path=child_path,
                items=collected,
                limit=limit,
            )
            if len(collected) >= limit:
                break
        return collected
    text_value = stage_summary_value(value)
    if text_value and path:
        collected.append((stage_summary_label(path), text_value))
    return collected


def build_stage_summary_fallback(
    stage: str,
    payload: dict[str, Any],
    *,
    output_locale: str,
) -> str:
    stage_key = stage.strip().lower()
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    items = collect_stage_summary_items(data)
    stage_name = stage_key.title() if stage_key else "Stage"
    heading = f"### {stage_name} summary"
    intro = "Generated from the confirmed live context."
    if output_locale == "zh":
        heading = f"### {stage_name} summary"
        intro = "Generated from the confirmed live context."
    if not items:
        return f"{heading}\n\n{intro}\n\nNo confirmed details were available."
    bullets = [f"- {label}: {text_value}" for label, text_value in items]
    return "\n".join([heading, "", intro, "", *bullets])


__all__ = [
    "build_stage_summary_fallback",
    "collect_stage_summary_items",
    "stage_summary_label",
    "stage_summary_value",
]
