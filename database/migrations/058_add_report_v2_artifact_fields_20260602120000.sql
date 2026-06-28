-- 058) Report v2 structured artifact fields

ALTER TABLE project_reports
    ADD COLUMN IF NOT EXISTS artifact_schema_version TEXT NOT NULL DEFAULT 'report_v1',
    ADD COLUMN IF NOT EXISTS decision_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS score_rationales_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS risk_register_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS experiment_plan_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS evidence_index_json JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_artifact_schema_version_not_blank'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_artifact_schema_version_not_blank
            CHECK (btrim(artifact_schema_version) <> '');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_decision_snapshot_json_object'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_decision_snapshot_json_object
            CHECK (jsonb_typeof(decision_snapshot_json) = 'object');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_score_rationales_json_object'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_score_rationales_json_object
            CHECK (jsonb_typeof(score_rationales_json) = 'object');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_risk_register_json_array'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_risk_register_json_array
            CHECK (jsonb_typeof(risk_register_json) = 'array');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_experiment_plan_json_array'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_experiment_plan_json_array
            CHECK (jsonb_typeof(experiment_plan_json) = 'array');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_evidence_index_json_object'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_evidence_index_json_object
            CHECK (jsonb_typeof(evidence_index_json) = 'object');
    END IF;
END;
$$;
