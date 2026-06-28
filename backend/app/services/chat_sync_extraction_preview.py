from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.answer_meta import set_answer_meta_entry
from app.services.chat_market_type_normalization import (
    canonicalize_extracted_value,
    canonicalize_market_type_fields,
)
from app.services.chat_sync_preview_answer_parsers import (
    looks_like_history_reference as looks_like_history_reference,
    _extract_ai_usage_value,
    _extract_compliance_requirements_value,
    _extract_current_solutions_value,
    _extract_current_status_value,
    _extract_data_evidence_value,
    _extract_data_sources_value,
    _extract_data_volume_year1_value,
    _extract_growth_expectations_value,
    _extract_key_learnings_value,
    _extract_key_unknowns_value,
    _extract_main_complaints_value,
    _extract_money_impact_value,
    _extract_mvp_definition_value,
    _extract_payer_role_value,
    _extract_performance_expectations_value,
    _extract_primary_channels_value,
    _extract_primary_line,
    _extract_revenue_model_value,
    _extract_satisfaction_score,
    _extract_scalability_strategy_value,
    _extract_sensitive_compliance_value,
    _extract_sensitive_data_types_value,
    _extract_severity_reason,
    _extract_severity_score,
    _extract_time_impact_value,
    _extract_user_interview_count_value,
    _has_alternatives_answer,
    _has_evidence_validation_answer,
    _has_market_business_model_answer,
    _has_market_competition_answer,
    _has_market_gtm_answer,
    _has_market_launch_segment_answer,
    _has_market_moat_answer,
    _has_market_unit_economics_answer,
    _has_market_validation_plan_answer,
    _has_money_impact_answer,
    _has_problem_scenarios_answer,
    _has_severity_answer,
    _has_tech_ai_quality_answer,
    _has_tech_compliance_plan_answer,
    _has_tech_complexity_debt_answer,
    _has_tech_data_access_answer,
    _has_tech_data_scalability_answer,
    _has_tech_infra_devops_answer,
    _has_tech_journey_components_answer,
    _has_tech_mvp_boundary_answer,
    _has_tech_product_scope_answer,
    _has_tech_reliability_testing_answer,
    _has_tech_sensitive_data_answer,
    _has_tech_slo_incident_answer,
    _has_time_impact_answer,
    _looks_like_idea_snapshot_answer,
    _looks_like_top_problems_answer,
)
from app.services.chat_sync_preview_field_fallbacks import (
    PreviewFieldFallbackHelpers,
    apply_preview_field_fallbacks,
)
from app.services.chat_sync_preview_post_fallbacks import (
    apply_mvp_boundary_preview_fallbacks,
    apply_problem_frequency_preview_fallback,
    infer_problem_frequency_from_answer,
)
from app.services.chat_sync_preview_question_matchers import (
    is_alternatives_question as _is_alternatives_question,
    is_evidence_validation_question as _is_evidence_validation_question,
    is_idea_snapshot_question as _is_idea_snapshot_question,
    is_market_business_model_question as _is_market_business_model_question,
    is_market_competition_prompt_question as _is_market_competition_prompt_question,
    is_market_competition_question as _is_market_competition_question,
    is_market_gtm_question as _is_market_gtm_question,
    is_market_launch_segment_question as _is_market_launch_segment_question,
    is_market_moat_prompt_question as _is_market_moat_prompt_question,
    is_market_unit_economics_question as _is_market_unit_economics_question,
    is_market_validation_plan_question as _is_market_validation_plan_question,
    is_problem_scenarios_question as _is_problem_scenarios_question,
    is_severity_question as _is_severity_question,
    is_tech_complexity_debt_question as _is_tech_complexity_debt_question,
    is_tech_compliance_plan_prompt_question as _is_tech_compliance_plan_prompt_question,
    is_tech_data_scalability_prompt_question as _is_tech_data_scalability_prompt_question,
    is_tech_dependencies_question as _is_tech_dependencies_question,
    is_tech_infra_devops_question as _is_tech_infra_devops_question,
    is_tech_mvp_boundary_prompt_question,
    is_tech_mvp_boundary_question as _is_tech_mvp_boundary_question,
    is_tech_reliability_testing_question as _is_tech_reliability_testing_question,
    is_tech_roadmap_risks_question as _is_tech_roadmap_risks_question,
    is_tech_sensitive_data_question as _is_tech_sensitive_data_question,
    is_tech_slo_incident_question as _is_tech_slo_incident_question,
    is_time_money_impact_question as _is_time_money_impact_question,
    is_top_problem_question as _is_top_problem_question,
)
from app.services.context_backfill import backfill_problem_idea_raw
from app.services.context_paths import (
    infer_context_path_stage as _infer_path_stage,
    set_context_path_value as _set_path,
)
from app.services.extraction_text_heuristics import (
    _first_non_empty_string,
    _is_target_user_question,
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
    build_extraction_targets as _build_extraction_targets,
    extract_value_meta as _extract_value_meta,
    has_explicit_none as _has_explicit_none,
    is_non_empty as _is_non_empty,
    remap_extracted as _remap_extracted,
)
from app.services.stage_payloads import normalize_ai_assisted_map


__all__ = [
    "apply_extraction_updates_to_state",
    "build_sync_extraction_preview",
    "infer_frequency_from_answer",
    "looks_like_history_reference",
    "prepare_extraction_updates",
    "should_soft_pass_answer",
    "update_ai_assisted_paths",
]


def should_soft_pass_answer(
    question_detail: dict,
    answer: str,
    gate_result: Any | None,
) -> bool:
    schema_paths = question_detail.get("schema_paths") or []
    schema_path_text = (
        " ".join(path for path in schema_paths if isinstance(path, str))
        if isinstance(schema_paths, list)
        else str(schema_paths)
    )
    if (
        "tech_execution.data_ai_scalability.data_sources" in schema_path_text
        and _has_tech_data_scalability_answer(answer)
    ):
        return True
    if (
        "tech_execution.roadmap_risks.top_technical_risks" in schema_path_text
        and len(_extract_top_technical_risks_value(answer)) >= 2
    ):
        return True
    if not schema_paths:
        if _has_tech_complexity_debt_answer(answer):
            return True
        if _has_tech_infra_devops_answer(answer):
            return True
        if _has_tech_reliability_testing_answer(answer):
            return True
        if _has_tech_slo_incident_answer(answer):
            return True
        if _has_tech_data_scalability_answer(answer):
            return True
        if _has_tech_data_access_answer(answer):
            return True
        if _has_tech_ai_quality_answer(answer):
            return True
        if _has_tech_sensitive_data_answer(answer):
            return True
        if _has_tech_compliance_plan_answer(answer):
            return True
        if len(_extract_key_integrations_value(answer)) >= 2:
            return True
        if len(_extract_top_technical_risks_value(answer)) >= 2:
            return True
    if _is_severity_question(schema_paths):
        return _has_severity_answer(answer)
    if _is_time_money_impact_question(schema_paths):
        return _has_time_impact_answer(answer) and _has_money_impact_answer(answer)
    if _is_alternatives_question(schema_paths):
        return _has_alternatives_answer(answer)
    if _is_evidence_validation_question(schema_paths):
        return _has_evidence_validation_answer(answer)
    if _is_problem_scenarios_question(schema_paths):
        return _has_problem_scenarios_answer(answer)
    if _is_target_user_question(schema_paths):
        return _is_non_empty(_extract_target_user_value(answer))
    if _is_market_competition_prompt_question(
        question_detail
    ) or _is_market_competition_question(schema_paths):
        require_full_competition = _is_market_competition_prompt_question(
            question_detail
        ) or any(
            path in set(schema_paths)
            for path in (
                "market_strategy.competition.named_competitors[]",
                "market_strategy.competition.positioning_summary",
                "market_strategy.competition.competitive_red_flags[]",
            )
        )
        return _has_market_competition_answer(
            answer,
            require_full=require_full_competition,
        )
    if _is_market_gtm_question(schema_paths):
        return _has_market_gtm_answer(answer)
    if _is_market_moat_prompt_question(question_detail) or _is_market_moat_question(
        schema_paths
    ):
        return _has_market_moat_answer(answer)
    if _is_market_business_model_question(schema_paths):
        return _has_market_business_model_answer(answer)
    if _is_market_launch_segment_question(question_detail):
        return _has_market_launch_segment_answer(answer)
    if _is_market_unit_economics_question(question_detail):
        return _has_market_unit_economics_answer(answer)
    if _is_market_validation_plan_question(question_detail):
        return _has_market_validation_plan_answer(answer)
    if _is_tech_product_scope_question(schema_paths):
        return _has_tech_product_scope_answer(answer)
    if _is_tech_complexity_debt_question(question_detail, schema_paths):
        return _has_tech_complexity_debt_answer(answer)
    if _is_tech_reliability_testing_question(question_detail, schema_paths):
        return _has_tech_reliability_testing_answer(answer)
    if _is_tech_slo_incident_question(question_detail, schema_paths):
        return _has_tech_slo_incident_answer(answer)
    if _is_tech_infra_devops_question(question_detail, schema_paths):
        return _has_tech_infra_devops_answer(answer)
    if _is_tech_dependencies_question(question_detail, schema_paths):
        return len(_extract_key_integrations_value(answer)) >= 2
    if _is_tech_roadmap_risks_question(question_detail, schema_paths):
        return len(_extract_top_technical_risks_value(answer)) >= 2
    if _is_tech_mvp_boundary_question(
        schema_paths
    ) or is_tech_mvp_boundary_prompt_question(question_detail):
        return _has_tech_mvp_boundary_answer(answer)
    if _is_tech_data_access_question(schema_paths):
        return _has_tech_data_access_answer(answer)
    if _is_tech_data_scalability_prompt_question(
        question_detail
    ) or _is_tech_data_scalability_question(schema_paths):
        return _has_tech_data_scalability_answer(answer)
    if _is_tech_journey_components_question(schema_paths):
        return _has_tech_journey_components_answer(schema_paths, answer)
    if _is_tech_sensitive_data_question(schema_paths):
        return _has_tech_sensitive_data_answer(answer)
    if _is_tech_ai_quality_question(schema_paths):
        return _has_tech_ai_quality_answer(answer)
    if _is_tech_compliance_plan_prompt_question(
        question_detail
    ) or _is_tech_compliance_plan_question(schema_paths):
        return _has_tech_compliance_plan_answer(answer)
    if _is_idea_snapshot_question(question_detail):
        return _looks_like_idea_snapshot_answer(answer)
    if gate_result and gate_result.verdict == "fail":
        return False
    if _is_top_problem_question(question_detail):
        return _looks_like_top_problems_answer(answer)
    if (
        len(schema_paths) == 1
        and len(answer.strip()) >= 20
        and not _has_explicit_none(answer)
    ):
        return True
    return False




FIELD_FALLBACK_HELPERS = PreviewFieldFallbackHelpers(
    is_non_empty=_is_non_empty,
    has_explicit_none=_has_explicit_none,
    first_non_empty_string=_first_non_empty_string,
    extract_primary_line=_extract_primary_line,
    is_target_user_question=_is_target_user_question,
    extract_target_user_value=_extract_target_user_value,
    is_severity_question=_is_severity_question,
    extract_severity_score=_extract_severity_score,
    extract_severity_reason=_extract_severity_reason,
    is_time_money_impact_question=_is_time_money_impact_question,
    extract_time_impact_value=_extract_time_impact_value,
    extract_money_impact_value=_extract_money_impact_value,
    is_alternatives_question=_is_alternatives_question,
    extract_current_solutions_value=_extract_current_solutions_value,
    extract_satisfaction_score=_extract_satisfaction_score,
    extract_main_complaints_value=_extract_main_complaints_value,
    is_evidence_validation_question=_is_evidence_validation_question,
    extract_user_interview_count_value=_extract_user_interview_count_value,
    extract_key_learnings_value=_extract_key_learnings_value,
    extract_data_evidence_value=_extract_data_evidence_value,
    extract_key_unknowns_value=_extract_key_unknowns_value,
    is_market_business_model_question=_is_market_business_model_question,
    extract_payer_role_value=_extract_payer_role_value,
    extract_revenue_model_value=_extract_revenue_model_value,
    is_market_competition_question=_is_market_competition_question,
    extract_competitor_types_value=_extract_competitor_types_value,
    extract_named_competitors_value=_extract_named_competitors_value,
    extract_positioning_summary_value=_extract_positioning_summary_value,
    extract_competitive_red_flags_value=_extract_competitive_red_flags_value,
    is_market_gtm_question=_is_market_gtm_question,
    extract_primary_channels_value=_extract_primary_channels_value,
    is_market_moat_question=_is_market_moat_question,
    extract_unfair_advantage_value=_extract_unfair_advantage_value,
    extract_long_term_moat_value=_extract_long_term_moat_value,
    extract_switching_costs_value=_extract_switching_costs_value,
    extract_big_tech_response_risk_value=_extract_big_tech_response_risk_value,
    is_tech_mvp_boundary_question=_is_tech_mvp_boundary_question,
    extract_current_status_value=_extract_current_status_value,
    extract_mvp_definition_value=_extract_mvp_definition_value,
    extract_non_functional_priorities_value=_extract_non_functional_priorities_value,
    is_tech_data_access_question=_is_tech_data_access_question,
    extract_data_access_rights_value=_extract_data_access_rights_value,
    extract_key_integrations_value=_extract_key_integrations_value,
    extract_top_technical_risks_value=_extract_top_technical_risks_value,
    extract_risk_mitigation_plan_value=_extract_risk_mitigation_plan_value,
    is_tech_data_scalability_question=_is_tech_data_scalability_question,
    extract_data_sources_value=_extract_data_sources_value,
    extract_data_volume_year1_value=_extract_data_volume_year1_value,
    extract_growth_expectations_value=_extract_growth_expectations_value,
    extract_ai_usage_value=_extract_ai_usage_value,
    extract_performance_expectations_value=_extract_performance_expectations_value,
    extract_scalability_strategy_value=_extract_scalability_strategy_value,
    is_tech_journey_components_question=_is_tech_journey_components_question,
    extract_core_user_journeys_value=_extract_core_user_journeys_value,
    extract_high_level_components_value=_extract_high_level_components_value,
    is_tech_sensitive_data_question=_is_tech_sensitive_data_question,
    extract_sensitive_data_types_value=_extract_sensitive_data_types_value,
    extract_sensitive_compliance_value=_extract_sensitive_compliance_value,
    is_tech_ai_quality_question=_is_tech_ai_quality_question,
    extract_ai_quality_metrics_value=_extract_ai_quality_metrics_value,
    extract_ai_monitoring_value=_extract_ai_monitoring_value,
    extract_ai_guardrails_value=_extract_ai_guardrails_value,
    is_tech_compliance_plan_question=_is_tech_compliance_plan_question,
    extract_compliance_requirements_value=_extract_compliance_requirements_value,
    extract_compliance_milestone_value=_extract_compliance_milestone_value,
    extract_data_retention_policy_value=_extract_data_retention_policy_value,
)


def _apply_extraction_fallbacks(
    schema_paths: list[str],
    remapped: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    return apply_preview_field_fallbacks(
        schema_paths,
        remapped,
        answer,
        helpers=FIELD_FALLBACK_HELPERS,
    )


def infer_frequency_from_answer(answer: str) -> str | None:
    return infer_problem_frequency_from_answer(answer)


def update_ai_assisted_paths(
    state_meta: dict[str, Any],
    resolved_paths: list[str],
    current_stage: str | None,
    ai_assisted: bool,
) -> None:
    if not resolved_paths or not current_stage:
        return
    ai_map = {
        stage: set(paths)
        for stage, paths in normalize_ai_assisted_map(state_meta).items()
    }
    for path in resolved_paths:
        stage = _infer_path_stage(path, current_stage).strip().lower()
        if not stage:
            continue
        if stage not in ai_map:
            ai_map[stage] = set()
        if ai_assisted:
            ai_map[stage].add(path)
        else:
            ai_map[stage].discard(path)
    cleaned_map = {stage: sorted(paths) for stage, paths in ai_map.items() if paths}
    if cleaned_map:
        state_meta["ai_assisted_paths"] = cleaned_map
    elif "ai_assisted_paths" in state_meta:
        state_meta.pop("ai_assisted_paths", None)


def prepare_extraction_updates(
    question_detail: dict,
    extracted: dict[str, Any],
    current_stage: str,
    answer: str,
) -> tuple[list[str], list[tuple[str, str, Any]]]:
    schema_paths = question_detail.get("schema_paths") or []
    if not schema_paths:
        return [], []
    remapped = _remap_extracted(
        extracted,
        schema_paths,
        canonicalize_value=canonicalize_extracted_value,
    )
    remapped = _apply_extraction_fallbacks(schema_paths, remapped, answer)
    if _has_explicit_none(answer):
        for path in schema_paths:
            if path.endswith("data_evidence") and not _is_non_empty(remapped.get(path)):
                remapped[path] = "None yet"
    return _build_extraction_targets(
        remapped,
        current_stage,
        canonicalize_value=canonicalize_extracted_value,
    )


def apply_extraction_updates_to_state(
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
    extraction_updates: list[tuple[str, str, Any]],
    *,
    current_stage: str | None,
    resolved_paths: list[str] | None = None,
    ai_assisted: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    next_state_json = deepcopy(state_json) if isinstance(state_json, dict) else {}
    next_state_meta = deepcopy(state_meta) if isinstance(state_meta, dict) else {}
    pending_confirm = next_state_meta.get("pending_confirm")
    if not isinstance(pending_confirm, dict):
        pending_confirm = {}

    for target, path, value in extraction_updates:
        default_source = "ai" if ai_assisted or target == "pending" else "user"
        value, meta_update = _extract_value_meta(value, default_source=default_source)
        value = canonicalize_extracted_value(path, value)
        if target == "state":
            _set_path(next_state_json, path, value)
            set_answer_meta_entry(
                next_state_meta,
                path,
                **meta_update,
            )
        else:
            _set_path(pending_confirm, path, {"value": value, **meta_update})

    next_state_meta["pending_confirm"] = pending_confirm
    update_ai_assisted_paths(
        next_state_meta,
        list(resolved_paths or []),
        current_stage,
        ai_assisted,
    )
    backfill_problem_idea_raw(
        next_state_json,
        next_state_meta,
        source="ai" if ai_assisted else "user",
    )
    canonicalize_market_type_fields(next_state_json)
    return next_state_json, next_state_meta


def build_sync_extraction_preview(
    question_detail: dict,
    extracted_payload: dict[str, Any],
    *,
    current_stage: str,
    answer: str,
    latest_answer: str | None = None,
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
    ai_assisted: bool = False,
) -> tuple[list[str], list[tuple[str, str, Any]], dict[str, Any], dict[str, Any]]:
    resolved_paths, extraction_updates = prepare_extraction_updates(
        question_detail,
        extracted_payload,
        current_stage,
        answer,
    )
    schema_paths = question_detail.get("schema_paths") or []
    if (
        schema_paths
        and isinstance(latest_answer, str)
        and latest_answer.strip()
        and latest_answer.strip() != answer.strip()
    ):
        unresolved_paths = {
            path for path in schema_paths if path not in set(resolved_paths)
        }
        if unresolved_paths:
            fallback_resolved_paths, fallback_updates = prepare_extraction_updates(
                question_detail,
                {},
                current_stage,
                latest_answer,
            )
            for path in fallback_resolved_paths:
                if path not in resolved_paths:
                    resolved_paths.append(path)
            existing_update_paths = {
                path for _target, path, _value in extraction_updates
            }
            for update in fallback_updates:
                _target, path, _value = update
                if path in unresolved_paths and path not in existing_update_paths:
                    extraction_updates.append(update)
                    existing_update_paths.add(path)
    next_state_json, next_state_meta = apply_extraction_updates_to_state(
        state_json,
        state_meta,
        extraction_updates,
        current_stage=current_stage,
        resolved_paths=resolved_paths,
        ai_assisted=ai_assisted,
    )
    if question_detail.get("question_id") == "L3Q1":
        boundary_answer = answer
        if (
            not _has_tech_mvp_boundary_answer(boundary_answer)
            and isinstance(latest_answer, str)
            and latest_answer.strip()
        ):
            boundary_answer = latest_answer
        fallback_values = {
            "tech_execution.product_scope.current_status": _extract_current_status_value(
                boundary_answer
            ),
            "tech_execution.product_scope.mvp_definition": _extract_mvp_definition_value(
                boundary_answer
            ),
        }
        apply_mvp_boundary_preview_fallbacks(
            fallback_values,
            resolved_paths=resolved_paths,
            extraction_updates=extraction_updates,
            next_state_json=next_state_json,
            next_state_meta=next_state_meta,
            ai_assisted=ai_assisted,
        )
    if question_detail.get("question_id") == "S1Q5":
        apply_problem_frequency_preview_fallback(
            answer,
            resolved_paths=resolved_paths,
            extraction_updates=extraction_updates,
            next_state_json=next_state_json,
            next_state_meta=next_state_meta,
            ai_assisted=ai_assisted,
        )
    canonicalize_market_type_fields(next_state_json)
    return resolved_paths, extraction_updates, next_state_json, next_state_meta
