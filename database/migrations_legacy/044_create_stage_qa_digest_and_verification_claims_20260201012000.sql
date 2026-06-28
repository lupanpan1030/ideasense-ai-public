-- 044) project_stage_qa_digests + project_stage_verification_claims
CREATE TABLE project_stage_qa_digests (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    assessment_id      UUID NOT NULL REFERENCES project_stage_assessments(id) ON DELETE CASCADE,
    stage              TEXT NOT NULL,
    question_id        TEXT NOT NULL,
    answer_summary     TEXT NULL,
    key_points         TEXT[] NULL,
    source_message_id  BIGINT NULL REFERENCES conversation_messages(id),
    model              TEXT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_stage_qa_digests_project_stage_created_idx
    ON project_stage_qa_digests (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_stage_qa_digests_assessment_idx
    ON project_stage_qa_digests (assessment_id)
    WHERE deleted_at IS NULL;

CREATE TRIGGER project_stage_qa_digests_set_updated_at
    BEFORE UPDATE ON project_stage_qa_digests
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE project_stage_qa_digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_qa_digests FORCE ROW LEVEL SECURITY;

CREATE POLICY project_stage_qa_digests_select ON project_stage_qa_digests
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_stage_qa_digests_system_insert ON project_stage_qa_digests
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_qa_digests_system_update ON project_stage_qa_digests
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE TABLE project_stage_verification_claims (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    assessment_id      UUID NOT NULL REFERENCES project_stage_assessments(id) ON DELETE CASCADE,
    stage              TEXT NOT NULL,
    claim              TEXT NOT NULL,
    verdict            TEXT NOT NULL,
    confidence         TEXT NULL,
    rationale          TEXT NULL,
    sources            JSONB NULL,
    evidence_mode      TEXT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    CHECK (verdict IN ('supported','contradicted','uncertain')),
    CHECK (confidence IS NULL OR confidence IN ('High','Medium','Low')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_stage_verification_claims_project_stage_created_idx
    ON project_stage_verification_claims (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_stage_verification_claims_assessment_idx
    ON project_stage_verification_claims (assessment_id)
    WHERE deleted_at IS NULL;

ALTER TABLE project_stage_verification_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_verification_claims FORCE ROW LEVEL SECURITY;

CREATE POLICY project_stage_verification_claims_select ON project_stage_verification_claims
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_stage_verification_claims_system_insert ON project_stage_verification_claims
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );
