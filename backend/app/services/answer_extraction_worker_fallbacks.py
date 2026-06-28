from __future__ import annotations

import re
from typing import Any

from app.services.extraction_text_heuristics import (
    _first_non_empty_string,
    _is_target_user_question,
    _is_time_money_impact_question,
    _extract_target_user_value,
    _is_tech_journey_components_question,
    _is_tech_product_scope_question,
    _is_tech_data_access_question,
    _is_tech_compliance_plan_question,
    _is_tech_ai_quality_question,
    _is_tech_data_scalability_question,
    _is_market_moat_question,
    _extract_core_user_journeys_value,
    _extract_high_level_components_value,
    _extract_labeled_answer_value,
    _extract_money_impact_value,
    _extract_time_impact_value,
    _clip_value_before_labels,
    _extract_competitor_types_value,
    _extract_named_competitors_value,
    _extract_positioning_summary_value,
    _extract_competitive_red_flags_value,
    _extract_unfair_advantage_value,
    _extract_long_term_moat_value,
    _extract_switching_costs_value,
    _extract_big_tech_response_risk_value,
    _extract_data_access_rights_value,
    _extract_key_integrations_value,
    _extract_top_technical_risks_value,
    _extract_risk_mitigation_plan_value,
    _extract_compliance_milestone_value,
    _extract_data_retention_policy_value,
    _extract_ai_quality_metrics_value,
    _extract_ai_monitoring_value,
    _extract_ai_guardrails_value,
    _extract_non_functional_priorities_value,
)
from app.services.extraction_transforms import (
    has_explicit_none as _has_explicit_none,
    is_non_empty as _is_non_empty,
)


def _extract_primary_line(answer: str) -> str | None:
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r"(?:^|\\s)#?1[\\).:\\s]", line) or line.startswith("1."):
            cleaned = re.sub(r"^[^a-zA-Z0-9]*#?1[\\).:\\s-]+", "", line).strip()
            return cleaned if cleaned else line
    return None


def _is_tech_dependencies_question(schema_paths: list[str]) -> bool:
    return "tech_execution.dependencies.key_integrations" in set(schema_paths)


def _is_tech_roadmap_risks_question(schema_paths: list[str]) -> bool:
    paths = set(schema_paths)
    return (
        "tech_execution.roadmap_risks.top_technical_risks" in paths
        or "tech_execution.roadmap_risks.risk_mitigation_plan" in paths
    )


def _is_tech_sensitive_data_question(schema_paths: list[str]) -> bool:
    return "tech_execution.security_compliance.data_types" in set(schema_paths)


def _is_market_competition_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return (
        "market_strategy.competition.competitor_types[]" in path_set
        or "market_strategy.competition.competitor_types" in path_set
        or "market_strategy.competition.named_competitors[]" in path_set
        or "market_strategy.competition.positioning_summary" in path_set
        or "market_strategy.competition.competitive_red_flags[]" in path_set
    )


def _extract_current_status_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (r"current\s*status", r"product\s*today", r"status"),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"in-?mvp\s*scope",
            r"mvp\s*boundaries",
            r"mvp\s*(?:must\s*include|definition|scope)",
            r"out-?of-?mvp",
            r"not\s*in\s*mvp",
        ),
    )


def _extract_mvp_definition_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
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
    if not value:
        return None
    return _clip_value_before_labels(
        value,
        (
            r"out-?of-?mvp\s*boundary",
            r"out-?of-?mvp",
            r"not\s*in\s*mvp",
            r"explicitly\s*not\s*in\s*mvp",
        ),
    )


def _extract_sensitive_data_types_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"data\s*handled",
            r"sensitive\s*data",
            r"data\s*types?",
        ),
    )
    if value:
        return _clip_value_before_labels(
            value,
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


def _extract_compliance_requirements_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
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
    if value:
        return _clip_value_before_labels(
            value,
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


def _extract_data_sources_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"data\s*sources?(?:\s*(?:and|/)\s*ownership)?",
            r"sources?\s*(?:and|/)\s*ownership",
            r"data\s*ownership",
        ),
    )
    if not value:
        return None
    return _clip_value_before_labels(
        value,
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
    value = _extract_labeled_answer_value(
        answer,
        (
            r"year[-\s]?1\s*data\s*volume",
            r"expected\s*data\s*volume(?:\s*in\s*year\s*1)?",
            r"data\s*volume(?:\s*year\s*1)?",
        ),
    )
    if value:
        return _clip_value_before_labels(
            value,
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
    value = _extract_labeled_answer_value(
        answer,
        (
            r"growth(?:\s*(?:rate|expectations?))?",
            r"expected\s*growth",
        ),
    )
    if value:
        return _clip_value_before_labels(
            value,
            (r"ai\s*usage", r"performance", r"scalability", r"scaling"),
        )
    match = re.search(
        r"\bgrowth\b[^.。\n]*(?:\b\d+\s*x\b|percent|%|if\s+|per\s+year|annually)[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_ai_usage_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (r"ai\s*usage", r"ai\s*role", r"ai(?:/ml)?\s*usage"),
    )
    if value:
        return _clip_value_before_labels(
            value,
            (r"performance", r"slas?", r"scalability", r"scaling"),
        )
    match = re.search(
        r"\bAI\b[^.。\n]*(?:core|auxiliary|extraction|summar(?:y|ies)|reports?)[^.。\n]*",
        answer,
    )
    return match.group(0).strip() if match else None


def _extract_performance_expectations_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"performance\s*expectations?",
            r"sla\s*expectations?",
            r"slas?",
            r"performance",
        ),
    )
    if value:
        return _clip_value_before_labels(
            value,
            (r"scalability", r"scaling", r"10x"),
        )
    match = re.search(
        r"\b(?:p95|latency|response\s*time|uptime|availability|sla|slo|under\s+\d+\s*seconds?)\b[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _extract_scalability_strategy_value(answer: str) -> str | None:
    value = _extract_labeled_answer_value(
        answer,
        (
            r"10x\s*scal(?:ing|ability)\s*strategy",
            r"scal(?:ing|ability)\s*strategy",
            r"10x\s*scal(?:ing|ability)",
            r"scaling",
        ),
    )
    if value:
        return value
    match = re.search(
        r"\b(?:10x|scale|scaling|scalability)\b[^.。\n]*(?:queue|cache|index|worker|process|service|database)[^.。\n]*",
        answer,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else None


def _apply_extraction_fallbacks(
    schema_paths: list[str],
    remapped: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    if "problem.one_line" in schema_paths and not _is_non_empty(
        remapped.get("problem.one_line")
    ):
        candidates = remapped.get("problem.main_problems[]")
        primary = None
        if isinstance(candidates, list):
            primary = _first_non_empty_string(candidates)
        elif isinstance(candidates, str) and candidates.strip():
            primary = candidates.strip()
        if not primary:
            primary = _extract_primary_line(answer)
        if primary:
            remapped["problem.one_line"] = primary
    if _is_target_user_question(schema_paths):
        target_user = _extract_target_user_value(answer)
        if target_user:
            if not _is_non_empty(remapped.get("target_user.core")):
                remapped["target_user.core"] = target_user
            if not _is_non_empty(remapped.get("target_user.priority_segment")):
                remapped["target_user.priority_segment"] = target_user
    if _is_time_money_impact_question(schema_paths):
        if not _is_non_empty(remapped.get("impact.time_impact")):
            time_impact = _extract_time_impact_value(answer)
            if time_impact:
                remapped["impact.time_impact"] = time_impact
        if not _is_non_empty(remapped.get("impact.money_impact")):
            money_impact = _extract_money_impact_value(answer)
            if money_impact:
                remapped["impact.money_impact"] = money_impact
    if _is_market_moat_question(schema_paths):
        fallback_values = {
            "market_strategy.unfair_advantage": _extract_unfair_advantage_value(answer),
            "market_strategy.moat.long_term_moat": _extract_long_term_moat_value(
                answer
            ),
            "market_strategy.moat.switching_costs": _extract_switching_costs_value(
                answer
            ),
            "market_strategy.moat.big_tech_response_risk": _extract_big_tech_response_risk_value(
                answer
            ),
        }
        for path, value in fallback_values.items():
            if path in schema_paths and not _is_non_empty(remapped.get(path)) and value:
                remapped[path] = value
    if _is_market_competition_question(schema_paths):
        fallback_values = {
            "market_strategy.competition.competitor_types[]": _extract_competitor_types_value(
                answer
            ),
            "market_strategy.competition.competitor_types": _extract_competitor_types_value(
                answer
            ),
            "market_strategy.competition.named_competitors[]": _extract_named_competitors_value(
                answer
            ),
            "market_strategy.competition.named_competitors": _extract_named_competitors_value(
                answer
            ),
            "market_strategy.competition.positioning_summary": _extract_positioning_summary_value(
                answer
            ),
            "market_strategy.competition.competitive_red_flags[]": _extract_competitive_red_flags_value(
                answer
            ),
            "market_strategy.competition.competitive_red_flags": _extract_competitive_red_flags_value(
                answer
            ),
        }
        for path, value in fallback_values.items():
            if path in schema_paths and not _is_non_empty(remapped.get(path)) and value:
                remapped[path] = value
    if _is_tech_product_scope_question(schema_paths):
        fallback_values = {
            "tech_execution.product_scope.current_status": _extract_current_status_value(
                answer
            ),
            "tech_execution.product_scope.mvp_definition": _extract_mvp_definition_value(
                answer
            ),
            "tech_execution.product_scope.non_functional_priorities": _extract_non_functional_priorities_value(
                answer
            ),
        }
        for path, value in fallback_values.items():
            if path in schema_paths and not _is_non_empty(remapped.get(path)) and value:
                remapped[path] = value
    if _is_tech_journey_components_question(schema_paths):
        if not _is_non_empty(
            remapped.get("tech_execution.product_scope.core_user_journeys")
        ):
            journeys = _extract_core_user_journeys_value(answer)
            if journeys:
                remapped["tech_execution.product_scope.core_user_journeys"] = journeys
        if not _is_non_empty(
            remapped.get("tech_execution.architecture.high_level_components")
        ):
            components = _extract_high_level_components_value(answer)
            if components:
                remapped["tech_execution.architecture.high_level_components"] = (
                    components
                )
    if _is_tech_data_access_question(schema_paths) and not _is_non_empty(
        remapped.get("tech_execution.data_ai_scalability.data_access_rights")
    ):
        data_access = _extract_data_access_rights_value(answer)
        if data_access:
            remapped["tech_execution.data_ai_scalability.data_access_rights"] = (
                data_access
            )
    if _is_tech_dependencies_question(schema_paths) and not _is_non_empty(
        remapped.get("tech_execution.dependencies.key_integrations")
    ):
        integrations = _extract_key_integrations_value(answer)
        if integrations:
            remapped["tech_execution.dependencies.key_integrations"] = integrations
    if _is_tech_roadmap_risks_question(schema_paths) and not _is_non_empty(
        remapped.get("tech_execution.roadmap_risks.top_technical_risks")
    ):
        risks = _extract_top_technical_risks_value(answer)
        if risks:
            remapped["tech_execution.roadmap_risks.top_technical_risks"] = risks
    if "tech_execution.roadmap_risks.risk_mitigation_plan" in schema_paths and not _is_non_empty(
        remapped.get("tech_execution.roadmap_risks.risk_mitigation_plan")
    ):
        mitigation_plan = _extract_risk_mitigation_plan_value(answer)
        if mitigation_plan:
            remapped["tech_execution.roadmap_risks.risk_mitigation_plan"] = (
                mitigation_plan
            )
    if _is_tech_sensitive_data_question(schema_paths):
        if not _is_non_empty(
            remapped.get("tech_execution.security_compliance.data_types")
        ):
            data_types = _extract_sensitive_data_types_value(answer)
            if data_types:
                remapped["tech_execution.security_compliance.data_types"] = data_types
        if not _is_non_empty(
            remapped.get("tech_execution.security_compliance.compliance_requirements")
        ):
            compliance = _extract_sensitive_compliance_value(answer)
            if compliance:
                remapped[
                    "tech_execution.security_compliance.compliance_requirements"
                ] = compliance
    if _is_tech_compliance_plan_question(schema_paths):
        requirements = _extract_compliance_requirements_value(answer)
        if requirements:
            has_compliance_path = (
                "tech_execution.security_compliance.compliance_requirements"
                in schema_paths
            )
            has_audit_path = (
                "tech_execution.security_compliance.audit_requirements" in schema_paths
            )
            if has_compliance_path and not _is_non_empty(
                remapped.get("tech_execution.security_compliance.compliance_requirements")
            ):
                remapped[
                    "tech_execution.security_compliance.compliance_requirements"
                ] = requirements
            if has_audit_path and not _is_non_empty(
                remapped.get("tech_execution.security_compliance.audit_requirements")
            ):
                remapped[
                    "tech_execution.security_compliance.audit_requirements"
                ] = requirements
        if not _is_non_empty(
            remapped.get("tech_execution.security_compliance.compliance_milestones")
        ):
            milestone = _extract_compliance_milestone_value(answer)
            if milestone:
                remapped["tech_execution.security_compliance.compliance_milestones"] = (
                    milestone
                )
        if not _is_non_empty(
            remapped.get("tech_execution.security_compliance.data_retention_policy")
        ):
            retention = _extract_data_retention_policy_value(answer)
            if retention:
                remapped["tech_execution.security_compliance.data_retention_policy"] = (
                    retention
                )
    if _is_tech_ai_quality_question(schema_paths):
        if not _is_non_empty(
            remapped.get("tech_execution.data_ai_scalability.model_quality_metrics")
        ):
            metrics = _extract_ai_quality_metrics_value(answer)
            if metrics:
                remapped[
                    "tech_execution.data_ai_scalability.model_quality_metrics"
                ] = metrics
        if not _is_non_empty(
            remapped.get(
                "tech_execution.data_ai_scalability.monitoring_feedback_loop"
            )
        ):
            monitoring = _extract_ai_monitoring_value(answer)
            if monitoring:
                remapped[
                    "tech_execution.data_ai_scalability.monitoring_feedback_loop"
                ] = monitoring
        if not _is_non_empty(
            remapped.get("tech_execution.data_ai_scalability.fallback_guardrails")
        ):
            guardrails = _extract_ai_guardrails_value(answer)
            if guardrails:
                remapped[
                    "tech_execution.data_ai_scalability.fallback_guardrails"
                ] = guardrails
    if _is_tech_data_scalability_question(schema_paths):
        fallback_values = {
            "tech_execution.data_ai_scalability.data_sources": _extract_data_sources_value(
                answer
            ),
            "tech_execution.data_ai_scalability.data_volume_year1": _extract_data_volume_year1_value(
                answer
            ),
            "tech_execution.data_ai_scalability.growth_expectations": _extract_growth_expectations_value(
                answer
            ),
            "tech_execution.data_ai_scalability.ai_usage": _extract_ai_usage_value(
                answer
            ),
            "tech_execution.data_ai_scalability.performance_expectations": _extract_performance_expectations_value(
                answer
            ),
            "tech_execution.data_ai_scalability.scalability_strategy": _extract_scalability_strategy_value(
                answer
            ),
        }
        for path, value in fallback_values.items():
            if path in schema_paths and not _is_non_empty(remapped.get(path)) and value:
                remapped[path] = value
    if (
        len(schema_paths) == 1
        and not any(_is_non_empty(value) for value in remapped.values())
        and _is_non_empty(answer)
        and not _has_explicit_none(answer)
    ):
        remapped[schema_paths[0]] = answer.strip()
    return remapped
