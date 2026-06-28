# Database

Start here:
- Full reference: `database/docs/schema_reference.md`
- Docs index: `database/docs/README.md`
- Bootstrap script: `database/scripts/bootstrap_db.py`
- Reset script: `database/scripts/reset_db.py`
- Schema snapshot: `database/schema/schema.sql`

## Common Tasks
Bootstrap a local database (create DB, run migrations, apply roles, import question bank, generate snapshot):
```
DATABASE_URL_ADMIN=... python database/scripts/bootstrap_db.py
```
Managed DBs should add `--managed-db` to skip role grants and relax FORCE RLS during question bank imports.

Reset a local database (drop/recreate + migrations + roles + question bank + seed):
```
DATABASE_URL_ADMIN=... python database/scripts/reset_db.py --db-name ideasense_ai_dev
```
Managed DBs should add `--managed-db` (and usually `--skip-seed`) when rebuilding remotely.

Useful flags:
- `--db-name` (default: `ideasense_ai_dev`)
- `--env-file` (loads `DATABASE_URL_ADMIN`)
- `--managed-db`, `--skip-roles`, `--skip-migrations`, `--skip-question-bank`, `--skip-schema`

Import a question bank only:
```
python database/scripts/import_question_bank.py --dsn "<dsn>" --yaml resources/question_bank.example.yaml
```

Private deployments may pass their private production question-bank YAML
explicitly. Public exports should use `resources/question_bank.example.yaml`.

Regenerate the schema snapshot:
```
python database/scripts/generate_schema_snapshot.py
```

Manual psql debugging under RLS:
```
psql "<dsn>" -f database/scripts/with_system_actor.sql
```

Seed data (all flows):
```
psql "<dsn>" -f database/seeds/seed_dev.sql
```

Seed a single flow:
```
psql "<dsn>" -f database/seeds/flows/<flow>/<flow>_seed.sql
```

## Directory Map
- `migrations/`: ordered SQL migrations (source of truth).
- `schema/`: generated snapshots (do not edit by hand).
- `docs/`: schema notes and references.
- `roles/`: role and grant definitions.
- `scripts/`: bootstrap/import/snapshot helpers.
- `seeds/`: baseline data (manual application).
- `fixtures/`: dev/test demo data.
- `README.zh.md`: Chinese summary.

## Conventions
- Soft deletes use `deleted_at`; uniqueness is enforced with partial indexes on `deleted_at IS NULL`.
- Email/slug/type keys are trimmed and validated for whitespace; slugs are lowercase.
- Case-insensitive email columns use `CITEXT`.
- Global vs org scope uses `scope_org_id = COALESCE(org_id, ZERO_UUID)`.
- `updated_at` is auto-maintained by a shared trigger (`set_updated_at`).
- Stage/variant combinations are whitelisted by `question_bank_stage_variants`.
- RLS is enabled on all tables and expects session vars `app.user_id`, `app.org_id`, `app.actor_type`.

## Schema Modules
Identity and auth:
- `users`, `user_identities`

Organizations and cohorts:
- `organizations`, `organization_memberships`, `organization_invitations`
- `cohorts`, `cohort_memberships`
- `mentor_student_assignments`

Question bank:
- `question_bank_versions`, `question_bank_stage_variants`, `question_bank_questions`

Projects and runtime:
- `projects`, `project_runtime`, `project_question_instances`
- `project_states`, `project_state_events`

Evidence and collaboration:
- `conversation_messages`, `project_comments`, `notifications`

Outputs:
- `project_stage_assessments`, `project_reports`

Prompts and documents:
- `prompt_templates`, `documents`

Analytics and audit:
- `analytics_events`, `audit_events`

Evaluation:
- `evaluation_rubrics`, `answer_evaluations`, `message_evaluations`

Async and idempotency:
- `background_jobs`, `idempotency_keys`
