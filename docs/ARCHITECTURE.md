# Architecture

## Current Status
- The current FastAPI backend and PostgreSQL schema are the active architecture.
- The core product flow is live in code: auth, projects, staged chat, context extraction, stage confirmation, and reports.
- This document is maintained alongside implementation and may lag slightly behind fast-moving modules.

## System Overview
- Frontend: Next.js app in `frontend/` (App Router).
- Backend: FastAPI app in `backend/`.
- Database: Postgres migrations in `database/`.
- Auth routes: `backend/app/api/routes/auth.py` remains the HTTP boundary for
  auth request validation, captcha/rate-limit handling, bearer token response
  creation, and HTTP error mapping. Auth route request/response DTOs live in
  `backend/app/schemas/auth.py`. Local registration
  workflow orchestration, including persisted user/org data shaping,
  organization/user/profile/identity/membership writes, email-verification token
  issuance, and verification email delivery, lives in
  `backend/app/services/auth_registration.py`. Local password reset request and
  confirm workflow orchestration, including reset-eligible user lookup, reset
  token issuance, reset email delivery behavior, password hash update, and reset
  token consumption, lives in `backend/app/services/auth_password_reset.py`.
  Local email verification and resend workflow orchestration, including token
  validation, resend user lookup, already-verified detection, email validation,
  verification token issuance, and verification email delivery, lives in
  `backend/app/services/auth_email_verification.py`. Local login and dev-login
  workflow orchestration, including credential lookup, dev-login lookup, active
  membership enforcement, and login failure counter mutation, lives in
  `backend/app/services/auth_login.py`.
- Prompt runtime: `backend/app/services/prompt_runtime.py` defines the
  IdeaSense LLM runtime registry facade, sectioned prompt context builder
  public API, trace redaction metadata, and shared execution entrypoints for
  selected prompt tasks. Prompt task metadata, mutation boundaries, and default
  task spec definitions live in `backend/app/services/prompt_task_specs.py`.
  Prompt context builder implementation and pure section-assembly helpers live in
  `backend/app/services/prompt_context_builders.py`. Prompt runtime execution
  trace, timeout, fallback, and failure-result helpers live in
  `backend/app/services/prompt_runtime_execution.py`. Chat, assessment, report,
  and verification workflows remain in their existing route/service owners.
- Chat runtime helpers: `backend/app/api/routes/chat.py` remains the HTTP and
  streaming route boundary. Shared stream event and metadata formatting lives
  in `backend/app/services/chat_stream/events.py`; chat stream latency
  instrumentation lives in `backend/app/services/chat_stream/latency.py`;
  streamed assistant question message persistence lives in
  `backend/app/services/chat_stream/message_persistence.py`;
  chat context read helpers, question-detail context assembly, and chat
  session RLS context setup live in
  `backend/app/services/chat_context_reads.py`;
  chat runtime settings parsing lives in
  `backend/app/services/chat_runtime_settings.py`;
  chat-specific question rewrite prompt execution lives in
  `backend/app/services/project_question_prompts.py`;
  chat question runtime reads, routing helpers, repair-question selection,
  early next-question planning, question-instance initialization, and answer
  rubric lookup live in `backend/app/services/chat_question_runtime.py`;
  answer-gate and sync-extraction prompt task wrappers live in
  `backend/app/services/chat_prompt_tasks.py`;
  AI-assist draft request detection, draft prompt execution, draft message
  formatting, and draft metadata persistence live in
  `backend/app/services/chat_ai_assist.py`;
  answer-gate resolution and repeated-follow-up partial-unknown metadata
  marking live in `backend/app/services/chat_gate_resolution.py`;
  turn answer evaluation, sync-extraction preview resolution, heuristic
  enrichment, and router-mode answer guard orchestration live in
  `backend/app/services/chat_turn_evaluation.py`;
  turn preflight user-message persistence and gate-context assembly live in
  `backend/app/services/chat_turn_preflight.py`;
  turn result dataclasses and pure answer-score payload assembly live in
  `backend/app/services/chat_turn_payloads.py`;
  turn commit workflow writes live in
  `backend/app/services/chat_turn_commit.py`;
  pure turn-commit state/meta patch shaping, skip-answer status metadata,
  runtime missing-path derivation, transition-state selection, router/state
  event patch shaping, stage-gate-ready payload shaping, routing state fallback,
  and repeated next-question assistant/result payload assembly live in
  `backend/app/services/chat_turn_commit_shapers.py`;
  question response compose streaming, fallback streaming, and streamed
  assistant message update orchestration live in
  `backend/app/services/chat_stream/question_response.py`;
  turn-scoped assistant metadata, extracted key point collection, answer
  selection, and gate context summary shaping live in
  `backend/app/services/chat_turn_context.py`;
  chat visible-copy sanitization, follow-up message shaping, answer-gate
  decision payload shaping, repeated-follow-up cap logic, and
  question/follow-up compose stream-context assembly live in
  `backend/app/services/chat_followup_compose.py`;
  optional/conditional question skip heuristics, trigger keyword checks,
  missing-path state filtering, and market-specific missing-path adjustments
  live in `backend/app/services/chat_question_filters.py`;
  chat market type normalization and context-state market type inference live in
  `backend/app/services/chat_market_type_normalization.py`;
  question planning, deterministic grouping, planner selection, question-group
  metadata, and question plan persistence live in
  `backend/app/services/chat_question_planning.py`;
  chat visible-path sync extraction preview assembly lives in
  `backend/app/services/chat_sync_extraction_preview.py`;
  preview-only question/schema matchers live in
  `backend/app/services/chat_sync_preview_question_matchers.py`;
  preview-only answer parser compatibility exports live in
  `backend/app/services/chat_sync_preview_answer_parsers.py`; problem/impact/
  evidence, market, and technical parser domain helpers live in
  `backend/app/services/chat_sync_preview_problem_parsers.py`,
  `backend/app/services/chat_sync_preview_market_parsers.py`, and
  `backend/app/services/chat_sync_preview_tech_parsers.py`;
  preview-only field fallback assembly lives in
  `backend/app/services/chat_sync_preview_field_fallbacks.py`;
  preview-only post-fallback state/meta patching lives in
  `backend/app/services/chat_sync_preview_post_fallbacks.py`;
  shared pure answer-text parsing and question heuristics used by preview and
  worker extraction live in
  `backend/app/services/extraction_text_heuristics.py`;
  shared extraction target-assignment and transform helpers live in
  `backend/app/services/extraction_transforms.py`; pass-answer background job
  triggers live in `backend/app/services/chat_background_jobs.py`; and chat
  technical router mode selection helpers live in
  `backend/app/services/chat_router_mode.py`; and chat stage-gate readiness
  helpers live in
  `backend/app/services/chat_stage_gate.py`.
- Prompt runtime traces: redacted traces are persisted in existing artifact JSONB
  containers and exposed through an org-admin debug endpoint for project-level
  diagnosis. They include execution latency and parse status but not raw prompts,
  and they are not part of normal student/report views.
- Prompt template admin helpers: `backend/app/services/prompt_templates.py`
  owns shared prompt-template row payload normalization, unique-version
  resolution, active global list read-model assembly, and create-revision write
  workflow. Organization-admin and platform-admin prompt template routes keep
  their route-specific permission checks, org-specific list/revert behavior,
  and HTTP error mapping; platform-admin route DTOs live in
  `backend/app/schemas/platform_admin.py`.
- Platform report-quality read models:
  `backend/app/services/platform_report_quality.py` owns query status
  normalization, observation filtering, row-to-payload shaping, and
  summary/list/detail SQL read-model workflows. `backend/app/api/routes/platform_admin.py`
  keeps FastAPI query parameters, platform-admin permission checks, and HTTP
  error mapping; response DTOs live in `backend/app/schemas/platform_admin.py`.
- Platform settings workflow:
  `backend/app/services/platform_settings.py` owns setting-key normalization,
  update payload validation, settings read payload assembly, and settings
  upsert/delete workflow. `backend/app/api/routes/platform_admin.py` keeps
  FastAPI route declarations, platform-admin permission checks, and HTTP error
  mapping; request/response DTOs live in
  `backend/app/schemas/platform_admin.py`.
- Platform admin user management:
  `backend/app/services/platform_admin_users.py` owns admin row shaping, admin
  listing, user lookup, role/status validation, membership validation, and
  admin upsert workflow. `backend/app/api/routes/platform_admin.py` keeps
  FastAPI route declarations, platform-admin permission checks, and HTTP error
  mapping; request/response DTOs live in
  `backend/app/schemas/platform_admin.py`.
- Platform organization management:
  `backend/app/services/platform_orgs.py` owns organization row shaping, search
  filtering, list read-model assembly, update payload validation, and update
  workflow. `backend/app/api/routes/platform_admin.py` keeps FastAPI route
  declarations, platform-admin permission checks, and HTTP error mapping;
  request/response DTOs live in `backend/app/schemas/platform_admin.py`.
- Project creation workflow:
  `backend/app/services/project_creation.py` owns create payload normalization,
  bank-key validation, admin-session orchestration, membership resolution
  sequence, RLS context setup, question setup calls, record creation calls, and
  created-row payload assembly. `backend/app/api/routes/projects.py` keeps
  FastAPI route declarations, actor/header extraction, dependency wiring, and
  HTTP error mapping. Project route request/response DTOs live in
  `backend/app/schemas/projects.py`.
- Pending-confirm write workflows:
  `backend/app/services/pending_confirms.py` owns pending-confirm update and
  resolve admin-session orchestration, membership resolution, RLS context setup,
  update payload validation, accept/reject path normalization, and calls to the
  pending-confirm mutation helpers. `backend/app/api/routes/projects.py` keeps
  FastAPI route declarations, actor/header extraction, dependency wiring, and
  HTTP error mapping. Project route request/response DTOs live in
  `backend/app/schemas/projects.py`.
- Project report access gate:
  `backend/app/services/project_report_access.py` owns admin-session
  availability checks, system actor setup, email-verification gating, and
  project report access policy checks. `backend/app/api/routes/projects.py`
  keeps report route declarations, actor dependency wiring, output-locale query
  normalization, report payload/status service calls, and HTTP error mapping.
  Project route request/response DTOs live in `backend/app/schemas/projects.py`.
- Admin overview read-model assembly: `backend/app/services/admin_overview.py`
  owns organization dashboard SQL aggregation, metric/trend calculation,
  deadline assembly, pending-action assembly, and localized insight copy.
  Admin overview localized label, period, date bucket, and delta formatting
  helpers live in `backend/app/services/admin_overview_formatters.py`;
  admin overview activity-feed SQL and read-model assembly lives in
  `backend/app/services/admin_overview_activity.py`.
  `backend/app/api/routes/admin_overview.py` remains
  the HTTP boundary for dependency injection, org-admin permission checks,
  output-locale query normalization, response-model definitions, and response
  validation.
- Question-bank admin workflows: `backend/app/services/question_bank_drafts.py`
  owns admin question-bank draft creation and bank-key normalization.
  `backend/app/services/question_bank_draft_imports.py` owns admin
  question-bank draft YAML/JSON import orchestration, including payload parsing,
  import-mode semantics, question payload mapping, replace/merge writes, raw
  draft payload updates, and imported-question refetching.
  `backend/app/services/question_bank_publish.py` owns admin question-bank
  draft publish orchestration, including version collision handling, raw
  payload generation, content-hash reuse, active-version switching, question
  copy, and draft cleanup. `backend/app/api/routes/admin_question_banks.py`
  keeps HTTP schemas, permission checks, read/detail/update/reorder route
  behavior, import/publish HTTP mapping, and response-model conversion.
- Stage transition runtime: `backend/app/services/stage_transition.py` owns the
  pure decision rules for question-answering access, stage readiness, draft
  generation, confirmation advancement, and report completion.
  `backend/app/services/stage_runtime.py` owns normal project
  `stage_status` / `current_stage` writes that consume those decisions. Admin
  project edit routes remain an explicit privileged override boundary rather
  than part of the automated stage engine.
- Stage confirmation visible path: `POST /api/v1/assessments/{stage}/confirm`
  confirms a ready draft summary, advances project/runtime state, initializes
  the next stage or report-ready message, enqueues background jobs, and returns
  after the transaction commits. Stage-level DVF scoring, verification, QA
  digests, and project-description enrichment run through `stage_finalize_v0`
  in `background_jobs` so users do not wait on post-confirm AI work before
  seeing the next stage.
  `backend/app/services/stage_confirmations.py` owns the normal confirmation
  preparation and commit workflow; pure state-row normalization and
  preparation payload shaping lives in
  `backend/app/services/stage_confirmation_preparation.py`, while pure
  confirmed-stage persistence artifact payload shaping lives in
  `backend/app/services/stage_confirmation_persistence_payloads.py`. Public
  stage-confirmation errors, result dataclasses, prepared-workflow dataclass,
  and next-stage map live in
  `backend/app/services/stage_confirmation_types.py`.
  `backend/app/api/routes/assessments.py` keeps org/email boundary checks and
  HTTP error mapping, with assessment request/response DTOs in
  `backend/app/schemas/assessments.py` and verified assessment access context
  and system RLS setup shared through `backend/app/api/deps.py`.
  Stage draft route workflow, including
  project lookup, project
  mutation permission enforcement, and draft preparation, lives in
  `backend/app/services/stage_drafts.py`. Report confirmation route workflow,
  including project lookup, project mutation permission enforcement, and report
  job recovery/enqueue orchestration, lives in
  `backend/app/services/report_confirmations.py`. Verification refresh route
  workflow, including feature/provider skip behavior, stage normalization, and
  refresh job scheduling, lives in `backend/app/services/verification_refresh.py`.
- Background job worker ownership: `backend/app/worker.py` owns the polling,
  claim, lock, retry, and failure bookkeeping loop. Job bodies are service
  handlers: verification, stage summary, answer extraction, stage finalization,
  and report generation each live in their matching `backend/app/services/*`
  worker handler module. Authoritative answer extraction worker fallback value
  extraction lives in
  `backend/app/services/answer_extraction_worker_fallbacks.py`; authoritative
  answer extraction worker market canonicalization and market missing-path
  adjustment live in
  `backend/app/services/answer_extraction_worker_market.py`, while
  `backend/app/services/answer_extraction_worker_handler.py` keeps the worker
  handler facade, prompt execution wrapper, state writes, answer meta refresh,
  and stage/runtime update decisions. Shared background job primitives, sort helpers, and
  final-report prompt rendering wrappers live in services; deterministic report
  payload shaping remains in `backend/app/core/report_builder.py`.
  Deterministic report recovery fallback section assembly lives in
  `backend/app/core/report_recovery_sections.py`. Pure Report v2 section
  assembly for decision snapshot, score rationales, evidence index, risk
  register, and experiment plan lives in `backend/app/core/report_sections.py`.
  raw status normalization live in `backend/app/services/background_jobs.py`;
  job-specific services keep their own workflow status mapping semantics.
  Assessment routes stay HTTP-boundary only for stage summary, project
  description, final report prompt execution, stage draft preparation, report
  confirmation, and verification refresh; those prompt paths and workflows live
  in their service owners. Stage summary and stage verification read-model
  assembly live in `backend/app/services/assessment_summaries.py`.
- Frontend feature ownership: operational admin screens live under
  `frontend/features/admin/components` with route pages kept as thin shells in
  `frontend/app/(admin)`. The legacy `frontend/components/admin` path is not a
  component owner. Admin question-bank management is owned by
  `frontend/features/admin/components/org/question-banks/question-bank-manager.tsx`,
  its leaf panels live in
  `frontend/features/admin/components/org/question-banks/question-bank-panels.tsx`,
  its questions-tab filter, list, and editor display lives in
  `frontend/features/admin/components/org/question-banks/question-bank-questions-panel.tsx`,
  and copy/constants plus pure view-model helpers are kept in
  `frontend/features/admin/question-bank-messages.ts` and
  `frontend/features/admin/question-bank-view-model.ts`. Admin mentor
  assignment orchestration stays in
  `frontend/features/admin/components/org/mentor-assignments-table.tsx`, with
  toolbar/table/pagination display composition in
  `frontend/features/admin/components/org/mentor-assignments-panels.tsx` and
  modal/toast display composition in
  `frontend/features/admin/components/org/mentor-assignments-modals.tsx`;
  shared assignment UI types, status variants, member-option transforms,
  initials/interpolation helpers, locale formatting, and query-string helpers
  live in
  `frontend/features/admin/admin-mentor-assignments-view-model.ts`.
  The admin organization settings route at
  `frontend/app/(admin)/admin/org/page.tsx` is a thin shell; settings
  orchestration lives in
  `frontend/features/admin/components/org/settings/admin-org-settings-client.tsx`,
  display cards live in
  `frontend/features/admin/components/org/settings/admin-org-settings-surface.tsx`,
  logo modal display lives in
  `frontend/features/admin/components/org/settings/admin-org-logo-modal.tsx`,
  and settings messages/view-model helpers live in
  `frontend/features/admin/org-settings-messages.ts` and
  `frontend/features/admin/org-settings-view-model.ts`.
  Admin organization invites orchestration stays in
  `frontend/features/admin/components/org/invites-table.tsx`, with the invite
  toolbar, rows, pagination, alerts, empty/loading states, and toast display in
  `frontend/features/admin/components/org/invites-table-surface.tsx`; create
  and revoke modal display lives in
  `frontend/features/admin/components/org/invite-modals.tsx`, and invite UI
  types, filter constants, date formatting, interpolation, and query-string
  helpers live in `frontend/features/admin/admin-invites-view-model.ts`.
  Admin organization members orchestration stays in
  `frontend/features/admin/components/org/members-table.tsx`, with the member
  toolbar, rows, pagination, alerts, empty/loading states, and toast display in
  `frontend/features/admin/components/org/members-table-surface.tsx`; remove
  modal display lives in
  `frontend/features/admin/components/org/member-modals.tsx`, and member UI
  types, role constants, initials/date formatting, interpolation, and
  query-string helpers live in
  `frontend/features/admin/admin-members-view-model.ts`.
  The admin prompt-template route at
  `frontend/app/(admin)/admin/org/prompts/page.tsx` is a thin shell;
  prompt-template API loading, draft state, filters, sorting, publish, and
  revert orchestration live in
  `frontend/features/admin/components/org/prompts/prompt-templates-client.tsx`,
  display composition lives in
  `frontend/features/admin/components/org/prompts/prompt-templates-surface.tsx`,
  and messages plus pure grouping/stage helpers live in
  `frontend/features/admin/prompt-template-messages.ts` and
  `frontend/features/admin/prompt-template-view-model.ts`.
  Platform report-quality dashboard orchestration stays in
  `frontend/features/admin/components/platform/report-quality-dashboard.tsx`,
  with display composition in
  `frontend/features/admin/components/platform/report-quality-dashboard-surface.tsx`
  and localized copy in
  `frontend/features/admin/components/platform/report-quality-dashboard-messages.ts`.
  Admin cohort list orchestration stays in
  `frontend/features/admin/components/cohorts/cohorts-table.tsx`, with toolbar,
  rows, pagination, alerts, empty/loading states, and toast display in
  `frontend/features/admin/components/cohorts/cohorts-table-surface.tsx`;
  create modal display lives in
  `frontend/features/admin/components/cohorts/cohort-modals.tsx`, and cohort
  list UI types, date/timeline formatting, interpolation, locale, and
  query-string helpers live in
  `frontend/features/admin/admin-cohorts-view-model.ts`.
  Admin cohort detail orchestration stays in
  `frontend/features/admin/components/cohorts/cohort-detail.tsx`, with the
  header, tabs, tables, pagination, and toast display in
  `frontend/features/admin/components/cohorts/cohort-detail-surface.tsx`;
  member add/remove dialog display is owned by
  `frontend/features/admin/components/cohorts/cohort-detail-dialogs.tsx`, and
  shared cohort detail UI data shapes live in
  `frontend/features/admin/components/cohorts/cohort-detail-types.ts`.
  Admin reports table orchestration stays in
  `frontend/features/admin/components/reports/reports-table.tsx`, with
  toolbar, filters, batch/export controls, report rows, pagination, alerts, and
  toast display in
  `frontend/features/admin/components/reports/reports-table-surface.tsx` and
  shared report-list UI data shapes in
  `frontend/features/admin/components/reports/reports-table-types.ts`.
  Admin project detail orchestration stays in
  `frontend/features/admin/components/projects/project-detail.tsx`, with the
  header, tabs, summary, reports timeline, comments composer/list, pagination,
  and toast display in
  `frontend/features/admin/components/projects/project-detail-surface.tsx`;
  edit/delete modal display is owned by
  `frontend/features/admin/components/projects/project-detail-dialogs.tsx`, and
  shared project detail UI data shapes live in
  `frontend/features/admin/components/projects/project-detail-types.ts`.
  Report pages keep `frontend/features/reports/report-viewer.tsx` as the
  canonical live/sample entrypoint, with the display surface, display-only
  report document, job status, sample hero, and sample verification helpers in
  feature-owned sibling modules under `frontend/features/reports`. Report card
  family display components are split into summary, score, technical, Report
  v2, and diagnosis card modules under the same feature folder, with
  `report-viewer-cards.tsx` kept as a compatibility export facade for the
  report document composition imports.
  Marketing homepage composition stays in
  `frontend/components/marketing/HomePage.tsx`, with section exports in
  `frontend/components/marketing/HomePageSections.tsx`. The actual homepage
  intro/problem, DVF/process, report/insights, and trust/team section families
  live in dedicated sibling modules; header, FAQ/CTA, wrappers, and helper
  hooks stay in their existing sibling marketing modules.
  Marketing methodology page shell composition stays in
  `frontend/components/marketing/MethodologyPageView.tsx`, with methodology
  section exports in
  `frontend/components/marketing/MethodologyPageSections.tsx`. The actual
  methodology intro, framework, review, and output/closing section families
  live in dedicated sibling modules; methodology-only animation, typography,
  focus-ring, and class helpers live in
  `frontend/components/marketing/methodology-page-utils.tsx`, and content
  typing lives in `frontend/components/marketing/methodology-page-types.ts`.
  The live context board keeps orchestration in
  `frontend/features/context/live-context-board.tsx`, with the display surface
  in `frontend/features/context/live-context-board-surface.tsx`, display
  controls and diagnosis sections, board-specific review/header panels, and
  UI-local draft editing state split into feature-owned sibling modules.
- Project state audit: versioned `project_states` mutations are paired with
  `project_state_events` rows through
  `backend/app/services/project_state_events.py`. Full production smoke gates
  must verify that exported state events cover the final `state_version`, so a
  run cannot pass with only the final state snapshot persisted.

  | Stage/status | Answer | Draft | Confirm | Result |
  | --- | --- | --- | --- | --- |
  | problem/market/tech + `in_progress` | Allowed | Blocked | Blocked | When blocking paths resolve, status may move to `awaiting_confirm` without advancing `current_stage`. |
  | problem/market/tech + `awaiting_confirm` | Blocked | Allowed for matching stage | Allowed for matching stage | Confirmation advances to the next stage through `stage_runtime`. |
  | problem/market/tech + `passed` | Blocked | Blocked | Blocked | Stage is locked for normal chat. |
  | report + `awaiting_confirm` | Blocked | Blocked | Report confirm only | Final report is persisted and status moves to `passed`. |
  | report + other statuses | Blocked | Blocked | Blocked | Report stage is not an interview chat stage. |

## Contracts
- Source of truth: `docs/spec/MASTER_SPEC.md` in the private repository;
  public-safe exports use `docs/spec/PUBLIC_SPEC.md` as the available contract
  summary.
- JSON schema for stage payload validation lives in `schema/`.

## Notes
- The repo still contains some legacy-oriented wording from the migration period; the codebase itself now targets the new backend/database stack.
- Auth flow, API boundaries, and data flow should be read from the current route and schema modules when docs are incomplete.
