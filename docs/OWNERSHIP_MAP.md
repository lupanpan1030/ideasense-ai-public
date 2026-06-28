# Ownership Map

## Purpose

This map prevents accidental dual-path or multi-path implementations after code
is split into smaller modules. Every important product or technical capability
should have one canonical owner. Moving an owner is allowed, but the map and old
call sites must move in the same change.

## Rules

- Name the canonical owner before editing a boundary.
- Do not add a second implementation for the same capability.
- When extracting logic, replace or delete the old implementation in the same
  change.
- Temporary dual paths require an explicit migration note, a single owner, a
  removal condition, and tests that prove both paths cannot diverge silently.
- Update this file when ownership changes.
- Run `make architecture-check` after module moves, route changes, shared
  helper changes, or architecture-boundary edits.

## Canonical Owners

| Capability | Canonical owner |
| --- | --- |
| Product flow and data contract | `docs/spec/MASTER_SPEC.md` in the private repository; `docs/spec/PUBLIC_SPEC.md` in public-safe exports |
| Current system shape | `docs/ARCHITECTURE.md` |
| Backend layering rules | `docs/CONVENTIONS.md` |
| API router aggregation | `backend/app/main.py` and `backend/app/api/routes/__init__.py` |
| HTTP route boundaries | `backend/app/api/routes/*` |
| Auth route request/response DTOs | `backend/app/schemas/auth.py` |
| Auth/session dependency wiring | `backend/app/api/deps.py` |
| Local auth email verification workflow orchestration | `backend/app/services/auth_email_verification.py` |
| Local auth login workflow orchestration | `backend/app/services/auth_login.py` |
| Local auth registration workflow orchestration | `backend/app/services/auth_registration.py` |
| Local auth password reset workflow orchestration | `backend/app/services/auth_password_reset.py` |
| Assessment route verified access context and system RLS setup | `backend/app/api/deps.py` |
| Permission checks | `backend/app/api/permissions.py` |
| Project mutation access policy | `backend/app/services/project_permissions.py` |
| Project report access policy | `backend/app/services/project_report_access.py` |
| Project report access gate orchestration | `backend/app/services/project_report_access.py` |
| Stage transition decisions | `backend/app/services/stage_transition.py` |
| Chat stage-gate readiness helpers | `backend/app/services/chat_stage_gate.py` |
| Project stage state writes | `backend/app/services/stage_runtime.py` |
| Context path mutation helpers | `backend/app/services/context_paths.py` |
| Project state audit events | `backend/app/services/project_state_events.py` |
| Background job enqueue primitive | `backend/app/services/background_jobs.py` |
| Background job ordering helpers | `backend/app/services/background_jobs.py` |
| Background job status normalization | `backend/app/services/background_jobs.py` |
| Answer extraction job enqueue | `backend/app/services/answer_extraction_jobs.py` |
| Question verification job enqueue | `backend/app/services/verification_jobs.py` |
| Chat pass-answer background job enqueue | `backend/app/services/chat_background_jobs.py` |
| Verification refresh scheduling and route workflow orchestration | `backend/app/services/verification_refresh.py` |
| Assessment stage summaries read-model assembly | `backend/app/services/assessment_summaries.py` |
| Assessment route request/response DTOs | `backend/app/schemas/assessments.py` |
| Assessment verification read-model assembly and provider availability resolution | `backend/app/services/assessment_summaries.py` |
| Stage verification read-model status and source helpers | `backend/app/services/stage_verifications.py` |
| Stage draft cache, generation status helpers, and route workflow orchestration | `backend/app/services/stage_drafts.py` |
| Stage confirmation question setup | `backend/app/services/stage_question_setup.py` |
| Stage confirmation pure state-row normalization and preparation payload shaping | `backend/app/services/stage_confirmation_preparation.py` |
| Stage confirmation pure confirmed-stage persistence artifact payload shaping | `backend/app/services/stage_confirmation_persistence_payloads.py` |
| Stage confirmation public errors, result dataclasses, prepared-workflow dataclass, and next-stage map | `backend/app/services/stage_confirmation_types.py` |
| Normal stage confirmation preparation and orchestration | `backend/app/services/stage_confirmations.py` |
| Normal stage confirmation commit orchestration | `backend/app/services/stage_confirmations.py` |
| Confirmed stage assessment persistence | `backend/app/services/stage_confirmations.py` |
| Post-confirm stage runtime and assistant message initialization | `backend/app/services/stage_confirmations.py` |
| Stage payload assembly and stage path metadata maps | `backend/app/services/stage_payloads.py` |
| Stage summary fallback text helpers | `backend/app/services/stage_summary_fallbacks.py` |
| Pending-confirm state mutation semantics | `backend/app/services/pending_confirms.py` |
| Pending-confirm update/resolve admin-session workflow orchestration | `backend/app/services/pending_confirms.py` |
| Project runtime gate-state synchronization | `backend/app/services/project_gate_sync.py` |
| Project route request/response DTOs | `backend/app/schemas/projects.py` |
| Project creation question-bank setup and record insertion | `backend/app/services/project_creation.py` |
| Project creation payload normalization and admin-session workflow orchestration | `backend/app/services/project_creation.py` |
| Project conversation cursor parsing and read payload assembly | `backend/app/services/project_conversations.py` |
| Project latest question prompt localization | `backend/app/services/project_conversations.py` |
| Project context read payload assembly | `backend/app/services/project_contexts.py` |
| Project detail read payload assembly | `backend/app/services/project_details.py` |
| Project list filtering and read payload assembly | `backend/app/services/project_listings.py` |
| Project update/delete mutation semantics | `backend/app/services/project_mutations.py` |
| Project question prompt fetch and rewrite helpers | `backend/app/services/project_question_prompts.py` |
| Project report read payload assembly | `backend/app/services/project_reports.py` |
| Admin question-bank draft creation and bank-key normalization | `backend/app/services/question_bank_drafts.py` |
| Admin question-bank draft YAML/JSON import workflow | `backend/app/services/question_bank_draft_imports.py` |
| Admin question-bank draft publish workflow | `backend/app/services/question_bank_publish.py` |
| Admin prompt template row payload, version helpers, global list read-model, and create-revision workflow | `backend/app/services/prompt_templates.py` |
| Admin overview dashboard read-model assembly | `backend/app/services/admin_overview.py` |
| Admin overview localized formatter helpers | `backend/app/services/admin_overview_formatters.py` |
| Admin overview activity-feed read-model assembly | `backend/app/services/admin_overview_activity.py` |
| Report conversation source queries | `backend/app/services/report_conversation_sources.py` |
| Background job type wrappers | `backend/app/services/report_jobs.py`, `backend/app/services/stage_finalize_jobs.py`, `backend/app/services/stage_summary_jobs.py`, and job-specific service modules |
| Background job worker consumption | `backend/app/worker.py` |
| Worker job dispatch registry | `backend/app/worker.py` |
| Answer extraction background job handler | `backend/app/services/answer_extraction_worker_handler.py` |
| Answer extraction worker fallback value extraction | `backend/app/services/answer_extraction_worker_fallbacks.py` |
| Answer extraction worker market canonicalization and missing-path adjustment | `backend/app/services/answer_extraction_worker_market.py` |
| Report generation background job handler | `backend/app/services/report_generation_worker_handler.py` |
| Stage finalization background job handler | `backend/app/services/stage_finalize_worker_handler.py` |
| Stage summary background job handler | `backend/app/services/stage_summary_worker_handler.py` |
| Assessment prompt execution helpers | `backend/app/services/stage_summary_worker_handler.py`, `backend/app/services/stage_finalize_worker_handler.py`, and `backend/app/services/report_generation_worker_handler.py` |
| Verification background job handler | `backend/app/services/verification_job_handler.py` |
| Chat stream SSE event and metadata formatting | `backend/app/services/chat_stream/events.py` |
| Chat stream latency instrumentation | `backend/app/services/chat_stream/latency.py` |
| Chat streamed assistant question message persistence | `backend/app/services/chat_stream/message_persistence.py` |
| Chat question response compose/fallback streaming and streamed message update orchestration | `backend/app/services/chat_stream/question_response.py` |
| Chat context reads, question-detail context assembly, and chat session RLS context setup | `backend/app/services/chat_context_reads.py` |
| Chat runtime settings parsing | `backend/app/services/chat_runtime_settings.py` |
| Chat output-locale and quick-action helpers | `backend/app/services/chat_output_locale.py` |
| Chat answer-action and skip decision helpers | `backend/app/services/chat_answer_actions.py` |
| Chat technical router mode selection helpers | `backend/app/services/chat_router_mode.py` |
| Chat answer-gate and sync-extraction prompt tasks | `backend/app/services/chat_prompt_tasks.py` |
| Chat AI-assist draft detection, generation, formatting, and persistence helpers | `backend/app/services/chat_ai_assist.py` |
| Chat answer-gate resolution and partial-unknown metadata helpers | `backend/app/services/chat_gate_resolution.py` |
| Chat turn answer evaluation, preview resolution, heuristic enrichment, and router-mode answer guard | `backend/app/services/chat_turn_evaluation.py` |
| Chat turn preflight user-message persistence and gate-context assembly | `backend/app/services/chat_turn_preflight.py` |
| Chat turn result payload dataclasses and answer-score payload assembly | `backend/app/services/chat_turn_payloads.py` |
| Chat turn commit workflow writes | `backend/app/services/chat_turn_commit.py` |
| Chat turn commit pure state/meta, status, runtime, transition, state-event, stage-gate-ready, routing, assistant-meta, and assistant-result shapers | `backend/app/services/chat_turn_commit_shapers.py` |
| Chat turn-scoped assistant metadata, answer selection, key point collection, and gate context summary helpers | `backend/app/services/chat_turn_context.py` |
| Chat follow-up visible copy, compose context, gate decision shaping, and repeated follow-up cap helpers | `backend/app/services/chat_followup_compose.py` |
| Chat optional/conditional question filter, trigger, and market missing-path adjustment helpers | `backend/app/services/chat_question_filters.py` |
| Chat market type normalization and state inference | `backend/app/services/chat_market_type_normalization.py` |
| Chat question runtime reads, routing helpers, repair-question selection, early planning, instance initialization, and answer rubric lookup | `backend/app/services/chat_question_runtime.py` |
| Chat question planning, deterministic grouping, group metadata, and question plan persistence | `backend/app/services/chat_question_planning.py` |
| Chat sync extraction preview assembly and fallback value extraction | `backend/app/services/chat_sync_extraction_preview.py` |
| Chat sync preview question/schema matchers | `backend/app/services/chat_sync_preview_question_matchers.py` |
| Chat sync preview answer parser compatibility facade | `backend/app/services/chat_sync_preview_answer_parsers.py` |
| Chat sync preview problem, impact, and evidence parsers | `backend/app/services/chat_sync_preview_problem_parsers.py` |
| Chat sync preview market parsers | `backend/app/services/chat_sync_preview_market_parsers.py` |
| Chat sync preview technical execution parsers | `backend/app/services/chat_sync_preview_tech_parsers.py` |
| Chat sync preview field fallback assembly | `backend/app/services/chat_sync_preview_field_fallbacks.py` |
| Chat sync preview post-fallback state/meta patching | `backend/app/services/chat_sync_preview_post_fallbacks.py` |
| Shared extraction answer-text parsing and question heuristics | `backend/app/services/extraction_text_heuristics.py` |
| Extraction transform helpers for chat preview and worker writes | `backend/app/services/extraction_transforms.py` |
| Prompt runtime facade, rendering, registry construction, and public execution entrypoints | `backend/app/services/prompt_runtime.py` |
| Prompt task metadata, mutation classes, and default task spec definitions | `backend/app/services/prompt_task_specs.py` |
| Prompt context builder implementation and section assembly helpers | `backend/app/services/prompt_context_builders.py` |
| Prompt runtime execution trace, timeout, and fallback result helpers | `backend/app/services/prompt_runtime_execution.py` |
| Final report prompt rendering wrapper | `backend/app/services/report_prompt_tasks.py` |
| QA digest answer summarization | `backend/app/services/qa_digests.py` |
| LLM provider routing | `backend/app/core/llm_router.py` |
| Verification evidence pipeline | `backend/app/services/verification/service.py` and `backend/app/services/verification/judge.py` |
| Deterministic report payload assembly | `backend/app/core/report_builder.py` |
| Deterministic report recovery fallback section assembly | `backend/app/core/report_recovery_sections.py` |
| Report v2 derived section assembly | `backend/app/core/report_sections.py` |
| Report job orchestration | `backend/app/services/report_jobs.py` |
| Report job status payload builders | `backend/app/services/report_jobs.py` |
| Report confirmation route and core orchestration | `backend/app/services/report_confirmations.py` |
| Report confirmation prerequisites | `backend/app/services/report_confirmations.py` |
| Report confirmation recovery lookup | `backend/app/services/report_confirmations.py` |
| Report status API contract | `backend/app/api/routes/projects.py` and `frontend/features/reports/reports-api.ts` |
| Platform report-quality filters, row shaping, and read-model workflows | `backend/app/services/platform_report_quality.py` |
| Platform admin route request/response DTOs | `backend/app/schemas/platform_admin.py` |
| Platform settings key normalization, read payload assembly, and update workflow | `backend/app/services/platform_settings.py` |
| Platform admin user listing, validation, row shaping, and upsert workflow | `backend/app/services/platform_admin_users.py` |
| Platform organization listing, validation, row shaping, and update workflow | `backend/app/services/platform_orgs.py` |
| Organization invite link policy | `backend/app/services/org_invite_links.py` |
| Frontend API base URL and auth client | `frontend/lib/api/client.ts` |
| Frontend safe error messages | `frontend/lib/api/safe-error-message.ts` |
| Frontend routes and layouts | `frontend/app` |
| Reusable frontend UI primitives | `frontend/components` |
| Feature-specific frontend UI and API calls | `frontend/features` |
| Sample showcase data source (DB-only, no static fallback) | `frontend/features/sample/sample-api.ts` |
| Admin shared shell and modal components | `frontend/features/admin/components/shared` |
| Admin overview dashboard component | `frontend/features/admin/components/overview/admin-overview.tsx` |
| Admin report quality dashboard orchestration, display, and messages | `frontend/features/admin/components/platform/report-quality-dashboard.tsx`, `frontend/features/admin/components/platform/report-quality-dashboard-surface.tsx`, and `frontend/features/admin/components/platform/report-quality-dashboard-messages.ts` |
| Admin organization table components | `frontend/features/admin/components/org` |
| Admin organization invite orchestration, display, modals, and view-model helpers | `frontend/features/admin/components/org/invites-table.tsx`, `frontend/features/admin/components/org/invites-table-surface.tsx`, `frontend/features/admin/components/org/invite-modals.tsx`, and `frontend/features/admin/admin-invites-view-model.ts` |
| Admin organization member orchestration, display, modals, and view-model helpers | `frontend/features/admin/components/org/members-table.tsx`, `frontend/features/admin/components/org/members-table-surface.tsx`, `frontend/features/admin/components/org/member-modals.tsx`, and `frontend/features/admin/admin-members-view-model.ts` |
| Admin organization settings route shell, client, display, messages, and view-model helpers | `frontend/app/(admin)/admin/org/page.tsx`, `frontend/features/admin/components/org/settings/admin-org-settings-client.tsx`, `frontend/features/admin/components/org/settings/admin-org-settings-surface.tsx`, `frontend/features/admin/components/org/settings/admin-org-logo-modal.tsx`, `frontend/features/admin/org-settings-messages.ts`, and `frontend/features/admin/org-settings-view-model.ts` |
| Admin prompt-template route shell, client, display, messages, and view-model helpers | `frontend/app/(admin)/admin/org/prompts/page.tsx`, `frontend/features/admin/components/org/prompts/prompt-templates-client.tsx`, `frontend/features/admin/components/org/prompts/prompt-templates-surface.tsx`, `frontend/features/admin/prompt-template-messages.ts`, and `frontend/features/admin/prompt-template-view-model.ts` |
| Admin mentor-assignment orchestration, display modules, and view-model helpers | `frontend/features/admin/components/org/mentor-assignments-table.tsx`, `frontend/features/admin/components/org/mentor-assignments-panels.tsx`, `frontend/features/admin/components/org/mentor-assignments-modals.tsx`, and `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| Admin question-bank manager UI, leaf panels, and questions display | `frontend/features/admin/components/org/question-banks/question-bank-manager.tsx`, `frontend/features/admin/components/org/question-banks/question-bank-panels.tsx`, and `frontend/features/admin/components/org/question-banks/question-bank-questions-panel.tsx` |
| Admin question-bank messages and view-model helpers | `frontend/features/admin/question-bank-messages.ts` and `frontend/features/admin/question-bank-view-model.ts` |
| Admin cohort components | `frontend/features/admin/components/cohorts` |
| Admin cohort list orchestration, display, modals, and view-model helpers | `frontend/features/admin/components/cohorts/cohorts-table.tsx`, `frontend/features/admin/components/cohorts/cohorts-table-surface.tsx`, `frontend/features/admin/components/cohorts/cohort-modals.tsx`, and `frontend/features/admin/admin-cohorts-view-model.ts` |
| Admin cohort detail orchestration, display, dialogs, and UI data types | `frontend/features/admin/components/cohorts/cohort-detail.tsx`, `frontend/features/admin/components/cohorts/cohort-detail-surface.tsx`, `frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx`, and `frontend/features/admin/components/cohorts/cohort-detail-types.ts` |
| Admin project components | `frontend/features/admin/components/projects` |
| Admin project detail orchestration, display, dialogs, and UI data types | `frontend/features/admin/components/projects/project-detail.tsx`, `frontend/features/admin/components/projects/project-detail-surface.tsx`, `frontend/features/admin/components/projects/project-detail-dialogs.tsx`, and `frontend/features/admin/components/projects/project-detail-types.ts` |
| Admin report table components | `frontend/features/admin/components/reports` |
| Admin reports table orchestration, display, and UI data types | `frontend/features/admin/components/reports/reports-table.tsx`, `frontend/features/admin/components/reports/reports-table-surface.tsx`, and `frontend/features/admin/components/reports/reports-table-types.ts` |
| Report viewer entrypoint and display modules | `frontend/features/reports/report-viewer.tsx`, `frontend/features/reports/report-viewer-surface.tsx`, `frontend/features/reports/report-document.tsx`, `frontend/features/reports/report-job-status-card.tsx`, `frontend/features/reports/sample-report-hero.tsx`, and `frontend/features/reports/report-sample-verification.ts` |
| Report viewer card-family compatibility facade | `frontend/features/reports/report-viewer-cards.tsx` |
| Report viewer summary, market evidence, and verification cards | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| Report viewer DVF score cards | `frontend/features/reports/report-viewer-score-cards.tsx` |
| Report viewer risk, architecture, and narrative cards | `frontend/features/reports/report-viewer-technical-cards.tsx` |
| Report viewer Report v2 artifact cards | `frontend/features/reports/report-viewer-v2-cards.tsx` |
| Report viewer diagnosis and validation cards | `frontend/features/reports/report-viewer-diagnosis-cards.tsx` |
| Live context board orchestration | `frontend/features/context/live-context-board.tsx` |
| Live context board display surface | `frontend/features/context/live-context-board-surface.tsx` |
| Live context board shared formatting and stage helpers | `frontend/features/context/live-context-formatters.tsx` |
| Live context board draft and insight views | `frontend/features/context/live-context-draft-view.tsx` and `frontend/features/context/live-context-insight-view.tsx` |
| Live context board controls and diagnosis view | `frontend/features/context/live-context-controls.tsx` and `frontend/features/context/live-context-diagnosis-view.tsx` |
| Live context board review and header panels | `frontend/features/context/live-context-review-panels.tsx` |
| Live context board draft editing controller | `frontend/features/context/use-live-context-editing.ts` |
| Projects workspace route orchestration | `frontend/app/(app)/projects/projects-client.tsx` |
| Projects workspace utility helpers, action modals, and presentation panels | `frontend/features/projects/projects-workspace-utils.tsx`, `frontend/features/projects/project-action-modals.tsx`, and `frontend/features/projects/projects-workspace-panels.tsx` |
| Marketing homepage composition, section facade, section families, shared wrappers, FAQ section, and header utilities | `frontend/components/marketing/HomePage.tsx`, `frontend/components/marketing/HomePageSections.tsx`, `frontend/components/marketing/HomePageIntroSections.tsx`, `frontend/components/marketing/HomePageDvfSection.tsx`, `frontend/components/marketing/HomePageReportSection.tsx`, `frontend/components/marketing/HomePageTrustSection.tsx`, `frontend/components/marketing/HomePageHeader.tsx`, `frontend/components/marketing/HomePageSectionShell.tsx`, `frontend/components/marketing/HomePageFaqSection.tsx`, and `frontend/components/marketing/home-page-utils.ts` |
| Marketing methodology page shell, section facade, section families, helper utilities, and content type owner | `frontend/components/marketing/MethodologyPageView.tsx`, `frontend/components/marketing/MethodologyPageSections.tsx`, `frontend/components/marketing/MethodologyIntroSections.tsx`, `frontend/components/marketing/MethodologyFrameworkSection.tsx`, `frontend/components/marketing/MethodologyReviewSection.tsx`, `frontend/components/marketing/MethodologyOutputSections.tsx`, `frontend/components/marketing/methodology-page-utils.tsx`, and `frontend/components/marketing/methodology-page-types.ts` |
| Database contract | `database/migrations` and `database/schema` |

## Guarded Symbols

`scripts/architecture_guard.py` currently enforces these single-owner symbols:

| Symbol | Owner |
| --- | --- |
| `build_invite_link` | `backend/app/services/org_invite_links.py` |
| `resolve_app_base_url` | `backend/app/services/org_invite_links.py` |
| `_apply_authoritative_extraction_updates` | `backend/app/services/answer_extraction_worker_handler.py` |
| `_extract_with_openai` | `backend/app/services/answer_extraction_worker_handler.py` |
| `_should_skip_authoritative_extract_mutation` | `backend/app/services/answer_extraction_worker_handler.py` |
| `adjust_answer_extraction_market_missing_paths` | `backend/app/services/answer_extraction_worker_market.py` |
| `build_extraction_targets` | `backend/app/services/extraction_transforms.py` |
| `_worker_job_handlers` | `backend/app/worker.py` |
| `ai_draft_message_parts` | `backend/app/services/chat_ai_assist.py` |
| `ai_draft_unavailable_message` | `backend/app/services/chat_ai_assist.py` |
| `adjust_missing_paths_for_market` | `backend/app/services/chat_question_filters.py` |
| `apply_group_override` | `backend/app/services/chat_question_planning.py` |
| `apply_repeated_followup_cap` | `backend/app/services/chat_followup_compose.py` |
| `apply_transition_prefix` | `backend/app/services/chat_question_planning.py` |
| `apply_router_mode_selection_guard` | `backend/app/services/chat_router_mode.py` |
| `augment_router_mode_message_meta` | `backend/app/services/chat_router_mode.py` |
| `build_chat_status_payload` | `backend/app/services/chat_stream/events.py` |
| `build_followup_compose_context` | `backend/app/services/chat_followup_compose.py` |
| `build_followup_compose_prompt` | `backend/app/services/chat_followup_compose.py` |
| `build_followup_message` | `backend/app/services/chat_followup_compose.py` |
| `build_followup_stream_context` | `backend/app/services/chat_followup_compose.py` |
| `build_gate_decision` | `backend/app/services/chat_followup_compose.py` |
| `build_question_compose_context` | `backend/app/services/chat_followup_compose.py` |
| `build_question_compose_prompt` | `backend/app/services/chat_followup_compose.py` |
| `build_question_group_payload` | `backend/app/services/chat_question_planning.py` |
| `build_question_meta_payload` | `backend/app/services/chat_question_planning.py` |
| `build_question_stream_context` | `backend/app/services/chat_followup_compose.py` |
| `build_sync_extraction_preview` | `backend/app/services/chat_sync_extraction_preview.py` |
| `build_router_mode_selection_followup` | `backend/app/services/chat_router_mode.py` |
| `build_stream_error_payload` | `backend/app/services/chat_stream/events.py` |
| `build_streamed_question_message_meta` | `backend/app/services/chat_stream/events.py` |
| `build_skip_decision` | `backend/app/services/chat_answer_actions.py` |
| `build_turn_event_meta` | `backend/app/services/chat_stream/events.py` |
| `extract_answer_action` | `backend/app/services/chat_output_locale.py` |
| `extract_mode_from_state` | `backend/app/services/chat_router_mode.py` |
| `extract_router_mode_from_message_meta` | `backend/app/services/chat_router_mode.py` |
| `extract_router_mode_from_text` | `backend/app/services/chat_router_mode.py` |
| `extract_skip_reason` | `backend/app/services/chat_answer_actions.py` |
| `fetch_group_meta` | `backend/app/services/chat_question_planning.py` |
| `fetch_question_planner_candidates` | `backend/app/services/chat_question_planning.py` |
| `filter_missing_paths_by_state` | `backend/app/services/chat_question_filters.py` |
| `focus_followup_on_unresolved_paths` | `backend/app/services/chat_followup_compose.py` |
| `followup_compose_enabled` | `backend/app/services/chat_runtime_settings.py` |
| `is_quick_action_answer` | `backend/app/services/chat_output_locale.py` |
| `is_required_question` | `backend/app/services/chat_question_filters.py` |
| `is_optional_question` | `backend/app/services/chat_question_filters.py` |
| `is_conditional_question` | `backend/app/services/chat_question_filters.py` |
| `is_compliance_triggered` | `backend/app/services/chat_question_filters.py` |
| `is_ai_data_triggered` | `backend/app/services/chat_question_filters.py` |
| `is_high_reliability_triggered` | `backend/app/services/chat_question_filters.py` |
| `apply_extraction_updates_to_state` | `backend/app/services/chat_sync_extraction_preview.py` |
| `apply_mvp_boundary_preview_fallbacks` | `backend/app/services/chat_sync_preview_post_fallbacks.py` |
| `apply_preview_field_fallbacks` | `backend/app/services/chat_sync_preview_field_fallbacks.py` |
| `apply_problem_frequency_preview_fallback` | `backend/app/services/chat_sync_preview_post_fallbacks.py` |
| `canonicalize_extracted_value` | `backend/app/services/chat_market_type_normalization.py` |
| `canonicalize_market_type_fields` | `backend/app/services/chat_market_type_normalization.py` |
| `canonicalize_market_type_value` | `backend/app/services/chat_market_type_normalization.py` |
| `collect_strings` | `backend/app/services/chat_market_type_normalization.py` |
| `infer_frequency_from_answer` | `backend/app/services/chat_sync_extraction_preview.py` |
| `infer_problem_frequency_from_answer` | `backend/app/services/chat_sync_preview_post_fallbacks.py` |
| `infer_market_type_enum_from_state` | `backend/app/services/chat_market_type_normalization.py` |
| `infer_market_type` | `backend/app/services/chat_question_filters.py` |
| `is_alternatives_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_evidence_validation_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_idea_snapshot_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_business_model_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_competition_prompt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_competition_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_gtm_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_launch_segment_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_moat_prompt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_unit_economics_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_market_validation_plan_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_problem_scenarios_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_severity_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_complexity_debt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_compliance_plan_prompt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_data_scalability_prompt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_dependencies_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_infra_devops_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_mvp_boundary_prompt_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_mvp_boundary_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_reliability_testing_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_roadmap_risks_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_sensitive_data_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_tech_slo_incident_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_time_money_impact_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `is_top_problem_question` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `looks_like_history_reference` | `backend/app/services/chat_sync_preview_problem_parsers.py` |
| `prepare_extraction_updates` | `backend/app/services/chat_sync_extraction_preview.py` |
| `question_id_or_prompt_matches` | `backend/app/services/chat_sync_preview_question_matchers.py` |
| `should_soft_pass_answer` | `backend/app/services/chat_sync_extraction_preview.py` |
| `update_ai_assisted_paths` | `backend/app/services/chat_sync_extraction_preview.py` |
| `latency_span` | `backend/app/services/chat_stream/latency.py` |
| `log_chat_stream_latency` | `backend/app/services/chat_stream/latency.py` |
| `parse_csv_set` | `backend/app/services/chat_runtime_settings.py` |
| `parse_env_flag` | `backend/app/services/chat_runtime_settings.py` |
| `persist_question_plan` | `backend/app/services/chat_question_planning.py` |
| `question_compose_enabled` | `backend/app/services/chat_runtime_settings.py` |
| `question_has_missing_paths` | `backend/app/services/chat_question_planning.py` |
| `question_overlaps_only_deferred_paths` | `backend/app/services/chat_question_planning.py` |
| `question_schema_paths` | `backend/app/services/chat_question_planning.py` |
| `question_supports_grouping` | `backend/app/services/chat_question_planning.py` |
| `question_market_lock` | `backend/app/services/chat_question_filters.py` |
| `question_triggers` | `backend/app/services/chat_question_filters.py` |
| `resolve_chat_answer_action` | `backend/app/services/chat_answer_actions.py` |
| `resolve_followup_output_locale` | `backend/app/services/chat_output_locale.py` |
| `resolve_interview_output_locale` | `backend/app/services/chat_output_locale.py` |
| `resolve_question_compose_start_timeout_sec` | `backend/app/services/chat_runtime_settings.py` |
| `resolve_question_group` | `backend/app/services/chat_question_planning.py` |
| `resolve_question_group_plan` | `backend/app/services/chat_question_planning.py` |
| `resolve_question_group_settings` | `backend/app/services/chat_runtime_settings.py` |
| `resolve_question_planner_settings` | `backend/app/services/chat_runtime_settings.py` |
| `record_latency_span` | `backend/app/services/chat_stream/latency.py` |
| `record_project_state_event` | `backend/app/services/project_state_events.py` |
| `answer_extraction_job_idempotency_key` | `backend/app/services/answer_extraction_jobs.py` |
| `enqueue_authoritative_answer_extraction_job` | `backend/app/services/answer_extraction_jobs.py` |
| `apply_chat_state_patch` | `backend/app/services/chat_turn_commit_shapers.py` |
| `canonicalize_extraction_update_value` | `backend/app/services/extraction_transforms.py` |
| `background_job_sort_time` | `backend/app/services/background_jobs.py` |
| `normalize_background_job_status` | `backend/app/services/background_jobs.py` |
| `build_answer_extraction_queued_payload` | `backend/app/services/chat_background_jobs.py` |
| `build_answer_text_from_history` | `backend/app/services/chat_ai_assist.py` |
| `build_ai_assist_context` | `backend/app/services/chat_ai_assist.py` |
| `build_assistant_meta` | `backend/app/services/chat_turn_context.py` |
| `build_confirmed_stage_artifact_payload` | `backend/app/services/stage_confirmation_persistence_payloads.py` |
| `build_gate_context_summary` | `backend/app/services/chat_turn_context.py` |
| `build_needs_info_assistant_meta` | `backend/app/services/chat_turn_commit_shapers.py` |
| `build_next_question_assistant_meta` | `backend/app/services/chat_turn_commit_shapers.py` |
| `build_next_question_turn_result` | `backend/app/services/chat_turn_commit_shapers.py` |
| `build_qa_digests_from_messages` | `backend/app/services/qa_digests.py` |
| `build_state_event_patch` | `backend/app/services/chat_turn_commit_shapers.py` |
| `build_schema_key_map` | `backend/app/services/extraction_transforms.py` |
| `build_queued_report_job_status` | `backend/app/services/report_jobs.py` |
| `build_ready_report_job_status` | `backend/app/services/report_jobs.py` |
| `build_stage_payload` | `backend/app/services/stage_payloads.py` |
| `build_stage_question_meta_payload` | `backend/app/services/stage_question_setup.py` |
| `build_stage_summary_fallback` | `backend/app/services/stage_summary_fallbacks.py` |
| `build_stage_transition_assistant_meta` | `backend/app/services/chat_turn_commit_shapers.py` |
| `build_question_rewrite_prompt` | `backend/app/services/project_question_prompts.py` |
| `can_reuse_stage_draft_cache` | `backend/app/services/stage_drafts.py` |
| `can_mutate_project` | `backend/app/services/project_permissions.py` |
| `claim_verdict_counts` | `backend/app/services/stage_verifications.py` |
| `collect_sources_from_claims` | `backend/app/services/stage_verifications.py` |
| `collect_key_points` | `backend/app/services/chat_turn_context.py` |
| `collect_stage_summary_items` | `backend/app/services/stage_summary_fallbacks.py` |
| `commit_prepared_stage_confirmation_workflow` | `backend/app/services/stage_confirmations.py` |
| `commit_stage_confirmation_workflow` | `backend/app/services/stage_confirmations.py` |
| `confirm_project_report_stage_workflow` | `backend/app/services/report_confirmations.py` |
| `confirm_report_stage_workflow` | `backend/app/services/report_confirmations.py` |
| `create_question_bank_draft` | `backend/app/services/question_bank_drafts.py` |
| `create_prompt_template_revision` | `backend/app/services/prompt_templates.py` |
| `create_project_records` | `backend/app/services/project_creation.py` |
| `create_project_workflow` | `backend/app/services/project_creation.py` |
| `derive_updated_runtime_missing_paths` | `backend/app/services/chat_turn_commit_shapers.py` |
| `derive_answer_summary` | `backend/app/services/qa_digests.py` |
| `extract_value_meta` | `backend/app/services/extraction_transforms.py` |
| `flatten_extraction_payload` | `backend/app/services/extraction_transforms.py` |
| `format_ai_draft_message` | `backend/app/services/chat_ai_assist.py` |
| `apply_pending_confirm_updates` | `backend/app/services/pending_confirms.py` |
| `fetch_project_conversation_list` | `backend/app/services/project_conversations.py` |
| `fetch_question_detail` | `backend/app/services/project_question_prompts.py` |
| `fetch_chat_answer_history` | `backend/app/services/chat_context_reads.py` |
| `fetch_chat_state_context` | `backend/app/services/chat_context_reads.py` |
| `fetch_chat_question_detail` | `backend/app/services/chat_question_runtime.py` |
| `fetch_context_meta` | `backend/app/services/chat_context_reads.py` |
| `fetch_stage_question_detail` | `backend/app/services/stage_question_setup.py` |
| `fetch_project_pending_confirm` | `backend/app/services/pending_confirms.py` |
| `fetch_project_context` | `backend/app/services/project_contexts.py` |
| `fetch_project_detail` | `backend/app/services/project_details.py` |
| `fetch_project_list` | `backend/app/services/project_listings.py` |
| `fetch_report_last_user_message` | `backend/app/services/report_conversation_sources.py` |
| `fetch_report_confirmation_project_row` | `backend/app/services/report_confirmations.py` |
| `soft_delete_project` | `backend/app/services/project_mutations.py` |
| `fetch_report_confirmation_recovery_report` | `backend/app/services/report_confirmations.py` |
| `fetch_project_report_payload` | `backend/app/services/project_reports.py` |
| `fetch_project_stage_verification_read_models` | `backend/app/services/assessment_summaries.py` |
| `fetch_stage_draft_project_row` | `backend/app/services/stage_drafts.py` |
| `fetch_stage_summary_read_models` | `backend/app/services/assessment_summaries.py` |
| `ensure_project_report_access` | `backend/app/services/project_report_access.py` |
| `ensure_project_report_access_gate` | `backend/app/services/project_report_access.py` |
| `get_nested_state_value` | `backend/app/services/extraction_transforms.py` |
| `has_explicit_none` | `backend/app/services/extraction_transforms.py` |
| `has_substantive_answer` | `backend/app/services/chat_ai_assist.py` |
| `increment_verification_summary` | `backend/app/services/stage_verifications.py` |
| `is_non_empty` | `backend/app/services/extraction_transforms.py` |
| `is_not_applicable_rationale` | `backend/app/services/stage_verifications.py` |
| `is_stage_gate_ready_for_review` | `backend/app/services/chat_stage_gate.py` |
| `maybe_localize_latest_question_prompt` | `backend/app/services/project_conversations.py` |
| `normalize_extraction_key` | `backend/app/services/extraction_transforms.py` |
| `normalize_project_state_payload` | `backend/app/services/chat_turn_commit_shapers.py` |
| `prepare_stage_draft_workflow` | `backend/app/services/stage_drafts.py` |
| `update_project_summary` | `backend/app/services/project_mutations.py` |
| `normalize_pending_confirm` | `backend/app/services/pending_confirms.py` |
| `normalize_pending_confirm_resolve_paths` | `backend/app/services/pending_confirms.py` |
| `normalize_pending_confirm_updates` | `backend/app/services/pending_confirms.py` |
| `normalize_market_type` | `backend/app/services/chat_question_filters.py` |
| `normalize_market_text` | `backend/app/services/chat_question_filters.py` |
| `normalize_conversation_cursor` | `backend/app/services/project_conversations.py` |
| `normalize_context_value` | `backend/app/services/chat_turn_context.py` |
| `normalize_project_creation_input` | `backend/app/services/project_creation.py` |
| `normalize_project_list_filters` | `backend/app/services/project_listings.py` |
| `mark_partial_unknown_paths` | `backend/app/services/chat_gate_resolution.py` |
| `normalize_router_mode` | `backend/app/services/chat_router_mode.py` |
| `prepare_project_stage_draft_workflow` | `backend/app/services/stage_drafts.py` |
| `prepare_stage_confirmation_workflow` | `backend/app/services/stage_confirmations.py` |
| `resolve_pending_confirm_paths` | `backend/app/services/pending_confirms.py` |
| `refresh_project_stage_verification_workflow` | `backend/app/services/verification_refresh.py` |
| `remap_extracted` | `backend/app/services/extraction_transforms.py` |
| `require_verified_system_actor` | `backend/app/api/deps.py` |
| `require_router_mode` | `backend/app/services/chat_router_mode.py` |
| `resolve_verified_org_context` | `backend/app/api/deps.py` |
| `set_system_rls_context` | `backend/app/api/deps.py` |
| `prompt_template_row_to_payload` | `backend/app/services/prompt_templates.py` |
| `resolve_explicit_router_mode` | `backend/app/services/chat_router_mode.py` |
| `resolve_pending_confirm_context` | `backend/app/services/pending_confirms.py` |
| `resolve_pending_confirm_workflow` | `backend/app/services/pending_confirms.py` |
| `resolve_project_creation_question_setup` | `backend/app/services/project_creation.py` |
| `resolve_standard_question_routing` | `backend/app/services/chat_turn_commit_shapers.py` |
| `resolve_stage_initial_questions` | `backend/app/services/stage_question_setup.py` |
| `resolve_stage_missing_paths` | `backend/app/services/stage_question_setup.py` |
| `resolve_answer_rubric_id` | `backend/app/services/chat_question_runtime.py` |
| `resolve_askable_question_id` | `backend/app/services/chat_question_runtime.py` |
| `resolve_initial_questions` | `backend/app/services/chat_question_runtime.py` |
| `resolve_missing_paths` | `backend/app/services/chat_question_runtime.py` |
| `resolve_next_question_id` | `backend/app/services/chat_question_runtime.py` |
| `resolve_repair_question` | `backend/app/services/chat_question_runtime.py` |
| `resolve_unique_prompt_template_version` | `backend/app/services/prompt_templates.py` |
| `resolve_next_stage` | `backend/app/services/chat_stage_gate.py` |
| `resolve_question_verification_status` | `backend/app/services/stage_verifications.py` |
| `resolve_verification_provider_unavailable_reason` | `backend/app/services/assessment_summaries.py` |
| `sanitize_composed_question` | `backend/app/services/chat_followup_compose.py` |
| `sanitize_rewritten_prompt` | `backend/app/services/chat_followup_compose.py` |
| `select_fallback_followup` | `backend/app/services/chat_followup_compose.py` |
| `select_followup_answer_pattern` | `backend/app/services/chat_followup_compose.py` |
| `run_question_rewrite` | `backend/app/services/project_question_prompts.py` |
| `run_chat_question_rewrite` | `backend/app/services/project_question_prompts.py` |
| `run_extract_answer_v0` | `backend/app/services/answer_extraction_worker_handler.py` |
| `run_answer_extraction` | `backend/app/services/chat_prompt_tasks.py` |
| `run_answer_gate` | `backend/app/services/chat_prompt_tasks.py` |
| `run_answer_gate_for_context` | `backend/app/services/chat_prompt_tasks.py` |
| `run_report_generation_v0` | `backend/app/services/report_generation_worker_handler.py` |
| `run_stage_finalize_v0` | `backend/app/services/stage_finalize_worker_handler.py` |
| `run_stage_summary_v0` | `backend/app/services/stage_summary_worker_handler.py` |
| `run_sync_answer_extraction` | `backend/app/services/chat_prompt_tasks.py` |
| `run_sync_answer_extraction_for_context` | `backend/app/services/chat_prompt_tasks.py` |
| `run_verify_question_claims_v0` | `backend/app/services/verification_job_handler.py` |
| `sse_event` | `backend/app/services/chat_stream/events.py` |
| `sse_status_event` | `backend/app/services/chat_stream/events.py` |
| `resolve_report_confirmation_prerequisites` | `backend/app/services/report_confirmations.py` |
| `valid_pending_confirm_update_paths` | `backend/app/services/pending_confirms.py` |
| `sync_runtime_gate_state` | `backend/app/services/project_gate_sync.py` |
| `answer_verification_job_idempotency_key` | `backend/app/services/verification_jobs.py` |
| `summary_verification_job_idempotency_key` | `backend/app/services/verification_jobs.py` |
| `enqueue_answer_question_verification_job` | `backend/app/services/verification_jobs.py` |
| `enqueue_summary_question_verification_job` | `backend/app/services/verification_jobs.py` |
| `requeue_question_verification_job` | `backend/app/services/verification_jobs.py` |
| `update_pending_confirm_context` | `backend/app/services/pending_confirms.py` |
| `update_pending_confirm_workflow` | `backend/app/services/pending_confirms.py` |
| `update_streamed_question_message` | `backend/app/services/chat_stream/message_persistence.py` |
| `normalize_question_bank_key` | `backend/app/services/question_bank_drafts.py` |
| `import_question_bank_draft_json` | `backend/app/services/question_bank_draft_imports.py` |
| `import_question_bank_draft_yaml` | `backend/app/services/question_bank_draft_imports.py` |
| `is_ai_assist_request` | `backend/app/services/chat_ai_assist.py` |
| `is_ai_draft_tagged` | `backend/app/services/chat_ai_assist.py` |
| `publish_question_bank_draft` | `backend/app/services/question_bank_publish.py` |
| `persist_ai_draft_message` | `backend/app/services/chat_ai_assist.py` |
| `persist_fallback_question_message` | `backend/app/services/chat_stream/message_persistence.py` |
| `plan_question_prompt` | `backend/app/services/chat_question_runtime.py` |
| `resolve_stage_summary_generation_status` | `backend/app/services/stage_drafts.py` |
| `resolve_gate_and_sync_extraction` | `backend/app/services/chat_gate_resolution.py` |
| `requires_single_sentence` | `backend/app/services/chat_ai_assist.py` |
| `run_ai_assist_draft` | `backend/app/services/chat_ai_assist.py` |
| `run_ai_assist_draft_stream` | `backend/app/services/chat_ai_assist.py` |
| `schedule_project_stage_verification_refresh` | `backend/app/services/verification_refresh.py` |
| `select_extraction_answer` | `backend/app/services/chat_turn_context.py` |
| `select_gate_answer` | `backend/app/services/chat_turn_context.py` |
| `select_transition_state_payload` | `backend/app/services/chat_turn_commit_shapers.py` |
| `should_update_chat_state_meta` | `backend/app/services/chat_turn_commit_shapers.py` |
| `stage_summary_retryable` | `backend/app/services/stage_drafts.py` |
| `stage_summary_label` | `backend/app/services/stage_summary_fallbacks.py` |
| `stage_summary_value` | `backend/app/services/stage_summary_fallbacks.py` |
| `stream_text_events` | `backend/app/services/chat_stream/events.py` |
| `stream_question_response_events` | `backend/app/services/chat_stream/question_response.py` |
| `strip_ai_draft_prefix` | `backend/app/services/chat_ai_assist.py` |
| `truncate_context_value` | `backend/app/services/chat_turn_context.py` |
| `split_state_path` | `backend/app/services/extraction_transforms.py` |
| `split_context_path` | `backend/app/services/context_paths.py` |
| `get_context_path_value` | `backend/app/services/context_paths.py` |
| `set_context_path_value` | `backend/app/services/context_paths.py` |
| `set_chat_session_context` | `backend/app/services/chat_context_reads.py` |
| `ensure_question_instance` | `backend/app/services/chat_question_runtime.py` |
| `should_enqueue_pass_answer_background_jobs` | `backend/app/services/chat_background_jobs.py` |
| `should_enter_stage_gate_review` | `backend/app/services/chat_stage_gate.py` |
| `should_attempt_question_planner` | `backend/app/services/chat_question_planning.py` |
| `should_skip_non_required_question` | `backend/app/services/chat_question_filters.py` |
| `pop_context_path_value` | `backend/app/services/context_paths.py` |
| `persist_confirmed_stage_assessment` | `backend/app/services/stage_confirmations.py` |
| `infer_context_path_stage` | `backend/app/services/context_paths.py` |
| `initialize_stage_confirmation_runtime` | `backend/app/services/stage_confirmations.py` |
| `enqueue_background_job` | `backend/app/services/background_jobs.py` |
| `enqueue_chat_pass_background_jobs` | `backend/app/services/chat_background_jobs.py` |
| `generate_answer_summary` | `backend/app/services/qa_digests.py` |
| `normalize_ai_assisted_map` | `backend/app/services/stage_payloads.py` |
| `normalize_user_edited_map` | `backend/app/services/stage_payloads.py` |
| `resolve_stage_paths` | `backend/app/services/stage_payloads.py` |
| `AdminModal` | `frontend/features/admin/components/shared/admin-modal.tsx` |
| `AdminOverviewClient` | `frontend/features/admin/components/overview/admin-overview.tsx` |
| `AdminOrgLogoModal` | `frontend/features/admin/components/org/settings/admin-org-logo-modal.tsx` |
| `AdminOrgSettingsClient` | `frontend/features/admin/components/org/settings/admin-org-settings-client.tsx` |
| `AdminOrgSettingsSurface` | `frontend/features/admin/components/org/settings/admin-org-settings-surface.tsx` |
| `AdminShell` | `frontend/features/admin/components/shared/admin-shell.tsx` |
| `AddCohortMembersModal` | `frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx` |
| `CohortDetail` | `frontend/features/admin/components/cohorts/cohort-detail.tsx` |
| `CohortDetailSurface` | `frontend/features/admin/components/cohorts/cohort-detail-surface.tsx` |
| `buildCohortsQuery` | `frontend/features/admin/admin-cohorts-view-model.ts` |
| `CohortsTableSurface` | `frontend/features/admin/components/cohorts/cohorts-table-surface.tsx` |
| `CohortsTable` | `frontend/features/admin/components/cohorts/cohorts-table.tsx` |
| `CreateCohortModal` | `frontend/features/admin/components/cohorts/cohort-modals.tsx` |
| `formatCohortTimeline` | `frontend/features/admin/admin-cohorts-view-model.ts` |
| `interpolateCohortMessage` | `frontend/features/admin/admin-cohorts-view-model.ts` |
| `resolveCohortIntlLocale` | `frontend/features/admin/admin-cohorts-view-model.ts` |
| `ContextStageNav` | `frontend/features/context/live-context-controls.tsx` |
| `ContextViewToggle` | `frontend/features/context/live-context-controls.tsx` |
| `DiagnosisView` | `frontend/features/context/live-context-diagnosis-view.tsx` |
| `DeleteProjectModal` | `frontend/features/projects/project-action-modals.tsx` |
| `DeleteProjectCommentModal` | `frontend/features/admin/components/projects/project-detail-dialogs.tsx` |
| `EditProjectModal` | `frontend/features/admin/components/projects/project-detail-dialogs.tsx` |
| `FaqAndCtaSection` | `frontend/components/marketing/HomePageFaqSection.tsx` |
| `LiveContextBoard` | `frontend/features/context/live-context-board.tsx` |
| `LiveContextBoardSurface` | `frontend/features/context/live-context-board-surface.tsx` |
| `LiveContextBoardHeader` | `frontend/features/context/live-context-review-panels.tsx` |
| `LiveContextReviewCta` | `frontend/features/context/live-context-review-panels.tsx` |
| `LiveContextReviewPanel` | `frontend/features/context/live-context-review-panels.tsx` |
| `LiveDraftView` | `frontend/features/context/live-context-draft-view.tsx` |
| `useLiveContextEditing` | `frontend/features/context/use-live-context-editing.ts` |
| `MarketingHeader` | `frontend/components/marketing/HomePageHeader.tsx` |
| `ORG_SETTINGS_MESSAGES` | `frontend/features/admin/org-settings-messages.ts` |
| `PROMPT_MESSAGES` | `frontend/features/admin/prompt-template-messages.ts` |
| `formatStageLabel` | `frontend/features/admin/prompt-template-view-model.ts` |
| `groupTemplates` | `frontend/features/admin/prompt-template-view-model.ts` |
| `parseStageList` | `frontend/features/admin/prompt-template-view-model.ts` |
| `PromptTemplatesClient` | `frontend/features/admin/components/org/prompts/prompt-templates-client.tsx` |
| `PromptTemplatesSurface` | `frontend/features/admin/components/org/prompts/prompt-templates-surface.tsx` |
| `RemoveCohortMemberModal` | `frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx` |
| `RenameProjectModal` | `frontend/features/projects/project-action-modals.tsx` |
| `HomePageDvfSection` | `frontend/components/marketing/HomePageDvfSection.tsx` |
| `HomePageHeroSection` | `frontend/components/marketing/HomePageIntroSections.tsx` |
| `HomePageProblemSection` | `frontend/components/marketing/HomePageIntroSections.tsx` |
| `HomePageReportSection` | `frontend/components/marketing/HomePageReportSection.tsx` |
| `HomePageSectionReveal` | `frontend/components/marketing/HomePageSectionShell.tsx` |
| `HomePageSectionShell` | `frontend/components/marketing/HomePageSectionShell.tsx` |
| `HomePageTrustSection` | `frontend/components/marketing/HomePageTrustSection.tsx` |
| `MethodologyPageView` | `frontend/components/marketing/MethodologyPageView.tsx` |
| `HeroSection` | `frontend/components/marketing/MethodologyIntroSections.tsx` |
| `WhySection` | `frontend/components/marketing/MethodologyIntroSections.tsx` |
| `FrameworkSection` | `frontend/components/marketing/MethodologyFrameworkSection.tsx` |
| `ReviewSection` | `frontend/components/marketing/MethodologyReviewSection.tsx` |
| `OutputsSection` | `frontend/components/marketing/MethodologyOutputSections.tsx` |
| `ClosingSection` | `frontend/components/marketing/MethodologyOutputSections.tsx` |
| `SectionHeading` | `frontend/components/marketing/methodology-page-utils.tsx` |
| `SectionReveal` | `frontend/components/marketing/methodology-page-utils.tsx` |
| `StageInsightView` | `frontend/features/context/live-context-insight-view.tsx` |
| `InvitesTable` | `frontend/features/admin/components/org/invites-table.tsx` |
| `CreateInviteModal` | `frontend/features/admin/components/org/invite-modals.tsx` |
| `RevokeInviteModal` | `frontend/features/admin/components/org/invite-modals.tsx` |
| `InvitesTableSurface` | `frontend/features/admin/components/org/invites-table-surface.tsx` |
| `buildInvitesQuery` | `frontend/features/admin/admin-invites-view-model.ts` |
| `formatInviteDate` | `frontend/features/admin/admin-invites-view-model.ts` |
| `interpolateInviteMessage` | `frontend/features/admin/admin-invites-view-model.ts` |
| `MembersTable` | `frontend/features/admin/components/org/members-table.tsx` |
| `MembersTableSurface` | `frontend/features/admin/components/org/members-table-surface.tsx` |
| `RemoveMemberModal` | `frontend/features/admin/components/org/member-modals.tsx` |
| `buildMembersQuery` | `frontend/features/admin/admin-members-view-model.ts` |
| `formatMemberDate` | `frontend/features/admin/admin-members-view-model.ts` |
| `interpolateMemberMessage` | `frontend/features/admin/admin-members-view-model.ts` |
| `resolveMemberInitials` | `frontend/features/admin/admin-members-view-model.ts` |
| `AssignmentFormModal` | `frontend/features/admin/components/org/mentor-assignments-modals.tsx` |
| `AssignmentToast` | `frontend/features/admin/components/org/mentor-assignments-modals.tsx` |
| `ASSIGNMENT_STATUS_VARIANTS` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `buildAssignmentsQuery` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `buildMentorAssignmentMemberLabel` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `ensureMentorAssignmentOption` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `interpolateMentorAssignmentMessage` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `MentorAssignmentsSurface` | `frontend/features/admin/components/org/mentor-assignments-panels.tsx` |
| `MentorAssignmentsTable` | `frontend/features/admin/components/org/mentor-assignments-table.tsx` |
| `RevokeAssignmentModal` | `frontend/features/admin/components/org/mentor-assignments-modals.tsx` |
| `resolveMentorAssignmentInitials` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `resolveMentorAssignmentIntlLocale` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `toCohortMemberOptions` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `toMemberOptions` | `frontend/features/admin/admin-mentor-assignments-view-model.ts` |
| `ProjectDetail` | `frontend/features/admin/components/projects/project-detail.tsx` |
| `ProjectDetailSurface` | `frontend/features/admin/components/projects/project-detail-surface.tsx` |
| `ProjectsOrgPickerModal` | `frontend/features/projects/projects-workspace-panels.tsx` |
| `ProjectsTable` | `frontend/features/admin/components/projects/projects-table.tsx` |
| `ProjectsWorkspaceContent` | `frontend/features/projects/projects-workspace-panels.tsx` |
| `ProjectsWorkspaceFilters` | `frontend/features/projects/projects-workspace-panels.tsx` |
| `ProjectsWorkspaceHeader` | `frontend/features/projects/projects-workspace-panels.tsx` |
| `ProjectsWorkspaceTabs` | `frontend/features/projects/projects-workspace-panels.tsx` |
| `QuestionBankQuestionsPanel` | `frontend/features/admin/components/org/question-banks/question-bank-questions-panel.tsx` |
| `ArchitectureDiagramCard` | `frontend/features/reports/report-viewer-technical-cards.tsx` |
| `DataQualityCard` | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| `DiagnosisCard` | `frontend/features/reports/report-viewer-diagnosis-cards.tsx` |
| `DvfAssessmentCard` | `frontend/features/reports/report-viewer-score-cards.tsx` |
| `DvfScoreboardCard` | `frontend/features/reports/report-viewer-score-cards.tsx` |
| `KeyRisksCard` | `frontend/features/reports/report-viewer-technical-cards.tsx` |
| `LeanCanvasCard` | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| `MarketEvidenceCard` | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| `OverallSummaryCard` | `frontend/features/reports/report-viewer-technical-cards.tsx` |
| `ReportDocument` | `frontend/features/reports/report-document.tsx` |
| `ReportJobStatusCard` | `frontend/features/reports/report-job-status-card.tsx` |
| `ReportQualityDashboard` | `frontend/features/admin/components/platform/report-quality-dashboard.tsx` |
| `ReportQualityDashboardSurface` | `frontend/features/admin/components/platform/report-quality-dashboard-surface.tsx` |
| `REPORT_QUALITY_MESSAGES` | `frontend/features/admin/components/platform/report-quality-dashboard-messages.ts` |
| `ReportSnapshotCard` | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| `ReportV2ArtifactCard` | `frontend/features/reports/report-viewer-v2-cards.tsx` |
| `ReportViewer` | `frontend/features/reports/report-viewer.tsx` |
| `ReportViewerSurface` | `frontend/features/reports/report-viewer-surface.tsx` |
| `build_quality_observation_filters` | `backend/app/services/platform_report_quality.py` |
| `fetch_report_quality_summary_payload` | `backend/app/services/platform_report_quality.py` |
| `get_report_quality_observation_payload` | `backend/app/services/platform_report_quality.py` |
| `list_report_quality_observation_payloads` | `backend/app/services/platform_report_quality.py` |
| `normalize_quality_status` | `backend/app/services/platform_report_quality.py` |
| `row_to_report_quality_detail_payload` | `backend/app/services/platform_report_quality.py` |
| `row_to_report_quality_item_payload` | `backend/app/services/platform_report_quality.py` |
| `build_platform_settings_payload` | `backend/app/services/platform_settings.py` |
| `fetch_platform_settings_payload` | `backend/app/services/platform_settings.py` |
| `normalize_setting_key` | `backend/app/services/platform_settings.py` |
| `row_to_platform_setting_entry_payload` | `backend/app/services/platform_settings.py` |
| `update_platform_settings_payload` | `backend/app/services/platform_settings.py` |
| `list_platform_admin_payloads` | `backend/app/services/platform_admin_users.py` |
| `row_to_platform_admin_payload` | `backend/app/services/platform_admin_users.py` |
| `upsert_platform_admin_payload` | `backend/app/services/platform_admin_users.py` |
| `build_platform_org_filters` | `backend/app/services/platform_orgs.py` |
| `fetch_platform_orgs_payload` | `backend/app/services/platform_orgs.py` |
| `row_to_platform_org_payload` | `backend/app/services/platform_orgs.py` |
| `update_platform_org_payload` | `backend/app/services/platform_orgs.py` |
| `ReportsTable` | `frontend/features/admin/components/reports/reports-table.tsx` |
| `ReportsTableSurface` | `frontend/features/admin/components/reports/reports-table-surface.tsx` |
| `SampleReportHero` | `frontend/features/reports/sample-report-hero.tsx` |
| `ValidationPlanCard` | `frontend/features/reports/report-viewer-diagnosis-cards.tsx` |
| `VerificationSummaryCard` | `frontend/features/reports/report-viewer-summary-cards.tsx` |
| `buildApiUrl` | `frontend/lib/api/client.ts` |
| `buildContextSections` | `frontend/features/context/live-context-formatters.tsx` |
| `build_report_prompt` | `backend/app/services/report_prompt_tasks.py` |
| `list_active_global_prompt_template_payloads` | `backend/app/services/prompt_templates.py` |
| `buildSampleVerificationSnapshot` | `frontend/features/reports/report-sample-verification.ts` |
| `filterProjects` | `frontend/features/projects/projects-workspace-utils.tsx` |
| `formatSettings` | `frontend/features/admin/org-settings-view-model.ts` |
| `getSafeErrorMessage` | `frontend/lib/api/safe-error-message.ts` |
| `getSafeStatusErrorMessage` | `frontend/lib/api/safe-error-message.ts` |
| `getSafeResponseErrorMessage` | `frontend/lib/api/safe-error-message.ts` |
| `normalizeReportJobStatus` | `frontend/features/reports/reports-api.ts` |
| `resolveOrgSlug` | `frontend/features/admin/org-settings-view-model.ts` |
| `useActiveMarketingSection` | `frontend/components/marketing/home-page-utils.ts` |
| `useMarketingPageContent` | `frontend/components/marketing/home-page-utils.ts` |

Add symbols here and in `scripts/architecture_guard.py` when a helper becomes a
shared contract rather than a local implementation detail.

The guard also rejects these old local helper aliases so split route modules do
not recreate parallel implementations:

| Forbidden local helper | Canonical owner |
| --- | --- |
| `_build_skip_decision` | `backend/app/services/chat_answer_actions.py` |
| `_apply_router_mode_selection_guard` | `backend/app/services/chat_router_mode.py` |
| `_augment_router_mode_message_meta` | `backend/app/services/chat_router_mode.py` |
| `_build_router_mode_selection_followup` | `backend/app/services/chat_router_mode.py` |
| `_build_sync_extraction_preview` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_prepare_extraction_updates` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_apply_extraction_updates_to_state` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_apply_extraction_fallbacks` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_update_ai_assisted_paths` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_canonicalize_market_type_fields` | `backend/app/services/chat_market_type_normalization.py` |
| `_infer_frequency_from_answer` | `backend/app/services/chat_sync_extraction_preview.py` |
| `_apply_group_override` | `backend/app/services/chat_question_planning.py` |
| `_apply_transition_prefix` | `backend/app/services/chat_question_planning.py` |
| `_build_group_prompt` | `backend/app/services/chat_question_planning.py` |
| `_build_question_group_payload` | `backend/app/services/chat_question_planning.py` |
| `_build_question_meta_payload` | `backend/app/services/chat_question_planning.py` |
| `_build_question_plan_context` | `backend/app/services/chat_question_planning.py` |
| `_build_transition_text` | `backend/app/services/chat_question_planning.py` |
| `_fetch_group_meta` | `backend/app/services/chat_question_planning.py` |
| `_fetch_question_planner_candidates` | `backend/app/services/chat_question_planning.py` |
| `_format_candidate_list` | `backend/app/services/chat_question_planning.py` |
| `_merge_group_details` | `backend/app/services/chat_question_planning.py` |
| `_merge_group_strings` | `backend/app/services/chat_question_planning.py` |
| `_normalize_planner_selection` | `backend/app/services/chat_question_planning.py` |
| `_persist_question_plan` | `backend/app/services/chat_question_planning.py` |
| `_planner_stage_allowed` | `backend/app/services/chat_question_planning.py` |
| `_question_has_missing_paths` | `backend/app/services/chat_question_planning.py` |
| `_question_overlaps_only_deferred_paths` | `backend/app/services/chat_question_planning.py` |
| `_question_schema_paths` | `backend/app/services/chat_question_planning.py` |
| `_question_supports_grouping` | `backend/app/services/chat_question_planning.py` |
| `_resolve_question_group` | `backend/app/services/chat_question_planning.py` |
| `_resolve_question_group_plan` | `backend/app/services/chat_question_planning.py` |
| `_should_attempt_question_planner` | `backend/app/services/chat_question_planning.py` |
| `_build_invite_link` | `backend/app/services/org_invite_links.py` |
| `_resolve_app_base_url` | `backend/app/services/org_invite_links.py` |
| `_run_extract_answer_v0` | `backend/app/services/answer_extraction_worker_handler.py` |
| `_run_report_generation_v0` | `backend/app/services/report_generation_worker_handler.py` |
| `_run_stage_finalize_v0` | `backend/app/services/stage_finalize_worker_handler.py` |
| `_build_stream_error_payload` | `backend/app/services/chat_stream/events.py` |
| `_build_streamed_question_message_meta` | `backend/app/services/chat_stream/events.py` |
| `_build_turn_event_meta` | `backend/app/services/chat_stream/events.py` |
| `_latency_span` | `backend/app/services/chat_stream/latency.py` |
| `_log_chat_stream_latency` | `backend/app/services/chat_stream/latency.py` |
| `_record_latency_span` | `backend/app/services/chat_stream/latency.py` |
| `_build_project_description_prompt` | `backend/app/services/prompt_runtime.py` and `backend/app/services/stage_finalize_worker_handler.py` |
| `_build_summary_prompt` | `backend/app/services/prompt_runtime.py` and `backend/app/services/stage_summary_worker_handler.py` |
| `DEFAULT_PROMPT_TASK_SPECS` | `backend/app/services/prompt_task_specs.py` |
| `PromptContextBuilder` | `backend/app/services/prompt_context_builders.py` |
| `PromptMutationClass` | `backend/app/services/prompt_task_specs.py` |
| `PromptTaskSpec` | `backend/app/services/prompt_task_specs.py` |
| `PreviewFieldFallbackHelpers` | `backend/app/services/chat_sync_preview_field_fallbacks.py` |
| `assessment_summary_by_stage` | `backend/app/core/report_sections.py` |
| `build_report_recovery_sections` | `backend/app/core/report_recovery_sections.py` |
| `build_report_v2_sections` | `backend/app/core/report_sections.py` |
| `compact_report_text` | `backend/app/core/report_sections.py` |
| `fallback_decision_band` | `backend/app/core/report_sections.py` |
| `fallback_dimension_score` | `backend/app/core/report_sections.py` |
| `normalize_report_value` | `backend/app/core/report_sections.py` |
| `scoreboard_has_scores` | `backend/app/core/report_sections.py` |
| `to_report_score` | `backend/app/core/report_sections.py` |
| `execution_trace` | `backend/app/services/prompt_runtime_execution.py` |
| `failure_result` | `backend/app/services/prompt_runtime_execution.py` |
| `preparation_failure_result` | `backend/app/services/prompt_runtime_execution.py` |
| `resolve_prompt_task_timeout_ms` | `backend/app/services/prompt_runtime_execution.py` |
| `serialize_prompt_task_trace` | `backend/app/services/prompt_runtime_execution.py` |
| `stream_failure_result` | `backend/app/services/prompt_runtime_execution.py` |
| `_resolve_unique_version` | `backend/app/services/prompt_templates.py` |
| `_row_to_prompt_template` | `backend/app/services/prompt_templates.py` |
| `_followup_compose_enabled` | `backend/app/services/chat_runtime_settings.py` |
| `_parse_csv_set` | `backend/app/services/chat_runtime_settings.py` |
| `_parse_env_flag` | `backend/app/services/chat_runtime_settings.py` |
| `_question_compose_enabled` | `backend/app/services/chat_runtime_settings.py` |
| `_resolve_question_compose_start_timeout_sec` | `backend/app/services/chat_runtime_settings.py` |
| `_resolve_question_group_settings` | `backend/app/services/chat_runtime_settings.py` |
| `_resolve_question_planner_settings` | `backend/app/services/chat_runtime_settings.py` |
| `_claim_verdict_counts` | `backend/app/services/stage_verifications.py` |
| `_collect_sources_from_claims` | `backend/app/services/stage_verifications.py` |
| `_build_schema_key_map` | `backend/app/services/extraction_transforms.py` |
| `_canonicalize_extraction_update_value` | `backend/app/services/extraction_transforms.py` |
| `_extract_value_meta` | `backend/app/services/extraction_transforms.py` |
| `_extract_answer_action` | `backend/app/services/chat_output_locale.py` |
| `_extract_mode_from_state` | `backend/app/services/chat_router_mode.py` |
| `_extract_router_mode_from_message_meta` | `backend/app/services/chat_router_mode.py` |
| `_extract_router_mode_from_text` | `backend/app/services/chat_router_mode.py` |
| `_extract_skip_reason` | `backend/app/services/chat_answer_actions.py` |
| `_flatten_dict` | `backend/app/services/extraction_transforms.py` |
| `_get_nested_state_value` | `backend/app/services/extraction_transforms.py` |
| `_generate_project_description` | `backend/app/services/stage_finalize_worker_handler.py` |
| `_generate_stage_summary` | `backend/app/services/stage_summary_worker_handler.py` |
| `_generate_structured_report` | `backend/app/services/report_generation_worker_handler.py` |
| `_has_explicit_none` | `backend/app/services/extraction_transforms.py` |
| `_increment_verification_summary` | `backend/app/services/stage_verifications.py` |
| `_is_not_applicable_rationale` | `backend/app/services/stage_verifications.py` |
| `_is_quick_action_answer` | `backend/app/services/chat_output_locale.py` |
| `_is_stage_gate_ready_for_review` | `backend/app/services/chat_stage_gate.py` |
| `_normalize_key` | `backend/app/services/extraction_transforms.py` |
| `_normalize_router_mode` | `backend/app/services/chat_router_mode.py` |
| `_remap_extracted` | `backend/app/services/extraction_transforms.py` |
| `_require_router_mode` | `backend/app/services/chat_router_mode.py` |
| `_resolve_explicit_router_mode` | `backend/app/services/chat_router_mode.py` |
| `_resolve_followup_output_locale` | `backend/app/services/chat_output_locale.py` |
| `_resolve_interview_output_locale` | `backend/app/services/chat_output_locale.py` |
| `_resolve_next_stage` | `backend/app/services/chat_stage_gate.py` |
| `_resolve_question_verification_status` | `backend/app/services/stage_verifications.py` |
| `_ensure_project_report_access` | `backend/app/services/project_report_access.py` |
| `_run_answer_extraction` | `backend/app/services/chat_prompt_tasks.py` |
| `_run_answer_gate` | `backend/app/services/chat_prompt_tasks.py` |
| `_run_answer_gate_for_context` | `backend/app/services/chat_prompt_tasks.py` |
| `_split_state_path` | `backend/app/services/extraction_transforms.py` |
| `_should_enter_stage_gate_review` | `backend/app/services/chat_stage_gate.py` |
| `_run_sync_answer_extraction` | `backend/app/services/chat_prompt_tasks.py` |
| `_run_sync_answer_extraction_for_context` | `backend/app/services/chat_prompt_tasks.py` |
| `_sse_event` | `backend/app/services/chat_stream/events.py` |
| `_sse_status_event` | `backend/app/services/chat_stream/events.py` |
| `_stream_text_events` | `backend/app/services/chat_stream/events.py` |
| `_normalize_ai_assisted_map` | `backend/app/services/stage_payloads.py` |
| `_normalize_user_edited_map` | `backend/app/services/stage_payloads.py` |

The guard also rejects direct extraction/verification background job enqueue
references in `backend/app/api/routes/chat.py`; use
`backend/app/services/chat_background_jobs.py` for that route-owned trigger.

## Known Consolidation Candidates

These areas have existing duplication or direct-write patterns. Do not add a
new copy. If touched, prefer consolidating them behind the owner named above and
then promote the owner into `scripts/architecture_guard.py`.

| Area | Current risk | Next hygiene move |
| --- | --- | --- |
| Route workflow orchestration | Some route handlers still mix HTTP concerns with multi-step service workflows. | Move workflow bodies into service modules while keeping permission checks and HTTP error mapping at the route boundary. |
| Chat and worker extraction fallbacks | Shared extraction target-assignment and transform helpers live in `backend/app/services/extraction_transforms.py`; chat visible-path preview assembly and fallback value extraction live in `backend/app/services/chat_sync_extraction_preview.py`; preview-only question/schema matchers live in `backend/app/services/chat_sync_preview_question_matchers.py`; preview-only field fallback assembly lives in `backend/app/services/chat_sync_preview_field_fallbacks.py`; preview-only post-fallback state/meta patching lives in `backend/app/services/chat_sync_preview_post_fallbacks.py`; authoritative worker fallback value extraction lives in `backend/app/services/answer_extraction_worker_fallbacks.py`; authoritative worker market canonicalization and market missing-path adjustment live in `backend/app/services/answer_extraction_worker_market.py`; authoritative worker mutation semantics live in `backend/app/services/answer_extraction_worker_handler.py`. | Do not merge preview and authoritative fallback behavior unless tests prove their product semantics match. |

## AI Change Checklist

Before changing a split-prone boundary, an AI coding assistant should verify:

1. The boundary has a canonical owner in this map.
2. The change edits that owner or intentionally moves ownership.
3. Old routes, helpers, client utilities, and call paths are deleted or rewired
   in the same change.
4. Any temporary migration path has an owner, removal condition, and tests.
5. `make architecture-check` and the relevant product tests pass.
