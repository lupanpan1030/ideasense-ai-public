-- 025) message_evaluations
CREATE TABLE message_evaluations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL,
    project_id        UUID NOT NULL,
    message_id        BIGINT NOT NULL REFERENCES conversation_messages(id),
    rubric_id         UUID NOT NULL REFERENCES evaluation_rubrics(id),
    scores_json       JSONB NOT NULL,
    overall_score     NUMERIC NULL,
    feedback_markdown TEXT NULL,
    evaluator_type    TEXT NOT NULL,
    evaluator_model   TEXT NULL,
    request_id        UUID NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ NULL,
    CHECK (evaluator_type IN ('ai','human','system')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX message_evaluations_request_unique
    ON message_evaluations (request_id)
    WHERE request_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX message_evaluations_project_created_idx
    ON message_evaluations (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_message_evaluation_scope()
RETURNS trigger AS $$
DECLARE
    message_project_id UUID;
    message_org_id UUID;
BEGIN
    SELECT project_id, org_id
      INTO message_project_id, message_org_id
      FROM conversation_messages
     WHERE id = NEW.message_id
       AND deleted_at IS NULL;

    IF message_project_id IS NULL THEN
        RAISE EXCEPTION 'message % not found or deleted',
            NEW.message_id
            USING ERRCODE = '23514';
    END IF;

    IF message_project_id <> NEW.project_id
        OR message_org_id <> NEW.org_id THEN
        RAISE EXCEPTION 'message % does not belong to project %',
            NEW.message_id, NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER message_evaluations_scope_guard
    BEFORE INSERT OR UPDATE ON message_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION enforce_message_evaluation_scope();
