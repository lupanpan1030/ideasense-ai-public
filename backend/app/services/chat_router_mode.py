from __future__ import annotations

import re
from typing import Any

from app.services.chat_output_locale import resolve_followup_output_locale
from app.services.localization import DEFAULT_OUTPUT_LOCALE, OutputLocale


def normalize_router_mode(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    if cleaned in {"pro", "lite"}:
        return cleaned
    return None


def extract_router_mode_from_text(answer: Any) -> str | None:
    if not isinstance(answer, str):
        return None
    cleaned = re.sub(r"\s+", " ", answer.strip().lower())
    if not cleaned:
        return None
    cleaned = cleaned.strip(" .!?。！？")

    lite_exact = {
        "lite",
        "mid",
        "non-technical",
        "non technical",
        "nontechnical",
        "plain",
        "plain language",
    }
    pro_exact = {
        "pro",
        "professional",
        "pro path",
        "professional path",
        "developer",
        "engineer",
        "technical",
    }
    if cleaned in lite_exact:
        return "lite"
    if cleaned in pro_exact:
        return "pro"

    lite_patterns = (
        r"\bnon[-\s]?technical\b",
        r"\bnot\s+(?:very\s+)?technical\b",
        r"\bnot\s+an?\s+expert\b",
        r"\bplain\s+language\b",
        r"\bprefer\s+(?:simple|plain|non[-\s]?technical)\b",
        r"\bfollow\s+roughly\b",
    )
    if any(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in lite_patterns):
        return "lite"

    pro_patterns = (
        r"\b(?:software\s+)?developer\b",
        r"\b(?:software\s+)?engineer\b",
        r"\btechnical\s+(?:founder|cofounder|lead|person|user|background)\b",
        r"\b(?:i'?m|i\s+am|as\s+a|i\s+work\s+as\s+a)\s+(?:a\s+)?(?:technical|developer|engineer)\b",
        r"\bprefer\s+(?:the\s+)?(?:technical|pro|professional)\b",
    )
    if any(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in pro_patterns):
        return "pro"
    return None


def extract_mode_from_state(state_json: Any) -> str | None:
    if not isinstance(state_json, dict):
        return None
    tech_execution = state_json.get("tech_execution")
    if not isinstance(tech_execution, dict):
        return None
    meta = tech_execution.get("meta")
    if not isinstance(meta, dict):
        return None
    return normalize_router_mode(meta.get("mode"))


def extract_router_mode_from_message_meta(message_meta: Any) -> str | None:
    if not isinstance(message_meta, dict):
        return None
    raw = message_meta.get("selected_option_key") or message_meta.get(
        "selected_option"
    )
    if not isinstance(raw, str):
        raw = message_meta.get("mode")
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().lower()
    if cleaned in {"pro", "developer", "engineer"}:
        return "pro"
    if cleaned in {
        "mid",
        "lite",
        "non-technical",
        "nontechnical",
        "non_technical",
        "plain",
    }:
        return "lite"
    return normalize_router_mode(cleaned)


def augment_router_mode_message_meta(
    message_meta: Any,
    latest_answer: str | None,
    *,
    runtime_stage: str | None,
    runtime_variant: str | None,
) -> dict[str, Any]:
    next_meta = dict(message_meta) if isinstance(message_meta, dict) else {}
    if runtime_stage != "tech" or runtime_variant != "router":
        return next_meta
    if extract_router_mode_from_message_meta(next_meta):
        return next_meta
    text_mode = extract_router_mode_from_text(latest_answer)
    if not text_mode:
        return next_meta
    next_meta["selected_option_key"] = text_mode
    next_meta["router_mode_source"] = "free_text"
    return next_meta


def resolve_explicit_router_mode(
    state_json: Any,
    message_meta: Any | None = None,
    latest_answer: str | None = None,
) -> str | None:
    meta_mode = extract_router_mode_from_message_meta(message_meta)
    if meta_mode:
        return meta_mode
    text_mode = extract_router_mode_from_text(latest_answer)
    if text_mode:
        return text_mode
    return extract_mode_from_state(state_json)


def require_router_mode(chosen_mode: str | None) -> str:
    mode = normalize_router_mode(chosen_mode)
    if mode:
        return mode
    raise RuntimeError(
        "Router mode must be selected explicitly before entering tech depth."
    )


def build_router_mode_selection_followup(
    question_detail: dict,
    latest_answer: str | None = None,
    *,
    output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
) -> str:
    resolved_locale = resolve_followup_output_locale(
        latest_answer,
        output_locale,
    )
    if resolved_locale == "zh":
        return (
            "请明确选择技术深度：pro 或 lite。"
            "可以点下面的选项，也可以直接输入 Pro、Lite，或说明你是 developer/engineer。"
        )
    return (
        "Please choose the technical depth explicitly: pro or lite. "
        "Use one of the options below, or type Pro, Lite, or that you're a developer/engineer."
    )


def apply_router_mode_selection_guard(
    question_detail: dict,
    decision: dict,
    *,
    state_json: Any,
    message_meta: Any | None = None,
    latest_answer: str | None = None,
    output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
) -> tuple[dict, str | None, str | None]:
    if decision.get("final_verdict") != "pass":
        return decision, None, None

    chosen_mode = resolve_explicit_router_mode(
        state_json,
        message_meta,
        latest_answer,
    )
    if chosen_mode:
        return decision, chosen_mode, None

    guarded_decision = {
        **decision,
        "final_verdict": "needs_info",
        "model_verdict": "needs_info",
        "missing_points": ["Select either the pro or lite technical path."],
        "critical_issues": [],
        "followup_questions": [],
        "help_examples": [],
        "followup_message": build_router_mode_selection_followup(
            question_detail,
            latest_answer,
            output_locale=output_locale,
        ),
        "risk_notes": ["Router mode requires an explicit user selection."],
    }
    return guarded_decision, None, guarded_decision["followup_message"]
