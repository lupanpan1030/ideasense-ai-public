from __future__ import annotations

import re

from app.services.extraction_text_heuristics import (
    _clip_value_before_labels,
    _extract_ai_guardrails_value,
    _extract_ai_monitoring_value,
    _extract_ai_quality_metrics_value,
    _extract_compliance_milestone_value,
    _extract_core_user_journeys_value,
    _extract_data_access_rights_value,
    _extract_data_retention_policy_value,
    _extract_high_level_components_value,
    _extract_labeled_answer_value,
    _extract_non_functional_priorities_value,
)
from app.services.extraction_transforms import is_non_empty as _is_non_empty


def _has_tech_journey_components_answer(
    schema_paths: list[str],
    answer: str,
) -> bool:
    path_set = set(schema_paths)
    needs_journeys = "tech_execution.product_scope.core_user_journeys" in path_set
    needs_components = (
        "tech_execution.architecture.high_level_components" in path_set
    )
    if needs_journeys and len(_extract_core_user_journeys_value(answer)) < 2:
        return False
    if needs_components and len(_extract_high_level_components_value(answer)) < 2:
        return False
    return needs_journeys or needs_components


def _extract_data_sources_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"data\s*sources?(?:\s*(?:and|/)\s*ownership)?",
            r"sources?\s*(?:and|/)\s*ownership",
            r"data\s*ownership",
        ),
    )
    if not labeled:
        return None
    return _clip_value_before_labels(
        labeled,
        (
            r"year[-\s]?1\s*data\s*volume",
            r"expected\s*data\s*volume",
            r"data\s*volume",
            r"growth",
            r"ai\s*usage",
            r"performance",
            r"scalability",
            r"scaling",
        ),
    )


def _extract_data_volume_year1_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"year[-\s]?1\s*data\s*volume",
            r"expected\s*data\s*volume(?:\s*in\s*year\s*1)?",
            r"data\s*volume(?:\s*year\s*1)?",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"growth",
                r"ai\s*usage",
                r"performance",
                r"scalability",
                r"scaling",
            ),
        )
    match = re.search(
        r"\b(?:year[-\s]?1|first\s+year)\b[^.。\n]*(?:messages?|reports?|teams?|programs?|records?)[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_growth_expectations_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"growth(?:\s*(?:rate|expectations?))?",
            r"expected\s*growth",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"ai\s*usage",
                r"performance",
                r"scalability",
                r"scaling",
            ),
        )
    match = re.search(
        r"\bgrowth\b[^.。\n]*(?:\b\d+\s*x\b|percent|%|if\s+|per\s+year|annually)[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_ai_usage_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"ai\s*usage",
            r"ai\s*role",
            r"ai(?:/ml)?\s*usage",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"performance",
                r"slas?",
                r"scalability",
                r"scaling",
            ),
        )
    match = re.search(
        r"\bAI\b[^.。\n]*(?:core|auxiliary|extraction|summar(?:y|ies)|reports?)[^.。\n]*",
        answer,
    )
    return match.group(0).strip() if match else None


def _extract_performance_expectations_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"performance\s*expectations?",
            r"sla\s*expectations?",
            r"slas?",
            r"performance",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"scalability",
                r"scaling",
                r"10x",
            ),
        )
    match = re.search(
        r"\b(?:p95|latency|response\s*time|uptime|availability|sla|slo|under\s+\d+\s*seconds?)\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_scalability_strategy_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"10x\s*scal(?:ing|ability)\s*strategy",
            r"scal(?:ing|ability)\s*strategy",
            r"10x\s*scal(?:ing|ability)",
            r"scaling",
        ),
    )
    if labeled:
        return labeled
    match = re.search(
        r"\b(?:10x|scale|scaling|scalability)\b[^.。\n]*(?:queue|cache|index|worker|process|service|database)[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_current_status_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"current\s*status",
            r"product\s*today",
            r"status",
        ),
    )
    if not labeled:
        return None
    return _clip_value_before_labels(
        labeled,
        (
            r"in-?mvp\s*scope",
            r"mvp\s*(?:must\s*include|definition|scope)",
            r"out-?of-?mvp",
            r"not\s*in\s*mvp",
        ),
    )


def _extract_mvp_definition_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"in-?mvp\s*scope",
            r"mvp\s*boundaries",
            r"mvp\s*must\s*include",
            r"mvp\s*definition",
            r"mvp\s*scope",
            r"in\s*mvp",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"out-?of-?mvp\s*boundary",
                r"out-?of-?mvp",
                r"not\s*in\s*mvp",
                r"explicitly\s*not\s*in\s*mvp",
            ),
        )
    match = re.search(
        r"\bmvp\s+must\s+include\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _has_out_of_mvp_boundary(answer: str) -> bool:
    return bool(
        re.search(
            r"\b(?:out-?of-?mvp|not\s+in\s+mvp|excluded\s+from\s+the\s+mvp)\b",
            answer,
            flags=re.IGNORECASE,
        )
    )


def _extract_compliance_requirements_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"regulations?",
            r"applicable\s*regulations?",
            r"compliance\s*requirements?",
            r"required\s*audits\s*/\s*certs",
            r"required\s*audits\s+or\s+certs",
            r"required\s*certifications?\s*/\s*audits?",
            r"required\s*certifications?\s+or\s+audits?",
            r"required\s*certifications?",
            r"certifications?\s+or\s+audits?",
            r"certifications?\s*/\s*audits?",
            r"audits?\s*/\s*certs",
            r"audits?",
            r"certifications?",
            r"requirements?",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"first\s*compliance\s*milestone",
                r"first\s*milestone",
                r"compliance\s*milestones?",
                r"milestones?",
                r"data\s*retention",
                r"retention\s*/\s*deletion",
                r"retention(?:/deletion)?\s*plan",
            ),
        )
    match = re.search(
        r"\b(?:gdpr|hipaa|pci|soc\s*2|soc2|ccpa|ferpa)\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_sensitive_data_types_value(answer: str) -> str | None:
    labeled = _extract_labeled_answer_value(
        answer,
        (
            r"data\s*handled",
            r"sensitive\s*data",
            r"data\s*types?",
        ),
    )
    if labeled:
        return _clip_value_before_labels(
            labeled,
            (
                r"data\s*access\s*rights",
                r"access\s*rights",
                r"compliance\s*requirements?",
                r"regulations?",
            ),
        )
    matches = [
        label
        for label, pattern in (
            ("personal information", r"\bpersonal\s+(?:information|info|data)\b"),
            ("money/payment data", r"\b(?:money|payment|payments|card)\b"),
            ("health data", r"\bhealth\b"),
            ("children's data", r"\bchildren'?s?\b"),
            ("EU users", r"\b(?:eu|european\s+union|gdpr)\b"),
            ("none", r"\bnone\b|no\s+(?:sensitive|regulated)\s+data"),
        )
        if re.search(pattern, answer, flags=re.IGNORECASE)
    ]
    return ", ".join(dict.fromkeys(matches)) if matches else None


def _extract_sensitive_compliance_value(answer: str) -> str | None:
    explicit = _extract_compliance_requirements_value(answer)
    if explicit:
        return explicit
    match = re.search(
        r"\b(?:gdpr|privacy|consent|deletion|export|dpa|data\s+processing)\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(0).strip()
    if re.search(r"\bnone\b|no\s+(?:regulated|sensitive)\s+data", answer, re.IGNORECASE):
        return "No specific regulated-data compliance requirements identified for MVP."
    return None


def _has_tech_data_access_answer(answer: str) -> bool:
    return _is_non_empty(_extract_data_access_rights_value(answer))


def _has_tech_complexity_debt_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"complexity\s+hotspots?|hotspots?",
            r"debt",
            r"strict|day\s+one|hard\s+line",
        )
    )


def _has_tech_infra_devops_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"hosting",
            r"environments?|staging|production",
            r"ci/cd|deploy",
            r"monitoring|alerts?|logs?|metrics?",
            r"backup|disaster\s+recovery|\bdr\b|rpo|rto",
        )
    )


def _has_tech_reliability_testing_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"reliability|uptime|availability",
            r"testing|tests?",
            r"release|rollback|deploy",
        )
    )


def _has_tech_slo_incident_answer(answer: str) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    return all(
        re.search(pattern, cleaned, flags=re.IGNORECASE)
        for pattern in (
            r"slo|sla|availability|uptime",
            r"failover|backup|retry",
            r"incident|runbook|alert",
        )
    )


def _has_tech_data_scalability_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_data_sources_value(answer))
        and _is_non_empty(_extract_data_volume_year1_value(answer))
        and _is_non_empty(_extract_growth_expectations_value(answer))
        and _is_non_empty(_extract_ai_usage_value(answer))
        and _is_non_empty(_extract_performance_expectations_value(answer))
        and _is_non_empty(_extract_scalability_strategy_value(answer))
    )


def _has_tech_mvp_boundary_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_current_status_value(answer))
        and _is_non_empty(_extract_mvp_definition_value(answer))
        and _has_out_of_mvp_boundary(answer)
    )


def _has_tech_product_scope_answer(answer: str) -> bool:
    return (
        _has_tech_mvp_boundary_answer(answer)
        and len(_extract_core_user_journeys_value(answer)) >= 2
        and _is_non_empty(_extract_non_functional_priorities_value(answer))
    )


def _has_tech_compliance_plan_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_compliance_requirements_value(answer))
        and _is_non_empty(_extract_compliance_milestone_value(answer))
        and _is_non_empty(_extract_data_retention_policy_value(answer))
    )


def _has_tech_sensitive_data_answer(answer: str) -> bool:
    return _is_non_empty(_extract_sensitive_data_types_value(answer))


def _has_tech_ai_quality_answer(answer: str) -> bool:
    return (
        _is_non_empty(_extract_ai_quality_metrics_value(answer))
        and _is_non_empty(_extract_ai_monitoring_value(answer))
        and _is_non_empty(_extract_ai_guardrails_value(answer))
    )
