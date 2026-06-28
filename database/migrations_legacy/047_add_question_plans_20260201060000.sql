-- 047) question_plans for AI question planning
CREATE TABLE question_plans (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID NOT NULL,
    project_id                  UUID NOT NULL,
    stage                       TEXT NOT NULL,
    variant                     TEXT NOT NULL,
    question_instance_id         UUID NULL REFERENCES project_question_instances(id) ON DELETE SET NULL,
    question_bank_question_ids  UUID[] NOT NULL,
    question_ids                TEXT[] NULL,
    schema_paths                TEXT[] NULL,
    prompt                      TEXT NOT NULL,
    model                       TEXT NULL,
    latency_ms                  INTEGER NULL,
    meta                        JSONB NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX question_plans_project_stage_created_idx
    ON question_plans (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX question_plans_project_created_idx
    ON question_plans (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TRIGGER question_plans_set_updated_at
    BEFORE UPDATE ON question_plans
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE question_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_plans FORCE ROW LEVEL SECURITY;

CREATE POLICY question_plans_select ON question_plans
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY question_plans_system_insert ON question_plans
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY question_plans_system_update ON question_plans
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );
