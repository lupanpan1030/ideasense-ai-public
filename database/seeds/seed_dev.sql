-- Seed data for local/dev testing.
-- Requires a question bank to be imported first.

\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
    bank_id uuid;
BEGIN
    SELECT id
      INTO bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1;

    IF bank_id IS NULL THEN
        RAISE EXCEPTION 'question bank not imported; run import_question_bank.py first';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM question_bank_questions
         WHERE bank_version_id = bank_id
           AND stage = 'problem'
           AND variant = 'default'
           AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'question bank missing problem/default questions';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM question_bank_questions
         WHERE bank_version_id = bank_id
           AND stage = 'market'
           AND variant = 'default'
           AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'question bank missing market/default questions';
    END IF;
END;
$$;

\ir flows/org/org_seed.sql
\ir flows/auth/auth_seed.sql
\ir flows/cohorts/cohorts_seed.sql
\ir flows/assignments/assignments_seed.sql
\ir flows/projects/projects_seed.sql
\ir flows/evidence/evidence_seed.sql
\ir flows/outputs/outputs_seed.sql
\ir flows/evaluations/evaluations_seed.sql
\ir flows/assets/assets_seed.sql
\ir flows/ops/ops_seed.sql

COMMIT;
