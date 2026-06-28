# Migrations

Purpose: ordered SQL migrations. These are the source of truth for the schema.

## Baseline
- `000_baseline_*.sql` is the consolidated schema snapshot.
- `001_seed_core_*.sql` seeds required lookup data (e.g. default rubrics).
- Historical migrations are archived in `database/migrations_legacy/` and are
  no longer executed.

## Naming
- `NNN_description_YYYYMMDDHHMMSS.sql`

## How to add a migration
- Create a new file with the next sequence number.
- Never edit historical migrations; add a new one for changes.
- Regenerate the schema snapshot after changes.

Related:
- Schema snapshot: `database/schema/schema.sql`
- Generator: `database/scripts/generate_schema_snapshot.py`
- Root README: `database/README.md`
