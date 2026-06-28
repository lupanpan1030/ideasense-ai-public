# 结构参考（中文）

本文档按 `database/migrations/` 当前状态列出所有表、字段、约束、索引与关键完整性触发器。

## 全局约定
- 软删除：使用 `deleted_at` 标记逻辑删除；唯一性通常用 `deleted_at IS NULL` 的 partial index 保证。
- 规范化：邮箱/slug/type 等字段会做 trim，并检查空白字符；slug 强制小写。
- 邮箱字段使用 `CITEXT`，大小写不敏感。
- 全局/组织范围：使用生成列 `scope_org_id = COALESCE(org_id, ZERO_UUID)`。
  - `ZERO_UUID` 为 `00000000-0000-0000-0000-000000000000`。
- `updated_at` 由统一触发器 `set_updated_at` 自动维护。
- 合法的 stage/variant 组合由 `question_bank_stage_variants` 统一白名单。
- RLS 已启用，策略依赖会话变量 `app.user_id`、`app.org_id`、`app.actor_type`。

## 表结构

### organizations
用途：租户边界与组织配置。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `name` TEXT，组织名称。
- `slug` TEXT，URL 标识。
- `settings` JSONB，组织配置（含默认值）。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ，软删除。

约束与索引：
- CHECK `slug = lower(slug)`。
- CHECK `slug = btrim(slug)`。
- CHECK `slug !~ '\s'`。
- UNIQUE `organizations_slug_unique` on `slug` where `deleted_at IS NULL`。

### users
用途：系统内用户主档案（与登录身份解耦）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `email` CITEXT，主邮箱。
- `display_name` TEXT，显示名。
- `primary_org_id` UUID FK `organizations(id)` ON DELETE SET NULL。
- `is_active` BOOLEAN，默认 `true`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `email = btrim(email)`。
- CHECK `email !~ '\s'`。
- UNIQUE `users_email_unique` on `email` where `deleted_at IS NULL`。

### user_identities
用途：登录身份集合（外部 provider + 本地账号）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `user_id` UUID FK `users(id)` ON DELETE CASCADE。
- `provider` TEXT，登录来源。
- `provider_subject` TEXT，provider 唯一 subject。
- `email` CITEXT，身份邮箱。
- `password_hash` TEXT，仅 `provider='local'` 使用。
- `status` TEXT，默认 `active`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `provider IN ('local','clerk','nextauth','sso')`。
- CHECK `status IN ('active','disabled')`。
- CHECK `provider = 'local' OR provider_subject IS NOT NULL`。
- CHECK `provider <> 'local' OR password_hash IS NOT NULL`。
- CHECK `email IS NULL OR (email = btrim(email) AND email !~ '\s')`。
- UNIQUE `user_identities_provider_subject_unique` on `(provider, provider_subject)` where `deleted_at IS NULL`。

### organization_memberships
用途：用户在组织中的角色与状态。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `user_id` UUID FK `users(id)` ON DELETE CASCADE。
- `org_role` TEXT，组织角色。
- `status` TEXT，默认 `active`。
- `created_by` UUID FK `users(id)` ON DELETE SET NULL。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `org_role IN ('owner','admin','mentor','student')`。
- CHECK `status IN ('invited','active','removed')`。
- UNIQUE `organization_memberships_org_user_unique` on `(org_id, user_id)` where `deleted_at IS NULL`。
- INDEX `organization_memberships_user_id_idx` on `user_id` where `deleted_at IS NULL`。

### organization_invitations
用途：邀请某邮箱加入组织并赋角色。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `invitee_email` CITEXT，被邀请邮箱。
- `invited_role` TEXT，被邀角色。
- `invited_by` UUID FK `users(id)` ON DELETE SET NULL。
- `token` TEXT，邀请 token。
- `expires_at` TIMESTAMPTZ。
- `status` TEXT，默认 `pending`。
- `accepted_user_id` UUID FK `users(id)` ON DELETE SET NULL。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `invited_role IN ('mentor','student','admin')`。
- CHECK `status IN ('pending','accepted','expired','revoked')`。
- CHECK `invitee_email = btrim(invitee_email)`。
- CHECK `invitee_email !~ '\s'`。
- UNIQUE `organization_invitations_org_token_unique` on `(org_id, token)` where `deleted_at IS NULL`。

### cohorts
用途：组织内班级/课程分组。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `name` TEXT。
- `description` TEXT。
- `start_at` TIMESTAMPTZ。
- `end_at` TIMESTAMPTZ。
- `is_archived` BOOLEAN，默认 `false`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CONSTRAINT `cohorts_org_id_id_unique` UNIQUE `(org_id, id)`。
- UNIQUE `cohorts_org_name_unique` on `(org_id, name)` where `deleted_at IS NULL`。

### cohort_memberships
用途：用户在 cohort 内的角色与状态。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `cohort_id` UUID。
- `user_id` UUID FK `users(id)` ON DELETE CASCADE。
- `role_in_cohort` TEXT。
- `status` TEXT，默认 `active`。
- `joined_at` TIMESTAMPTZ，默认 `now()`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `role_in_cohort IN ('student','mentor','assistant')`。
- CHECK `status IN ('active','removed')`。
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)` ON DELETE CASCADE。
- UNIQUE `cohort_memberships_cohort_user_unique` on `(cohort_id, user_id)` where `deleted_at IS NULL`。

### mentor_student_assignments
用途：导师-学生授权关系（带可见性开关）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `cohort_id` UUID，可选。
- `mentor_user_id` UUID FK `users(id)` ON DELETE CASCADE。
- `student_user_id` UUID FK `users(id)` ON DELETE CASCADE。
- `status` TEXT，默认 `pending`。
- `can_view_messages` BOOLEAN，默认 `false`。
- `can_view_facts` BOOLEAN，默认 `false`。
- `can_comment` BOOLEAN，默认 `true`。
- `created_by` UUID FK `users(id)` ON DELETE SET NULL。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `status IN ('pending','active','revoked')`。
- CHECK `mentor_user_id <> student_user_id`。
- CHECK `can_view_messages IS FALSE OR can_view_facts IS TRUE`。
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)` ON DELETE CASCADE。
- UNIQUE `mentor_student_assignments_unique` on `(org_id, mentor_user_id, student_user_id, COALESCE(cohort_id, ZERO_UUID))` where `deleted_at IS NULL`。
- INDEX `mentor_student_assignments_mentor_idx` on `(org_id, mentor_user_id)` where `deleted_at IS NULL`。
- INDEX `mentor_student_assignments_student_idx` on `(org_id, student_user_id)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_assignment_membership`：校验 mentor/student/created_by 为 org active 成员；若 `cohort_id` 有值，双方必须为该 cohort 的 active 成员。

### question_bank_versions
用途：题库版本（全局或组织私有）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `scope_org_id` UUID 生成列 `COALESCE(org_id, ZERO_UUID)`。
- `bank_key` TEXT。
- `version` TEXT。
- `source` TEXT。
- `raw_yaml` TEXT。
- `raw_json` JSONB。
- `content_hash` TEXT。
- `is_active` BOOLEAN，默认 `false`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。
- `activated_at` TIMESTAMPTZ。
- `deactivated_at` TIMESTAMPTZ。

约束与索引：
- CHECK `bank_key = lower(btrim(bank_key))`。
- CHECK `bank_key <> ''`。
- CHECK `bank_key !~ '\s'`。
- CHECK `version = btrim(version)`。
- CHECK `version <> ''`。
- CHECK `NOT is_active OR (activated_at IS NOT NULL AND deactivated_at IS NULL)`。
- UNIQUE `question_bank_versions_scope_key_version_unique` on `(scope_org_id, bank_key, version)` where `deleted_at IS NULL`。
- UNIQUE `question_bank_versions_scope_key_active_unique` on `(scope_org_id, bank_key)` where `is_active AND deleted_at IS NULL`。
- UNIQUE `question_bank_versions_scope_content_hash_unique` on `(scope_org_id, content_hash)` where `content_hash IS NOT NULL AND deleted_at IS NULL`。
- INDEX `question_bank_versions_scope_key_idx` on `(scope_org_id, bank_key)`。

完整性触发器：
- `set_question_bank_version_activation`：维护 `activated_at`/`deactivated_at` 与 `is_active` 一致性。

### question_bank_stage_variants
用途：合法的 stage/variant 组合白名单。

字段：
- `stage` TEXT。
- `variant` TEXT。

约束与索引：
- PRIMARY KEY `(stage, variant)`。
- CHECK `stage IN ('problem','market','tech','report')`。
- CHECK `variant IN ('default','router','pro','lite')`。

预置数据：
- `problem/default`、`market/default`、`report/default`、`tech/default`、`tech/router`、`tech/pro`、`tech/lite`。

### question_bank_questions
用途：题库题目明细（每题一行）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `bank_version_id` UUID FK `question_bank_versions(id)` ON DELETE CASCADE。
- `stage` TEXT。
- `variant` TEXT。
- `question_id` TEXT。
- `order_index` INT。
- `title` TEXT。
- `type_raw` TEXT。
- `prompt` TEXT。
- `standard_question` TEXT。
- `consultant_tactic` TEXT。
- `instruction` TEXT。
- `validation_rule` TEXT。
- `schema_paths` TEXT[]，默认空数组。
- `expected_key_points` TEXT[]。
- `capture_intent` TEXT。
- `capture_spec` JSONB，默认 `{}`。
- `answer_examples` JSONB[]，默认空数组。
- `expected_patch_example` JSONB。
- `display_if` JSONB。
- `meta` JSONB，默认 `{}`。
- `is_active` BOOLEAN，默认 `true`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- FK `(stage, variant)` REFERENCES `question_bank_stage_variants(stage, variant)`。
- UNIQUE `question_bank_questions_unique_id` on `(bank_version_id, stage, variant, question_id)` where `deleted_at IS NULL`。
- UNIQUE `question_bank_questions_unique_order` on `(bank_version_id, stage, variant, order_index)` where `deleted_at IS NULL`。
- INDEX `question_bank_questions_next_idx` on `(bank_version_id, stage, variant, order_index)` where `deleted_at IS NULL`。
- GIN `question_bank_questions_schema_paths_gin` on `schema_paths` where `deleted_at IS NULL`。

### projects
用途：学生项目工作流主体。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `cohort_id` UUID，可选。
- `owner_user_id` UUID FK `users(id)`。
- `title` TEXT。
- `description` TEXT。
- `question_bank_version_id` UUID FK `question_bank_versions(id)`。
- `current_stage` TEXT。
- `current_variant` TEXT，默认 `default`。
- `stage_status` TEXT，默认 `in_progress`。
- `settings` JSONB，默认 `{}`。
- `is_archived` BOOLEAN，默认 `false`。
- `archived_at` TIMESTAMPTZ。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CONSTRAINT `projects_org_id_id_unique` UNIQUE `(org_id, id)`。
- CHECK `current_stage IN ('problem','market','tech','report')`。
- CHECK `current_variant IN ('default','router','pro','lite')`。
- CHECK `stage_status IN ('in_progress','awaiting_confirm','passed')`。
- CHECK `is_archived`/`archived_at` 一致性。
- FK `(org_id, cohort_id)` REFERENCES `cohorts(org_id, id)`。
- FK `(current_stage, current_variant)` REFERENCES `question_bank_stage_variants(stage, variant)`。
- INDEX `projects_org_id_idx` on `org_id` where `deleted_at IS NULL`。
- INDEX `projects_owner_user_id_idx` on `owner_user_id` where `deleted_at IS NULL`。
- INDEX `projects_cohort_id_idx` on `cohort_id` where `deleted_at IS NULL`。
- INDEX `projects_question_bank_version_idx` on `question_bank_version_id` where `deleted_at IS NULL`。
- INDEX `projects_org_stage_idx` on `(org_id, current_stage)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_project_owner_membership`：owner 必须是 org active 成员；如有 cohort，必须是该 cohort 的 active student。
- `enforce_project_question_bank_scope`：题库版本必须为 global 或同 org。
- `set_project_archive_timestamps`：维护 `archived_at`。

### project_runtime
用途：当前流程指针（问到哪、下一题等）。

字段：
- `project_id` UUID PK FK `projects(id)` ON DELETE CASCADE。
- `org_id` UUID。
- `stage` TEXT。
- `variant` TEXT。
- `current_question_bank_question_id` UUID FK `question_bank_questions(id)`。
- `next_question_bank_question_id` UUID FK `question_bank_questions(id)`。
- `turn_state` TEXT，默认 `draft`。
- `missing_paths` TEXT[]，默认空数组。
- `runtime_version` INT，默认 `0`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `turn_state IN ('draft','updated','needs_info')`。
- CHECK `runtime_version >= 0`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)`。
- FK `(stage, variant)` REFERENCES `question_bank_stage_variants(stage, variant)`。
- INDEX `project_runtime_org_stage_idx` on `(org_id, stage, variant)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_project_runtime_questions`：自动对齐 project 的 stage/variant，并校验 current/next question 与项目题库一致。

### prompt_templates
用途：Prompt 版本管理。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `scope_org_id` UUID 生成列 `COALESCE(org_id, ZERO_UUID)`。
- `template_key` TEXT，规范化 key。
- `purpose` TEXT。
- `stage` TEXT。
- `variant` TEXT。
- `version` TEXT。
- `content` TEXT。
- `params` JSONB。
- `is_active` BOOLEAN，默认 `false`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `purpose IN ('chat','extract','summary','score','evaluate','report')`。
- CHECK `template_key` 规范化且匹配 `^[a-z0-9_.-]+$`。
- CHECK `variant IS NULL OR stage IS NOT NULL`。
- CHECK `stage IS NULL OR stage IN ('problem','market','tech','report')`。
- UNIQUE `prompt_templates_scope_unique` on `(scope_org_id, template_key, version)` where `deleted_at IS NULL`。
- UNIQUE `prompt_templates_scope_active_unique` on `(scope_org_id, template_key)` where `is_active AND deleted_at IS NULL`。

完整性触发器：
- `enforce_prompt_template_stage_variant`：当 `variant` 有值时，`(stage, variant)` 必须在白名单中。

### project_question_instances
用途：项目内某题的实例状态与抽取结果。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `question_bank_question_id` UUID FK `question_bank_questions(id)`。
- `status` TEXT，默认 `pending`。
- `asked_count` INT，默认 `0`。
- `last_asked_at` TIMESTAMPTZ。
- `answered_at` TIMESTAMPTZ。
- `final_answer_text` TEXT。
- `extracted_patch_json` JSONB，默认 `{}`。
- `validation_status` TEXT，默认 `not_validated`。
- `validation_errors` JSONB，默认 `[]`。
- `extract_model` TEXT。
- `extract_prompt_template_id` UUID FK `prompt_templates(id)`。
- `extract_confidence` NUMERIC(4,3)。
- `meta` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `status IN ('pending','asked','answered','needs_info','skipped','invalid','autofilled')`。
- CHECK `asked_count >= 0`。
- CHECK `validation_status IN ('not_validated','valid','invalid','needs_info')`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `project_question_instances_unique` on `(project_id, question_bank_question_id)` where `deleted_at IS NULL`。
- INDEX `project_question_instances_status_idx` on `(project_id, status, updated_at DESC)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_project_question_instance_bank`：确保该题属于项目绑定的题库版本。

### conversation_messages
用途：对话证据层消息记录。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `project_id` UUID。
- `author_user_id` UUID FK `users(id)`。
- `role` TEXT。
- `is_visible` BOOLEAN，默认 `true`。
- `stage` TEXT。
- `variant` TEXT。
- `question_instance_id` UUID FK `project_question_instances(id)`。
- `client_message_id` UUID。
- `request_id` UUID。
- `content` TEXT。
- `content_format` TEXT，默认 `markdown`。
- `model_name` TEXT。
- `prompt_template_id` UUID FK `prompt_templates(id)`。
- `token_prompt` INT。
- `token_output` INT。
- `latency_ms` INT。
- `meta` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `redacted_at` TIMESTAMPTZ。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `role IN ('user','assistant','system','tool')`。
- CHECK `stage IN ('problem','market','tech','report')`。
- CHECK `content_format IN ('markdown','text','json')`。
- CHECK `token_prompt >= 0` when not null.
- CHECK `token_output >= 0` when not null.
- CHECK `latency_ms >= 0` when not null.
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `conversation_messages_client_unique` on `(project_id, client_message_id)` where `client_message_id IS NOT NULL AND deleted_at IS NULL`。
- INDEX `conversation_messages_project_created_idx` on `(project_id, created_at)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_conversation_message_integrity`：校验 question_instance 归属；当 `role='user'` 时要求 author 为项目 owner 并对齐 runtime 的 stage/variant。

### project_states
用途：项目事实层（结构化唯一来源）。

字段：
- `project_id` UUID PK FK `projects(id)` ON DELETE CASCADE。
- `org_id` UUID。
- `bank_version_id` UUID FK `question_bank_versions(id)`。
- `state_schema_version` TEXT，默认 `v1`。
- `state_json` JSONB，默认 `{}`。
- `state_version` INT，默认 `0`。
- `state_meta` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `state_version >= 0`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。

完整性触发器：
- `enforce_project_state_bank_version`：确保 `bank_version_id` 与项目绑定的题库一致。

### project_state_events
用途：事实层变更事件（审计/回滚/排错）。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `project_id` UUID。
- `question_instance_id` UUID FK `project_question_instances(id)`。
- `event_type` TEXT。
- `patch_json` JSONB。
- `actor_type` TEXT。
- `actor_user_id` UUID FK `users(id)`。
- `model_name` TEXT。
- `prompt_template_id` UUID FK `prompt_templates(id)`。
- `prev_state_version` INT。
- `next_state_version` INT。
- `request_id` UUID。
- `created_at` TIMESTAMPTZ，默认 `now()`。

约束与索引：
- CHECK `actor_type IN ('user','system','ai')`。
- CHECK `actor_type <> 'user' OR actor_user_id IS NOT NULL`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- INDEX `project_state_events_project_created_idx` on `(project_id, created_at DESC)`。

完整性触发器：
- `enforce_project_state_event_integrity`：校验 question_instance 归属；对 `apply_patch` 强制版本连续。

### documents
用途：项目资料/附件与解析状态。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `file_name` TEXT。
- `content_type` TEXT。
- `storage_key` TEXT。
- `status` TEXT，默认 `uploaded`。
- `error_message` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。
- `meta` JSONB，默认 `{}`。

约束与索引：
- CHECK `status IN ('uploaded','extracting','extracted','chunked','embedded','indexed','failed')`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `documents_storage_key_unique` on `(org_id, storage_key)` where `deleted_at IS NULL`。
- INDEX `documents_project_status_idx` on `(project_id, status)` where `deleted_at IS NULL`。

### analytics_events
用途：分析/埋点事件。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `project_id` UUID FK `projects(id)` ON DELETE SET NULL。
- `actor_user_id` UUID FK `users(id)`。
- `event_type` TEXT。
- `payload` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。

索引：
- `analytics_events_org_created_idx` on `(org_id, created_at DESC)`。
- `analytics_events_project_created_idx` on `(project_id, created_at DESC)`。
- `analytics_events_org_type_created_idx` on `(org_id, event_type, created_at DESC)`。

### audit_events
用途：跨域审计日志。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `actor_user_id` UUID FK `users(id)`。
- `actor_type` TEXT。
- `event_type` TEXT。
- `target_type` TEXT。
- `target_id` TEXT。
- `payload` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。

约束与索引：
- CHECK `actor_type IN ('user','system')`。
- `audit_events_org_created_idx` on `(org_id, created_at DESC)`。
- `audit_events_org_type_created_idx` on `(org_id, event_type, created_at DESC)`。
- `audit_events_org_target_idx` on `(org_id, target_type, target_id, created_at DESC)`。
- `audit_events_org_actor_idx` on `(org_id, actor_user_id, created_at DESC)`。

### project_stage_assessments
用途：阶段总结与 Gate 确认。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `stage` TEXT。
- `draft_summary_markdown` TEXT。
- `final_summary_markdown` TEXT。
- `confirmed` BOOLEAN，默认 `false`。
- `confirmed_at` TIMESTAMPTZ。
- `confirmed_by_user_id` UUID FK `users(id)`。
- `generated_from_state_version` INT。
- `generator_model` TEXT。
- `generator_prompt_template_id` UUID FK `prompt_templates(id)`。
- `scores_json` JSONB。
- `total_score` NUMERIC。
- `risk_matrix` JSONB。
- `context_card_json` JSONB，默认 `{}`。已确认阶段的证据分层诊断卡片。
- `validation_plan_json` JSONB，默认 `[]`。已确认阶段的短周期验证动作。
- `diagram_mermaid` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `stage IN ('problem','market','tech')`。
- CHECK `confirmed` 与 `confirmed_at`、`confirmed_by_user_id` 的一致性。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `project_stage_assessments_unique` on `(project_id, stage)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_project_stage_assessment_confirmer`：确认人必须为项目 owner 或 org owner/admin 且为 active 成员，并维护 `confirmed_at`。
- `enforce_project_stage_assessment_state_version`：`generated_from_state_version` 不能超过当前 state_version。

### project_stage_qa_digests
用途：按题的 QA 摘要，用于验证与报告引用。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `assessment_id` UUID FK `project_stage_assessments(id)`。
- `stage` TEXT。
- `question_id` TEXT。
- `answer_summary` TEXT。
- `key_points` TEXT[]。
- `source_message_id` BIGINT FK `conversation_messages(id)`。
- `model` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `stage IN ('problem','market','tech')`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- `project_stage_qa_digests_project_stage_created_idx` on `(project_id, stage, created_at DESC)` where `deleted_at IS NULL`。
- `project_stage_qa_digests_assessment_idx` on `(assessment_id)` where `deleted_at IS NULL`。

### project_stage_verification_claims
用途：阶段验证的证据条目（claim + verdict）。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `assessment_id` UUID FK `project_stage_assessments(id)`（可为空）。
- `stage` TEXT。
- `question_id` TEXT（可为空）。
- `question_bank_question_id` UUID FK `question_bank_questions(id)`（可为空）。
- `source_message_id` BIGINT FK `conversation_messages(id)`（可为空）。
- `priority` TEXT（可为空）。
- `batch_id` UUID（可为空）。
- `claim` TEXT。
- `verdict` TEXT。
- `confidence` TEXT。
- `rationale` TEXT。
- `sources` JSONB。
- `evidence_mode` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `stage IN ('problem','market','tech')`。
- CHECK `verdict IN ('supported','contradicted','uncertain')`。
- CHECK `confidence IN ('High','Medium','Low')`（允许空）。
- CHECK `priority IN ('high','medium','low','none')`（允许空）。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- `project_stage_verification_claims_project_stage_created_idx` on `(project_id, stage, created_at DESC)` where `deleted_at IS NULL`。
- `project_stage_verification_claims_project_stage_question_created_idx` on `(project_id, stage, question_bank_question_id, created_at DESC)` where `deleted_at IS NULL`。
- `project_stage_verification_claims_assessment_idx` on `(assessment_id)` where `deleted_at IS NULL`。

### project_reports
用途：最终报告版本化存储。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `report_version` INT。
- `status` TEXT，默认 `draft`。
- `content_markdown` TEXT。
- `content_json` JSONB。
- `diagnosis_json` JSONB，默认 `{}`。最终报告的证据分层诊断载荷。
- `validation_plan_json` JSONB，默认 `[]`。报告层聚合验证计划。
- `generated_from_state_version` INT。
- `generator_model` TEXT。
- `generator_prompt_template_id` UUID FK `prompt_templates(id)`。
- `confirmed` BOOLEAN，默认 `false`。
- `confirmed_at` TIMESTAMPTZ。
- `export_storage_key` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `report_version >= 1`。
- CHECK `status IN ('draft','final','archived')`。
- CHECK `confirmed` 与 `confirmed_at` 一致性。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `project_reports_unique` on `(project_id, report_version)` where `deleted_at IS NULL`。

完整性触发器：
- `set_project_report_confirmed_at`：维护 `confirmed_at`。

### project_comments
用途：导师/学生批注通道。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `author_user_id` UUID FK `users(id)`。
- `visibility` TEXT，默认 `student_and_mentors`。
- `status` TEXT，默认 `open`。
- `content` TEXT。
- `content_format` TEXT，默认 `markdown`。
- `target_stage` TEXT。
- `target_question_instance_id` UUID FK `project_question_instances(id)`。
- `target_message_id` BIGINT FK `conversation_messages(id)`。
- `target_report_id` UUID FK `project_reports(id)`。
- `target_section_key` TEXT。
- `parent_comment_id` UUID FK `project_comments(id)`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `visibility IN ('student_and_mentors','mentors_only','private')`。
- CHECK `status IN ('open','resolved','archived')`。
- CHECK `content_format IN ('markdown','text')`。
- CHECK `target_stage IS NULL OR target_stage IN ('problem','market','tech','report')`。
- CHECK `num_nonnulls(...) <= 1`（最多一个定位目标）。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- INDEX `project_comments_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`。
- INDEX `project_comments_project_status_idx` on `(project_id, status)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_project_comment_author_membership`：作者必须为 org active 成员。
- `enforce_project_comment_targets`：目标必须属于同一 project/org。

### notifications
用途：通知投递记录。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `recipient_user_id` UUID FK `users(id)`。
- `type` TEXT。
- `title` TEXT。
- `body` TEXT。
- `link` TEXT。
- `payload` JSONB，默认 `{}`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `read_at` TIMESTAMPTZ。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `type = lower(btrim(type))`。
- CHECK `type <> ''`。
- CHECK `type ~ '^[a-z0-9_.-]+$'`。
- CHECK `link IS NULL OR length(link) <= 2000`。
- INDEX `notifications_recipient_unread_idx` on `(recipient_user_id, read_at, created_at DESC)` where `deleted_at IS NULL`。

### evaluation_rubrics
用途：评分标准版本库。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID FK `organizations(id)` ON DELETE CASCADE。
- `scope_org_id` UUID 生成列 `COALESCE(org_id, ZERO_UUID)`。
- `rubric_key` TEXT。
- `rubric_version` TEXT。
- `scope` TEXT。
- `definition_json` JSONB。
- `is_active` BOOLEAN，默认 `true`。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `scope IN ('answer','message')`。
- UNIQUE `evaluation_rubrics_unique` on `(scope_org_id, scope, rubric_key, rubric_version)` where `deleted_at IS NULL`。
- UNIQUE `evaluation_rubrics_active_unique` on `(scope_org_id, rubric_key, scope)` where `is_active AND deleted_at IS NULL`。

### answer_evaluations
用途：对题实例的评分结果。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `question_instance_id` UUID FK `project_question_instances(id)`。
- `rubric_id` UUID FK `evaluation_rubrics(id)`。
- `scores_json` JSONB。
- `overall_score` NUMERIC。
- `feedback_markdown` TEXT。
- `evaluator_type` TEXT。
- `evaluator_model` TEXT。
- `request_id` UUID。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `evaluator_type IN ('ai','human','system')`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `answer_evaluations_request_unique` on `request_id` where `request_id IS NOT NULL AND deleted_at IS NULL`。
- INDEX `answer_evaluations_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_answer_evaluation_scope`：question_instance 必须属于同一 project/org。

### message_evaluations
用途：对消息（AI 回复）的评分结果。

字段：
- `id` UUID PK，默认 `gen_random_uuid()`。
- `org_id` UUID。
- `project_id` UUID。
- `message_id` BIGINT FK `conversation_messages(id)`。
- `rubric_id` UUID FK `evaluation_rubrics(id)`。
- `scores_json` JSONB。
- `overall_score` NUMERIC。
- `feedback_markdown` TEXT。
- `evaluator_type` TEXT。
- `evaluator_model` TEXT。
- `request_id` UUID。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `evaluator_type IN ('ai','human','system')`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE CASCADE。
- UNIQUE `message_evaluations_request_unique` on `request_id` where `request_id IS NOT NULL AND deleted_at IS NULL`。
- INDEX `message_evaluations_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_message_evaluation_scope`：message 必须属于同一 project/org。

### background_jobs
用途：异步任务队列。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `project_id` UUID。
- `job_type` TEXT。
- `status` TEXT，默认 `queued`。
- `priority` INT，默认 `100`。
- `payload` JSONB。
- `idempotency_key` TEXT。
- `attempts` INT，默认 `0`。
- `max_attempts` INT，默认 `5`。
- `run_at` TIMESTAMPTZ，默认 `now()`。
- `locked_at` TIMESTAMPTZ。
- `lock_expires_at` TIMESTAMPTZ。
- `locked_by` TEXT。
- `started_at` TIMESTAMPTZ。
- `completed_at` TIMESTAMPTZ。
- `last_error` TEXT。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `updated_at` TIMESTAMPTZ，默认 `now()`。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `job_type` 规范化且匹配 `^[a-z0-9_.-]+$`。
- CHECK `status IN ('queued','running','succeeded','failed','cancelled')`。
- CHECK `priority >= 0`。
- CHECK `attempts >= 0`。
- CHECK `max_attempts >= 0`。
- CHECK 锁字段三元一致（全空或全有）。
- CHECK `status='running'` => `started_at` 有值且 `completed_at` 为空。
- CHECK 终态必须有 `completed_at`。
- FK `(org_id, project_id)` REFERENCES `projects(org_id, id)` ON DELETE SET NULL。
- UNIQUE `background_jobs_idempotency_unique` on `(org_id, job_type, idempotency_key)` where `idempotency_key IS NOT NULL AND deleted_at IS NULL`。
- INDEX `background_jobs_queue_idx` on `(status, run_at, priority)` where `deleted_at IS NULL`。
- INDEX `background_jobs_locked_idx` on `(locked_at)` where `deleted_at IS NULL`。
- INDEX `background_jobs_project_created_idx` on `(project_id, created_at DESC)` where `deleted_at IS NULL`。

完整性触发器：
- `set_background_job_timestamps`：根据状态维护 `started_at`/`completed_at`。

### idempotency_keys
用途：API 幂等键记录。

字段：
- `id` BIGINT PK，自增。
- `org_id` UUID。
- `user_id` UUID FK `users(id)`。
- `scope` TEXT。
- `key` TEXT。
- `request_hash` TEXT。
- `response_ref` JSONB。
- `created_at` TIMESTAMPTZ，默认 `now()`。
- `expires_at` TIMESTAMPTZ。
- `deleted_at` TIMESTAMPTZ。

约束与索引：
- CHECK `scope = lower(btrim(scope))`。
- CHECK `scope <> ''`。
- CHECK `scope !~ '\s'`。
- CHECK `key = btrim(key)`。
- CHECK `key <> ''`。
- CHECK `key ~ '^[A-Za-z0-9_.:-]+$'`。
- CHECK `expires_at IS NULL OR expires_at > created_at`。
- UNIQUE `idempotency_keys_unique` on `(org_id, scope, key)` where `deleted_at IS NULL`。
- INDEX `idempotency_keys_user_created_idx` on `(user_id, created_at DESC)` where `deleted_at IS NULL`。

完整性触发器：
- `enforce_idempotency_key_consistency`：`request_hash` 与 `response_ref` 一旦设置不可再变更。
