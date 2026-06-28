from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

BoolPredicate = Callable[[Any], bool]
SchemaPredicate = Callable[[list[str]], bool]
AnswerExtractor = Callable[[str], Any]


@dataclass(frozen=True)
class PreviewFieldFallbackHelpers:
    is_non_empty: BoolPredicate
    has_explicit_none: BoolPredicate
    first_non_empty_string: Callable[[list[Any]], str | None]
    extract_primary_line: Callable[[str], str | None]
    is_target_user_question: SchemaPredicate
    extract_target_user_value: AnswerExtractor
    is_severity_question: SchemaPredicate
    extract_severity_score: AnswerExtractor
    extract_severity_reason: AnswerExtractor
    is_time_money_impact_question: SchemaPredicate
    extract_time_impact_value: AnswerExtractor
    extract_money_impact_value: AnswerExtractor
    is_alternatives_question: SchemaPredicate
    extract_current_solutions_value: AnswerExtractor
    extract_satisfaction_score: AnswerExtractor
    extract_main_complaints_value: AnswerExtractor
    is_evidence_validation_question: SchemaPredicate
    extract_user_interview_count_value: AnswerExtractor
    extract_key_learnings_value: AnswerExtractor
    extract_data_evidence_value: AnswerExtractor
    extract_key_unknowns_value: AnswerExtractor
    is_market_business_model_question: SchemaPredicate
    extract_payer_role_value: AnswerExtractor
    extract_revenue_model_value: AnswerExtractor
    is_market_competition_question: SchemaPredicate
    extract_competitor_types_value: AnswerExtractor
    extract_named_competitors_value: AnswerExtractor
    extract_positioning_summary_value: AnswerExtractor
    extract_competitive_red_flags_value: AnswerExtractor
    is_market_gtm_question: SchemaPredicate
    extract_primary_channels_value: AnswerExtractor
    is_market_moat_question: SchemaPredicate
    extract_unfair_advantage_value: AnswerExtractor
    extract_long_term_moat_value: AnswerExtractor
    extract_switching_costs_value: AnswerExtractor
    extract_big_tech_response_risk_value: AnswerExtractor
    is_tech_mvp_boundary_question: SchemaPredicate
    extract_current_status_value: AnswerExtractor
    extract_mvp_definition_value: AnswerExtractor
    extract_non_functional_priorities_value: AnswerExtractor
    is_tech_data_access_question: SchemaPredicate
    extract_data_access_rights_value: AnswerExtractor
    extract_key_integrations_value: AnswerExtractor
    extract_top_technical_risks_value: AnswerExtractor
    extract_risk_mitigation_plan_value: AnswerExtractor
    is_tech_data_scalability_question: SchemaPredicate
    extract_data_sources_value: AnswerExtractor
    extract_data_volume_year1_value: AnswerExtractor
    extract_growth_expectations_value: AnswerExtractor
    extract_ai_usage_value: AnswerExtractor
    extract_performance_expectations_value: AnswerExtractor
    extract_scalability_strategy_value: AnswerExtractor
    is_tech_journey_components_question: SchemaPredicate
    extract_core_user_journeys_value: AnswerExtractor
    extract_high_level_components_value: AnswerExtractor
    is_tech_sensitive_data_question: SchemaPredicate
    extract_sensitive_data_types_value: AnswerExtractor
    extract_sensitive_compliance_value: AnswerExtractor
    is_tech_ai_quality_question: SchemaPredicate
    extract_ai_quality_metrics_value: AnswerExtractor
    extract_ai_monitoring_value: AnswerExtractor
    extract_ai_guardrails_value: AnswerExtractor
    is_tech_compliance_plan_question: SchemaPredicate
    extract_compliance_requirements_value: AnswerExtractor
    extract_compliance_milestone_value: AnswerExtractor
    extract_data_retention_policy_value: AnswerExtractor


def _fill_if_missing(
    remapped: dict[str, Any],
    path: str,
    value: Any,
    *,
    is_non_empty: BoolPredicate,
) -> None:
    if not is_non_empty(remapped.get(path)) and value:
        remapped[path] = value


def _fill_schema_paths_if_missing(
    schema_paths: list[str],
    remapped: dict[str, Any],
    fallback_values: dict[str, Any],
    *,
    is_non_empty: BoolPredicate,
) -> None:
    for path, value in fallback_values.items():
        if path in schema_paths and not is_non_empty(remapped.get(path)) and value:
            remapped[path] = value


def apply_preview_field_fallbacks(
    schema_paths: list[str],
    remapped: dict[str, Any],
    answer: str,
    *,
    helpers: PreviewFieldFallbackHelpers,
) -> dict[str, Any]:
    is_non_empty = helpers.is_non_empty

    if "problem.one_line" in schema_paths and not is_non_empty(
        remapped.get("problem.one_line")
    ):
        candidates = remapped.get("problem.main_problems[]")
        primary = None
        if isinstance(candidates, list):
            primary = helpers.first_non_empty_string(candidates)
        elif isinstance(candidates, str) and candidates.strip():
            primary = candidates.strip()
        if not primary:
            primary = helpers.extract_primary_line(answer)
        if primary:
            remapped["problem.one_line"] = primary
    if helpers.is_target_user_question(schema_paths):
        target_user = helpers.extract_target_user_value(answer)
        if target_user:
            _fill_if_missing(
                remapped,
                "target_user.core",
                target_user,
                is_non_empty=is_non_empty,
            )
            _fill_if_missing(
                remapped,
                "target_user.priority_segment",
                target_user,
                is_non_empty=is_non_empty,
            )
    if helpers.is_severity_question(schema_paths):
        if not is_non_empty(remapped.get("problem.severity_score")):
            severity_score = helpers.extract_severity_score(answer)
            if severity_score is not None:
                remapped["problem.severity_score"] = severity_score
        _fill_if_missing(
            remapped,
            "problem.severity_reason",
            helpers.extract_severity_reason(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_time_money_impact_question(schema_paths):
        _fill_if_missing(
            remapped,
            "impact.time_impact",
            helpers.extract_time_impact_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "impact.money_impact",
            helpers.extract_money_impact_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_alternatives_question(schema_paths):
        _fill_if_missing(
            remapped,
            "alternatives.current_solutions[]",
            helpers.extract_current_solutions_value(answer),
            is_non_empty=is_non_empty,
        )
        if not is_non_empty(remapped.get("alternatives.satisfaction_score")):
            satisfaction_score = helpers.extract_satisfaction_score(answer)
            if satisfaction_score is not None:
                remapped["alternatives.satisfaction_score"] = satisfaction_score
        _fill_if_missing(
            remapped,
            "alternatives.main_complaints[]",
            helpers.extract_main_complaints_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_evidence_validation_question(schema_paths):
        _fill_if_missing(
            remapped,
            "evidence.user_interview_count",
            helpers.extract_user_interview_count_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "evidence.key_learnings[]",
            helpers.extract_key_learnings_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "evidence.data_evidence",
            helpers.extract_data_evidence_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "evidence.key_unknowns[]",
            helpers.extract_key_unknowns_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_market_business_model_question(schema_paths):
        _fill_if_missing(
            remapped,
            "market_strategy.business_model.payer_role",
            helpers.extract_payer_role_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "market_strategy.business_model.revenue_model",
            helpers.extract_revenue_model_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_market_competition_question(schema_paths):
        _fill_schema_paths_if_missing(
            schema_paths,
            remapped,
            {
                "market_strategy.competition.competitor_types[]": helpers.extract_competitor_types_value(
                    answer
                ),
                "market_strategy.competition.competitor_types": helpers.extract_competitor_types_value(
                    answer
                ),
                "market_strategy.competition.named_competitors[]": helpers.extract_named_competitors_value(
                    answer
                ),
                "market_strategy.competition.named_competitors": helpers.extract_named_competitors_value(
                    answer
                ),
                "market_strategy.competition.positioning_summary": helpers.extract_positioning_summary_value(
                    answer
                ),
                "market_strategy.competition.competitive_red_flags[]": helpers.extract_competitive_red_flags_value(
                    answer
                ),
                "market_strategy.competition.competitive_red_flags": helpers.extract_competitive_red_flags_value(
                    answer
                ),
            },
            is_non_empty=is_non_empty,
        )
    if helpers.is_market_gtm_question(schema_paths):
        primary_channels = helpers.extract_primary_channels_value(answer)
        if primary_channels:
            for path in (
                "market_strategy.go_to_market.primary_channels[]",
                "market_strategy.go_to_market.primary_channels",
            ):
                if path in schema_paths and not is_non_empty(remapped.get(path)):
                    remapped[path] = primary_channels
    if helpers.is_market_moat_question(schema_paths):
        _fill_schema_paths_if_missing(
            schema_paths,
            remapped,
            {
                "market_strategy.unfair_advantage": helpers.extract_unfair_advantage_value(
                    answer
                ),
                "market_strategy.moat.long_term_moat": helpers.extract_long_term_moat_value(
                    answer
                ),
                "market_strategy.moat.switching_costs": helpers.extract_switching_costs_value(
                    answer
                ),
                "market_strategy.moat.big_tech_response_risk": helpers.extract_big_tech_response_risk_value(
                    answer
                ),
            },
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_mvp_boundary_question(schema_paths):
        _fill_if_missing(
            remapped,
            "tech_execution.product_scope.current_status",
            helpers.extract_current_status_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.product_scope.mvp_definition",
            helpers.extract_mvp_definition_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.product_scope.non_functional_priorities",
            helpers.extract_non_functional_priorities_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_data_access_question(schema_paths):
        _fill_if_missing(
            remapped,
            "tech_execution.data_ai_scalability.data_access_rights",
            helpers.extract_data_access_rights_value(answer),
            is_non_empty=is_non_empty,
        )
    _fill_if_missing(
        remapped,
        "tech_execution.dependencies.key_integrations",
        helpers.extract_key_integrations_value(answer)
        if "tech_execution.dependencies.key_integrations" in schema_paths
        else None,
        is_non_empty=is_non_empty,
    )
    _fill_if_missing(
        remapped,
        "tech_execution.roadmap_risks.top_technical_risks",
        helpers.extract_top_technical_risks_value(answer)
        if "tech_execution.roadmap_risks.top_technical_risks" in schema_paths
        else None,
        is_non_empty=is_non_empty,
    )
    _fill_if_missing(
        remapped,
        "tech_execution.roadmap_risks.risk_mitigation_plan",
        helpers.extract_risk_mitigation_plan_value(answer)
        if "tech_execution.roadmap_risks.risk_mitigation_plan" in schema_paths
        else None,
        is_non_empty=is_non_empty,
    )
    if helpers.is_tech_data_scalability_question(schema_paths):
        _fill_schema_paths_if_missing(
            schema_paths,
            remapped,
            {
                "tech_execution.data_ai_scalability.data_sources": helpers.extract_data_sources_value(
                    answer
                ),
                "tech_execution.data_ai_scalability.data_volume_year1": helpers.extract_data_volume_year1_value(
                    answer
                ),
                "tech_execution.data_ai_scalability.growth_expectations": helpers.extract_growth_expectations_value(
                    answer
                ),
                "tech_execution.data_ai_scalability.ai_usage": helpers.extract_ai_usage_value(
                    answer
                ),
                "tech_execution.data_ai_scalability.performance_expectations": helpers.extract_performance_expectations_value(
                    answer
                ),
                "tech_execution.data_ai_scalability.scalability_strategy": helpers.extract_scalability_strategy_value(
                    answer
                ),
            },
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_journey_components_question(schema_paths):
        _fill_if_missing(
            remapped,
            "tech_execution.product_scope.core_user_journeys",
            helpers.extract_core_user_journeys_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.architecture.high_level_components",
            helpers.extract_high_level_components_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_sensitive_data_question(schema_paths):
        _fill_if_missing(
            remapped,
            "tech_execution.security_compliance.data_types",
            helpers.extract_sensitive_data_types_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.security_compliance.compliance_requirements",
            helpers.extract_sensitive_compliance_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_ai_quality_question(schema_paths):
        _fill_if_missing(
            remapped,
            "tech_execution.data_ai_scalability.model_quality_metrics",
            helpers.extract_ai_quality_metrics_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.data_ai_scalability.monitoring_feedback_loop",
            helpers.extract_ai_monitoring_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.data_ai_scalability.fallback_guardrails",
            helpers.extract_ai_guardrails_value(answer),
            is_non_empty=is_non_empty,
        )
    if helpers.is_tech_compliance_plan_question(schema_paths):
        requirements = helpers.extract_compliance_requirements_value(answer)
        if requirements:
            has_compliance_path = (
                "tech_execution.security_compliance.compliance_requirements"
                in schema_paths
            )
            has_audit_path = (
                "tech_execution.security_compliance.audit_requirements" in schema_paths
            )
            if has_compliance_path:
                _fill_if_missing(
                    remapped,
                    "tech_execution.security_compliance.compliance_requirements",
                    requirements,
                    is_non_empty=is_non_empty,
                )
            if has_audit_path:
                _fill_if_missing(
                    remapped,
                    "tech_execution.security_compliance.audit_requirements",
                    requirements,
                    is_non_empty=is_non_empty,
                )
        _fill_if_missing(
            remapped,
            "tech_execution.security_compliance.compliance_milestones",
            helpers.extract_compliance_milestone_value(answer),
            is_non_empty=is_non_empty,
        )
        _fill_if_missing(
            remapped,
            "tech_execution.security_compliance.data_retention_policy",
            helpers.extract_data_retention_policy_value(answer),
            is_non_empty=is_non_empty,
        )
    if (
        len(schema_paths) == 1
        and not any(is_non_empty(value) for value in remapped.values())
        and is_non_empty(answer)
        and not helpers.has_explicit_none(answer)
    ):
        remapped[schema_paths[0]] = answer.strip()
    return remapped
