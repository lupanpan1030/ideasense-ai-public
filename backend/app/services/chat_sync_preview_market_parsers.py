from __future__ import annotations

import re

from app.services.extraction_text_heuristics import (
    _clip_value_before_labels,
    _extract_competitive_red_flags_value,
    _extract_competitor_types_value,
    _extract_labeled_answer_value,
    _extract_named_competitors_value,
    _extract_positioning_summary_value,
)
from app.services.extraction_transforms import (
    has_explicit_none as _has_explicit_none,
    is_non_empty as _is_non_empty,
)


def _extract_payer_role_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"payer",
            r"who\s*pays",
            r"buyer",
            r"purchase\s*decision\s*maker",
            r"decision\s*maker",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"end\s*users?",
            r"users?",
            r"revenue\s*model",
            r"pricing\s*unit",
            r"initial\s*(?:target\s*)?price",
            r"price\s*rationale",
            r"secondary\s*revenue",
        ),
    )


def _extract_revenue_model_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"revenue\s*model",
            r"business\s*model",
            r"moneti[sz]ation",
        ),
    )
    if labeled:
        return labeled
    match = re.search(
        r"\b(?:annual\s+)?(?:saas|subscription|license|usage-based|transaction\s+fee|per-seat|per\s+seat|per\s+program|per\s+cohort)\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_primary_channels_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"primary\s*channels",
            r"go-to-market\s*channels",
            r"gtm\s*channels",
            r"channels",
        ),
    )


def _has_market_business_model_answer(answer: str) -> bool:
    return _is_non_empty(_extract_payer_role_value(answer)) and _is_non_empty(
        _extract_revenue_model_value(answer)
    )


def _has_market_moat_answer(answer: str) -> bool:
    if len(answer.strip()) < 80 or _has_explicit_none(answer):
        return False
    cleaned = answer.lower()
    checks = (
        r"unfair\s+advantage|advantage\s+today",
        r"12.{0,3}18|differentiation|meaningfully\s+different",
        r"long.{0,3}term\s+moat|\bmoat\b",
        r"switching\s+costs?|hard\s+to\s+leave",
        r"incumbent|big\s+tech|defensible|copy",
    )
    return all(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in checks)


def _has_market_competition_answer(answer: str, *, require_full: bool = False) -> bool:
    if len(answer.strip()) < 60 or _has_explicit_none(answer):
        return False
    if not require_full:
        return _is_non_empty(_extract_competitor_types_value(answer))
    return (
        _is_non_empty(_extract_competitor_types_value(answer))
        and _is_non_empty(_extract_named_competitors_value(answer))
        and _is_non_empty(_extract_positioning_summary_value(answer))
        and _is_non_empty(_extract_competitive_red_flags_value(answer))
    )


def _has_market_gtm_answer(answer: str) -> bool:
    return _is_non_empty(_extract_primary_channels_value(answer))


def _has_market_launch_segment_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"initial\s+launch\s+segment|initial\s+segment",
            r"estimated\s+(?:number\s+of\s+)?(?:potential\s+)?customers|customers?\s*:",
            r"annual\s+revenue|arpc|revenue\s+per\s+customer",
            r"why\s+now",
        )
    )


def _has_market_unit_economics_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"cost\s+drivers?",
            r"\bcac\b|customer\s+acquisition",
            r"\bltv\b|lifetime\s+value",
            r"gross\s+margin",
            r"payback",
        )
    )


def _has_market_validation_plan_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"must-?be-?true|assumptions?",
            r"top\s+risks?|risks?",
            r"validation\s+plan|experiments?",
            r"validation\s+signals?|signals?",
        )
    )
