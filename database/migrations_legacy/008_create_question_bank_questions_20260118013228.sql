-- 008) question_bank_questions
CREATE TABLE question_bank_questions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_version_id         UUID NOT NULL REFERENCES question_bank_versions(id) ON DELETE CASCADE,
    stage                  TEXT NOT NULL,
    variant                TEXT NOT NULL,
    question_id            TEXT NOT NULL,
    order_index            INT NOT NULL,
    title                  TEXT NOT NULL,
    type_raw               TEXT NOT NULL,
    prompt                 TEXT NOT NULL,
    standard_question      TEXT NULL,
    consultant_tactic      TEXT NULL,
    instruction            TEXT NULL,
    validation_rule        TEXT NULL,
    schema_paths           TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    capture_intent         TEXT NULL,
    capture_spec           JSONB NOT NULL DEFAULT '{}'::jsonb,
    answer_examples        JSONB[] NOT NULL DEFAULT ARRAY[]::jsonb[],
    expected_patch_example JSONB NULL,
    display_if             JSONB NULL,
    meta                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active              BOOLEAN NOT NULL DEFAULT true,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ,
    FOREIGN KEY (stage, variant)
        REFERENCES question_bank_stage_variants (stage, variant)
);

CREATE UNIQUE INDEX question_bank_questions_unique_id
    ON question_bank_questions (bank_version_id, stage, variant, question_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_questions_unique_order
    ON question_bank_questions (bank_version_id, stage, variant, order_index)
    WHERE deleted_at IS NULL;

CREATE INDEX question_bank_questions_next_idx
    ON question_bank_questions (bank_version_id, stage, variant, order_index)
    WHERE deleted_at IS NULL;

CREATE INDEX question_bank_questions_schema_paths_gin
    ON question_bank_questions USING gin (schema_paths)
    WHERE deleted_at IS NULL;
