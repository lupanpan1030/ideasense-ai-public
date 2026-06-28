-- 024) answer_evaluations
CREATE TABLE answer_evaluations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL,
    project_id          UUID NOT NULL,
    question_instance_id UUID NOT NULL REFERENCES project_question_instances(id),
    rubric_id           UUID NOT NULL REFERENCES evaluation_rubrics(id),
    scores_json         JSONB NOT NULL,
    overall_score       NUMERIC NULL,
    feedback_markdown   TEXT NULL,
    evaluator_type      TEXT NOT NULL,
    evaluator_model     TEXT NULL,
    request_id          UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ NULL,
    CHECK (evaluator_type IN ('ai','human','system')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX answer_evaluations_request_unique
    ON answer_evaluations (request_id)
    WHERE request_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX answer_evaluations_project_created_idx
    ON answer_evaluations (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_answer_evaluation_scope()
RETURNS trigger AS $$
DECLARE
    instance_project_id UUID;
    instance_org_id UUID;
BEGIN
    SELECT project_id, org_id
      INTO instance_project_id, instance_org_id
      FROM project_question_instances
     WHERE id = NEW.question_instance_id
       AND deleted_at IS NULL;

    IF instance_project_id IS NULL THEN
        RAISE EXCEPTION 'question_instance % not found or deleted',
            NEW.question_instance_id
            USING ERRCODE = '23514';
    END IF;

    IF instance_project_id <> NEW.project_id
        OR instance_org_id <> NEW.org_id THEN
        RAISE EXCEPTION 'question_instance % does not belong to project %',
            NEW.question_instance_id, NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER answer_evaluations_scope_guard
    BEFORE INSERT OR UPDATE ON answer_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION enforce_answer_evaluation_scope();
