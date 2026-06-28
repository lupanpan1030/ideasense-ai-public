#!/usr/bin/env python3
"""Low-noise architecture checks for duplicate paths and owner drift."""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_METHODS = {"delete", "get", "patch", "post", "put"}
OWNERSHIP_MAP = REPO_ROOT / "docs" / "OWNERSHIP_MAP.md"
BACKEND_APP_ROOT = REPO_ROOT / "backend" / "app"
FRONTEND_APP_ROOT = REPO_ROOT / "frontend" / "app"
LEGACY_ADMIN_COMPONENTS_ROOT = REPO_ROOT / "frontend" / "components" / "admin"
INCLUDE_ROUTER_OWNERS = {
    "backend/app/main.py",
    "backend/app/api/routes/__init__.py",
}
CHAT_ROUTE = REPO_ROOT / "backend" / "app" / "api" / "routes" / "chat.py"
ASSESSMENTS_ROUTE = REPO_ROOT / "backend" / "app" / "api" / "routes" / "assessments.py"
REPORT_BUILDER = REPO_ROOT / "backend" / "app" / "core" / "report_builder.py"
REPORT_SECTIONS = REPO_ROOT / "backend" / "app" / "core" / "report_sections.py"
ANSWER_EXTRACTION_WORKER_HANDLER = (
    REPO_ROOT / "backend" / "app" / "services" / "answer_extraction_worker_handler.py"
)
PROMPT_TEMPLATE_CREATE_ROUTE_OWNERS = {
    REPO_ROOT / "backend" / "app" / "api" / "routes" / "admin_prompt_templates.py": (
        "create_prompt_template"
    ),
    REPO_ROOT / "backend" / "app" / "api" / "routes" / "platform_admin.py": (
        "create_global_prompt_template"
    ),
}
QUESTION_BANK_DRAFT_CREATE_ROUTE_OWNERS = {
    REPO_ROOT / "backend" / "app" / "api" / "routes" / "admin_question_banks.py": (
        "create_draft"
    ),
}
QUESTION_BANK_DRAFT_IMPORT_ROUTE_OWNERS = {
    REPO_ROOT / "backend" / "app" / "api" / "routes" / "admin_question_banks.py": (
        "import_draft",
        "import_draft_json",
    ),
}
QUESTION_BANK_PUBLISH_ROUTE_OWNERS = {
    REPO_ROOT / "backend" / "app" / "api" / "routes" / "admin_question_banks.py": (
        "publish_draft"
    ),
}
CHAT_ROUTE_FORBIDDEN_BACKGROUND_JOB_REFERENCES = {
    "ANSWER_EXTRACTION_JOB_TYPE": "Use app.services.chat_background_jobs instead.",
    "enqueue_authoritative_answer_extraction_job": "Use app.services.chat_background_jobs instead.",
    "enqueue_answer_question_verification_job": "Use app.services.chat_background_jobs instead.",
    "extract_verification_priority": "Use app.services.chat_background_jobs instead.",
    "priority_at_least": "Use app.services.chat_background_jobs instead.",
    "verification_enabled": "Use app.services.chat_background_jobs instead.",
    "verification_min_priority": "Use app.services.chat_background_jobs instead.",
}
CHAT_ROUTE_FORBIDDEN_SYNC_PREVIEW_DEFINITIONS = {
    "_apply_extraction_fallbacks": (
        "Use app.services.chat_sync_extraction_preview instead."
    ),
    "_apply_extraction_updates_to_state": (
        "Use app.services.chat_sync_extraction_preview.apply_extraction_updates_to_state instead."
    ),
    "_build_sync_extraction_preview": (
        "Use app.services.chat_sync_extraction_preview.build_sync_extraction_preview instead."
    ),
    "_canonicalize_market_type_fields": (
        "Use app.services.chat_market_type_normalization.canonicalize_market_type_fields instead."
    ),
    "_infer_frequency_from_answer": (
        "Use app.services.chat_sync_extraction_preview.infer_frequency_from_answer instead."
    ),
    "_prepare_extraction_updates": (
        "Use app.services.chat_sync_extraction_preview.prepare_extraction_updates instead."
    ),
    "_should_soft_pass": (
        "Use app.services.chat_sync_extraction_preview.should_soft_pass_answer instead."
    ),
    "_update_ai_assisted_paths": (
        "Use app.services.chat_sync_extraction_preview.update_ai_assisted_paths instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_QUESTION_PLANNING_DEFINITIONS = {
    "_apply_group_override": (
        "Use app.services.chat_question_planning.apply_group_override instead."
    ),
    "_apply_transition_prefix": (
        "Use app.services.chat_question_planning.apply_transition_prefix instead."
    ),
    "_build_group_prompt": "Use app.services.chat_question_planning instead.",
    "_build_question_group_payload": (
        "Use app.services.chat_question_planning.build_question_group_payload instead."
    ),
    "_build_question_meta_payload": (
        "Use app.services.chat_question_planning.build_question_meta_payload instead."
    ),
    "_build_question_plan_context": (
        "Use app.services.chat_question_planning instead."
    ),
    "_build_transition_text": "Use app.services.chat_question_planning instead.",
    "_fetch_group_meta": (
        "Use app.services.chat_question_planning.fetch_group_meta instead."
    ),
    "_fetch_question_planner_candidates": (
        "Use app.services.chat_question_planning.fetch_question_planner_candidates instead."
    ),
    "_format_candidate_list": "Use app.services.chat_question_planning instead.",
    "_merge_group_details": "Use app.services.chat_question_planning instead.",
    "_merge_group_strings": "Use app.services.chat_question_planning instead.",
    "_normalize_planner_selection": (
        "Use app.services.chat_question_planning instead."
    ),
    "_persist_question_plan": (
        "Use app.services.chat_question_planning.persist_question_plan instead."
    ),
    "_planner_stage_allowed": "Use app.services.chat_question_planning instead.",
    "_question_has_missing_paths": (
        "Use app.services.chat_question_planning.question_has_missing_paths instead."
    ),
    "_question_overlaps_only_deferred_paths": (
        "Use app.services.chat_question_planning.question_overlaps_only_deferred_paths instead."
    ),
    "_question_schema_paths": (
        "Use app.services.chat_question_planning.question_schema_paths instead."
    ),
    "_question_supports_grouping": (
        "Use app.services.chat_question_planning.question_supports_grouping instead."
    ),
    "_resolve_question_group": (
        "Use app.services.chat_question_planning.resolve_question_group instead."
    ),
    "_resolve_question_group_plan": (
        "Use app.services.chat_question_planning.resolve_question_group_plan instead."
    ),
    "_should_attempt_question_planner": (
        "Use app.services.chat_question_planning.should_attempt_question_planner instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_FOLLOWUP_COMPOSE_DEFINITIONS = {
    "_apply_repeated_followup_cap": (
        "Use app.services.chat_followup_compose.apply_repeated_followup_cap instead."
    ),
    "_build_followup_compose_context": (
        "Use app.services.chat_followup_compose.build_followup_compose_context instead."
    ),
    "_build_followup_compose_prompt": (
        "Use app.services.chat_followup_compose.build_followup_compose_prompt instead."
    ),
    "_build_followup_message": (
        "Use app.services.chat_followup_compose.build_followup_message instead."
    ),
    "_build_followup_stream_context": (
        "Use app.services.chat_followup_compose.build_followup_stream_context instead."
    ),
    "_build_gate_decision": (
        "Use app.services.chat_followup_compose.build_gate_decision instead."
    ),
    "_build_question_compose_context": (
        "Use app.services.chat_followup_compose.build_question_compose_context instead."
    ),
    "_build_question_compose_prompt": (
        "Use app.services.chat_followup_compose.build_question_compose_prompt instead."
    ),
    "_build_question_stream_context": (
        "Use app.services.chat_followup_compose.build_question_stream_context instead."
    ),
    "_focus_followup_on_unresolved_paths": (
        "Use app.services.chat_followup_compose.focus_followup_on_unresolved_paths instead."
    ),
    "_is_internal_prompt_line": (
        "Use app.services.chat_followup_compose.is_internal_prompt_line instead."
    ),
    "_sanitize_composed_question": (
        "Use app.services.chat_followup_compose.sanitize_composed_question instead."
    ),
    "_sanitize_rewritten_prompt": (
        "Use app.services.chat_followup_compose.sanitize_rewritten_prompt instead."
    ),
    "_select_fallback_followup": (
        "Use app.services.chat_followup_compose.select_fallback_followup instead."
    ),
    "_select_followup_answer_pattern": (
        "Use app.services.chat_followup_compose.select_followup_answer_pattern instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_QUESTION_FILTER_DEFINITIONS = {
    "_adjust_missing_paths_for_market": (
        "Use app.services.chat_question_filters.adjust_missing_paths_for_market instead."
    ),
    "_contains_keywords": (
        "Use app.services.chat_question_filters.contains_keywords instead."
    ),
    "_filter_missing_paths_by_state": (
        "Use app.services.chat_question_filters.filter_missing_paths_by_state instead."
    ),
    "_has_meaningful_value": (
        "Use app.services.chat_question_filters.has_meaningful_value instead."
    ),
    "_infer_market_type": (
        "Use app.services.chat_question_filters.infer_market_type instead."
    ),
    "_is_ai_data_triggered": (
        "Use app.services.chat_question_filters.is_ai_data_triggered instead."
    ),
    "_is_compliance_triggered": (
        "Use app.services.chat_question_filters.is_compliance_triggered instead."
    ),
    "_is_conditional_question": (
        "Use app.services.chat_question_filters.is_conditional_question instead."
    ),
    "_is_high_reliability_triggered": (
        "Use app.services.chat_question_filters.is_high_reliability_triggered instead."
    ),
    "_is_optional_question": (
        "Use app.services.chat_question_filters.is_optional_question instead."
    ),
    "_is_required_question": (
        "Use app.services.chat_question_filters.is_required_question instead."
    ),
    "_normalize_market_text": (
        "Use app.services.chat_question_filters.normalize_market_text instead."
    ),
    "_normalize_market_type": (
        "Use app.services.chat_question_filters.normalize_market_type instead."
    ),
    "_path_has_value": (
        "Use app.services.chat_question_filters.path_has_value instead."
    ),
    "_question_market_lock": (
        "Use app.services.chat_question_filters.question_market_lock instead."
    ),
    "_question_triggers": (
        "Use app.services.chat_question_filters.question_triggers instead."
    ),
    "_should_skip_non_required_question": (
        "Use app.services.chat_question_filters.should_skip_non_required_question instead."
    ),
    "_triggers_active": (
        "Use app.services.chat_question_filters.triggers_active instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_AI_ASSIST_DEFINITIONS = {
    "_ai_draft_message_parts": (
        "Use app.services.chat_ai_assist.ai_draft_message_parts instead."
    ),
    "_ai_draft_unavailable_message": (
        "Use app.services.chat_ai_assist.ai_draft_unavailable_message instead."
    ),
    "_build_ai_assist_context": (
        "Use app.services.chat_ai_assist.build_ai_assist_context instead."
    ),
    "_build_answer_text_from_history": (
        "Use app.services.chat_ai_assist.build_answer_text_from_history instead."
    ),
    "_format_ai_draft_message": (
        "Use app.services.chat_ai_assist.format_ai_draft_message instead."
    ),
    "_has_substantive_answer": (
        "Use app.services.chat_ai_assist.has_substantive_answer instead."
    ),
    "_is_ai_assist_request": (
        "Use app.services.chat_ai_assist.is_ai_assist_request instead."
    ),
    "_is_ai_draft_tagged": (
        "Use app.services.chat_ai_assist.is_ai_draft_tagged instead."
    ),
    "_mark_ai_draft_requested": (
        "Use app.services.chat_ai_assist.mark_ai_draft_requested instead."
    ),
    "_persist_ai_draft_message": (
        "Use app.services.chat_ai_assist.persist_ai_draft_message instead."
    ),
    "_requires_single_sentence": (
        "Use app.services.chat_ai_assist.requires_single_sentence instead."
    ),
    "_run_ai_assist_draft": (
        "Use app.services.chat_ai_assist.run_ai_assist_draft instead."
    ),
    "_run_ai_assist_draft_stream": (
        "Use app.services.chat_ai_assist.run_ai_assist_draft_stream instead."
    ),
    "_strip_ai_draft_prefix": (
        "Use app.services.chat_ai_assist.strip_ai_draft_prefix instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_TURN_PREFLIGHT_DEFINITIONS = {
    "_build_chat_gate_context": (
        "Use app.services.chat_turn_preflight.build_chat_gate_context instead."
    ),
    "_insert_chat_user_message": (
        "Use app.services.chat_turn_preflight.insert_chat_user_message instead."
    ),
    "build_chat_gate_context": (
        "Use app.services.chat_turn_preflight.build_chat_gate_context instead."
    ),
    "insert_chat_user_message": (
        "Use app.services.chat_turn_preflight.insert_chat_user_message instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_TURN_CONTEXT_DEFINITIONS = {
    "_build_assistant_meta": (
        "Use app.services.chat_turn_context.build_assistant_meta instead."
    ),
    "_build_gate_context_summary": (
        "Use app.services.chat_turn_context.build_gate_context_summary instead."
    ),
    "_collect_key_points": (
        "Use app.services.chat_turn_context.collect_key_points instead."
    ),
    "_normalize_context_value": (
        "Use app.services.chat_turn_context.normalize_context_value instead."
    ),
    "_select_extraction_answer": (
        "Use app.services.chat_turn_context.select_extraction_answer instead."
    ),
    "_select_gate_answer": (
        "Use app.services.chat_turn_context.select_gate_answer instead."
    ),
    "_truncate_context_value": (
        "Use app.services.chat_turn_context.truncate_context_value instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_CONTEXT_READ_DEFINITIONS = {
    "_fetch_chat_answer_history": (
        "Use app.services.chat_context_reads.fetch_chat_answer_history instead."
    ),
    "_fetch_chat_question_detail_context": (
        "Use app.services.chat_context_reads.fetch_chat_question_detail_context instead."
    ),
    "_fetch_chat_state_context": (
        "Use app.services.chat_context_reads.fetch_chat_state_context instead."
    ),
    "_fetch_context_meta": (
        "Use app.services.chat_context_reads.fetch_context_meta instead."
    ),
    "_set_chat_session_context": (
        "Use app.services.chat_context_reads.set_chat_session_context instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_MESSAGE_PERSISTENCE_DEFINITIONS = {
    "_persist_fallback_question_message": (
        "Use app.services.chat_stream.message_persistence.persist_fallback_question_message instead."
    ),
    "_stream_question_response_events": (
        "Use app.services.chat_stream.question_response.stream_question_response_events instead."
    ),
    "_update_streamed_question_message": (
        "Use app.services.chat_stream.message_persistence.update_streamed_question_message instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_QUESTION_RUNTIME_DEFINITIONS = {
    "_ensure_question_instance": (
        "Use app.services.chat_question_runtime.ensure_question_instance instead."
    ),
    "_fetch_question_detail": (
        "Use app.services.chat_question_runtime.fetch_chat_question_detail instead."
    ),
    "_plan_question_prompt": (
        "Use app.services.chat_question_runtime.plan_question_prompt instead."
    ),
    "_resolve_answer_rubric_id": (
        "Use app.services.chat_question_runtime.resolve_answer_rubric_id instead."
    ),
    "_resolve_askable_question_id": (
        "Use app.services.chat_question_runtime.resolve_askable_question_id instead."
    ),
    "_resolve_initial_questions": (
        "Use app.services.chat_question_runtime.resolve_initial_questions instead."
    ),
    "_resolve_missing_paths": (
        "Use app.services.chat_question_runtime.resolve_missing_paths instead."
    ),
    "_resolve_next_question_id": (
        "Use app.services.chat_question_runtime.resolve_next_question_id instead."
    ),
    "_resolve_repair_question": (
        "Use app.services.chat_question_runtime.resolve_repair_question instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_GATE_RESOLUTION_DEFINITIONS = {
    "_mark_partial_unknown_paths": (
        "Use app.services.chat_gate_resolution.mark_partial_unknown_paths instead."
    ),
    "_resolve_gate_and_sync_extraction": (
        "Use app.services.chat_gate_resolution.resolve_gate_and_sync_extraction instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_TURN_EVALUATION_DEFINITIONS = {
    "_evaluate_chat_turn": (
        "Use app.services.chat_turn_evaluation.evaluate_chat_turn instead."
    ),
    "evaluate_chat_turn": (
        "Use app.services.chat_turn_evaluation.evaluate_chat_turn instead."
    ),
}
CHAT_ROUTE_FORBIDDEN_TURN_COMMIT_DEFINITIONS = {
    "_apply_chat_state_updates": (
        "Use app.services.chat_turn_commit.apply_chat_state_updates instead."
    ),
    "_build_answer_scores_payload": (
        "Use app.services.chat_turn_payloads.build_answer_scores_payload instead."
    ),
    "_commit_answer_status": (
        "Use app.services.chat_turn_commit.commit_answer_status instead."
    ),
    "_commit_needs_info_turn": (
        "Use app.services.chat_turn_commit.commit_needs_info_turn instead."
    ),
    "_commit_router_mode_next_turn": (
        "Use app.services.chat_turn_commit.commit_router_mode_next_turn instead."
    ),
    "_commit_standard_next_turn": (
        "Use app.services.chat_turn_commit.commit_standard_next_turn instead."
    ),
    "_commit_stage_transition_turn": (
        "Use app.services.chat_turn_commit.commit_stage_transition_turn instead."
    ),
    "_update_runtime_metadata_after_answer": (
        "Use app.services.chat_turn_commit.update_runtime_metadata_after_answer instead."
    ),
    "commit_answer_status": (
        "Use app.services.chat_turn_commit.commit_answer_status instead."
    ),
    "apply_chat_state_updates": (
        "Use app.services.chat_turn_commit.apply_chat_state_updates instead."
    ),
    "build_answer_scores_payload": (
        "Use app.services.chat_turn_payloads.build_answer_scores_payload instead."
    ),
    "commit_needs_info_turn": (
        "Use app.services.chat_turn_commit.commit_needs_info_turn instead."
    ),
    "commit_router_mode_next_turn": (
        "Use app.services.chat_turn_commit.commit_router_mode_next_turn instead."
    ),
    "commit_standard_next_turn": (
        "Use app.services.chat_turn_commit.commit_standard_next_turn instead."
    ),
    "commit_stage_transition_turn": (
        "Use app.services.chat_turn_commit.commit_stage_transition_turn instead."
    ),
    "update_runtime_metadata_after_answer": (
        "Use app.services.chat_turn_commit.update_runtime_metadata_after_answer instead."
    ),
    "_insert_answer_evaluation": (
        "Use app.services.chat_turn_commit.insert_answer_evaluation instead."
    ),
    "insert_answer_evaluation": (
        "Use app.services.chat_turn_commit.insert_answer_evaluation instead."
    ),
}
ANSWER_EXTRACTION_WORKER_FORBIDDEN_FALLBACK_DEFINITIONS = {
    "_apply_extraction_fallbacks": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_ai_usage_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_compliance_requirements_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_current_status_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_data_sources_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_data_volume_year1_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_mvp_definition_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_primary_line": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
    "_extract_sensitive_data_types_value": (
        "Use app.services.answer_extraction_worker_fallbacks instead."
    ),
}
ANSWER_EXTRACTION_WORKER_FORBIDDEN_MARKET_DEFINITIONS = {
    "MARKET_TYPE_ENUM_PATHS": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "PATH_EQUIVALENTS": "Use app.services.answer_extraction_worker_market instead.",
    "_adjust_missing_paths_for_market": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_canonicalize_extracted_value": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_canonicalize_market_type_fields": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_filter_missing_paths_by_state": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_infer_market_type": "Use app.services.answer_extraction_worker_market instead.",
    "_infer_market_type_enum_from_state": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_normalize_market_text": (
        "Use app.services.answer_extraction_worker_market instead."
    ),
    "_path_has_value": "Use app.services.answer_extraction_worker_market instead.",
}
ASSESSMENTS_ROUTE_FORBIDDEN_PROMPT_EXEC_REFERENCES = {
    "execute_prompt_task": "Use assessment worker/service prompt owners instead.",
    "PromptContextBuilder": "Use assessment worker/service prompt owners instead.",
    "PromptMutationClass": "Use assessment worker/service prompt owners instead.",
    "render_prompt_messages": "Use assessment worker/service prompt owners instead.",
}
REPORT_BUILDER_FORBIDDEN_PROMPT_RUNTIME_REFERENCES = {
    "execute_prompt_task": "Use service-owned report prompt/runtime task modules instead.",
    "PromptContextBuilder": "Use app.services.report_prompt_tasks instead.",
    "render_prompt_messages": "Use app.services.report_prompt_tasks instead.",
}
PROMPT_TEMPLATE_CREATE_ROUTE_FORBIDDEN_WRITES = {
    "INSERT INTO prompt_templates": (
        "Use app.services.prompt_templates.create_prompt_template_revision instead."
    ),
    "UPDATE prompt_templates": (
        "Use app.services.prompt_templates.create_prompt_template_revision instead."
    ),
}
QUESTION_BANK_DRAFT_CREATE_ROUTE_FORBIDDEN_WRITES = {
    "INSERT INTO question_bank_versions": (
        "Use app.services.question_bank_drafts.create_question_bank_draft instead."
    ),
    "INSERT INTO question_bank_questions": (
        "Use app.services.question_bank_drafts.create_question_bank_draft instead."
    ),
    "UPDATE question_bank_versions": (
        "Use app.services.question_bank_drafts.create_question_bank_draft instead."
    ),
}
QUESTION_BANK_DRAFT_IMPORT_ROUTE_FORBIDDEN_WRITES = {
    "INSERT INTO question_bank_versions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
    "UPDATE question_bank_versions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
    "DELETE FROM question_bank_versions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
    "INSERT INTO question_bank_questions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
    "UPDATE question_bank_questions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
    "DELETE FROM question_bank_questions": (
        "Use app.services.question_bank_draft_imports instead."
    ),
}
QUESTION_BANK_PUBLISH_ROUTE_FORBIDDEN_WRITES = {
    "INSERT INTO question_bank_versions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
    "UPDATE question_bank_versions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
    "DELETE FROM question_bank_versions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
    "INSERT INTO question_bank_questions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
    "UPDATE question_bank_questions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
    "DELETE FROM question_bank_questions": (
        "Use app.services.question_bank_publish.publish_question_bank_draft instead."
    ),
}

PYTHON_SINGLE_OWNER = {
    "PromptContextBuilder": "backend/app/services/prompt_context_builders.py",
    "PromptMutationClass": "backend/app/services/prompt_task_specs.py",
    "PromptTaskSpec": "backend/app/services/prompt_task_specs.py",
    "PreviewFieldFallbackHelpers": "backend/app/services/chat_sync_preview_field_fallbacks.py",
    "ConversationListResponse": "backend/app/schemas/projects.py",
    "ConversationMessage": "backend/app/schemas/projects.py",
    "ConfirmedStagePersistenceResult": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "DevLoginRequest": "backend/app/schemas/auth.py",
    "LoginRequest": "backend/app/schemas/auth.py",
    "PasswordResetConfirmRequest": "backend/app/schemas/auth.py",
    "PasswordResetRequest": "backend/app/schemas/auth.py",
    "PasswordResetResponse": "backend/app/schemas/auth.py",
    "OrgListResponse": "backend/app/schemas/platform_admin.py",
    "OrgSummary": "backend/app/schemas/platform_admin.py",
    "OrgUpdateRequest": "backend/app/schemas/platform_admin.py",
    "PlatformAdminItem": "backend/app/schemas/platform_admin.py",
    "PlatformAdminListResponse": "backend/app/schemas/platform_admin.py",
    "PlatformAdminUpsertRequest": "backend/app/schemas/platform_admin.py",
    "PlatformSettingEntry": "backend/app/schemas/platform_admin.py",
    "PlatformSettingsResponse": "backend/app/schemas/platform_admin.py",
    "PlatformSettingsUpdateRequest": "backend/app/schemas/platform_admin.py",
    "ProjectActionResponse": "backend/app/schemas/projects.py",
    "ProjectContextResponse": "backend/app/schemas/projects.py",
    "ProjectCreateRequest": "backend/app/schemas/projects.py",
    "ProjectCreateResponse": "backend/app/schemas/projects.py",
    "ProjectDetailResponse": "backend/app/schemas/projects.py",
    "ProjectPendingConfirmResolveRequest": "backend/app/schemas/projects.py",
    "ProjectPendingConfirmResponse": "backend/app/schemas/projects.py",
    "ProjectPendingConfirmUpdateRequest": "backend/app/schemas/projects.py",
    "ProjectQuestionInstance": "backend/app/schemas/projects.py",
    "ProjectRecord": "backend/app/schemas/projects.py",
    "ProjectReportResponse": "backend/app/schemas/projects.py",
    "ProjectReportStatusResponse": "backend/app/schemas/projects.py",
    "ProjectRuntimeRecord": "backend/app/schemas/projects.py",
    "ProjectVerificationResponse": "backend/app/schemas/assessments.py",
    "ProjectsListResponse": "backend/app/schemas/projects.py",
    "RegisterRequest": "backend/app/schemas/auth.py",
    "ReportQualityInvariantCount": "backend/app/schemas/platform_admin.py",
    "ReportQualityObservationDetail": "backend/app/schemas/platform_admin.py",
    "ReportQualityObservationItem": "backend/app/schemas/platform_admin.py",
    "ReportQualityObservationListResponse": (
        "backend/app/schemas/platform_admin.py"
    ),
    "ReportQualityStatusCount": "backend/app/schemas/platform_admin.py",
    "ReportQualitySummaryResponse": "backend/app/schemas/platform_admin.py",
    "ResendVerificationRequest": "backend/app/schemas/auth.py",
    "ResendVerificationResponse": "backend/app/schemas/auth.py",
    "StageConfirmRequest": "backend/app/schemas/assessments.py",
    "StageConfirmResponse": "backend/app/schemas/assessments.py",
    "StageDraftResponse": "backend/app/schemas/assessments.py",
    "StageConfirmationCommitResult": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "StageConfirmationConflictError": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "StageConfirmationNotFoundError": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "StageConfirmationPermissionError": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "StageConfirmationRuntimeError": (
        "backend/app/services/stage_confirmation_types.py"
    ),
    "StageQuestionVerification": "backend/app/schemas/assessments.py",
    "StageSummariesResponse": "backend/app/schemas/assessments.py",
    "StageSummaryItem": "backend/app/schemas/assessments.py",
    "StageVerificationSummary": "backend/app/schemas/assessments.py",
    "PreparedStageConfirmation": "backend/app/services/stage_confirmation_types.py",
    "TokenResponse": "backend/app/schemas/auth.py",
    "VerificationRefreshResponse": "backend/app/schemas/assessments.py",
    "VerificationSource": "backend/app/schemas/assessments.py",
    "VerifyEmailRequest": "backend/app/schemas/auth.py",
    "VerifyEmailResponse": "backend/app/schemas/auth.py",
    "adjust_answer_extraction_market_missing_paths": "backend/app/services/answer_extraction_worker_market.py",
    "assessment_summary_by_stage": "backend/app/core/report_sections.py",
    "build_report_prompt": "backend/app/services/report_prompt_tasks.py",
    "build_report_recovery_sections": "backend/app/core/report_recovery_sections.py",
    "build_invite_link": "backend/app/services/org_invite_links.py",
    "require_verified_system_actor": "backend/app/api/deps.py",
    "resolve_app_base_url": "backend/app/services/org_invite_links.py",
    "resolve_verified_org_context": "backend/app/api/deps.py",
    "set_system_rls_context": "backend/app/api/deps.py",
    "_apply_authoritative_extraction_updates": "backend/app/services/answer_extraction_worker_handler.py",
    "_clean_extracted_text_items": "backend/app/services/extraction_text_heuristics.py",
    "_clip_target_user_value": "backend/app/services/extraction_text_heuristics.py",
    "_clip_value_before_labels": "backend/app/services/extraction_text_heuristics.py",
    "_extract_ai_guardrails_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_ai_monitoring_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_ai_quality_metrics_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_big_tech_response_risk_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_competitive_red_flags_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_competitor_types_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_compliance_milestone_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_core_user_journeys_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_data_access_rights_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_data_retention_policy_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_high_level_components_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_key_integrations_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_labeled_answer_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_labeled_impact_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_long_term_moat_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_money_impact_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_named_competitors_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_non_functional_priorities_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_positioning_summary_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_risk_mitigation_plan_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_switching_costs_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_target_user_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_time_impact_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_top_technical_risks_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_unfair_advantage_value": "backend/app/services/extraction_text_heuristics.py",
    "_extract_with_openai": "backend/app/services/answer_extraction_worker_handler.py",
    "_first_non_empty_string": "backend/app/services/extraction_text_heuristics.py",
    "_has_money_impact_answer": "backend/app/services/extraction_text_heuristics.py",
    "_has_time_impact_answer": "backend/app/services/extraction_text_heuristics.py",
    "_is_market_moat_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_target_user_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_time_money_impact_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_ai_quality_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_compliance_plan_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_data_access_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_data_scalability_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_journey_components_question": "backend/app/services/extraction_text_heuristics.py",
    "_is_tech_product_scope_question": "backend/app/services/extraction_text_heuristics.py",
    "_should_skip_authoritative_extract_mutation": "backend/app/services/answer_extraction_worker_handler.py",
    "_strip_list_prefix": "backend/app/services/extraction_text_heuristics.py",
    "_worker_job_handlers": "backend/app/worker.py",
    "ai_draft_message_parts": "backend/app/services/chat_ai_assist.py",
    "ai_draft_unavailable_message": "backend/app/services/chat_ai_assist.py",
    "adjust_missing_paths_for_market": "backend/app/services/chat_question_filters.py",
    "answer_extraction_job_idempotency_key": "backend/app/services/answer_extraction_jobs.py",
    "apply_chat_state_updates": "backend/app/services/chat_turn_commit.py",
    "apply_chat_state_patch": "backend/app/services/chat_turn_commit_shapers.py",
    "apply_repeated_followup_cap": "backend/app/services/chat_followup_compose.py",
    "answer_verification_job_idempotency_key": "backend/app/services/verification_jobs.py",
    "apply_group_override": "backend/app/services/chat_question_planning.py",
    "apply_extraction_updates_to_state": "backend/app/services/chat_sync_extraction_preview.py",
    "apply_mvp_boundary_preview_fallbacks": "backend/app/services/chat_sync_preview_post_fallbacks.py",
    "apply_preview_field_fallbacks": "backend/app/services/chat_sync_preview_field_fallbacks.py",
    "apply_problem_frequency_preview_fallback": "backend/app/services/chat_sync_preview_post_fallbacks.py",
    "apply_transition_prefix": "backend/app/services/chat_question_planning.py",
    "apply_router_mode_selection_guard": "backend/app/services/chat_router_mode.py",
    "background_job_sort_time": "backend/app/services/background_jobs.py",
    "build_chat_status_payload": "backend/app/services/chat_stream/events.py",
    "build_admin_overview_payload": "backend/app/services/admin_overview.py",
    "build_admin_overview_activity_feed": (
        "backend/app/services/admin_overview_activity.py"
    ),
    "build_chat_gate_context": "backend/app/services/chat_turn_preflight.py",
    "build_confirmed_stage_artifact_payload": (
        "backend/app/services/stage_confirmation_persistence_payloads.py"
    ),
    "build_needs_info_assistant_meta": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_next_question_assistant_meta": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_next_question_turn_result": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_state_event_patch": "backend/app/services/chat_turn_commit_shapers.py",
    "build_sync_extraction_preview": "backend/app/services/chat_sync_extraction_preview.py",
    "build_qa_digests_from_messages": "backend/app/services/qa_digests.py",
    "build_answer_extraction_queued_payload": "backend/app/services/chat_background_jobs.py",
    "build_answer_scores_payload": "backend/app/services/chat_turn_payloads.py",
    "build_answer_text_from_history": "backend/app/services/chat_ai_assist.py",
    "build_ai_assist_context": "backend/app/services/chat_ai_assist.py",
    "build_assistant_meta": "backend/app/services/chat_turn_context.py",
    "build_extraction_targets": "backend/app/services/extraction_transforms.py",
    "build_gate_context_summary": "backend/app/services/chat_turn_context.py",
    "build_question_group_payload": "backend/app/services/chat_question_planning.py",
    "build_question_meta_payload": "backend/app/services/chat_question_planning.py",
    "build_quality_observation_filters": (
        "backend/app/services/platform_report_quality.py"
    ),
    "build_question_rewrite_prompt": "backend/app/services/project_question_prompts.py",
    "build_queued_report_job_status": "backend/app/services/report_jobs.py",
    "build_ready_report_job_status": "backend/app/services/report_jobs.py",
    "build_report_v2_sections": "backend/app/core/report_sections.py",
    "build_skip_decision": "backend/app/services/chat_answer_actions.py",
    "build_schema_key_map": "backend/app/services/extraction_transforms.py",
    "build_skip_answer_status_meta": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_stage_gate_ready_payload": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_stage_transition_assistant_meta": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_stream_error_payload": "backend/app/services/chat_stream/events.py",
    "build_streamed_question_message_meta": "backend/app/services/chat_stream/events.py",
    "build_stage_payload": "backend/app/services/stage_payloads.py",
    "build_stage_question_meta_payload": "backend/app/services/stage_question_setup.py",
    "build_stage_summary_fallback": "backend/app/services/stage_summary_fallbacks.py",
    "build_turn_event_meta": "backend/app/services/chat_stream/events.py",
    "build_router_mode_state_event_patch": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "build_router_mode_selection_followup": "backend/app/services/chat_router_mode.py",
    "can_reuse_stage_draft_cache": "backend/app/services/stage_drafts.py",
    "can_mutate_project": "backend/app/services/project_permissions.py",
    "canonicalize_extracted_value": "backend/app/services/chat_market_type_normalization.py",
    "canonicalize_market_type_fields": "backend/app/services/chat_market_type_normalization.py",
    "canonicalize_market_type_value": "backend/app/services/chat_market_type_normalization.py",
    "claim_verdict_counts": "backend/app/services/stage_verifications.py",
    "collect_key_points": "backend/app/services/chat_turn_context.py",
    "collect_strings": "backend/app/services/chat_market_type_normalization.py",
    "commit_answer_status": "backend/app/services/chat_turn_commit.py",
    "commit_needs_info_turn": "backend/app/services/chat_turn_commit.py",
    "commit_router_mode_next_turn": "backend/app/services/chat_turn_commit.py",
    "commit_standard_next_turn": "backend/app/services/chat_turn_commit.py",
    "commit_stage_transition_turn": "backend/app/services/chat_turn_commit.py",
    "derive_updated_runtime_missing_paths": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "update_runtime_metadata_after_answer": "backend/app/services/chat_turn_commit.py",
    "collect_sources_from_claims": "backend/app/services/stage_verifications.py",
    "collect_stage_summary_items": "backend/app/services/stage_summary_fallbacks.py",
    "compact_report_text": "backend/app/core/report_sections.py",
    "commit_prepared_stage_confirmation_workflow": "backend/app/services/stage_confirmations.py",
    "commit_stage_confirmation_workflow": "backend/app/services/stage_confirmations.py",
    "confirm_project_report_stage_workflow": "backend/app/services/report_confirmations.py",
    "confirm_report_stage_workflow": "backend/app/services/report_confirmations.py",
    "confirm_password_reset_workflow": "backend/app/services/auth_password_reset.py",
    "create_question_bank_draft": "backend/app/services/question_bank_drafts.py",
    "create_prompt_template_revision": "backend/app/services/prompt_templates.py",
    "create_project_records": "backend/app/services/project_creation.py",
    "create_project_workflow": "backend/app/services/project_creation.py",
    "derive_answer_summary": "backend/app/services/qa_digests.py",
    "register_local_user": "backend/app/services/auth_registration.py",
    "resend_email_verification_workflow": (
        "backend/app/services/auth_email_verification.py"
    ),
    "dev_login_local_user": "backend/app/services/auth_login.py",
    "login_local_user": "backend/app/services/auth_login.py",
    "request_password_reset_workflow": "backend/app/services/auth_password_reset.py",
    "import_question_bank_draft_json": "backend/app/services/question_bank_draft_imports.py",
    "import_question_bank_draft_yaml": "backend/app/services/question_bank_draft_imports.py",
    "apply_pending_confirm_updates": "backend/app/services/pending_confirms.py",
    "fetch_project_conversation_list": "backend/app/services/project_conversations.py",
    "fetch_project_context": "backend/app/services/project_contexts.py",
    "fetch_project_detail": "backend/app/services/project_details.py",
    "fetch_project_list": "backend/app/services/project_listings.py",
    "fetch_project_pending_confirm": "backend/app/services/pending_confirms.py",
    "fetch_project_report_payload": "backend/app/services/project_reports.py",
    "fetch_project_stage_verification_read_models": "backend/app/services/assessment_summaries.py",
    "fetch_group_meta": "backend/app/services/chat_question_planning.py",
    "fetch_report_last_user_message": "backend/app/services/report_conversation_sources.py",
    "fetch_report_quality_summary_payload": (
        "backend/app/services/platform_report_quality.py"
    ),
    "fetch_question_detail": "backend/app/services/project_question_prompts.py",
    "fetch_question_planner_candidates": "backend/app/services/chat_question_planning.py",
    "fetch_report_confirmation_recovery_report": "backend/app/services/report_confirmations.py",
    "fetch_report_confirmation_project_row": "backend/app/services/report_confirmations.py",
    "fetch_stage_summary_read_models": "backend/app/services/assessment_summaries.py",
    "fetch_stage_draft_project_row": "backend/app/services/stage_drafts.py",
    "fetch_stage_question_detail": "backend/app/services/stage_question_setup.py",
    "normalize_stage_state_snapshot": (
        "backend/app/services/stage_confirmation_preparation.py"
    ),
    "resolve_stage_confirmation_defaults": (
        "backend/app/services/stage_confirmation_preparation.py"
    ),
    "extract_stage_prompt_task_traces": (
        "backend/app/services/stage_confirmation_preparation.py"
    ),
    "build_prepared_stage_confirmation_payload": (
        "backend/app/services/stage_confirmation_preparation.py"
    ),
    "fetch_chat_answer_history": "backend/app/services/chat_context_reads.py",
    "fetch_chat_question_detail_context": "backend/app/services/chat_context_reads.py",
    "fetch_chat_state_context": "backend/app/services/chat_context_reads.py",
    "fetch_chat_question_detail": "backend/app/services/chat_question_runtime.py",
    "fetch_context_meta": "backend/app/services/chat_context_reads.py",
    "ensure_project_report_access": "backend/app/services/project_report_access.py",
    "ensure_project_report_access_gate": (
        "backend/app/services/project_report_access.py"
    ),
    "extract_answer_action": "backend/app/services/chat_output_locale.py",
    "infer_frequency_from_answer": "backend/app/services/chat_sync_extraction_preview.py",
    "infer_problem_frequency_from_answer": "backend/app/services/chat_sync_preview_post_fallbacks.py",
    "infer_market_type_enum_from_state": "backend/app/services/chat_market_type_normalization.py",
    "extract_mode_from_state": "backend/app/services/chat_router_mode.py",
    "extract_router_mode_from_message_meta": "backend/app/services/chat_router_mode.py",
    "extract_router_mode_from_text": "backend/app/services/chat_router_mode.py",
    "_format_delta_counts": "backend/app/services/admin_overview_formatters.py",
    "_format_delta_rate": "backend/app/services/admin_overview_formatters.py",
    "_format_period_change": "backend/app/services/admin_overview_formatters.py",
    "extract_skip_reason": "backend/app/services/chat_answer_actions.py",
    "fallback_decision_band": "backend/app/core/report_sections.py",
    "fallback_dimension_score": "backend/app/core/report_sections.py",
    "filter_missing_paths_by_state": "backend/app/services/chat_question_filters.py",
    "format_ai_draft_message": "backend/app/services/chat_ai_assist.py",
    "focus_followup_on_unresolved_paths": "backend/app/services/chat_followup_compose.py",
    "followup_compose_enabled": "backend/app/services/chat_runtime_settings.py",
    "infer_market_type": "backend/app/services/chat_question_filters.py",
    "is_stage_gate_ready_for_review": "backend/app/services/chat_stage_gate.py",
    "is_required_question": "backend/app/services/chat_question_filters.py",
    "is_optional_question": "backend/app/services/chat_question_filters.py",
    "is_conditional_question": "backend/app/services/chat_question_filters.py",
    "is_compliance_triggered": "backend/app/services/chat_question_filters.py",
    "is_ai_data_triggered": "backend/app/services/chat_question_filters.py",
    "is_high_reliability_triggered": "backend/app/services/chat_question_filters.py",
    "soft_delete_project": "backend/app/services/project_mutations.py",
    "enqueue_answer_question_verification_job": "backend/app/services/verification_jobs.py",
    "enqueue_background_job": "backend/app/services/background_jobs.py",
    "enqueue_authoritative_answer_extraction_job": "backend/app/services/answer_extraction_jobs.py",
    "enqueue_chat_pass_background_jobs": "backend/app/services/chat_background_jobs.py",
    "enqueue_summary_question_verification_job": "backend/app/services/verification_jobs.py",
    "ensure_question_instance": "backend/app/services/chat_question_runtime.py",
    "evaluate_chat_turn": "backend/app/services/chat_turn_evaluation.py",
    "execution_trace": "backend/app/services/prompt_runtime_execution.py",
    "failure_result": "backend/app/services/prompt_runtime_execution.py",
    "canonicalize_extraction_update_value": "backend/app/services/extraction_transforms.py",
    "extract_value_meta": "backend/app/services/extraction_transforms.py",
    "get_context_path_value": "backend/app/services/context_paths.py",
    "get_report_quality_observation_payload": (
        "backend/app/services/platform_report_quality.py"
    ),
    "build_platform_settings_payload": "backend/app/services/platform_settings.py",
    "build_platform_org_filters": "backend/app/services/platform_orgs.py",
    "fetch_platform_settings_payload": "backend/app/services/platform_settings.py",
    "fetch_platform_orgs_payload": "backend/app/services/platform_orgs.py",
    "get_nested_state_value": "backend/app/services/extraction_transforms.py",
    "flatten_extraction_payload": "backend/app/services/extraction_transforms.py",
    "generate_answer_summary": "backend/app/services/qa_digests.py",
    "has_substantive_answer": "backend/app/services/chat_ai_assist.py",
    "has_explicit_none": "backend/app/services/extraction_transforms.py",
    "increment_verification_summary": "backend/app/services/stage_verifications.py",
    "insert_answer_evaluation": "backend/app/services/chat_turn_commit.py",
    "insert_chat_user_message": "backend/app/services/chat_turn_preflight.py",
    "list_report_quality_observation_payloads": (
        "backend/app/services/platform_report_quality.py"
    ),
    "list_platform_admin_payloads": "backend/app/services/platform_admin_users.py",
    "list_active_global_prompt_template_payloads": (
        "backend/app/services/prompt_templates.py"
    ),
    "normalize_project_state_payload": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "initialize_stage_confirmation_runtime": "backend/app/services/stage_confirmations.py",
    "infer_context_path_stage": "backend/app/services/context_paths.py",
    "is_ai_assist_request": "backend/app/services/chat_ai_assist.py",
    "is_ai_draft_tagged": "backend/app/services/chat_ai_assist.py",
    "is_alternatives_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_evidence_validation_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_idea_snapshot_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_business_model_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_competition_prompt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_competition_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_gtm_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_launch_segment_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_moat_prompt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_unit_economics_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_market_validation_plan_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_non_empty": "backend/app/services/extraction_transforms.py",
    "is_not_applicable_rationale": "backend/app/services/stage_verifications.py",
    "is_problem_scenarios_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_quick_action_answer": "backend/app/services/chat_output_locale.py",
    "is_severity_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_complexity_debt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_compliance_plan_prompt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_data_scalability_prompt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_dependencies_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_infra_devops_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_mvp_boundary_prompt_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_mvp_boundary_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_reliability_testing_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_roadmap_risks_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_sensitive_data_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_tech_slo_incident_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_time_money_impact_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "is_top_problem_question": "backend/app/services/chat_sync_preview_question_matchers.py",
    "looks_like_history_reference": "backend/app/services/chat_sync_preview_problem_parsers.py",
    "latency_span": "backend/app/services/chat_stream/latency.py",
    "log_chat_stream_latency": "backend/app/services/chat_stream/latency.py",
    "mark_partial_unknown_paths": "backend/app/services/chat_gate_resolution.py",
    "mark_ai_draft_requested": "backend/app/services/chat_ai_assist.py",
    "maybe_localize_latest_question_prompt": "backend/app/services/project_conversations.py",
    "normalize_conversation_cursor": "backend/app/services/project_conversations.py",
    "normalize_ai_assisted_map": "backend/app/services/stage_payloads.py",
    "normalize_extraction_key": "backend/app/services/extraction_transforms.py",
    "normalize_background_job_status": "backend/app/services/background_jobs.py",
    "normalize_context_value": "backend/app/services/chat_turn_context.py",
    "normalize_report_value": "backend/app/core/report_sections.py",
    "normalize_market_type": "backend/app/services/chat_question_filters.py",
    "normalize_market_text": "backend/app/services/chat_question_filters.py",
    "persist_question_plan": "backend/app/services/chat_question_planning.py",
    "persist_fallback_question_message": "backend/app/services/chat_stream/message_persistence.py",
    "plan_question_prompt": "backend/app/services/chat_question_runtime.py",
    "parse_csv_set": "backend/app/services/chat_runtime_settings.py",
    "prepare_extraction_updates": "backend/app/services/chat_sync_extraction_preview.py",
    "parse_env_flag": "backend/app/services/chat_runtime_settings.py",
    "normalize_pending_confirm": "backend/app/services/pending_confirms.py",
    "normalize_pending_confirm_resolve_paths": (
        "backend/app/services/pending_confirms.py"
    ),
    "normalize_pending_confirm_updates": "backend/app/services/pending_confirms.py",
    "normalize_question_bank_key": "backend/app/services/question_bank_drafts.py",
    "normalize_project_creation_input": "backend/app/services/project_creation.py",
    "normalize_project_list_filters": "backend/app/services/project_listings.py",
    "normalize_quality_status": "backend/app/services/platform_report_quality.py",
    "normalize_setting_key": "backend/app/services/platform_settings.py",
    "normalize_router_mode": "backend/app/services/chat_router_mode.py",
    "normalize_user_edited_map": "backend/app/services/stage_payloads.py",
    "persist_ai_draft_message": "backend/app/services/chat_ai_assist.py",
    "persist_confirmed_stage_assessment": "backend/app/services/stage_confirmations.py",
    "pop_context_path_value": "backend/app/services/context_paths.py",
    "prepare_project_stage_draft_workflow": "backend/app/services/stage_drafts.py",
    "prepare_stage_draft_workflow": "backend/app/services/stage_drafts.py",
    "prepare_stage_confirmation_workflow": "backend/app/services/stage_confirmations.py",
    "preparation_failure_result": "backend/app/services/prompt_runtime_execution.py",
    "prompt_template_row_to_payload": "backend/app/services/prompt_templates.py",
    "publish_question_bank_draft": "backend/app/services/question_bank_publish.py",
    "question_id_or_prompt_matches": "backend/app/services/chat_sync_preview_question_matchers.py",
    "build_followup_compose_context": "backend/app/services/chat_followup_compose.py",
    "build_followup_compose_prompt": "backend/app/services/chat_followup_compose.py",
    "build_followup_message": "backend/app/services/chat_followup_compose.py",
    "build_followup_stream_context": "backend/app/services/chat_followup_compose.py",
    "build_gate_decision": "backend/app/services/chat_followup_compose.py",
    "build_question_compose_context": "backend/app/services/chat_followup_compose.py",
    "build_question_compose_prompt": "backend/app/services/chat_followup_compose.py",
    "build_question_stream_context": "backend/app/services/chat_followup_compose.py",
    "question_compose_enabled": "backend/app/services/chat_runtime_settings.py",
    "question_has_missing_paths": "backend/app/services/chat_question_planning.py",
    "question_market_lock": "backend/app/services/chat_question_filters.py",
    "question_overlaps_only_deferred_paths": "backend/app/services/chat_question_planning.py",
    "question_schema_paths": "backend/app/services/chat_question_planning.py",
    "question_supports_grouping": "backend/app/services/chat_question_planning.py",
    "question_triggers": "backend/app/services/chat_question_filters.py",
    "requeue_question_verification_job": "backend/app/services/verification_jobs.py",
    "refresh_project_stage_verification_workflow": "backend/app/services/verification_refresh.py",
    "record_latency_span": "backend/app/services/chat_stream/latency.py",
    "record_project_state_event": "backend/app/services/project_state_events.py",
    "remap_extracted": "backend/app/services/extraction_transforms.py",
    "require_router_mode": "backend/app/services/chat_router_mode.py",
    "resolve_explicit_router_mode": "backend/app/services/chat_router_mode.py",
    "resolve_pending_confirm_context": "backend/app/services/pending_confirms.py",
    "resolve_pending_confirm_paths": "backend/app/services/pending_confirms.py",
    "resolve_pending_confirm_workflow": "backend/app/services/pending_confirms.py",
    "resolve_prompt_task_timeout_ms": "backend/app/services/prompt_runtime_execution.py",
    "resolve_chat_answer_action": "backend/app/services/chat_answer_actions.py",
    "augment_router_mode_message_meta": "backend/app/services/chat_router_mode.py",
    "resolve_followup_output_locale": "backend/app/services/chat_output_locale.py",
    "resolve_gate_and_sync_extraction": "backend/app/services/chat_gate_resolution.py",
    "resolve_interview_output_locale": "backend/app/services/chat_output_locale.py",
    "resolve_question_compose_start_timeout_sec": "backend/app/services/chat_runtime_settings.py",
    "resolve_question_group_settings": "backend/app/services/chat_runtime_settings.py",
    "resolve_question_group": "backend/app/services/chat_question_planning.py",
    "resolve_question_group_plan": "backend/app/services/chat_question_planning.py",
    "resolve_question_planner_settings": "backend/app/services/chat_runtime_settings.py",
    "resolve_project_creation_question_setup": "backend/app/services/project_creation.py",
    "resolve_routing_state_json": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "resolve_standard_question_routing": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "row_to_report_quality_detail_payload": (
        "backend/app/services/platform_report_quality.py"
    ),
    "row_to_report_quality_item_payload": (
        "backend/app/services/platform_report_quality.py"
    ),
    "row_to_platform_setting_entry_payload": (
        "backend/app/services/platform_settings.py"
    ),
    "row_to_platform_admin_payload": "backend/app/services/platform_admin_users.py",
    "row_to_platform_org_payload": "backend/app/services/platform_orgs.py",
    "upsert_platform_admin_payload": (
        "backend/app/services/platform_admin_users.py"
    ),
    "update_platform_org_payload": "backend/app/services/platform_orgs.py",
    "update_platform_settings_payload": "backend/app/services/platform_settings.py",
    "resolve_report_confirmation_prerequisites": "backend/app/services/report_confirmations.py",
    "resolve_verification_provider_unavailable_reason": "backend/app/services/assessment_summaries.py",
    "resolve_stage_initial_questions": "backend/app/services/stage_question_setup.py",
    "resolve_stage_missing_paths": "backend/app/services/stage_question_setup.py",
    "resolve_answer_rubric_id": "backend/app/services/chat_question_runtime.py",
    "resolve_askable_question_id": "backend/app/services/chat_question_runtime.py",
    "resolve_initial_questions": "backend/app/services/chat_question_runtime.py",
    "resolve_missing_paths": "backend/app/services/chat_question_runtime.py",
    "resolve_next_question_id": "backend/app/services/chat_question_runtime.py",
    "resolve_repair_question": "backend/app/services/chat_question_runtime.py",
    "resolve_unique_prompt_template_version": "backend/app/services/prompt_templates.py",
    "resolve_question_verification_status": "backend/app/services/stage_verifications.py",
    "resolve_next_stage": "backend/app/services/chat_stage_gate.py",
    "resolve_stage_summary_generation_status": "backend/app/services/stage_drafts.py",
    "resolve_stage_paths": "backend/app/services/stage_payloads.py",
    "run_extract_answer_v0": "backend/app/services/answer_extraction_worker_handler.py",
    "run_answer_extraction": "backend/app/services/chat_prompt_tasks.py",
    "run_answer_gate": "backend/app/services/chat_prompt_tasks.py",
    "run_answer_gate_for_context": "backend/app/services/chat_prompt_tasks.py",
    "requires_single_sentence": "backend/app/services/chat_ai_assist.py",
    "run_ai_assist_draft": "backend/app/services/chat_ai_assist.py",
    "run_ai_assist_draft_stream": "backend/app/services/chat_ai_assist.py",
    "run_chat_question_rewrite": "backend/app/services/project_question_prompts.py",
    "run_question_rewrite": "backend/app/services/project_question_prompts.py",
    "run_report_generation_v0": "backend/app/services/report_generation_worker_handler.py",
    "run_stage_finalize_v0": "backend/app/services/stage_finalize_worker_handler.py",
    "run_stage_summary_v0": "backend/app/services/stage_summary_worker_handler.py",
    "run_sync_answer_extraction": "backend/app/services/chat_prompt_tasks.py",
    "run_sync_answer_extraction_for_context": "backend/app/services/chat_prompt_tasks.py",
    "run_verify_question_claims_v0": "backend/app/services/verification_job_handler.py",
    "schedule_project_stage_verification_refresh": "backend/app/services/verification_refresh.py",
    "sanitize_composed_question": "backend/app/services/chat_followup_compose.py",
    "sanitize_rewritten_prompt": "backend/app/services/chat_followup_compose.py",
    "scoreboard_has_scores": "backend/app/core/report_sections.py",
    "select_extraction_answer": "backend/app/services/chat_turn_context.py",
    "select_fallback_followup": "backend/app/services/chat_followup_compose.py",
    "select_followup_answer_pattern": "backend/app/services/chat_followup_compose.py",
    "select_gate_answer": "backend/app/services/chat_turn_context.py",
    "select_transition_state_payload": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "serialize_prompt_task_trace": "backend/app/services/prompt_runtime_execution.py",
    "set_chat_session_context": "backend/app/services/chat_context_reads.py",
    "set_context_path_value": "backend/app/services/context_paths.py",
    "should_enqueue_pass_answer_background_jobs": "backend/app/services/chat_background_jobs.py",
    "should_enter_stage_gate_review": "backend/app/services/chat_stage_gate.py",
    "should_update_chat_state_meta": (
        "backend/app/services/chat_turn_commit_shapers.py"
    ),
    "should_attempt_question_planner": "backend/app/services/chat_question_planning.py",
    "should_skip_non_required_question": "backend/app/services/chat_question_filters.py",
    "should_soft_pass_answer": "backend/app/services/chat_sync_extraction_preview.py",
    "split_context_path": "backend/app/services/context_paths.py",
    "split_state_path": "backend/app/services/extraction_transforms.py",
    "sse_event": "backend/app/services/chat_stream/events.py",
    "sse_status_event": "backend/app/services/chat_stream/events.py",
    "stage_summary_label": "backend/app/services/stage_summary_fallbacks.py",
    "stage_summary_retryable": "backend/app/services/stage_drafts.py",
    "stage_summary_value": "backend/app/services/stage_summary_fallbacks.py",
    "stream_text_events": "backend/app/services/chat_stream/events.py",
    "stream_question_response_events": (
        "backend/app/services/chat_stream/question_response.py"
    ),
    "stream_failure_result": "backend/app/services/prompt_runtime_execution.py",
    "strip_ai_draft_prefix": "backend/app/services/chat_ai_assist.py",
    "sync_runtime_gate_state": "backend/app/services/project_gate_sync.py",
    "to_report_score": "backend/app/core/report_sections.py",
    "truncate_context_value": "backend/app/services/chat_turn_context.py",
    "summary_verification_job_idempotency_key": "backend/app/services/verification_jobs.py",
    "update_pending_confirm_context": "backend/app/services/pending_confirms.py",
    "update_pending_confirm_workflow": "backend/app/services/pending_confirms.py",
    "update_streamed_question_message": "backend/app/services/chat_stream/message_persistence.py",
    "update_ai_assisted_paths": "backend/app/services/chat_sync_extraction_preview.py",
    "update_project_summary": "backend/app/services/project_mutations.py",
    "valid_pending_confirm_update_paths": "backend/app/services/pending_confirms.py",
    "verify_email_workflow": "backend/app/services/auth_email_verification.py",
}

FORBIDDEN_PYTHON_DEFINITIONS = {
    "_build_invite_link": "Use app.services.org_invite_links.build_invite_link instead.",
    "_build_project_description_prompt": "Use prompt runtime builders in tests or app.services.stage_finalize_worker_handler._generate_project_description_v0 for execution.",
    "_build_summary_prompt": "Use prompt runtime builders in tests or app.services.stage_summary_worker_handler.generate_stage_summary_v0 for execution.",
    "_resolve_unique_version": "Use app.services.prompt_templates.resolve_unique_prompt_template_version instead.",
    "_row_to_prompt_template": "Use app.services.prompt_templates.prompt_template_row_to_payload instead.",
    "_create_prompt_template_revision": "Use app.services.prompt_templates.create_prompt_template_revision instead.",
    "_deactivate_prompt_template_revisions": "Use app.services.prompt_templates.create_prompt_template_revision instead.",
    "_insert_prompt_template_revision": "Use app.services.prompt_templates.create_prompt_template_revision instead.",
    "_apply_router_mode_selection_guard": "Use app.services.chat_router_mode.apply_router_mode_selection_guard instead.",
    "_augment_router_mode_message_meta": "Use app.services.chat_router_mode.augment_router_mode_message_meta instead.",
    "_build_router_mode_selection_followup": "Use app.services.chat_router_mode.build_router_mode_selection_followup instead.",
    "_build_skip_decision": "Use app.services.chat_answer_actions.build_skip_decision instead.",
    "_resolve_app_base_url": "Use app.services.org_invite_links.resolve_app_base_url instead.",
    "_infer_path_stage": "Use app.services.context_paths.infer_context_path_stage instead.",
    "_normalize_ai_assisted_map": "Use app.services.stage_payloads.normalize_ai_assisted_map instead.",
    "_normalize_user_edited_map": "Use app.services.stage_payloads.normalize_user_edited_map instead.",
    "_pop_path": "Use app.services.context_paths.pop_context_path_value instead.",
    "_build_stream_error_payload": "Use app.services.chat_stream.events.build_stream_error_payload instead.",
    "_build_streamed_question_message_meta": "Use app.services.chat_stream.events.build_streamed_question_message_meta instead.",
    "_build_turn_event_meta": "Use app.services.chat_stream.events.build_turn_event_meta instead.",
    "_latency_span": "Use app.services.chat_stream.latency.latency_span instead.",
    "_log_chat_stream_latency": "Use app.services.chat_stream.latency.log_chat_stream_latency instead.",
    "_record_latency_span": "Use app.services.chat_stream.latency.record_latency_span instead.",
    "_followup_compose_enabled": "Use app.services.chat_runtime_settings.followup_compose_enabled instead.",
    "_parse_csv_set": "Use app.services.chat_runtime_settings.parse_csv_set instead.",
    "_parse_env_flag": "Use app.services.chat_runtime_settings.parse_env_flag instead.",
    "_question_compose_enabled": "Use app.services.chat_runtime_settings.question_compose_enabled instead.",
    "_resolve_question_compose_start_timeout_sec": "Use app.services.chat_runtime_settings.resolve_question_compose_start_timeout_sec instead.",
    "_resolve_question_group_settings": "Use app.services.chat_runtime_settings.resolve_question_group_settings instead.",
    "_resolve_question_planner_settings": "Use app.services.chat_runtime_settings.resolve_question_planner_settings instead.",
    "_run_question_rewrite": "Use app.services.project_question_prompts.run_chat_question_rewrite instead.",
    "_build_schema_key_map": "Use app.services.extraction_transforms.build_schema_key_map instead.",
    "_canonicalize_extraction_update_value": "Use app.services.extraction_transforms.canonicalize_extraction_update_value instead.",
    "_claim_verdict_counts": "Use app.services.stage_verifications.claim_verdict_counts instead.",
    "_collect_sources_from_claims": "Use app.services.stage_verifications.collect_sources_from_claims instead.",
    "_extract_value_meta": "Use app.services.extraction_transforms.extract_value_meta instead.",
    "_extract_answer_action": "Use app.services.chat_output_locale.extract_answer_action instead.",
    "_extract_mode_from_state": "Use app.services.chat_router_mode.extract_mode_from_state instead.",
    "_extract_router_mode_from_message_meta": "Use app.services.chat_router_mode.extract_router_mode_from_message_meta instead.",
    "_extract_router_mode_from_text": "Use app.services.chat_router_mode.extract_router_mode_from_text instead.",
    "_extract_skip_reason": "Use app.services.chat_answer_actions.extract_skip_reason instead.",
    "_fetch_user_for_dev_login": "Use app.services.auth_login.fetch_user_for_dev_login instead.",
    "_fetch_user_for_login": "Use app.services.auth_login.fetch_user_for_login instead.",
    "_fetch_user_for_password_reset": "Use app.services.auth_password_reset.fetch_password_reset_user instead.",
    "_flatten_dict": "Use app.services.extraction_transforms.flatten_extraction_payload instead.",
    "_get_nested_state_value": "Use app.services.extraction_transforms.get_nested_state_value instead.",
    "_generate_project_description": "Use app.services.stage_finalize_worker_handler._generate_project_description_v0 instead.",
    "_generate_unique_slug": "Use app.services.auth_registration.generate_unique_registration_slug instead.",
    "_generate_stage_summary": "Use app.services.stage_summary_worker_handler.generate_stage_summary_v0 instead.",
    "_generate_structured_report": "Use app.services.report_generation_worker_handler._generate_structured_report_v0 instead.",
    "_derive_org_name": "Use app.services.auth_registration.derive_registration_org_name instead.",
    "_has_explicit_none": "Use app.services.extraction_transforms.has_explicit_none instead.",
    "_increment_verification_summary": "Use app.services.stage_verifications.increment_verification_summary instead.",
    "_is_not_applicable_rationale": "Use app.services.stage_verifications.is_not_applicable_rationale instead.",
    "_is_quick_action_answer": "Use app.services.chat_output_locale.is_quick_action_answer instead.",
    "_is_stage_gate_ready_for_review": "Use app.services.chat_stage_gate.is_stage_gate_ready_for_review instead.",
    "_normalize_key": "Use app.services.extraction_transforms.normalize_extraction_key instead.",
    "_normalize_router_mode": "Use app.services.chat_router_mode.normalize_router_mode instead.",
    "_remap_extracted": "Use app.services.extraction_transforms.remap_extracted instead.",
    "_require_router_mode": "Use app.services.chat_router_mode.require_router_mode instead.",
    "_require_active_membership": "Use app.services.auth_login.require_active_membership instead.",
    "_resolve_explicit_router_mode": "Use app.services.chat_router_mode.resolve_explicit_router_mode instead.",
    "_record_login_failure": "Use app.services.auth_login.record_login_failure instead.",
    "_resolve_next_stage": "Use app.services.chat_stage_gate.resolve_next_stage instead.",
    "_resolve_question_verification_status": "Use app.services.stage_verifications.resolve_question_verification_status instead.",
    "_resolve_followup_output_locale": "Use app.services.chat_output_locale.resolve_followup_output_locale instead.",
    "_resolve_interview_output_locale": "Use app.services.chat_output_locale.resolve_interview_output_locale instead.",
    "_ensure_project_report_access": "Use app.services.project_report_access.ensure_project_report_access instead.",
    "_run_answer_extraction": "Use app.services.chat_prompt_tasks.run_answer_extraction instead.",
    "_run_answer_gate": "Use app.services.chat_prompt_tasks.run_answer_gate instead.",
    "_run_answer_gate_for_context": "Use app.services.chat_prompt_tasks.run_answer_gate_for_context instead.",
    "_run_extract_answer_v0": "Use app.services.answer_extraction_worker_handler.run_extract_answer_v0 instead.",
    "_run_report_generation_v0": "Use app.services.report_generation_worker_handler.run_report_generation_v0 instead.",
    "_run_stage_finalize_v0": "Use app.services.stage_finalize_worker_handler.run_stage_finalize_v0 instead.",
    "_run_stage_summary_v0": "Use app.services.stage_summary_worker_handler.run_stage_summary_v0 instead.",
    "_run_sync_answer_extraction": "Use app.services.chat_prompt_tasks.run_sync_answer_extraction instead.",
    "_run_sync_answer_extraction_for_context": "Use app.services.chat_prompt_tasks.run_sync_answer_extraction_for_context instead.",
    "_run_verify_question_claims_v0": "Use app.services.verification_job_handler.run_verify_question_claims_v0 instead.",
    "_sse_event": "Use app.services.chat_stream.events.sse_event instead.",
    "_sse_status_event": "Use app.services.chat_stream.events.sse_status_event instead.",
    "_split_state_path": "Use app.services.extraction_transforms.split_state_path instead.",
    "_should_enter_stage_gate_review": "Use app.services.chat_stage_gate.should_enter_stage_gate_review instead.",
    "_stream_text_events": "Use app.services.chat_stream.events.stream_text_events instead.",
    "_set_path": "Use app.services.context_paths.set_context_path_value instead.",
}

FRONTEND_SINGLE_OWNER = {
    "AdminModal": "frontend/features/admin/components/shared/admin-modal.tsx",
    "AdminOverviewClient": "frontend/features/admin/components/overview/admin-overview.tsx",
    "AdminOrgLogoModal": (
        "frontend/features/admin/components/org/settings/admin-org-logo-modal.tsx"
    ),
    "AdminOrgSettingsClient": (
        "frontend/features/admin/components/org/settings/admin-org-settings-client.tsx"
    ),
    "AdminOrgSettingsSurface": (
        "frontend/features/admin/components/org/settings/admin-org-settings-surface.tsx"
    ),
    "AdminShell": "frontend/features/admin/components/shared/admin-shell.tsx",
    "AddCohortMembersModal": (
        "frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx"
    ),
    "CohortDetail": "frontend/features/admin/components/cohorts/cohort-detail.tsx",
    "CohortDetailSurface": (
        "frontend/features/admin/components/cohorts/cohort-detail-surface.tsx"
    ),
    "buildCohortsQuery": "frontend/features/admin/admin-cohorts-view-model.ts",
    "CohortsTable": "frontend/features/admin/components/cohorts/cohorts-table.tsx",
    "CohortsTableSurface": (
        "frontend/features/admin/components/cohorts/cohorts-table-surface.tsx"
    ),
    "ContextStageNav": "frontend/features/context/live-context-controls.tsx",
    "ContextViewToggle": "frontend/features/context/live-context-controls.tsx",
    "CreateCohortModal": (
        "frontend/features/admin/components/cohorts/cohort-modals.tsx"
    ),
    "CreateInviteModal": "frontend/features/admin/components/org/invite-modals.tsx",
    "DiagnosisView": "frontend/features/context/live-context-diagnosis-view.tsx",
    "DeleteProjectModal": "frontend/features/projects/project-action-modals.tsx",
    "DeleteProjectCommentModal": (
        "frontend/features/admin/components/projects/project-detail-dialogs.tsx"
    ),
    "EditProjectModal": (
        "frontend/features/admin/components/projects/project-detail-dialogs.tsx"
    ),
    "FaqAndCtaSection": "frontend/components/marketing/HomePageFaqSection.tsx",
    "formatCohortTimeline": "frontend/features/admin/admin-cohorts-view-model.ts",
    "interpolateCohortMessage": (
        "frontend/features/admin/admin-cohorts-view-model.ts"
    ),
    "LiveContextBoard": "frontend/features/context/live-context-board.tsx",
    "LiveContextBoardSurface": "frontend/features/context/live-context-board-surface.tsx",
    "LiveContextBoardHeader": "frontend/features/context/live-context-review-panels.tsx",
    "LiveContextReviewCta": "frontend/features/context/live-context-review-panels.tsx",
    "LiveContextReviewPanel": "frontend/features/context/live-context-review-panels.tsx",
    "LiveDraftView": "frontend/features/context/live-context-draft-view.tsx",
    "useLiveContextEditing": "frontend/features/context/use-live-context-editing.ts",
    "MarketingHeader": "frontend/components/marketing/HomePageHeader.tsx",
    "ORG_SETTINGS_MESSAGES": "frontend/features/admin/org-settings-messages.ts",
    "PROMPT_MESSAGES": "frontend/features/admin/prompt-template-messages.ts",
    "RemoveCohortMemberModal": (
        "frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx"
    ),
    "resolveCohortIntlLocale": (
        "frontend/features/admin/admin-cohorts-view-model.ts"
    ),
    "RenameProjectModal": "frontend/features/projects/project-action-modals.tsx",
    "HomePageDvfSection": "frontend/components/marketing/HomePageDvfSection.tsx",
    "HomePageHeroSection": (
        "frontend/components/marketing/HomePageIntroSections.tsx"
    ),
    "HomePageProblemSection": (
        "frontend/components/marketing/HomePageIntroSections.tsx"
    ),
    "HomePageReportSection": (
        "frontend/components/marketing/HomePageReportSection.tsx"
    ),
    "HomePageSectionReveal": "frontend/components/marketing/HomePageSectionShell.tsx",
    "HomePageSectionShell": "frontend/components/marketing/HomePageSectionShell.tsx",
    "HomePageTrustSection": (
        "frontend/components/marketing/HomePageTrustSection.tsx"
    ),
    "MethodologyPageView": "frontend/components/marketing/MethodologyPageView.tsx",
    "HeroSection": "frontend/components/marketing/MethodologyIntroSections.tsx",
    "WhySection": "frontend/components/marketing/MethodologyIntroSections.tsx",
    "FrameworkSection": (
        "frontend/components/marketing/MethodologyFrameworkSection.tsx"
    ),
    "ReviewSection": "frontend/components/marketing/MethodologyReviewSection.tsx",
    "OutputsSection": (
        "frontend/components/marketing/MethodologyOutputSections.tsx"
    ),
    "ClosingSection": (
        "frontend/components/marketing/MethodologyOutputSections.tsx"
    ),
    "SectionHeading": "frontend/components/marketing/methodology-page-utils.tsx",
    "SectionReveal": "frontend/components/marketing/methodology-page-utils.tsx",
    "StageInsightView": "frontend/features/context/live-context-insight-view.tsx",
    "buildInvitesQuery": "frontend/features/admin/admin-invites-view-model.ts",
    "buildMembersQuery": "frontend/features/admin/admin-members-view-model.ts",
    "formatInviteDate": "frontend/features/admin/admin-invites-view-model.ts",
    "formatMemberDate": "frontend/features/admin/admin-members-view-model.ts",
    "interpolateInviteMessage": "frontend/features/admin/admin-invites-view-model.ts",
    "interpolateMemberMessage": "frontend/features/admin/admin-members-view-model.ts",
    "InvitesTable": "frontend/features/admin/components/org/invites-table.tsx",
    "InvitesTableSurface": (
        "frontend/features/admin/components/org/invites-table-surface.tsx"
    ),
    "MembersTable": "frontend/features/admin/components/org/members-table.tsx",
    "MembersTableSurface": (
        "frontend/features/admin/components/org/members-table-surface.tsx"
    ),
    "AssignmentFormModal": (
        "frontend/features/admin/components/org/mentor-assignments-modals.tsx"
    ),
    "AssignmentToast": (
        "frontend/features/admin/components/org/mentor-assignments-modals.tsx"
    ),
    "ASSIGNMENT_STATUS_VARIANTS": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "buildAssignmentsQuery": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "buildMentorAssignmentMemberLabel": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "ensureMentorAssignmentOption": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "interpolateMentorAssignmentMessage": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "MentorAssignmentsSurface": (
        "frontend/features/admin/components/org/mentor-assignments-panels.tsx"
    ),
    "MentorAssignmentsTable": "frontend/features/admin/components/org/mentor-assignments-table.tsx",
    "RevokeInviteModal": "frontend/features/admin/components/org/invite-modals.tsx",
    "RevokeAssignmentModal": (
        "frontend/features/admin/components/org/mentor-assignments-modals.tsx"
    ),
    "RemoveMemberModal": "frontend/features/admin/components/org/member-modals.tsx",
    "resolveMemberInitials": "frontend/features/admin/admin-members-view-model.ts",
    "resolveMentorAssignmentInitials": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "resolveMentorAssignmentIntlLocale": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "toCohortMemberOptions": (
        "frontend/features/admin/admin-mentor-assignments-view-model.ts"
    ),
    "toMemberOptions": "frontend/features/admin/admin-mentor-assignments-view-model.ts",
    "ProjectDetail": "frontend/features/admin/components/projects/project-detail.tsx",
    "ProjectDetailSurface": (
        "frontend/features/admin/components/projects/project-detail-surface.tsx"
    ),
    "ProjectsOrgPickerModal": "frontend/features/projects/projects-workspace-panels.tsx",
    "ProjectsTable": "frontend/features/admin/components/projects/projects-table.tsx",
    "ProjectsWorkspaceContent": "frontend/features/projects/projects-workspace-panels.tsx",
    "ProjectsWorkspaceFilters": "frontend/features/projects/projects-workspace-panels.tsx",
    "ProjectsWorkspaceHeader": "frontend/features/projects/projects-workspace-panels.tsx",
    "ProjectsWorkspaceTabs": "frontend/features/projects/projects-workspace-panels.tsx",
    "PromptTemplatesClient": (
        "frontend/features/admin/components/org/prompts/prompt-templates-client.tsx"
    ),
    "PromptTemplatesSurface": (
        "frontend/features/admin/components/org/prompts/prompt-templates-surface.tsx"
    ),
    "QUESTION_BANK_MESSAGES": "frontend/features/admin/question-bank-messages.ts",
    "formatStageLabel": "frontend/features/admin/prompt-template-view-model.ts",
    "groupTemplates": "frontend/features/admin/prompt-template-view-model.ts",
    "parseStageList": "frontend/features/admin/prompt-template-view-model.ts",
    "formatQuestionBankQuestionLabel": (
        "frontend/features/admin/question-bank-view-model.ts"
    ),
    "parseQuestionBankJson": "frontend/features/admin/question-bank-view-model.ts",
    "QuestionBankManager": "frontend/features/admin/components/org/question-banks/question-bank-manager.tsx",
    "QuestionBankOverviewPanel": (
        "frontend/features/admin/components/org/question-banks/question-bank-panels.tsx"
    ),
    "QuestionBankQuestionsPanel": (
        "frontend/features/admin/components/org/question-banks/question-bank-questions-panel.tsx"
    ),
    "ArchitectureDiagramCard": (
        "frontend/features/reports/report-viewer-technical-cards.tsx"
    ),
    "DataQualityCard": "frontend/features/reports/report-viewer-summary-cards.tsx",
    "DiagnosisCard": (
        "frontend/features/reports/report-viewer-diagnosis-cards.tsx"
    ),
    "DvfAssessmentCard": "frontend/features/reports/report-viewer-score-cards.tsx",
    "DvfScoreboardCard": "frontend/features/reports/report-viewer-score-cards.tsx",
    "KeyRisksCard": "frontend/features/reports/report-viewer-technical-cards.tsx",
    "LeanCanvasCard": "frontend/features/reports/report-viewer-summary-cards.tsx",
    "MarketEvidenceCard": "frontend/features/reports/report-viewer-summary-cards.tsx",
    "OverallSummaryCard": (
        "frontend/features/reports/report-viewer-technical-cards.tsx"
    ),
    "ReportDocument": "frontend/features/reports/report-document.tsx",
    "ReportJobStatusCard": "frontend/features/reports/report-job-status-card.tsx",
    "ReportQualityDashboard": "frontend/features/admin/components/platform/report-quality-dashboard.tsx",
    "ReportQualityDashboardSurface": (
        "frontend/features/admin/components/platform/report-quality-dashboard-surface.tsx"
    ),
    "REPORT_QUALITY_MESSAGES": (
        "frontend/features/admin/components/platform/report-quality-dashboard-messages.ts"
    ),
    "ReportSnapshotCard": "frontend/features/reports/report-viewer-summary-cards.tsx",
    "ReportV2ArtifactCard": "frontend/features/reports/report-viewer-v2-cards.tsx",
    "ReportViewer": "frontend/features/reports/report-viewer.tsx",
    "ReportViewerSurface": "frontend/features/reports/report-viewer-surface.tsx",
    "ReportsTable": "frontend/features/admin/components/reports/reports-table.tsx",
    "ReportsTableSurface": (
        "frontend/features/admin/components/reports/reports-table-surface.tsx"
    ),
    "SampleReportHero": "frontend/features/reports/sample-report-hero.tsx",
    "ValidationPlanCard": (
        "frontend/features/reports/report-viewer-diagnosis-cards.tsx"
    ),
    "VerificationSummaryCard": (
        "frontend/features/reports/report-viewer-summary-cards.tsx"
    ),
    "buildApiUrl": "frontend/lib/api/client.ts",
    "buildContextSections": "frontend/features/context/live-context-formatters.tsx",
    "buildSampleVerificationSnapshot": (
        "frontend/features/reports/report-sample-verification.ts"
    ),
    "getSafeErrorMessage": "frontend/lib/api/safe-error-message.ts",
    "filterProjects": "frontend/features/projects/projects-workspace-utils.tsx",
    "getSafeStatusErrorMessage": "frontend/lib/api/safe-error-message.ts",
    "getSafeResponseErrorMessage": "frontend/lib/api/safe-error-message.ts",
    "formatSettings": "frontend/features/admin/org-settings-view-model.ts",
    "normalizeReportJobStatus": "frontend/features/reports/reports-api.ts",
    "resolveOrgSlug": "frontend/features/admin/org-settings-view-model.ts",
    "useActiveMarketingSection": "frontend/components/marketing/home-page-utils.ts",
    "useMarketingPageContent": "frontend/components/marketing/home-page-utils.ts",
}

FRONTEND_SCAN_ROOTS = (
    FRONTEND_APP_ROOT,
    REPO_ROOT / "frontend" / "components",
    REPO_ROOT / "frontend" / "features",
    REPO_ROOT / "frontend" / "lib",
)


def rel_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def normalize_route(prefix: str, path: str) -> str:
    combined = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
    normalized = "/" + "/".join(part for part in combined.split("/") if part)
    return normalized if normalized != "" else "/"


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def is_apirouter_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "APIRouter") or (
        isinstance(func, ast.Attribute)
        and func.attr == "APIRouter"
        and isinstance(func.value, ast.Name)
        and func.value.id == "fastapi"
    )


def is_include_router_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
    )


class RouteCollector(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.prefix = ""
        self.routes: list[tuple[str, str, int]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            self._capture_router_prefix(node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id == "router":
            self._capture_router_prefix(node.value)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._capture_decorated_routes(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._capture_decorated_routes(node)
        self.generic_visit(node)

    def _capture_router_prefix(self, value: ast.AST | None) -> None:
        if not is_apirouter_call(value):
            return
        for keyword in value.keywords:
            if keyword.arg == "prefix":
                self.prefix = literal_string(keyword.value) or ""
                return
        self.prefix = ""

    def _capture_decorated_routes(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            route = self._route_from_decorator(decorator)
            if route is not None:
                self.routes.append(route)

    def _route_from_decorator(self, decorator: ast.AST) -> tuple[str, str, int] | None:
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr in ROUTE_METHODS
            and isinstance(func.value, ast.Name)
            and func.value.id == "router"
        ):
            return None
        path = literal_string(decorator.args[0]) if decorator.args else None
        if path is None:
            return None
        return (func.attr.upper(), normalize_route(self.prefix, path), decorator.lineno)


def collect_backend_routes(failures: list[str]) -> dict[tuple[str, str], list[str]]:
    routes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in sorted((REPO_ROOT / "backend" / "app" / "api" / "routes").glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{rel_path(path)}:{exc.lineno}: cannot parse route module")
            continue
        collector = RouteCollector(path)
        collector.visit(tree)
        for method, route_path, line in collector.routes:
            routes[(method, route_path)].append(f"{rel_path(path)}:{line}")
    return routes


def check_duplicate_backend_routes(failures: list[str]) -> None:
    routes = collect_backend_routes(failures)
    for (method, route_path), locations in sorted(routes.items()):
        if len(locations) > 1:
            joined = ", ".join(locations)
            failures.append(f"duplicate backend route {method} {route_path}: {joined}")


def check_backend_router_ownership(failures: list[str]) -> None:
    for path in sorted(BACKEND_APP_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{rel_path(path)}:{exc.lineno}: cannot parse python module")
            continue
        current_rel_path = rel_path(path)
        for node in ast.walk(tree):
            if is_apirouter_call(node) and not current_rel_path.startswith("backend/app/api/routes/"):
                failures.append(f"APIRouter call outside route modules at {current_rel_path}:{node.lineno}")
            if is_include_router_call(node) and current_rel_path not in INCLUDE_ROUTER_OWNERS:
                failures.append(f"include_router call outside router owners at {current_rel_path}:{node.lineno}")


def check_python_single_owner(failures: list[str]) -> None:
    definitions: dict[str, list[str]] = defaultdict(list)
    forbidden_definitions: dict[str, list[str]] = defaultdict(list)
    for path in sorted((REPO_ROOT / "backend" / "app").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{rel_path(path)}:{exc.lineno}: cannot parse python module")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in PYTHON_SINGLE_OWNER:
                    definitions[node.name].append(f"{rel_path(path)}:{node.lineno}")
                if node.name in FORBIDDEN_PYTHON_DEFINITIONS:
                    forbidden_definitions[node.name].append(f"{rel_path(path)}:{node.lineno}")

    for symbol, owner in sorted(PYTHON_SINGLE_OWNER.items()):
        owner_matches = [item for item in definitions[symbol] if item.startswith(f"{owner}:")]
        non_owner_matches = [item for item in definitions[symbol] if not item.startswith(f"{owner}:")]
        if not owner_matches:
            failures.append(f"single-owner python symbol {symbol} missing from {owner}")
        if non_owner_matches:
            joined = ", ".join(non_owner_matches)
            failures.append(f"single-owner python symbol {symbol} also defined at {joined}")

    for symbol, locations in sorted(forbidden_definitions.items()):
        joined = ", ".join(locations)
        failures.append(
            f"forbidden local helper {symbol} defined at {joined}. "
            f"{FORBIDDEN_PYTHON_DEFINITIONS[symbol]}"
        )


def check_route_background_job_write_ownership(failures: list[str]) -> None:
    write_patterns = ("INSERT INTO background_jobs", "UPDATE background_jobs")
    for path in sorted((REPO_ROOT / "backend" / "app" / "api" / "routes").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for pattern in write_patterns:
            if pattern in source:
                failures.append(
                    f"background job write {pattern!r} belongs in service modules, "
                    f"found in {rel_path(path)}"
                )


def check_chat_background_job_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    source = CHAT_ROUTE.read_text(encoding="utf-8")
    for symbol, guidance in sorted(CHAT_ROUTE_FORBIDDEN_BACKGROUND_JOB_REFERENCES.items()):
        if symbol in source:
            failures.append(
                f"chat route background job reference {symbol!r} belongs in "
                f"backend/app/services/chat_background_jobs.py. {guidance}"
            )


def check_chat_sync_extraction_preview_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_SYNC_PREVIEW_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route sync extraction preview helper {node.name!r} "
                f"belongs in backend/app/services/chat_sync_extraction_preview.py, "
                f"found in {rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_question_planning_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_QUESTION_PLANNING_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route question planning helper {node.name!r} belongs in "
                f"backend/app/services/chat_question_planning.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_followup_compose_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_FOLLOWUP_COMPOSE_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route follow-up/compose helper {node.name!r} belongs in "
                f"backend/app/services/chat_followup_compose.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_question_filter_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_QUESTION_FILTER_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route question filter helper {node.name!r} belongs in "
                f"backend/app/services/chat_question_filters.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_ai_assist_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_AI_ASSIST_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route AI-assist helper {node.name!r} belongs in "
                f"backend/app/services/chat_ai_assist.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_turn_context_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_TURN_CONTEXT_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route turn-context helper {node.name!r} belongs in "
                f"backend/app/services/chat_turn_context.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_turn_preflight_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_TURN_PREFLIGHT_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route turn-preflight helper {node.name!r} belongs in "
                f"backend/app/services/chat_turn_preflight.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_context_read_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_CONTEXT_READ_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route context-read helper {node.name!r} belongs in "
                f"backend/app/services/chat_context_reads.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_message_persistence_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_MESSAGE_PERSISTENCE_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route message-persistence helper {node.name!r} belongs in "
                f"backend/app/services/chat_stream/message_persistence.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_question_runtime_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_QUESTION_RUNTIME_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route question-runtime helper {node.name!r} belongs in "
                f"backend/app/services/chat_question_runtime.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_gate_resolution_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_GATE_RESOLUTION_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route gate-resolution helper {node.name!r} belongs in "
                f"backend/app/services/chat_gate_resolution.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_turn_evaluation_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_TURN_EVALUATION_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route turn-evaluation helper {node.name!r} belongs in "
                f"backend/app/services/chat_turn_evaluation.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_chat_turn_commit_ownership(failures: list[str]) -> None:
    if not CHAT_ROUTE.exists():
        return
    try:
        tree = ast.parse(
            CHAT_ROUTE.read_text(encoding="utf-8"),
            filename=str(CHAT_ROUTE),
        )
    except SyntaxError as exc:
        failures.append(f"{rel_path(CHAT_ROUTE)}:{exc.lineno}: cannot parse python module")
        return

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guidance = CHAT_ROUTE_FORBIDDEN_TURN_COMMIT_DEFINITIONS.get(node.name)
        if guidance:
            failures.append(
                f"chat route turn-commit helper {node.name!r} belongs in "
                f"backend/app/services/chat_turn_commit.py, found in "
                f"{rel_path(CHAT_ROUTE)}:{node.lineno}. {guidance}"
            )


def check_answer_extraction_worker_fallback_ownership(failures: list[str]) -> None:
    if not ANSWER_EXTRACTION_WORKER_HANDLER.exists():
        return
    try:
        tree = ast.parse(
            ANSWER_EXTRACTION_WORKER_HANDLER.read_text(encoding="utf-8"),
            filename=str(ANSWER_EXTRACTION_WORKER_HANDLER),
        )
    except SyntaxError as exc:
        failures.append(
            f"{rel_path(ANSWER_EXTRACTION_WORKER_HANDLER)}:{exc.lineno}: "
            "cannot parse python module"
        )
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            guidance = ANSWER_EXTRACTION_WORKER_FORBIDDEN_FALLBACK_DEFINITIONS.get(
                node.name
            )
            if guidance:
                failures.append(
                    f"answer extraction worker fallback helper {node.name!r} belongs in "
                    f"backend/app/services/answer_extraction_worker_fallbacks.py, "
                    f"found in {rel_path(ANSWER_EXTRACTION_WORKER_HANDLER)}:"
                    f"{node.lineno}. {guidance}"
                )
            guidance = ANSWER_EXTRACTION_WORKER_FORBIDDEN_MARKET_DEFINITIONS.get(
                node.name
            )
            if guidance:
                failures.append(
                    f"answer extraction worker market helper {node.name!r} belongs in "
                    f"backend/app/services/answer_extraction_worker_market.py, "
                    f"found in {rel_path(ANSWER_EXTRACTION_WORKER_HANDLER)}:"
                    f"{node.lineno}. {guidance}"
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                guidance = ANSWER_EXTRACTION_WORKER_FORBIDDEN_MARKET_DEFINITIONS.get(
                    target.id
                )
                if guidance:
                    failures.append(
                        f"answer extraction worker market constant {target.id!r} belongs in "
                        f"backend/app/services/answer_extraction_worker_market.py, "
                        f"found in {rel_path(ANSWER_EXTRACTION_WORKER_HANDLER)}:"
                        f"{node.lineno}. {guidance}"
                    )


def check_assessments_route_prompt_execution_ownership(failures: list[str]) -> None:
    if not ASSESSMENTS_ROUTE.exists():
        return
    source = ASSESSMENTS_ROUTE.read_text(encoding="utf-8")
    for symbol, guidance in sorted(
        ASSESSMENTS_ROUTE_FORBIDDEN_PROMPT_EXEC_REFERENCES.items()
    ):
        if symbol in source:
            failures.append(
                f"assessment route prompt execution reference {symbol!r} belongs "
                f"in service-owned worker handlers. {guidance}"
            )


def check_report_builder_prompt_runtime_boundary(failures: list[str]) -> None:
    for path in (REPORT_BUILDER, REPORT_SECTIONS):
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for symbol, guidance in sorted(
            REPORT_BUILDER_FORBIDDEN_PROMPT_RUNTIME_REFERENCES.items()
        ):
            if symbol in source:
                failures.append(
                    f"core report builder prompt-runtime reference {symbol!r} "
                    f"at {rel_path(path)} belongs in service-owned report "
                    f"prompt tasks. {guidance}"
                )


def function_source(path: Path, function_name: str, failures: list[str]) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        failures.append(f"{rel_path(path)}:{exc.lineno}: cannot parse python module")
        return None
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is None:
            failures.append(
                f"{rel_path(path)}:{node.lineno}: cannot locate end of "
                f"{function_name}"
            )
            return None
        return "\n".join(lines[node.lineno - 1 : end_lineno])
    failures.append(f"{rel_path(path)}: missing route handler {function_name}")
    return None


def function_source_with_local_callees(
    path: Path,
    function_name: str,
    failures: list[str],
) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        failures.append(f"{rel_path(path)}:{exc.lineno}: cannot parse python module")
        return None

    lines = source.splitlines()
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if function_name not in functions:
        failures.append(f"{rel_path(path)}: missing route handler {function_name}")
        return None

    visited: set[str] = set()
    chunks: list[str] = []

    def collect(name: str) -> None:
        if name in visited or name not in functions:
            return
        visited.add(name)
        node = functions[name]
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is None:
            failures.append(
                f"{rel_path(path)}:{node.lineno}: cannot locate end of {name}"
            )
            return
        chunks.append("\n".join(lines[node.lineno - 1 : end_lineno]))
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            callee = child.func
            if isinstance(callee, ast.Name):
                collect(callee.id)

    collect(function_name)
    return "\n\n".join(chunks)


def check_prompt_template_create_route_write_ownership(
    failures: list[str],
) -> None:
    for path, function_name in sorted(PROMPT_TEMPLATE_CREATE_ROUTE_OWNERS.items()):
        if not path.exists():
            continue
        source = function_source(path, function_name, failures)
        if source is None:
            continue
        for pattern, guidance in sorted(
            PROMPT_TEMPLATE_CREATE_ROUTE_FORBIDDEN_WRITES.items()
        ):
            if pattern in source:
                failures.append(
                    f"prompt template create route write {pattern!r} belongs in "
                    f"backend/app/services/prompt_templates.py, found in "
                    f"{rel_path(path)}::{function_name}. {guidance}"
                )


def check_question_bank_draft_create_route_write_ownership(
    failures: list[str],
) -> None:
    for path, function_name in sorted(QUESTION_BANK_DRAFT_CREATE_ROUTE_OWNERS.items()):
        if not path.exists():
            continue
        source = function_source(path, function_name, failures)
        if source is None:
            continue
        for pattern, guidance in sorted(
            QUESTION_BANK_DRAFT_CREATE_ROUTE_FORBIDDEN_WRITES.items()
        ):
            if pattern in source:
                failures.append(
                    f"question-bank draft create route write {pattern!r} belongs in "
                    f"backend/app/services/question_bank_drafts.py, found in "
                    f"{rel_path(path)}::{function_name}. {guidance}"
                )


def check_question_bank_draft_import_route_write_ownership(
    failures: list[str],
) -> None:
    for path, function_names in sorted(QUESTION_BANK_DRAFT_IMPORT_ROUTE_OWNERS.items()):
        if not path.exists():
            continue
        for function_name in function_names:
            source = function_source_with_local_callees(path, function_name, failures)
            if source is None:
                continue
            for pattern, guidance in sorted(
                QUESTION_BANK_DRAFT_IMPORT_ROUTE_FORBIDDEN_WRITES.items()
            ):
                if pattern in source:
                    failures.append(
                        f"question-bank draft import route write {pattern!r} "
                        f"belongs in backend/app/services/question_bank_draft_imports.py, "
                        f"found in {rel_path(path)}::{function_name} or a "
                        f"route-local helper it calls. {guidance}"
                    )


def check_question_bank_publish_route_write_ownership(
    failures: list[str],
) -> None:
    for path, function_name in sorted(QUESTION_BANK_PUBLISH_ROUTE_OWNERS.items()):
        if not path.exists():
            continue
        source = function_source(path, function_name, failures)
        if source is None:
            continue
        for pattern, guidance in sorted(
            QUESTION_BANK_PUBLISH_ROUTE_FORBIDDEN_WRITES.items()
        ):
            if pattern in source:
                failures.append(
                    f"question-bank draft publish route write {pattern!r} belongs "
                    f"in backend/app/services/question_bank_publish.py, found in "
                    f"{rel_path(path)}::{function_name}. {guidance}"
                )


def frontend_definition_patterns(symbol: str) -> tuple[re.Pattern[str], ...]:
    escaped = re.escape(symbol)
    return (
        re.compile(rf"^\s*export\s+(?:async\s+)?function\s+{escaped}\b", re.MULTILINE),
        re.compile(rf"^\s*(?:async\s+)?function\s+{escaped}\b", re.MULTILINE),
        re.compile(rf"^\s*export\s+(?:const|let|var)\s+{escaped}\b", re.MULTILINE),
        re.compile(rf"^\s*(?:const|let|var)\s+{escaped}\b", re.MULTILINE),
    )


def iter_frontend_source_files() -> list[Path]:
    files: list[Path] = []
    for root in FRONTEND_SCAN_ROOTS:
        if root.exists():
            for extension in ("*.js", "*.jsx", "*.mjs", "*.ts", "*.tsx"):
                files.extend(root.rglob(extension))
    return sorted(set(files))


def check_frontend_single_owner(failures: list[str]) -> None:
    definitions: dict[str, list[str]] = defaultdict(list)
    source_files = iter_frontend_source_files()

    for path in source_files:
        text = path.read_text(encoding="utf-8")
        for symbol in FRONTEND_SINGLE_OWNER:
            if any(pattern.search(text) for pattern in frontend_definition_patterns(symbol)):
                definitions[symbol].append(rel_path(path))

    for symbol, owner in sorted(FRONTEND_SINGLE_OWNER.items()):
        matches = definitions[symbol]
        if owner not in matches:
            failures.append(f"single-owner frontend symbol {symbol} missing from {owner}")
        non_owner_matches = [item for item in matches if item != owner]
        if non_owner_matches:
            joined = ", ".join(non_owner_matches)
            failures.append(f"single-owner frontend symbol {symbol} also defined in {joined}")


def check_legacy_admin_component_ownership(failures: list[str]) -> None:
    if not LEGACY_ADMIN_COMPONENTS_ROOT.exists():
        return
    legacy_files = [
        rel_path(path)
        for extension in ("*.js", "*.jsx", "*.mjs", "*.ts", "*.tsx")
        for path in LEGACY_ADMIN_COMPONENTS_ROOT.rglob(extension)
    ]
    if legacy_files:
        joined = ", ".join(sorted(legacy_files))
        failures.append(
            "admin feature components belong in frontend/features/admin/components; "
            f"found legacy files: {joined}"
        )


def normalize_next_route(path: Path) -> str:
    parts = []
    for part in path.relative_to(FRONTEND_APP_ROOT).parent.parts:
        if part.startswith("(") and part.endswith(")"):
            continue
        if part.startswith("@"):
            continue
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/"


def check_duplicate_frontend_routes(failures: list[str]) -> None:
    routes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in sorted(FRONTEND_APP_ROOT.rglob("*")):
        if path.name not in {"page.tsx", "page.ts", "page.jsx", "page.js", "route.ts", "route.js"}:
            continue
        kind = "handler" if path.name.startswith("route.") else "page"
        routes[(kind, normalize_next_route(path))].append(rel_path(path))

    for (kind, route_path), locations in sorted(routes.items()):
        if len(locations) > 1:
            joined = ", ".join(locations)
            failures.append(f"duplicate frontend {kind} route {route_path}: {joined}")


def main() -> int:
    failures: list[str] = []
    if not OWNERSHIP_MAP.exists():
        failures.append("docs/OWNERSHIP_MAP.md is missing")

    check_duplicate_backend_routes(failures)
    check_backend_router_ownership(failures)
    check_route_background_job_write_ownership(failures)
    check_chat_background_job_ownership(failures)
    check_chat_sync_extraction_preview_ownership(failures)
    check_chat_question_planning_ownership(failures)
    check_chat_followup_compose_ownership(failures)
    check_chat_question_filter_ownership(failures)
    check_chat_ai_assist_ownership(failures)
    check_chat_turn_context_ownership(failures)
    check_chat_turn_preflight_ownership(failures)
    check_chat_context_read_ownership(failures)
    check_chat_message_persistence_ownership(failures)
    check_chat_question_runtime_ownership(failures)
    check_chat_gate_resolution_ownership(failures)
    check_chat_turn_evaluation_ownership(failures)
    check_chat_turn_commit_ownership(failures)
    check_answer_extraction_worker_fallback_ownership(failures)
    check_assessments_route_prompt_execution_ownership(failures)
    check_report_builder_prompt_runtime_boundary(failures)
    check_prompt_template_create_route_write_ownership(failures)
    check_question_bank_draft_create_route_write_ownership(failures)
    check_question_bank_draft_import_route_write_ownership(failures)
    check_question_bank_publish_route_write_ownership(failures)
    check_duplicate_frontend_routes(failures)
    check_python_single_owner(failures)
    check_frontend_single_owner(failures)
    check_legacy_admin_component_ownership(failures)

    if failures:
        print("Architecture guard failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Architecture guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
