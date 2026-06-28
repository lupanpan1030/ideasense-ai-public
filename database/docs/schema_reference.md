# Schema Reference

This document lists all tables, columns, constraints, indexes, and key integrity triggers. It follows the current migrations under `database/migrations/`.

## Global Conventions
- Soft deletes: `deleted_at` marks logical deletion; uniqueness uses partial indexes on `deleted_at IS NULL`.
- Normalization: email/slug/type keys are trimmed and validated for whitespace; slugs are lowercase.
- Case-insensitive email columns use `CITEXT`.
- Scope normalization: global-or-org data uses `scope_org_id = COALESCE(org_id, ZERO_UUID)` as a generated column.
  - `ZERO_UUID` is `00000000-0000-0000-0000-000000000000`.
- Stage/variant whitelist: `question_bank_stage_variants` is the canonical list.
- `updated_at` is auto-maintained by a shared trigger (`set_updated_at`).
- Row Level Security (RLS) is enabled across all tables; policies assume session vars `app.user_id`, `app.org_id`, and `app.actor_type`.

## Tables

### organizations
Purpose: Tenant boundary and org configuration.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `name` TEXT, org display name.
- `slug` TEXT, URL identifier.
- `settings` JSONB, org configuration; default includes org type and defaults.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ, soft delete marker.

Constraints and indexes:
- CHECK `slug = lower(slug)`.
- CHECK `slug = btrim(slug)`.
- CHECK `slug !~ '\s'`.
- UNIQUE `organizations_slug_unique` on `slug` where `deleted_at IS NULL`.

### users
Purpose: Canonical user profile (independent of auth provider).

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `email` CITEXT, primary email.
- `display_name` TEXT, display name.
- `primary_org_id` UUID FK `organizations(id)` ON DELETE SET NULL.
- `is_active` BOOLEAN, default `true`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `email = btrim(email)`.
- CHECK `email !~ '\s'`.
- UNIQUE `users_email_unique` on `email` where `deleted_at IS NULL`.

### user_identities
Purpose: Login identities (external providers + local).

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `user_id` UUID FK `users(id)` ON DELETE CASCADE.
- `provider` TEXT, auth provider.
- `provider_subject` TEXT, provider user id.
- `email` CITEXT, identity email.
- `password_hash` TEXT, for `provider='local'`.
- `status` TEXT, default `active`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `provider IN ('local','clerk','nextauth','sso')`.
- CHECK `status IN ('active','disabled')`.
- CHECK `provider = 'local' OR provider_subject IS NOT NULL`.
- CHECK `provider <> 'local' OR password_hash IS NOT NULL`.
- CHECK `email IS NULL OR (email = btrim(email) AND email !~ '\s')`.
- UNIQUE `user_identities_provider_subject_unique` on `(provider, provider_subject)` where `deleted_at IS NULL`.

### organization_memberships
Purpose: User membership and role within an org.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `user_id` UUID FK `users(id)` ON DELETE CASCADE.
- `org_role` TEXT, role in org.
- `status` TEXT, default `active`.
- `created_by` UUID FK `users(id)` ON DELETE SET NULL.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `org_role IN ('owner','admin','mentor','student')`.
- CHECK `status IN ('invited','active','removed')`.
- UNIQUE `organization_memberships_org_user_unique` on `(org_id, user_id)` where `deleted_at IS NULL`.
- INDEX `organization_memberships_user_id_idx` on `user_id` where `deleted_at IS NULL`.

### organization_invitations
Purpose: Invite users by email into an org with a role.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `invitee_email` CITEXT, invited email.
- `invited_role` TEXT.
- `invited_by` UUID FK `users(id)` ON DELETE SET NULL.
- `token` TEXT, invite token.
- `expires_at` TIMESTAMPTZ.
- `status` TEXT, default `pending`.
- `accepted_user_id` UUID FK `users(id)` ON DELETE SET NULL.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `invited_role IN ('mentor','student','admin')`.
- CHECK `status IN ('pending','accepted','expired','revoked')`.
- CHECK `invitee_email = btrim(invitee_email)`.
- CHECK `invitee_email !~ '\s'`.
- UNIQUE `organization_invitations_org_token_unique` on `(org_id, token)` where `deleted_at IS NULL`.

### cohorts
Purpose: Cohorts/classes within an org.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `name` TEXT.
- `description` TEXT.
- `start_at` TIMESTAMPTZ.
- `end_at` TIMESTAMPTZ.
- `is_archived` BOOLEAN, default `false`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CONSTRAINT `cohorts_org_id_id_unique` UNIQUE `(org_id, id)`.
- UNIQUE `cohorts_org_name_unique` on `(org_id, name)` where `deleted_at IS NULL`.

### cohort_memberships
Purpose: Cohort membership and role.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `cohort_id` UUID.
- `user_id` UUID FK `users(id)` ON DELETE CASCADE.
- `role_in_cohort` TEXT.
- `status` TEXT, default `active`.
- `joined_at` TIMESTAMPTZ, default `now()`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `role_in_cohort IN ('student','mentor','assistant')`.
- CHECK `status IN ('active','removed')`.
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)` ON DELETE CASCADE.
- UNIQUE `cohort_memberships_cohort_user_unique` on `(cohort_id, user_id)` where `deleted_at IS NULL`.

### mentor_student_assignments
Purpose: Explicit mentor-student authorization with visibility switches.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `cohort_id` UUID, optional.
- `mentor_user_id` UUID FK `users(id)` ON DELETE CASCADE.
- `student_user_id` UUID FK `users(id)` ON DELETE CASCADE.
- `status` TEXT, default `pending`.
- `can_view_messages` BOOLEAN, default `false`.
- `can_view_facts` BOOLEAN, default `false`.
- `can_comment` BOOLEAN, default `true`.
- `created_by` UUID FK `users(id)` ON DELETE SET NULL.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `status IN ('pending','active','revoked')`.
- CHECK `mentor_user_id <> student_user_id`.
- CHECK `can_view_messages IS FALSE OR can_view_facts IS TRUE`.
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)` ON DELETE CASCADE.
- UNIQUE `mentor_student_assignments_unique` on `(org_id, mentor_user_id, student_user_id, COALESCE(cohort_id, ZERO_UUID))` where `deleted_at IS NULL`.
- INDEX `mentor_student_assignments_mentor_idx` on `(org_id, mentor_user_id)` where `deleted_at IS NULL`.
- INDEX `mentor_student_assignments_student_idx` on `(org_id, student_user_id)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_assignment_membership` ensures mentor/student/created_by are active org members; if `cohort_id` is set, both are active cohort members.

### question_bank_versions
Purpose: Versioned question bank (global or org-scoped).

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `scope_org_id` UUID generated as `COALESCE(org_id, ZERO_UUID)`.
- `bank_key` TEXT.
- `version` TEXT.
- `source` TEXT.
- `raw_yaml` TEXT.
- `raw_json` JSONB.
- `content_hash` TEXT.
- `is_active` BOOLEAN, default `false`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.
- `activated_at` TIMESTAMPTZ.
- `deactivated_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `bank_key = lower(btrim(bank_key))`.
- CHECK `bank_key <> ''`.
- CHECK `bank_key !~ '\s'`.
- CHECK `version = btrim(version)`.
- CHECK `version <> ''`.
- CHECK `NOT is_active OR (activated_at IS NOT NULL AND deactivated_at IS NULL)`.
- UNIQUE `question_bank_versions_scope_key_version_unique` on `(scope_org_id, bank_key, version)` where `deleted_at IS NULL`.
- UNIQUE `question_bank_versions_scope_key_active_unique` on `(scope_org_id, bank_key)` where `is_active AND deleted_at IS NULL`.
- UNIQUE `question_bank_versions_scope_content_hash_unique` on `(scope_org_id, content_hash)` where `content_hash IS NOT NULL AND deleted_at IS NULL`.
- INDEX `question_bank_versions_scope_key_idx` on `(scope_org_id, bank_key)`.

Integrity triggers:
- `set_question_bank_version_activation` maintains `activated_at`/`deactivated_at` based on `is_active`.

### question_bank_stage_variants
Purpose: Canonical list of stage/variant combinations.

Columns:
- `stage` TEXT.
- `variant` TEXT.

Constraints and indexes:
- PRIMARY KEY `(stage, variant)`.
- CHECK `stage IN ('problem','market','tech','report')`.
- CHECK `variant IN ('default','router','pro','lite')`.

Seed data:
- `problem/default`, `market/default`, `report/default`, `tech/default`, `tech/router`, `tech/pro`, `tech/lite`.

### question_bank_questions
Purpose: Question metadata for a bank version.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `bank_version_id` UUID FK `question_bank_versions(id)` ON DELETE CASCADE.
- `stage` TEXT.
- `variant` TEXT.
- `question_id` TEXT.
- `order_index` INT.
- `title` TEXT.
- `type_raw` TEXT.
- `prompt` TEXT.
- `standard_question` TEXT.
- `consultant_tactic` TEXT.
- `instruction` TEXT.
- `validation_rule` TEXT.
- `schema_paths` TEXT[] default empty array.
- `expected_key_points` TEXT[].
- `capture_intent` TEXT.
- `capture_spec` JSONB default `{}`.
- `answer_examples` JSONB[] default empty array.
- `expected_patch_example` JSONB.
- `display_if` JSONB.
- `meta` JSONB default `{}`.
- `is_active` BOOLEAN default `true`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- FK `(stage, variant)` REFERENCES `question_bank_stage_variants(stage, variant)`.
- UNIQUE `question_bank_questions_unique_id` on `(bank_version_id, stage, variant, question_id)` where `deleted_at IS NULL`.
- UNIQUE `question_bank_questions_unique_order` on `(bank_version_id, stage, variant, order_index)` where `deleted_at IS NULL`.
- INDEX `question_bank_questions_next_idx` on `(bank_version_id, stage, variant, order_index)` where `deleted_at IS NULL`.
- GIN `question_bank_questions_schema_paths_gin` on `schema_paths` where `deleted_at IS NULL`.

### projects
Purpose: A full student project workflow.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `cohort_id` UUID, optional.
- `owner_user_id` UUID FK `users(id)`.
- `title` TEXT.
- `description` TEXT.
- `question_bank_version_id` UUID FK `question_bank_versions(id)`.
- `current_stage` TEXT.
- `current_variant` TEXT, default `default`.
- `stage_status` TEXT, default `in_progress`.
- `settings` JSONB default `{}`.
- `is_archived` BOOLEAN default `false`.
- `archived_at` TIMESTAMPTZ.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CONSTRAINT `projects_org_id_id_unique` UNIQUE `(org_id, id)`.
- CHECK `current_stage IN ('problem','market','tech','report')`.
- CHECK `current_variant IN ('default','router','pro','lite')`.
- CHECK `stage_status IN ('in_progress','awaiting_confirm','passed')`.
- CHECK `is_archived`/`archived_at` consistency.
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)`.
- FK `(current_stage, current_variant)` REFERENCES `question_bank_stage_variants(stage, variant)`.
- INDEX `projects_org_id_idx` on `org_id` where `deleted_at IS NULL`.
- INDEX `projects_owner_user_id_idx` on `owner_user_id` where `deleted_at IS NULL`.
- INDEX `projects_cohort_id_idx` on `cohort_id` where `deleted_at IS NULL`.
- INDEX `projects_question_bank_version_idx` on `question_bank_version_id` where `deleted_at IS NULL`.
- INDEX `projects_org_stage_idx` on `(org_id, current_stage)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_project_owner_membership` ensures owner is an active org member and (if cohort set) an active cohort student.
- `enforce_project_question_bank_scope` ensures bank is global or scoped to the org.
- `set_project_archive_timestamps` maintains `archived_at`.

### project_runtime
Purpose: Runtime pointers for the current question flow.

Columns:
- `project_id` UUID PK FK `projects(id)` ON DELETE CASCADE.
- `org_id` UUID.
- `stage` TEXT.
- `variant` TEXT.
- `current_question_bank_question_id` UUID FK `question_bank_questions(id)`.
- `next_question_bank_question_id` UUID FK `question_bank_questions(id)`.
- `turn_state` TEXT, default `draft`.
- `missing_paths` TEXT[] default empty array.
- `runtime_version` INT, default `0`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `turn_state IN ('draft','updated','needs_info')`.
- CHECK `runtime_version >= 0`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)`.
- FK `(stage, variant)` REFERENCES `question_bank_stage_variants(stage, variant)`.
- INDEX `project_runtime_org_stage_idx` on `(org_id, stage, variant)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_project_runtime_questions` aligns `stage`/`variant` with the project and validates current/next question pointers against the project bank and stage/variant.

### prompt_templates
Purpose: Prompt versioning by purpose and stage.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `scope_org_id` UUID generated as `COALESCE(org_id, ZERO_UUID)`.
- `template_key` TEXT, normalized key.
- `purpose` TEXT.
- `stage` TEXT.
- `variant` TEXT.
- `version` TEXT.
- `content` TEXT.
- `params` JSONB.
- `is_active` BOOLEAN, default `false`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `purpose IN ('chat','extract','summary','score','evaluate','report')`.
- CHECK `template_key` normalized and matches `^[a-z0-9_.-]+$`.
- CHECK `variant IS NULL OR stage IS NOT NULL`.
- CHECK `stage IS NULL OR stage IN ('problem','market','tech','report')`.
- UNIQUE `prompt_templates_scope_unique` on `(scope_org_id, template_key, version)` where `deleted_at IS NULL`.
- UNIQUE `prompt_templates_scope_active_unique` on `(scope_org_id, template_key)` where `is_active AND deleted_at IS NULL`.

Integrity triggers:
- `enforce_prompt_template_stage_variant` requires `(stage, variant)` to exist in `question_bank_stage_variants` when `variant` is set.

### project_question_instances
Purpose: Per-project question instance state and extracted patch.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `question_bank_question_id` UUID FK `question_bank_questions(id)`.
- `status` TEXT, default `pending`.
- `asked_count` INT, default `0`.
- `last_asked_at` TIMESTAMPTZ.
- `answered_at` TIMESTAMPTZ.
- `final_answer_text` TEXT.
- `extracted_patch_json` JSONB default `{}`.
- `validation_status` TEXT, default `not_validated`.
- `validation_errors` JSONB default `[]`.
- `extract_model` TEXT.
- `extract_prompt_template_id` UUID FK `prompt_templates(id)`.
- `extract_confidence` NUMERIC(4,3).
- `meta` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `status IN ('pending','asked','answered','needs_info','skipped','invalid','autofilled')`.
- CHECK `asked_count >= 0`.
- CHECK `validation_status IN ('not_validated','valid','invalid','needs_info')`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `project_question_instances_unique` on `(project_id, question_bank_question_id)` where `deleted_at IS NULL`.
- INDEX `project_question_instances_status_idx` on `(project_id, status, updated_at DESC)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_project_question_instance_bank` ensures the question belongs to the project's bank version.

### conversation_messages
Purpose: Evidence layer of user/assistant/system messages.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `project_id` UUID.
- `author_user_id` UUID FK `users(id)`.
- `role` TEXT.
- `is_visible` BOOLEAN, default `true`.
- `stage` TEXT.
- `variant` TEXT.
- `question_instance_id` UUID FK `project_question_instances(id)`.
- `client_message_id` UUID.
- `request_id` UUID.
- `content` TEXT.
- `content_format` TEXT, default `markdown`.
- `model_name` TEXT.
- `prompt_template_id` UUID FK `prompt_templates(id)`.
- `token_prompt` INT.
- `token_output` INT.
- `latency_ms` INT.
- `meta` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `redacted_at` TIMESTAMPTZ.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `role IN ('user','assistant','system','tool')`.
- CHECK `stage IN ('problem','market','tech','report')`.
- CHECK `content_format IN ('markdown','text','json')`.
- CHECK `token_prompt >= 0` when not null.
- CHECK `token_output >= 0` when not null.
- CHECK `latency_ms >= 0` when not null.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `conversation_messages_client_unique` on `(project_id, client_message_id)` where `client_message_id IS NOT NULL AND deleted_at IS NULL`.
- INDEX `conversation_messages_project_created_idx` on `(project_id, created_at)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_conversation_message_integrity` validates question instance scope; forces `role='user'` author to be the project owner and aligns stage/variant with runtime.

### project_states
Purpose: Canonical structured state for a project.

Columns:
- `project_id` UUID PK FK `projects(id)` ON DELETE CASCADE.
- `org_id` UUID.
- `bank_version_id` UUID FK `question_bank_versions(id)`.
- `state_schema_version` TEXT, default `v1`.
- `state_json` JSONB default `{}`.
- `state_version` INT, default `0`.
- `state_meta` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `state_version >= 0`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.

Integrity triggers:
- `enforce_project_state_bank_version` ensures `bank_version_id` matches the project's bank version.

### project_state_events
Purpose: Append-only audit of state changes.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `project_id` UUID.
- `question_instance_id` UUID FK `project_question_instances(id)`.
- `event_type` TEXT.
- `patch_json` JSONB.
- `actor_type` TEXT.
- `actor_user_id` UUID FK `users(id)`.
- `model_name` TEXT.
- `prompt_template_id` UUID FK `prompt_templates(id)`.
- `prev_state_version` INT.
- `next_state_version` INT.
- `request_id` UUID.
- `created_at` TIMESTAMPTZ, default `now()`.

Constraints and indexes:
- CHECK `actor_type IN ('user','system','ai')`.
- CHECK `actor_type <> 'user' OR actor_user_id IS NOT NULL`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- INDEX `project_state_events_project_created_idx` on `(project_id, created_at DESC)`.

Integrity triggers:
- `enforce_project_state_event_integrity` validates question instance scope and enforces version continuity for `event_type='apply_patch'`.

### documents
Purpose: Project documents/attachments with ingestion status.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `file_name` TEXT.
- `content_type` TEXT.
- `storage_key` TEXT.
- `status` TEXT, default `uploaded`.
- `error_message` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.
- `meta` JSONB default `{}`.

Constraints and indexes:
- CHECK `status IN ('uploaded','extracting','extracted','chunked','embedded','indexed','failed')`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `documents_storage_key_unique` on `(org_id, storage_key)` where `deleted_at IS NULL`.
- INDEX `documents_project_status_idx` on `(project_id, status)` where `deleted_at IS NULL`.

### analytics_events
Purpose: Analytics/telemetry events.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `project_id` UUID FK `projects(id)` ON DELETE SET NULL.
- `actor_user_id` UUID FK `users(id)`.
- `event_type` TEXT.
- `payload` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.

Indexes:
- `analytics_events_org_created_idx` on `(org_id, created_at DESC)`.
- `analytics_events_project_created_idx` on `(project_id, created_at DESC)`.
- `analytics_events_org_type_created_idx` on `(org_id, event_type, created_at DESC)`.

### audit_events
Purpose: Cross-domain audit trail.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `actor_user_id` UUID FK `users(id)`.
- `actor_type` TEXT.
- `event_type` TEXT.
- `target_type` TEXT.
- `target_id` TEXT.
- `payload` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.

Constraints and indexes:
- CHECK `actor_type IN ('user','system')`.
- `audit_events_org_created_idx` on `(org_id, created_at DESC)`.
- `audit_events_org_type_created_idx` on `(org_id, event_type, created_at DESC)`.
- `audit_events_org_target_idx` on `(org_id, target_type, target_id, created_at DESC)`.
- `audit_events_org_actor_idx` on `(org_id, actor_user_id, created_at DESC)`.

### project_stage_assessments
Purpose: Stage summaries and gate confirmation.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `stage` TEXT.
- `draft_summary_markdown` TEXT.
- `final_summary_markdown` TEXT.
- `confirmed` BOOLEAN, default `false`.
- `confirmed_at` TIMESTAMPTZ.
- `confirmed_by_user_id` UUID FK `users(id)`.
- `generated_from_state_version` INT.
- `generator_model` TEXT.
- `generator_prompt_template_id` UUID FK `prompt_templates(id)`.
- `scores_json` JSONB.
- `total_score` NUMERIC.
- `risk_matrix` JSONB.
- `context_card_json` JSONB, default `{}`. Evidence-layered diagnosis card for the confirmed stage.
- `validation_plan_json` JSONB, default `[]`. Short-cycle validation actions for the confirmed stage.
- `diagram_mermaid` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `stage IN ('problem','market','tech')`.
- CHECK confirmation consistency (`confirmed` with `confirmed_at` and `confirmed_by_user_id`).
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `project_stage_assessments_unique` on `(project_id, stage)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_project_stage_assessment_confirmer` ensures confirmer is project owner or org owner/admin and active; sets `confirmed_at`.
- `enforce_project_stage_assessment_state_version` ensures `generated_from_state_version` does not exceed current project state.

### project_stage_qa_digests
Purpose: Per-question QA digests used for verification and reporting.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `assessment_id` UUID FK `project_stage_assessments(id)`.
- `stage` TEXT.
- `question_id` TEXT.
- `answer_summary` TEXT.
- `key_points` TEXT[].
- `source_message_id` BIGINT FK `conversation_messages(id)`.
- `model` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `stage IN ('problem','market','tech')`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- `project_stage_qa_digests_project_stage_created_idx` on `(project_id, stage, created_at DESC)` where `deleted_at IS NULL`.
- `project_stage_qa_digests_assessment_idx` on `(assessment_id)` where `deleted_at IS NULL`.

### project_stage_verification_claims
Purpose: Evidence-backed verification claims for stage summaries.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `assessment_id` UUID FK `project_stage_assessments(id)` (nullable).
- `stage` TEXT.
- `question_id` TEXT (nullable).
- `question_bank_question_id` UUID FK `question_bank_questions(id)` (nullable).
- `source_message_id` BIGINT FK `conversation_messages(id)` (nullable).
- `priority` TEXT (nullable).
- `batch_id` UUID (nullable).
- `claim` TEXT.
- `verdict` TEXT.
- `confidence` TEXT.
- `rationale` TEXT.
- `sources` JSONB.
- `evidence_mode` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `stage IN ('problem','market','tech')`.
- CHECK `verdict IN ('supported','contradicted','uncertain')`.
- CHECK `confidence IN ('High','Medium','Low')` (nullable).
- CHECK `priority IN ('high','medium','low','none')` (nullable).
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- `project_stage_verification_claims_project_stage_created_idx` on `(project_id, stage, created_at DESC)` where `deleted_at IS NULL`.
- `project_stage_verification_claims_project_stage_question_created_idx` on `(project_id, stage, question_bank_question_id, created_at DESC)` where `deleted_at IS NULL`.
- `project_stage_verification_claims_assessment_idx` on `(assessment_id)` where `deleted_at IS NULL`.

### project_reports
Purpose: Final reports with versioning.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `report_version` INT.
- `status` TEXT, default `draft`.
- `content_markdown` TEXT.
- `content_json` JSONB.
- `diagnosis_json` JSONB, default `{}`. Final evidence-layered diagnosis payload.
- `validation_plan_json` JSONB, default `[]`. Aggregated report-level validation plan.
- `generated_from_state_version` INT.
- `generator_model` TEXT.
- `generator_prompt_template_id` UUID FK `prompt_templates(id)`.
- `confirmed` BOOLEAN, default `false`.
- `confirmed_at` TIMESTAMPTZ.
- `export_storage_key` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `report_version >= 1`.
- CHECK `status IN ('draft','final','archived')`.
- CHECK confirmation consistency (`confirmed` with `confirmed_at`).
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `project_reports_unique` on `(project_id, report_version)` where `deleted_at IS NULL`.

Integrity triggers:
- `set_project_report_confirmed_at` maintains `confirmed_at`.

### report_quality_observations
Purpose: Safe persisted assessment-quality observations for platform report
quality operations.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `project_id` UUID.
- `project_title` TEXT, safe title snapshot for platform quality triage.
- `report_id` UUID FK `project_reports(id)` ON DELETE CASCADE.
- `report_version` INT.
- `generated_from_state_version` INT.
- `observation_schema_version` TEXT, default `assessment_quality_observation_v1`.
- `status` TEXT.
- `failed_invariants_json` JSONB, default `[]`.
- `warning_invariants_json` JSONB, default `[]`.
- `score_snapshot_json` JSONB, default `{}`.
- `evidence_counts_json` JSONB, default `{}`.
- `canonical_boundaries_json` JSONB, default `{}`.
- `observation_json` JSONB, default `{}`. Safe observation detail payload.
- `observed_at` TIMESTAMPTZ, default `now()`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `report_version >= 1`.
- CHECK `generated_from_state_version >= 1`.
- CHECK `status IN ('pass','warn','fail')`.
- CHECK JSONB shape for invariant arrays and summary objects.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `report_quality_observations_report_state_unique` on `(report_id, generated_from_state_version)` where `deleted_at IS NULL`.
- INDEX `report_quality_observations_org_status_observed_idx` on `(org_id, status, observed_at DESC)` where `deleted_at IS NULL`.
- INDEX `report_quality_observations_project_observed_idx` on `(project_id, observed_at DESC)` where `deleted_at IS NULL`.
- INDEX `report_quality_observations_report_idx` on `(report_id)` where `deleted_at IS NULL`.

RLS:
- System actors can insert/update/select rows in the active org context.
- Platform admins can select non-private-org rows across orgs.

Integrity triggers:
- `report_quality_observations_set_updated_at` maintains `updated_at`.

### project_comments
Purpose: Comment/annotation channel for mentors and students.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `author_user_id` UUID FK `users(id)`.
- `visibility` TEXT, default `student_and_mentors`.
- `status` TEXT, default `open`.
- `content` TEXT.
- `content_format` TEXT, default `markdown`.
- `target_stage` TEXT.
- `target_question_instance_id` UUID FK `project_question_instances(id)`.
- `target_message_id` BIGINT FK `conversation_messages(id)`.
- `target_report_id` UUID FK `project_reports(id)`.
- `target_section_key` TEXT.
- `parent_comment_id` UUID FK `project_comments(id)`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `visibility IN ('student_and_mentors','mentors_only','private')`.
- CHECK `status IN ('open','resolved','archived')`.
- CHECK `content_format IN ('markdown','text')`.
- CHECK `target_stage IS NULL OR target_stage IN ('problem','market','tech','report')`.
- CHECK `num_nonnulls(target_stage, target_question_instance_id, target_message_id, target_report_id, target_section_key) <= 1`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- INDEX `project_comments_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`.
- INDEX `project_comments_project_status_idx` on `(project_id, status)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_project_comment_author_membership` ensures author is an active org member.
- `enforce_project_comment_targets` validates target belongs to the same project/org.

### notifications
Purpose: Notification delivery to users.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `recipient_user_id` UUID FK `users(id)`.
- `type` TEXT.
- `title` TEXT.
- `body` TEXT.
- `link` TEXT.
- `payload` JSONB default `{}`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `read_at` TIMESTAMPTZ.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `type = lower(btrim(type))`.
- CHECK `type <> ''`.
- CHECK `type ~ '^[a-z0-9_.-]+$'`.
- CHECK `link IS NULL OR length(link) <= 2000`.
- INDEX `notifications_recipient_unread_idx` on `(recipient_user_id, read_at, created_at DESC)` where `deleted_at IS NULL`.

### evaluation_rubrics
Purpose: Versioned rubrics for evaluation.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE.
- `scope_org_id` UUID generated as `COALESCE(org_id, ZERO_UUID)`.
- `rubric_key` TEXT.
- `rubric_version` TEXT.
- `scope` TEXT.
- `definition_json` JSONB.
- `is_active` BOOLEAN, default `true`.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `scope IN ('answer','message')`.
- UNIQUE `evaluation_rubrics_unique` on `(scope_org_id, scope, rubric_key, rubric_version)` where `deleted_at IS NULL`.
- UNIQUE `evaluation_rubrics_active_unique` on `(scope_org_id, rubric_key, scope)` where `is_active AND deleted_at IS NULL`.

### answer_evaluations
Purpose: Evaluation results for question instances.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `question_instance_id` UUID FK `project_question_instances(id)`.
- `rubric_id` UUID FK `evaluation_rubrics(id)`.
- `scores_json` JSONB.
- `overall_score` NUMERIC.
- `feedback_markdown` TEXT.
- `evaluator_type` TEXT.
- `evaluator_model` TEXT.
- `request_id` UUID.
- `created_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `evaluator_type IN ('ai','human','system')`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `answer_evaluations_request_unique` on `request_id` where `request_id IS NOT NULL AND deleted_at IS NULL`.
- INDEX `answer_evaluations_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_answer_evaluation_scope` ensures the question instance belongs to the same project/org.

### message_evaluations
Purpose: Evaluation results for assistant messages.

Columns:
- `id` UUID PK, default `gen_random_uuid()`.
- `org_id` UUID.
- `project_id` UUID.
- `message_id` BIGINT FK `conversation_messages(id)`.
- `rubric_id` UUID FK `evaluation_rubrics(id)`.
- `scores_json` JSONB.
- `overall_score` NUMERIC.
- `feedback_markdown` TEXT.
- `evaluator_type` TEXT.
- `evaluator_model` TEXT.
- `request_id` UUID.
- `created_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `evaluator_type IN ('ai','human','system')`.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE.
- UNIQUE `message_evaluations_request_unique` on `request_id` where `request_id IS NOT NULL AND deleted_at IS NULL`.
- INDEX `message_evaluations_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_message_evaluation_scope` ensures the message belongs to the same project/org.

### background_jobs
Purpose: Async jobs with idempotency and locks.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `project_id` UUID.
- `job_type` TEXT.
- `status` TEXT, default `queued`.
- `priority` INT, default `100`.
- `payload` JSONB.
- `idempotency_key` TEXT.
- `attempts` INT, default `0`.
- `max_attempts` INT, default `5`.
- `run_at` TIMESTAMPTZ, default `now()`.
- `locked_at` TIMESTAMPTZ.
- `lock_expires_at` TIMESTAMPTZ.
- `locked_by` TEXT.
- `started_at` TIMESTAMPTZ.
- `completed_at` TIMESTAMPTZ.
- `last_error` TEXT.
- `created_at` TIMESTAMPTZ, default `now()`.
- `updated_at` TIMESTAMPTZ, default `now()`.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `job_type` normalized and matches `^[a-z0-9_.-]+$`.
- CHECK `status IN ('queued','running','succeeded','failed','cancelled')`.
- CHECK `priority >= 0`.
- CHECK `attempts >= 0`.
- CHECK `max_attempts >= 0`.
- CHECK lock tuple consistency (`locked_at`, `locked_by`, `lock_expires_at` are all null or all set).
- CHECK `status='running'` implies `started_at` set and `completed_at` null.
- CHECK terminal statuses imply `completed_at` set.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE SET NULL.
- UNIQUE `background_jobs_idempotency_unique` on `(org_id, job_type, idempotency_key)` where `idempotency_key IS NOT NULL AND deleted_at IS NULL`.
- INDEX `background_jobs_queue_idx` on `(status, run_at, priority)` where `deleted_at IS NULL`.
- INDEX `background_jobs_locked_idx` on `(locked_at)` where `deleted_at IS NULL`.
- INDEX `background_jobs_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`.

Integrity triggers:
- `set_background_job_timestamps` sets `started_at` and `completed_at` based on `status`.

### idempotency_keys
Purpose: Idempotency keys for API requests.

Columns:
- `id` BIGINT PK, identity.
- `org_id` UUID.
- `user_id` UUID FK `users(id)`.
- `scope` TEXT.
- `key` TEXT.
- `request_hash` TEXT.
- `response_ref` JSONB.
- `created_at` TIMESTAMPTZ, default `now()`.
- `expires_at` TIMESTAMPTZ.
- `deleted_at` TIMESTAMPTZ.

Constraints and indexes:
- CHECK `scope = lower(btrim(scope))`.
- CHECK `scope <> ''`.
- CHECK `scope !~ '\s'`.
- CHECK `key = btrim(key)`.
- CHECK `key <> ''`.
- CHECK `key ~ '^[A-Za-z0-9_.:-]+$'`.
- CHECK `expires_at IS NULL OR expires_at > created_at`.
- UNIQUE `idempotency_keys_unique` on `(org_id, scope, key)` where `deleted_at IS NULL`.
- INDEX `idempotency_keys_user_created_idx` on `(user_id, created_at DESC)` where `deleted_at IS NULL`.

Integrity triggers:
- `enforce_idempotency_key_consistency` prevents changing `request_hash` and `response_ref` after set.
