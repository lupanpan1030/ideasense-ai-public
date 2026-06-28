from __future__ import annotations

from app.services.extraction_text_heuristics import _is_time_money_impact_question


def is_top_problem_question(question_detail: dict) -> bool:
    schema_paths = question_detail.get("schema_paths") or []
    if "problem.main_problems[]" in schema_paths:
        return True
    if question_detail.get("question_id") == "S1Q2":
        return True
    return False


def is_idea_snapshot_question(question_detail: dict) -> bool:
    schema_paths = question_detail.get("schema_paths") or []
    if question_detail.get("question_id") == "S1Q1":
        return True
    if "problem_user.idea.raw" in schema_paths:
        return True
    prompt = question_detail.get("prompt")
    return isinstance(prompt, str) and "describe your idea" in prompt.lower()


def is_severity_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {"problem.severity_score", "problem.severity_reason"}.issubset(path_set)


def is_time_money_impact_question(schema_paths: list[str]) -> bool:
    return _is_time_money_impact_question(schema_paths)


def is_alternatives_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    if "alternatives.current_solutions[]" in path_set:
        return True
    return {
        "alternatives.current_solutions[]",
        "alternatives.satisfaction_score",
        "alternatives.main_complaints[]",
    }.issubset(path_set)


def is_evidence_validation_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "evidence.user_interview_count",
        "evidence.key_learnings[]",
        "evidence.data_evidence",
        "evidence.key_unknowns[]",
    }.issubset(path_set)


def is_problem_scenarios_question(schema_paths: list[str]) -> bool:
    return "problem.scenarios[]" in set(schema_paths)


def is_market_business_model_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return {
        "market_strategy.business_model.payer_role",
        "market_strategy.business_model.revenue_model",
    }.issubset(path_set)


def is_market_competition_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return (
        "market_strategy.competition.competitor_types[]" in path_set
        or "market_strategy.competition.competitor_types" in path_set
    )


def is_market_gtm_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return (
        "market_strategy.go_to_market.primary_channels[]" in path_set
        or "market_strategy.go_to_market.primary_channels" in path_set
    )


def question_id_or_prompt_matches(
    question_detail: dict,
    question_id: str,
    patterns: tuple[str, ...],
) -> bool:
    if question_detail.get("question_id") == question_id:
        return True
    prompt_parts = (
        question_detail.get("prompt"),
        question_detail.get("standard_question"),
        question_detail.get("instruction"),
    )
    prompt = " ".join(part for part in prompt_parts if isinstance(part, str)).lower()
    return any(pattern in prompt for pattern in patterns)


def is_market_launch_segment_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S2Q4",
        ("initial launch segment", "estimated annual revenue", "why now"),
    )


def is_market_unit_economics_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S2Q7",
        ("unit economics", "cac", "ltv", "payback"),
    )


def is_market_validation_plan_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S2Q8",
        ("must-be-true", "validation signals", "early validation plan"),
    )


def is_market_competition_prompt_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S2Q5",
        ("competitor types", "named alternatives", "positioning", "red flags"),
    )


def is_market_moat_prompt_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S2Q2",
        ("unfair advantage", "long-term moat", "switching costs", "incumbent"),
    )


def is_tech_mvp_boundary_prompt_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "L3Q1",
        ("where is your product today", "not in mvp", "in-mvp"),
    )


def is_tech_complexity_debt_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    path_set = set(schema_paths)
    return (
        "tech_execution.architecture.complexity_hotspots" in path_set
        or "tech_execution.architecture.tech_debt_strategy" in path_set
        or question_id_or_prompt_matches(
            question_detail,
            "S3Q4",
            ("complexity hotspots", "technical debt", "strict from day one"),
        )
    )


def is_tech_infra_devops_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    path_set = set(schema_paths)
    return bool(
        {
            "tech_execution.infra_devops.hosting_choice",
            "tech_execution.infra_devops.environments",
            "tech_execution.infra_devops.ci_cd",
            "tech_execution.infra_devops.deploy_frequency",
            "tech_execution.infra_devops.monitoring_alerts",
            "tech_execution.infra_devops.backup_dr_plan",
        }
        & path_set
    ) or question_id_or_prompt_matches(
        question_detail,
        "S3Q6",
        ("infra/devops", "hosting choice", "ci/cd", "backup/dr"),
    )


def is_tech_dependencies_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    return "tech_execution.dependencies.key_integrations" in set(
        schema_paths
    ) or question_id_or_prompt_matches(
        question_detail,
        "S3Q8",
        ("key integrations", "vendor lock-in", "dependencies"),
    )


def is_tech_reliability_testing_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    path_set = set(schema_paths)
    return bool(
        {
            "tech_execution.infra_devops.reliability_targets",
            "tech_execution.infra_devops.testing_strategy",
            "tech_execution.infra_devops.release_strategy",
        }
        & path_set
    ) or question_id_or_prompt_matches(
        question_detail,
        "S3Q12",
        ("reliability/uptime", "testing strategy", "release/rollback"),
    )


def is_tech_slo_incident_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    path_set = set(schema_paths)
    return bool(
        {
            "tech_execution.infra_devops.slo_targets",
            "tech_execution.infra_devops.failover_strategy",
            "tech_execution.infra_devops.incident_response",
        }
        & path_set
    ) or question_id_or_prompt_matches(
        question_detail,
        "S3Q14",
        ("slo", "sla", "failover", "incident response"),
    )


def is_tech_roadmap_risks_question(
    question_detail: dict,
    schema_paths: list[str],
) -> bool:
    path_set = set(schema_paths)
    return (
        "tech_execution.roadmap_risks.top_technical_risks" in path_set
        or "tech_execution.roadmap_risks.risk_mitigation_plan" in path_set
    ) or question_id_or_prompt_matches(
        question_detail,
        "S3Q9",
        ("top technical risks", "mitigation", "technical roadmap"),
    )


def is_tech_data_scalability_prompt_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S3Q5",
        ("data sources", "year-1 data volume", "10x scaling"),
    )


def is_tech_mvp_boundary_question(schema_paths: list[str]) -> bool:
    return "tech_execution.product_scope.mvp_definition" in set(schema_paths)


def is_tech_compliance_plan_prompt_question(question_detail: dict) -> bool:
    return question_id_or_prompt_matches(
        question_detail,
        "S3Q13",
        ("audits/certs", "certifications/audits", "retention policy"),
    )


def is_tech_sensitive_data_question(schema_paths: list[str]) -> bool:
    path_set = set(schema_paths)
    return "tech_execution.security_compliance.data_types" in path_set
