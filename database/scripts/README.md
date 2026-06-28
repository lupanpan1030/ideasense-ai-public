# Scripts

Purpose: bootstrap and maintenance helpers for the database.
Managed DBs (Neon/Render/etc.) should use `--managed-db` to skip role grants and
relax FORCE RLS during question bank imports.
For manual psql debugging under RLS, run `database/scripts/with_system_actor.sql`.

## bootstrap_db.py
Creates the database, runs migrations, applies roles, imports the question bank, and generates the schema snapshot.

Example:
```
DATABASE_URL_ADMIN=... python database/scripts/bootstrap_db.py
```

Useful flags:
- `--db-name`
- `--env-file`
- `--managed-db`, `--skip-roles`, `--skip-migrations`, `--skip-question-bank`, `--skip-schema`
- `--mark-existing` (mark all migrations as applied without running them)

## import_question_bank.py
Imports a YAML question bank into `question_bank_versions` and `question_bank_questions`.

Example:
```
python database/scripts/import_question_bank.py --dsn "<dsn>" --yaml resources/question_bank.example.yaml
```

Private deployments may pass a private production question-bank YAML
explicitly. Public exports should use `resources/question_bank.example.yaml`.

## verify_stage_flow.py
Validates problem -> market -> tech (router) -> pro/lite -> report with API calls, and checks
the router and pro/lite question IDs via the database.

Example:
```
IDEASENSE_API_BASE_URL=http://localhost:8000/api/v1 \
DATABASE_URL_ADMIN=... \
python database/scripts/verify_stage_flow.py
```

## verify_gate_flow.py
Validates the answer gate: a weak answer should not advance the runtime, while a strong
answer should advance and enqueue extraction.

Example:
```
IDEASENSE_API_BASE_URL=http://localhost:8000/api/v1 \
DATABASE_URL_ADMIN=... \
python database/scripts/verify_gate_flow.py
```

## reset_db.py
Drops and recreates the database, runs migrations, applies roles, imports the question bank, then seeds.

Example:
```
DATABASE_URL_ADMIN=... python database/scripts/reset_db.py --db-name ideasense_ai_dev
```

Useful flags:
- `--managed-db`, `--skip-roles`, `--skip-question-bank`, `--skip-seed`, `--skip-schema`
- `--question-bank-yaml`, `--seed-file`

## generate_schema_snapshot.py
Concatenates migrations into `database/schema/schema.sql`.

Example:
```
python database/scripts/generate_schema_snapshot.py
```

## rls_roles.sql
Role and grant setup for runtime/worker connections (no BYPASSRLS).
Located at `database/roles/rls_roles.sql`.

## with_system_actor.sql
Sets `app.actor_type=system` for the current session (helpful for RLS debugging).
