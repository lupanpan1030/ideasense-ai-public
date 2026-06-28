-- 015) project_state_events
CREATE TABLE project_state_events (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id              UUID NOT NULL,
    project_id          UUID NOT NULL,
    question_instance_id UUID NULL REFERENCES project_question_instances(id),
    event_type          TEXT NOT NULL,
    patch_json          JSONB NULL,
    actor_type          TEXT NOT NULL,
    actor_user_id       UUID NULL REFERENCES users(id),
    model_name          TEXT NULL,
    prompt_template_id  UUID NULL REFERENCES prompt_templates(id),
    prev_state_version  INT NULL,
    next_state_version  INT NULL,
    request_id          UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (actor_type IN ('user','system','ai')),
    CHECK (actor_type <> 'user' OR actor_user_id IS NOT NULL),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_state_events_project_created_idx
    ON project_state_events (project_id, created_at DESC);

CREATE OR REPLACE FUNCTION enforce_project_state_event_integrity()
RETURNS trigger AS $$
DECLARE
    instance_project_id UUID;
BEGIN
    IF NEW.question_instance_id IS NOT NULL THEN
        SELECT project_id
          INTO instance_project_id
          FROM project_question_instances
         WHERE id = NEW.question_instance_id
           AND deleted_at IS NULL;

        IF instance_project_id IS NULL THEN
            RAISE EXCEPTION 'question_instance_id % not found', NEW.question_instance_id
                USING ERRCODE = '23514';
        END IF;

        IF instance_project_id <> NEW.project_id THEN
            RAISE EXCEPTION 'question_instance_id % does not belong to project %',
                NEW.question_instance_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.event_type = 'apply_patch' THEN
        IF NEW.prev_state_version IS NULL OR NEW.next_state_version IS NULL THEN
            RAISE EXCEPTION 'apply_patch requires prev_state_version and next_state_version'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.next_state_version <> NEW.prev_state_version + 1 THEN
            RAISE EXCEPTION 'apply_patch requires next_state_version = prev_state_version + 1'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_state_events_integrity_guard
    BEFORE INSERT OR UPDATE ON project_state_events
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_state_event_integrity();
