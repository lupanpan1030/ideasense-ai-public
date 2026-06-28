from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal


OutputLocale = Literal["en", "zh"]

DEFAULT_OUTPUT_LOCALE: OutputLocale = "en"
SUPPORTED_OUTPUT_LOCALES: tuple[OutputLocale, ...] = ("en", "zh")


def normalize_output_locale(value: str | None) -> OutputLocale:
    if not value:
        return DEFAULT_OUTPUT_LOCALE
    normalized = value.strip().lower()
    if normalized in SUPPORTED_OUTPUT_LOCALES:
        return normalized if normalized == "zh" else "en"
    return DEFAULT_OUTPUT_LOCALE


def output_language_label(locale: OutputLocale) -> str:
    if locale == "zh":
        return "Simplified Chinese"
    return "English"


def optional_output_locale(value: Any) -> OutputLocale | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in SUPPORTED_OUTPUT_LOCALES:
        return normalized if normalized == "zh" else "en"
    return None


def normalize_summary_locale_map(
    state_meta: dict[str, Any] | None,
) -> dict[str, dict[str, OutputLocale]]:
    if not isinstance(state_meta, dict):
        return {}
    raw = state_meta.get("summary_locales")
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, OutputLocale]] = {}
    for stage, payload in raw.items():
        if not isinstance(stage, str) or not isinstance(payload, dict):
            continue
        stage_key = stage.strip().lower()
        if not stage_key:
            continue
        draft_output_locale = optional_output_locale(payload.get("draft"))
        final_output_locale = optional_output_locale(payload.get("final"))
        stage_payload: dict[str, OutputLocale] = {}
        if draft_output_locale:
            stage_payload["draft"] = draft_output_locale
        if final_output_locale:
            stage_payload["final"] = final_output_locale
        if stage_payload:
            normalized[stage_key] = stage_payload
    return normalized


def apply_summary_locale_update(
    state_meta: dict[str, Any] | None,
    *,
    stage: str,
    draft_output_locale: OutputLocale | None = None,
    final_output_locale: OutputLocale | None = None,
) -> dict[str, Any]:
    next_state_meta = deepcopy(state_meta) if isinstance(state_meta, dict) else {}
    if not isinstance(next_state_meta, dict):
        next_state_meta = {}
    summary_locales = next_state_meta.get("summary_locales")
    if not isinstance(summary_locales, dict):
        summary_locales = {}
    stage_key = stage.strip().lower()
    stage_payload = summary_locales.get(stage_key)
    if not isinstance(stage_payload, dict):
        stage_payload = {}
    if draft_output_locale is not None:
        stage_payload["draft"] = draft_output_locale
    if final_output_locale is not None:
        stage_payload["final"] = final_output_locale
    summary_locales[stage_key] = stage_payload
    next_state_meta["summary_locales"] = summary_locales
    return next_state_meta


__all__ = [
    "DEFAULT_OUTPUT_LOCALE",
    "SUPPORTED_OUTPUT_LOCALES",
    "OutputLocale",
    "apply_summary_locale_update",
    "normalize_output_locale",
    "normalize_summary_locale_map",
    "optional_output_locale",
    "output_language_label",
]
