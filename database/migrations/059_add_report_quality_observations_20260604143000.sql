-- 059) Persist report quality observations for platform operations

CREATE TABLE IF NOT EXISTS report_quality_observations (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id                   UUID NOT NULL,
    project_title                TEXT NULL,
    report_id                    UUID NOT NULL REFERENCES project_reports(id) ON DELETE CASCADE,
    report_version               INT NOT NULL,
    generated_from_state_version INT NOT NULL,
    observation_schema_version   TEXT NOT NULL DEFAULT 'assessment_quality_observation_v1',
    status                       TEXT NOT NULL,
    failed_invariants_json       JSONB NOT NULL DEFAULT '[]'::jsonb,
    warning_invariants_json      JSONB NOT NULL DEFAULT '[]'::jsonb,
    score_snapshot_json          JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_counts_json         JSONB NOT NULL DEFAULT '{}'::jsonb,
    canonical_boundaries_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
    observation_json             JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ,
    CHECK (report_version >= 1),
    CHECK (generated_from_state_version >= 1),
    CHECK (status IN ('pass','warn','fail')),
    CHECK (btrim(observation_schema_version) <> ''),
    CHECK (jsonb_typeof(failed_invariants_json) = 'array'),
    CHECK (jsonb_typeof(warning_invariants_json) = 'array'),
    CHECK (jsonb_typeof(score_snapshot_json) = 'object'),
    CHECK (jsonb_typeof(evidence_counts_json) = 'object'),
    CHECK (jsonb_typeof(canonical_boundaries_json) = 'object'),
    CHECK (jsonb_typeof(observation_json) = 'object'),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS report_quality_observations_report_state_unique
    ON report_quality_observations (report_id, generated_from_state_version)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS report_quality_observations_org_status_observed_idx
    ON report_quality_observations (org_id, status, observed_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS report_quality_observations_project_observed_idx
    ON report_quality_observations (project_id, observed_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS report_quality_observations_report_idx
    ON report_quality_observations (report_id)
    WHERE deleted_at IS NULL;

ALTER TABLE report_quality_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_quality_observations FORCE ROW LEVEL SECURITY;

CREATE POLICY report_quality_observations_system_insert
    ON report_quality_observations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY report_quality_observations_system_update
    ON report_quality_observations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY report_quality_observations_system_select
    ON report_quality_observations
    FOR SELECT USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY report_quality_observations_platform_select
    ON report_quality_observations
    FOR SELECT USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = report_quality_observations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE TRIGGER report_quality_observations_set_updated_at
    BEFORE UPDATE ON report_quality_observations
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
