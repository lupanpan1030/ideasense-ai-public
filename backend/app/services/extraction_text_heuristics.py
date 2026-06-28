from __future__ import annotations

import re
from typing import Any


def _first_non_empty_string(values: list[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _strip_list_prefix(text: str) -> str:
    return re.sub(r"^[\s\-*\d)#.、:：]+", "", text).strip()


def _clean_extracted_text_items(values: list[str], *, limit: int = 6) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = _strip_list_prefix(raw_value)
        value = re.sub(r"\s+", " ", value).strip(" .;:,")
        if len(value) < 3:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
        if len(cleaned) >= limit:
            break
    return cleaned


def _is_target_user_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "target_user.core",
        "target_user.priority_segment",
    }.issubset(path_set)


def _is_time_money_impact_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {"impact.time_impact", "impact.money_impact"}.issubset(path_set)


def _clip_target_user_value(value: str) -> str:
    match = re.search(
        r"(?:[.;。]\s+|\n)\s*(?:the\s+)?(?:day-to-day\s+user|daily\s+user|"
        r"end\s+user|buyer|payer|decision\s+maker|market\s+type)\b",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value.strip()
    return value[: match.start()].strip()


def _extract_target_user_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"p0\s*segment",
            r"priority\s*segment",
            r"initial\s+priority\s+segment",
            r"primary\s+(?:user|customer)",
            r"target\s+(?:user|customer|segment)",
        ),
    )
    candidate = labeled if labeled else answer.strip()
    if not candidate:
        return None
    candidate = _clip_target_user_value(candidate)
    candidate = _strip_list_prefix(candidate)
    return candidate if candidate else None


def _is_tech_journey_components_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return (
        "tech_execution.product_scope.core_user_journeys" in path_set
        or "tech_execution.architecture.high_level_components" in path_set
    )


def _is_tech_product_scope_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "tech_execution.product_scope.current_status",
        "tech_execution.product_scope.mvp_definition",
        "tech_execution.product_scope.core_user_journeys",
        "tech_execution.product_scope.non_functional_priorities",
    }.issubset(path_set)


def _is_tech_data_access_question(schema_paths: list[str]) -> bool:
    return "tech_execution.data_ai_scalability.data_access_rights" in set(schema_paths)


def _is_tech_compliance_plan_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    requirements_path = (
        "tech_execution.security_compliance.compliance_requirements" in path_set
        or "tech_execution.security_compliance.audit_requirements" in path_set
    )
    return (
        requirements_path
        and "tech_execution.security_compliance.compliance_milestones" in path_set
        and "tech_execution.security_compliance.data_retention_policy" in path_set
    )


def _is_tech_ai_quality_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "tech_execution.data_ai_scalability.model_quality_metrics",
        "tech_execution.data_ai_scalability.monitoring_feedback_loop",
        "tech_execution.data_ai_scalability.fallback_guardrails",
    }.issubset(path_set)


def _is_tech_data_scalability_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "tech_execution.data_ai_scalability.data_sources",
        "tech_execution.data_ai_scalability.data_volume_year1",
        "tech_execution.data_ai_scalability.growth_expectations",
        "tech_execution.data_ai_scalability.ai_usage",
        "tech_execution.data_ai_scalability.performance_expectations",
        "tech_execution.data_ai_scalability.scalability_strategy",
    }.issubset(path_set)


def _is_market_moat_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return (
        "market_strategy.unfair_advantage" in path_set
        or "market_strategy.moat.long_term_moat" in path_set
        or "market_strategy.moat.switching_costs" in path_set
        or "market_strategy.moat.big_tech_response_risk" in path_set
    )


def _extract_core_user_journeys_value(answer: str) -> list[str]:
    if not isinstance(answer, str) or not answer.strip():
        return []
    candidate = answer.strip()
    marker = re.search(
        r"\b(?:critical\s+)?(?:user\s+)?journeys?\s*[:：-]",
        candidate,
        flags=re.IGNORECASE,
    )
    if marker:
        candidate = candidate[marker.end() :]
    candidate = re.split(
        r"(?:^|[.;]\s+|\n\s*)(?:(?:[A-Z]|\d+)[).、]\s*)?(?:high[-\s]?level\s+components?|components?|architecture|non[-\s]?functional\s+requirements?|nfr\s+priorities|nfrs?)\s*[:：-]",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    numbered = re.findall(
        r"(?:^|[;\n])\s*\d+\s*[\).、]\s*(.*?)(?=(?:[;\n]\s*)\d+\s*[\).、]|$)",
        candidate,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if numbered:
        return _clean_extracted_text_items(numbered, limit=3)
    if ";" in candidate or "；" in candidate:
        return _clean_extracted_text_items(re.split(r"[;；]", candidate), limit=3)
    return []


def _extract_high_level_components_value(answer: str) -> list[str]:
    if not isinstance(answer, str) or not answer.strip():
        return []
    value = _extract_labeled_answer_value(
        answer,
        (
            r"high[-\s]?level\s+components?",
            r"components?",
            r"architecture\s+components?",
        ),
    )
    if not value:
        return []
    value = re.split(
        r"[.;]\s+(?:constraints?|risks?|data|compliance|reason|why|rationale)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return _clean_extracted_text_items(re.split(r",|\band\b", value), limit=8)


def _extract_labeled_answer_value(
    answer: str,
    labels: tuple[str, ...],
) -> str | None:
    label_pattern = "|".join(labels)
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(
            rf"^(?:[-*]\s*)?(?:(?:[A-Z]|\d+)[).、]\s*)?(?:{label_pattern})\s*[:：-]\s*(.+)$",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            value = match.group(1).strip()
            return value if value else None
    inline = re.search(
        rf"(?:^|[.;]\s+|\n\s*)(?:(?:[A-Z]|\d+)[).、]\s*)?(?:{label_pattern})\s*[:：-]\s*(.+)",
        answer,
        flags=re.IGNORECASE,
    )
    if inline:
        value = inline.group(1).strip()
        return value if value else None
    return None


def _has_time_impact_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    if re.search(
        r"(?:time\s*(?:wasted|impact)?|hours?\s*wasted)\s*[:：-]\s*(?:unknown|none|n/?a|[^\n]{2,})",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*(?:hours?|hrs?|minutes?|mins?|days?)\s+(?:per|/)\s*(?:week|month)\b",
            cleaned,
            flags=re.IGNORECASE,
        )
    )


def _has_money_impact_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    if re.search(
        r"(?:money|financial|costs?|lost\s+revenue|revenue\s+loss|risk)\s*(?:impact)?\s*[:：-]\s*(?:unknown|none|n/?a|[^\n]{2,})",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"(?:[$€£]\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars?|eur|gbp)\b).{0,40}\b(?:per|/)\s*(?:month|mo)\b",
            cleaned,
            flags=re.IGNORECASE,
        )
    )


def _extract_labeled_impact_value(
    answer: str,
    labels: tuple[str, ...],
) -> str | None:
    return _extract_labeled_answer_value(answer, labels)


def _extract_time_impact_value(answer: str) -> str | None:
    labeled = _extract_labeled_impact_value(
        answer,
        (
            r"time\s*wasted",
            r"time\s*impact",
            r"time",
            r"hours?\s*wasted",
        ),
    )
    if labeled:
        return labeled
    match = re.search(
        r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*(?:hours?|hrs?|minutes?|mins?|days?)\s+(?:per|/)\s*(?:week|month)\b",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_money_impact_value(answer: str) -> str | None:
    labeled = _extract_labeled_impact_value(
        answer,
        (
            r"money\s*impact",
            r"financial\s*impact",
            r"costs?",
            r"lost\s*revenue",
            r"revenue\s*loss",
        ),
    )
    if labeled:
        return labeled
    match = re.search(
        r"(?:[$€£]\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars?|eur|gbp)\b).{0,40}\b(?:per|/)\s*(?:month|mo)\b",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _clip_value_before_labels(value: str, labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(labels)
    match = re.search(
        rf"[.;]\s+(?:(?:[A-Z]|\d+)[).、]\s*)?(?:{label_pattern})\s*[:：-]",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value.strip()
    return value[: match.start()].strip()


def _extract_competitor_types_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"competitor\s*types",
            r"competitor\s*types\s*or\s*alternatives",
            r"alternatives",
            r"competitors?\s*/\s*alternatives",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"named\s*competitors?",
            r"named\s*alternatives?",
            r"positioning(?:\s*difference)?",
            r"red\s*flags?",
        ),
    )


def _extract_named_competitors_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"named\s*competitors?",
            r"named\s*alternatives?",
            r"specific\s*competitors?",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"positioning(?:\s*difference)?",
            r"red\s*flags?",
        ),
    )


def _extract_positioning_summary_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"positioning(?:\s*difference)?",
            r"positioning\s*summary",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"red\s*flags?",
            r"competitive\s*red\s*flags?",
        ),
    )


def _extract_competitive_red_flags_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"red\s*flags?",
            r"competitive\s*red\s*flags?",
        ),
    )
    return value.strip(" .;") if value else None


def _extract_unfair_advantage_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"unfair\s*advantage(?:\s*today)?",
            r"advantage\s*today",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"12.{0,3}18\s*month\s*differentiation",
            r"differentiation",
            r"long[-\s]*term\s*moat",
            r"switching\s*costs?",
            r"incumbent\s*risk",
        ),
    )


def _extract_long_term_moat_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"long[-\s]*term\s*moat",
            r"moat",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"switching\s*costs?",
            r"incumbent\s*risk",
            r"big\s*tech",
        ),
    )


def _extract_switching_costs_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"switching\s*costs?",
            r"hard\s*to\s*leave",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"incumbent\s*risk",
            r"big\s*tech",
            r"defensibility",
            r"protection\s*against",
        ),
    )


def _extract_big_tech_response_risk_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"incumbent\s*risk",
            r"big\s*tech\s*(?:response\s*)?risk",
            r"defensibility\s*vs\s*incumbents?",
            r"protection\s*against\s*incumbents?",
        ),
    )


def _extract_data_access_rights_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"data\s*access\s*rights",
            r"access\s*rights",
            r"rights\s*/\s*access",
            r"access\s*/\s*rights",
            r"rights\s+and\s+access",
            r"data\s*rights",
            r"access\s*plan",
            r"data\s*access",
        ),
    )
    if labeled:
        clipped = _clip_value_before_labels(
            labeled,
            (
                r"refresh\s*cadence",
                r"update\s*cadence",
                r"collection\s*/\s*refresh",
                r"collection\s*refresh",
                r"quality\s*gaps",
                r"required\s*data",
                r"data\s*required",
            ),
        )
        return clipped.strip(" .;")
    match = re.search(
        r"\b(?:we|they|users?|programs?)\s+(?:already\s+)?(?:have|will\s+get|can\s+grant|provide)\s+access\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_key_integrations_value(answer: str) -> list[str]:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"key\s+integrations\s*/\s*apis",
            r"key\s+integrations",
            r"integrations\s*/\s*apis",
            r"external\s+services",
            r"top\s+external\s+services",
            r"integrations?",
        ),
    )
    if not value:
        return []
    value = _clip_value_before_labels(
        value,
        (
            r"single\s+points?\s+of\s+dependency",
            r"vendor\s+lock[-\s]?in",
            r"maturity",
            r"reliability",
            r"dependency\s+maturity",
            r"top\s+technical\s+risks",
            r"technical\s+risks",
            r"main\s+risks",
        ),
    )
    return _clean_extracted_text_items(re.split(r",|\band\b", value), limit=8)


def _extract_top_technical_risks_value(answer: str) -> list[str]:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"top\s+\d+\s+technical\s+risks",
            r"top\s+technical\s+risks",
            r"top\s+\d+\s+tech\s+worries",
            r"top\s+tech\s+worries",
            r"technical\s+worries",
            r"tech\s+worries",
            r"top\s+risks\s+and\s+experiments",
            r"risks\s+and\s+experiments",
            r"risk\s+experiments",
            r"technical\s+risks",
            r"main\s+risks",
            r"top\s+risks",
            r"risks",
        ),
    )
    if not value:
        match = re.search(
            r"\bmain\s+risks\s+are\s+(.+)",
            answer,
            flags=re.IGNORECASE | re.DOTALL,
        )
        value = match.group(1).strip() if match else None
    if not value:
        return []
    value = _clip_value_before_labels(
        value,
        (
            r"mitigation(?:\s+experiments?)?",
            r"risk\s+mitigation",
            r"experiments?",
            r"roadmap",
            r"team\s+composition",
        ),
    )
    return _clean_extracted_text_items(re.split(r",|\band|\n|;", value), limit=6)


def _extract_risk_mitigation_plan_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"risk\s+mitigation\s+plan",
            r"mitigation\s+plan",
            r"mitigation\s+experiments?",
            r"risk\s+mitigation",
            r"mitigation",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"team\s+composition",
            r"dev\s+process",
            r"technical\s+roadmap",
            r"roadmap",
            r"top\s+\d+\s+technical\s+risks",
            r"top\s+technical\s+risks",
            r"technical\s+risks",
            r"main\s+risks",
        ),
    )


def _extract_compliance_milestone_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"first\s*compliance\s*milestone",
            r"first\s*milestone",
            r"compliance\s*milestones?",
            r"milestones?",
            r"milestone",
        ),
    )


def _extract_data_retention_policy_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"data\s*retention(?:/deletion)?\s*plan",
            r"retention\s*/\s*deletion",
            r"retention(?:/deletion)?\s*plan",
            r"retention\s*policy",
            r"deletion\s*plan",
        ),
    )


def _extract_ai_quality_metrics_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"good\s+(?:ai\s+)?output",
            r"quality\s+(?:definition|metrics?)",
            r"metrics?",
        ),
    )


def _extract_ai_monitoring_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"quality\s+(?:review|monitoring)",
            r"monitor(?:ing)?",
            r"review",
        ),
    )


def _extract_ai_guardrails_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"fallbacks?/guardrails?",
            r"guardrails?/fallbacks?",
            r"guardrails?",
            r"fallbacks?",
        ),
    )


def _extract_non_functional_priorities_value(answer: str) -> str | None:
    return _extract_labeled_answer_value(
        answer,
        (
            r"non[-\s]?functional\s+requirements?(?:\s*\(nfrs?\))?",
            r"non[-\s]?functional\s+priorities",
            r"nfr\s*priorities",
            r"nfrs?",
        ),
    )
