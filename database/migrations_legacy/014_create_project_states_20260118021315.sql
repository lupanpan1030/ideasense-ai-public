-- 014) project_states
CREATE TABLE project_states (
    project_id          UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL,
    bank_version_id     UUID NOT NULL REFERENCES question_bank_versions(id),
    state_schema_version TEXT NOT NULL DEFAULT 'v1',
    state_json          JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_version       INT NOT NULL DEFAULT 0,
    state_meta          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    CHECK (state_version >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION enforce_project_state_bank_version()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
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

    IF NEW.bank_version_id <> project_bank_id THEN
        RAISE EXCEPTION 'bank_version_id % does not match project bank %',
            NEW.bank_version_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_states_bank_guard
    BEFORE INSERT OR UPDATE ON project_states
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_state_bank_version();
