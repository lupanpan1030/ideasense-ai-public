-- 013) conversation_messages
CREATE TABLE conversation_messages (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    author_user_id     UUID NULL REFERENCES users(id),
    role               TEXT NOT NULL,
    is_visible         BOOLEAN NOT NULL DEFAULT true,
    stage              TEXT NOT NULL,
    variant            TEXT NULL,
    question_instance_id UUID NULL REFERENCES project_question_instances(id),
    client_message_id  UUID NULL,
    request_id         UUID NULL,
    content            TEXT NOT NULL,
    content_format     TEXT NOT NULL DEFAULT 'markdown',
    model_name         TEXT NULL,
    prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    token_prompt       INT NULL,
    token_output       INT NULL,
    latency_ms         INT NULL,
    meta               JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    redacted_at        TIMESTAMPTZ NULL,
    deleted_at         TIMESTAMPTZ NULL,
    CHECK (role IN ('user','assistant','system','tool')),
    CHECK (stage IN ('problem','market','tech','report')),
    CHECK (content_format IN ('markdown','text','json')),
    CHECK (token_prompt IS NULL OR token_prompt >= 0),
    CHECK (token_output IS NULL OR token_output >= 0),
    CHECK (latency_ms IS NULL OR latency_ms >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX conversation_messages_client_unique
    ON conversation_messages (project_id, client_message_id)
    WHERE client_message_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX conversation_messages_project_created_idx
    ON conversation_messages (project_id, created_at)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_conversation_message_integrity()
RETURNS trigger AS $$
DECLARE
    project_owner_id UUID;
    runtime_stage TEXT;
    runtime_variant TEXT;
    instance_project_id UUID;
    instance_org_id UUID;
BEGIN
    IF NEW.question_instance_id IS NOT NULL THEN
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
    END IF;

    IF NEW.role = 'user' THEN
        IF NEW.author_user_id IS NULL THEN
            RAISE EXCEPTION 'author_user_id is required for role=user'
                USING ERRCODE = '23514';
        END IF;

        SELECT owner_user_id
          INTO project_owner_id
          FROM projects
         WHERE id = NEW.project_id
           AND deleted_at IS NULL;

        IF project_owner_id IS NULL THEN
            RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.author_user_id <> project_owner_id THEN
            RAISE EXCEPTION 'author_user_id % does not match project owner %',
                NEW.author_user_id, project_owner_id
                USING ERRCODE = '23514';
        END IF;

        SELECT stage, variant
          INTO runtime_stage, runtime_variant
          FROM project_runtime
         WHERE project_id = NEW.project_id
           AND deleted_at IS NULL;

        IF runtime_stage IS NULL THEN
            RAISE EXCEPTION 'project_runtime not found for project %', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        NEW.stage := runtime_stage;
        NEW.variant := runtime_variant;
    ELSE
        IF NEW.variant IS NOT NULL THEN
            IF NOT EXISTS (
                SELECT 1
                FROM question_bank_stage_variants
                WHERE stage = NEW.stage
                  AND variant = NEW.variant
            ) THEN
                RAISE EXCEPTION 'invalid stage/variant for message: %/%',
                    NEW.stage, NEW.variant
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversation_messages_integrity_guard
    BEFORE INSERT OR UPDATE ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION enforce_conversation_message_integrity();
