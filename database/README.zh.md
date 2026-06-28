# 数据库

开始阅读：
- 完整表结构参考（中文）：`database/docs/schema_reference.zh.md`
- 完整表结构参考（英文）：`database/docs/schema_reference.md`
- 文档索引：`database/docs/README.md`
- 初始化脚本：`database/scripts/bootstrap_db.py`
- 重置脚本：`database/scripts/reset_db.py`
- 结构快照：`database/schema/schema.sql`

## 常见任务
本地初始化（建库 + 迁移 + 角色 + 题库 + 快照）：
```
DATABASE_URL_ADMIN=... python database/scripts/bootstrap_db.py
```
托管数据库建议加 `--managed-db`，跳过角色授权并在导入题库时临时放开 FORCE RLS。

本地重置（删库重建 + 迁移 + 角色 + 题库 + 种子）：
```
DATABASE_URL_ADMIN=... python database/scripts/reset_db.py --db-name ideasense_ai_dev
```
托管数据库重建时建议加 `--managed-db`（远端通常还会加 `--skip-seed`）。

常用参数：
- `--db-name`（默认：`ideasense_ai_dev`）
- `--env-file`（加载 `DATABASE_URL_ADMIN`）
- `--managed-db`、`--skip-roles`、`--skip-migrations`、`--skip-question-bank`、`--skip-schema`

仅导入题库：
```
python database/scripts/import_question_bank.py --dsn "<dsn>" --yaml resources/question_bank.example.yaml
```

私有部署可以显式传入私有生产题库 YAML。公开导出版本应使用
`resources/question_bank.example.yaml`。

生成快照：
```
python database/scripts/generate_schema_snapshot.py
```

RLS 下手动调试（psql）：
```
psql "<dsn>" -f database/scripts/with_system_actor.sql
```

全量种子：
```
psql "<dsn>" -f database/seeds/seed_dev.sql
```

单个流程种子：
```
psql "<dsn>" -f database/seeds/flows/<flow>/<flow>_seed.sql
```

## 目录说明
- `migrations/`: 迁移脚本（真实来源）。
- `schema/`: 迁移生成的快照（不要手改）。
- `docs/`: 结构说明与参考。
- `roles/`: 角色与授权定义。
- `scripts/`: 初始化/导入/生成脚本。
- `seeds/`: 基础数据（手动应用）。
- `fixtures/`: 测试/演示数据。

## 约定
- 软删除字段 `deleted_at`；唯一性多用 `deleted_at IS NULL` 的 partial index。
- 邮箱/slug/type 做 trim + 空白校验，slug 强制小写。
- 邮箱字段使用 `CITEXT` 做大小写不敏感。
- 全局/组织范围用 `scope_org_id = COALESCE(org_id, ZERO_UUID)`。
- `updated_at` 由统一触发器维护（`set_updated_at`）。
- `question_bank_stage_variants` 定义合法 stage/variant 组合。
- RLS 已启用，依赖会话变量 `app.user_id` / `app.org_id` / `app.actor_type`。

## RLS 与角色（补充说明）
- 角色与授权定义在 `database/roles/rls_roles.sql`。
- 运行时连接（app_runtime/app_worker）不应使用 BYPASSRLS。
- 应用每次事务内需要设置：
  - `SET LOCAL app.user_id = '<uuid>'`
  - `SET LOCAL app.org_id = '<uuid>'`
  - `SET LOCAL app.actor_type = 'user' | 'system'`

## 模块概览
身份与鉴权：
- `users`, `user_identities`

组织与班级：
- `organizations`, `organization_memberships`, `organization_invitations`
- `cohorts`, `cohort_memberships`
- `mentor_student_assignments`

题库：
- `question_bank_versions`, `question_bank_stage_variants`, `question_bank_questions`

项目与运行态：
- `projects`, `project_runtime`, `project_question_instances`
- `project_states`, `project_state_events`

证据与协作：
- `conversation_messages`, `project_comments`, `notifications`

输出：
- `project_stage_assessments`, `project_reports`

Prompt 与文档：
- `prompt_templates`, `documents`

分析与审计：
- `analytics_events`, `audit_events`

评估：
- `evaluation_rubrics`, `answer_evaluations`, `message_evaluations`

异步与幂等：
- `background_jobs`, `idempotency_keys`
