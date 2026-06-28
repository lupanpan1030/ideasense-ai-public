-- 010) project_runtime
CREATE TABLE project_runtime (
    project_id                       UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    org_id                           UUID NOT NULL,
    stage                            TEXT NOT NULL,
    variant                          TEXT NOT NULL,
    current_question_bank_question_id UUID NOT NULL REFERENCES question_bank_questions(id),
    next_question_bank_question_id   UUID NULL REFERENCES question_bank_questions(id),
    turn_state                       TEXT NOT NULL DEFAULT 'draft',
    missing_paths                    TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    runtime_version                  INT NOT NULL DEFAULT 0,
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                       TIMESTAMPTZ,
    CHECK (turn_state IN ('draft','updated','needs_info')),
    CHECK (runtime_version >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id),
    FOREIGN KEY (stage, variant)
        REFERENCES question_bank_stage_variants (stage, variant)
);

CREATE INDEX project_runtime_org_stage_idx
    ON project_runtime (org_id, stage, variant)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    SELECT question_bank_version_id, current_stage, current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects
     WHERE id = NEW.project_id
       AND deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    SELECT bank_version_id, stage, variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions
     WHERE id = NEW.current_question_bank_question_id
       AND deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT bank_version_id, stage, variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions
         WHERE id = NEW.next_question_bank_question_id
           AND deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_runtime_question_guard
    BEFORE INSERT OR UPDATE ON project_runtime
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_runtime_questions();
