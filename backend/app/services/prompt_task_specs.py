"""Canonical prompt task metadata for the IdeaSense prompt runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


STAGE_SUMMARY_TIMEOUT_MS = 60000


class PromptMutationClass(str, Enum):
    """State mutation boundary for model output."""

    NONE = "none"
    VISIBLE_COPY_ONLY = "visible_copy_only"
    DECISION_ONLY = "decision_only"
    VALIDATED_CONTEXT_UPDATE = "validated_context_update"
    REPORT_ARTIFACT = "report_artifact"
    USAGE_ONLY = "usage_only"


@dataclass(frozen=True)
class PromptTaskSpec:
    task_key: str
    system_template: str | None
    user_template: str | None
    provider_task: str
    temperature: float = 0.0
    timeout_ms: int | None = None
    timeout_env: str | None = None
    response_format: str | None = None
    output_contract: str | None = None
    parse_strategy: str = "text"
    fallback_policy: str = "none"
    allowed_mutation: PromptMutationClass = PromptMutationClass.NONE
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()
    trace_redaction: tuple[str, ...] = ("raw_prompt", "raw_variables")
    call_sites: tuple[str, ...] = ()
    phase: str = "planned"


DEFAULT_PROMPT_TASK_SPECS: tuple[PromptTaskSpec, ...] = (
    PromptTaskSpec(
        task_key="answer_gate",
        system_template="chat/answer_gate_system",
        user_template="chat/answer_gate_user",
        provider_task="answer_gate",
        timeout_ms=3000,
        timeout_env="ANSWER_GATE_TIMEOUT_MS",
        response_format="json_object",
        output_contract="answer_gate_json",
        parse_strategy="answer_gate_json",
        fallback_policy="skip_gate_and_use_backend_followup",
        allowed_mutation=PromptMutationClass.DECISION_ONLY,
        required_sections=(
            "stage_question_contract",
            "schema_paths",
            "latest_answer",
        ),
        optional_sections=("expected_key_points", "project_context"),
        call_sites=("backend/app/api/routes/chat.py:_run_answer_gate",),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="extract",
        system_template="shared/extraction_system",
        user_template="shared/extraction_user",
        provider_task="extract",
        timeout_ms=2500,
        timeout_env="SYNC_EXTRACT_TIMEOUT_MS",
        response_format="json_object",
        output_contract="schema_path_json",
        parse_strategy="schema_path_json",
        fallback_policy="skip_sync_extraction",
        allowed_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        required_sections=("schema_paths", "latest_answer"),
        call_sites=(
            "backend/app/api/routes/chat.py:_run_answer_extraction",
            "backend/app/services/answer_extraction_worker_handler.py:_extract_with_openai",
        ),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="question_compose",
        system_template="chat/question_compose_system",
        user_template="chat/question_compose_user",
        provider_task="question_compose",
        temperature=0.35,
        timeout_ms=3500,
        timeout_env="QUESTION_COMPOSE_START_TIMEOUT_MS",
        fallback_policy="persist_backend_selected_question",
        allowed_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        required_sections=(
            "output_locale",
            "latest_answer",
            "selected_question",
            "stage_question_contract",
            "schema_paths",
        ),
        optional_sections=("project_context", "expected_key_points"),
        call_sites=("backend/app/api/routes/chat.py:_build_question_stream_context",),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="followup_compose",
        system_template="chat/followup_compose_system",
        user_template="chat/followup_compose_user",
        provider_task="followup_compose",
        temperature=0.3,
        timeout_ms=3500,
        timeout_env="QUESTION_COMPOSE_START_TIMEOUT_MS",
        fallback_policy="persist_backend_followup_message",
        allowed_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        required_sections=(
            "output_locale",
            "selected_question",
            "latest_answer",
            "gate_decision",
            "backend_fallback",
            "stage_question_contract",
            "schema_paths",
        ),
        optional_sections=("project_context", "expected_key_points"),
        call_sites=("backend/app/api/routes/chat.py:_build_followup_stream_context",),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="question_plan",
        system_template="chat/question_plan_system",
        user_template="chat/question_plan_user",
        provider_task="question_rewrite",
        temperature=0.2,
        timeout_ms=1000,
        timeout_env="QUESTION_PLANNER_TIMEOUT_MS",
        response_format="json_object",
        output_contract="question_plan_json",
        parse_strategy="question_plan_json",
        fallback_policy="use_stage_engine_default_question",
        allowed_mutation=PromptMutationClass.DECISION_ONLY,
        required_sections=(
            "output_locale",
            "missing_paths",
            "candidate_questions",
            "planner_limits",
        ),
        optional_sections=("latest_answer",),
        call_sites=(
            "backend/app/services/chat_question_planning.py:resolve_question_group_plan",
        ),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="question_rewrite_chat",
        system_template="chat/question_rewrite_system",
        user_template="shared/question_rewrite_user",
        provider_task="question_rewrite",
        temperature=0.3,
        response_format="json_object",
        output_contract="question_rewrite_json",
        parse_strategy="question_rewrite_json",
        fallback_policy="use_original_question_text",
        allowed_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        required_sections=(
            "output_locale",
            "selected_question",
            "stage_question_contract",
            "schema_paths",
        ),
        call_sites=(
            "backend/app/services/project_question_prompts.py:run_chat_question_rewrite",
        ),
        phase="chat_migrated",
    ),
    PromptTaskSpec(
        task_key="question_rewrite_basic",
        system_template="shared/question_rewrite_system_basic",
        user_template="shared/question_rewrite_user",
        provider_task="question_rewrite",
        temperature=0.3,
        response_format="json_object",
        output_contract="question_rewrite_json",
        parse_strategy="question_rewrite_json",
        fallback_policy="use_original_question_text",
        allowed_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        required_sections=(
            "output_locale",
            "selected_question",
            "stage_question_contract",
            "schema_paths",
        ),
        call_sites=(
            "backend/app/services/project_question_prompts.py:run_question_rewrite",
        ),
    ),
    PromptTaskSpec(
        task_key="ai_assist",
        system_template="chat/ai_assist_system",
        user_template="chat/ai_assist_user",
        provider_task="ai_assist",
        temperature=0.2,
        fallback_policy="no_ai_draft",
        allowed_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        required_sections=(
            "output_locale",
            "selected_question",
            "output_constraints",
        ),
        optional_sections=("stage_question_contract", "project_context"),
        call_sites=(
            "backend/app/api/routes/chat.py:_run_ai_assist_draft",
            "backend/app/api/routes/chat.py:_run_ai_assist_draft_stream",
        ),
    ),
    PromptTaskSpec(
        task_key="qa_digest",
        system_template="shared/qa_digest_summary_system",
        user_template="shared/qa_digest_summary_user",
        provider_task="qa_digest",
        temperature=0.2,
        fallback_policy="derive_summary_from_key_points",
        allowed_mutation=PromptMutationClass.NONE,
        required_sections=("output_locale", "qa_digest_input"),
        call_sites=("backend/app/services/qa_digests.py:generate_answer_summary",),
    ),
    PromptTaskSpec(
        task_key="stage_summary_problem",
        system_template="report/stage_summary_problem_system",
        user_template="report/stage_summary_problem_user",
        provider_task="stage_summary",
        timeout_ms=STAGE_SUMMARY_TIMEOUT_MS,
        timeout_env="STAGE_SUMMARY_TIMEOUT_MS",
        fallback_policy="fail_stage_summary_generation",
        allowed_mutation=PromptMutationClass.REPORT_ARTIFACT,
        required_sections=("output_locale", "report_input"),
        call_sites=(
            "backend/app/services/stage_summary_worker_handler.py:generate_stage_summary_v0",
        ),
        phase="report_migrated",
    ),
    PromptTaskSpec(
        task_key="stage_summary_market",
        system_template="report/stage_summary_market_system",
        user_template="report/stage_summary_market_user",
        provider_task="stage_summary",
        timeout_ms=STAGE_SUMMARY_TIMEOUT_MS,
        timeout_env="STAGE_SUMMARY_TIMEOUT_MS",
        fallback_policy="fail_stage_summary_generation",
        allowed_mutation=PromptMutationClass.REPORT_ARTIFACT,
        required_sections=("output_locale", "report_input"),
        call_sites=(
            "backend/app/services/stage_summary_worker_handler.py:generate_stage_summary_v0",
        ),
        phase="report_migrated",
    ),
    PromptTaskSpec(
        task_key="stage_summary_tech",
        system_template="report/stage_summary_tech_system",
        user_template="report/stage_summary_tech_user",
        provider_task="stage_summary",
        timeout_ms=STAGE_SUMMARY_TIMEOUT_MS,
        timeout_env="STAGE_SUMMARY_TIMEOUT_MS",
        fallback_policy="fail_stage_summary_generation",
        allowed_mutation=PromptMutationClass.REPORT_ARTIFACT,
        required_sections=("output_locale", "report_input"),
        call_sites=(
            "backend/app/services/stage_summary_worker_handler.py:generate_stage_summary_v0",
        ),
        phase="report_migrated",
    ),
    PromptTaskSpec(
        task_key="project_description",
        system_template="report/project_description_system",
        user_template="report/project_description_user",
        provider_task="stage_summary",
        temperature=0.2,
        fallback_policy="skip_auto_description",
        allowed_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        required_sections=("output_locale", "report_input"),
        optional_sections=("project_title", "stage_summary"),
        call_sites=(
            "backend/app/services/stage_finalize_worker_handler.py:_generate_project_description_v0",
        ),
    ),
    PromptTaskSpec(
        task_key="dvf_scoring",
        system_template="report/dvf_scoring_system",
        user_template="report/dvf_scoring_user",
        provider_task="dvf_scoring",
        temperature=0.2,
        response_format="json_object",
        output_contract="dvf_json",
        parse_strategy="dvf_json",
        timeout_ms=45000,
        timeout_env="DVF_SCORING_TIMEOUT_MS",
        fallback_policy="skip_dvf_payload",
        allowed_mutation=PromptMutationClass.REPORT_ARTIFACT,
        required_sections=("output_locale", "report_input", "output_constraints"),
        call_sites=("backend/app/services/scoring/dvf_scoring.py:generate_dvf_scoring",),
        phase="report_migrated",
    ),
    PromptTaskSpec(
        task_key="final_report",
        system_template="report/final_report_system",
        user_template="report/final_report_user",
        provider_task="report",
        temperature=0.2,
        response_format="json_object",
        output_contract="final_report_json",
        parse_strategy="final_report_json",
        timeout_ms=60000,
        timeout_env="FINAL_REPORT_TIMEOUT_MS",
        fallback_policy="skip_structured_report",
        allowed_mutation=PromptMutationClass.REPORT_ARTIFACT,
        required_sections=("output_locale", "report_input", "output_constraints"),
        call_sites=(
            "backend/app/services/report_generation_worker_handler.py:_generate_structured_report_v0",
            "backend/app/services/report_prompt_tasks.py:build_report_prompt",
        ),
        phase="report_migrated",
    ),
    PromptTaskSpec(
        task_key="claim_verification",
        system_template="shared/claim_verification_system",
        user_template="shared/claim_verification_user",
        provider_task="report",
        response_format="json_object",
        output_contract="claim_verification_json",
        parse_strategy="claim_verification_json",
        fallback_policy="return_uncertain_verdict",
        allowed_mutation=PromptMutationClass.NONE,
        required_sections=("verification_input",),
        call_sites=("backend/app/services/verification/judge.py:_judge_claim",),
    ),
)


__all__ = [
    "DEFAULT_PROMPT_TASK_SPECS",
    "PromptMutationClass",
    "PromptTaskSpec",
    "STAGE_SUMMARY_TIMEOUT_MS",
]
