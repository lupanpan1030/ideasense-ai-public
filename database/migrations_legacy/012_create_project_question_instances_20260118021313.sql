-- 012) project_question_instances
CREATE TABLE project_question_instances (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                    UUID NOT NULL,
    project_id                UUID NOT NULL,
    question_bank_question_id UUID NOT NULL REFERENCES question_bank_questions(id),
    status                    TEXT NOT NULL DEFAULT 'pending',
    asked_count               INT NOT NULL DEFAULT 0,
    last_asked_at             TIMESTAMPTZ NULL,
    answered_at               TIMESTAMPTZ NULL,
    final_answer_text         TEXT NULL,
    extracted_patch_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_status         TEXT NOT NULL DEFAULT 'not_validated',
    validation_errors         JSONB NOT NULL DEFAULT '[]'::jsonb,
    extract_model             TEXT NULL,
    extract_prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    extract_confidence        NUMERIC(4,3) NULL,
    meta                      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    CHECK (status IN ('pending','asked','answered','needs_info','skipped','invalid','autofilled')),
    CHECK (asked_count >= 0),
    CHECK (validation_status IN ('not_validated','valid','invalid','needs_info')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX project_question_instances_unique
    ON project_question_instances (project_id, question_bank_question_id)
    WHERE deleted_at IS NULL;

CREATE INDEX project_question_instances_status_idx
    ON project_question_instances (project_id, status, updated_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_question_instance_bank()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    question_bank_id UUID;
BEGIN
    SELECT question_bank_version_id
      INTO project_bank_id
      FROM projects
     WHERE id = NEW.project_id
       AND deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    SELECT bank_version_id
      INTO question_bank_id
      FROM question_bank_questions
     WHERE id = NEW.question_bank_question_id
       AND deleted_at IS NULL;

    IF question_bank_id IS NULL THEN
        RAISE EXCEPTION 'question_bank_question_id % not found', NEW.question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF question_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'question_bank_question_id % does not match project bank %',
            NEW.question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_question_instances_bank_guard
    BEFORE INSERT OR UPDATE ON project_question_instances
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_question_instance_bank();
