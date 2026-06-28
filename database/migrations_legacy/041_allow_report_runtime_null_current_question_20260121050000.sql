-- 041) Allow report runtime without a current question
ALTER TABLE project_runtime
    ALTER COLUMN current_question_bank_question_id DROP NOT NULL;

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
    SELECT p.question_bank_version_id, p.current_stage, p.current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects p
     WHERE p.id = NEW.project_id
       AND p.deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    IF NEW.stage = 'report' AND NEW.current_question_bank_question_id IS NULL THEN
        NEW.next_question_bank_question_id := NULL;
        RETURN NEW;
    END IF;

    IF NEW.current_question_bank_question_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id is required'
            USING ERRCODE = '23514';
    END IF;

    SELECT q.bank_version_id, q.stage, q.variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions q
     WHERE q.id = NEW.current_question_bank_question_id
       AND q.deleted_at IS NULL;

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
        SELECT q.bank_version_id, q.stage, q.variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions q
         WHERE q.id = NEW.next_question_bank_question_id
           AND q.deleted_at IS NULL;

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
