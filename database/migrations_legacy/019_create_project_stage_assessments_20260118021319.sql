-- 019) project_stage_assessments
CREATE TABLE project_stage_assessments (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                       UUID NOT NULL,
    project_id                   UUID NOT NULL,
    stage                        TEXT NOT NULL,
    draft_summary_markdown       TEXT NULL,
    final_summary_markdown       TEXT NULL,
    confirmed                    BOOLEAN NOT NULL DEFAULT false,
    confirmed_at                 TIMESTAMPTZ NULL,
    confirmed_by_user_id         UUID NULL REFERENCES users(id),
    generated_from_state_version INT NULL,
    generator_model              TEXT NULL,
    generator_prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    scores_json                  JSONB NULL,
    total_score                  NUMERIC NULL,
    risk_matrix                  JSONB NULL,
    diagram_mermaid              TEXT NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    CHECK (
        (confirmed AND confirmed_at IS NOT NULL AND confirmed_by_user_id IS NOT NULL)
        OR (NOT confirmed AND confirmed_at IS NULL AND confirmed_by_user_id IS NULL)
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX project_stage_assessments_unique
    ON project_stage_assessments (project_id, stage)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_stage_assessment_confirmer()
RETURNS trigger AS $$
DECLARE
    project_owner_id UUID;
    member_role TEXT;
BEGIN
    IF NEW.confirmed THEN
        SELECT owner_user_id
          INTO project_owner_id
          FROM projects
         WHERE id = NEW.project_id
           AND deleted_at IS NULL;

        IF project_owner_id IS NULL THEN
            RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        SELECT org_role
          INTO member_role
          FROM organization_memberships
         WHERE org_id = NEW.org_id
           AND user_id = NEW.confirmed_by_user_id
           AND status = 'active'
           AND deleted_at IS NULL;

        IF member_role IS NULL THEN
            RAISE EXCEPTION 'confirmed_by_user_id % is not an active member of org %',
                NEW.confirmed_by_user_id, NEW.org_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.confirmed_by_user_id <> project_owner_id
           AND member_role NOT IN ('owner','admin') THEN
            RAISE EXCEPTION 'confirmed_by_user_id % cannot confirm stage assessments',
                NEW.confirmed_by_user_id
                USING ERRCODE = '23514';
        END IF;

        NEW.confirmed_at := COALESCE(NEW.confirmed_at, now());
    ELSE
        NEW.confirmed_at := NULL;
        NEW.confirmed_by_user_id := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enforce_project_stage_assessment_state_version()
RETURNS trigger AS $$
DECLARE
    current_state_version INT;
BEGIN
    IF NEW.generated_from_state_version IS NOT NULL THEN
        SELECT state_version
          INTO current_state_version
          FROM project_states
         WHERE project_id = NEW.project_id
           AND deleted_at IS NULL;

        IF current_state_version IS NULL THEN
            RAISE EXCEPTION 'project_state not found for project %', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.generated_from_state_version > current_state_version THEN
            RAISE EXCEPTION 'generated_from_state_version % exceeds current state_version %',
                NEW.generated_from_state_version, current_state_version
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_stage_assessments_confirmer_guard
    BEFORE INSERT OR UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_stage_assessment_confirmer();

CREATE TRIGGER project_stage_assessments_state_version_guard
    BEFORE INSERT OR UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_stage_assessment_state_version();
