-- 054) Evidence-layered diagnosis contract

ALTER TABLE project_stage_assessments
    ADD COLUMN IF NOT EXISTS context_card_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS validation_plan_json JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE project_reports
    ADD COLUMN IF NOT EXISTS diagnosis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS validation_plan_json JSONB NOT NULL DEFAULT '[]'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_stage_assessments_context_card_json_object'
    ) THEN
        ALTER TABLE project_stage_assessments
            ADD CONSTRAINT project_stage_assessments_context_card_json_object
            CHECK (jsonb_typeof(context_card_json) = 'object');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_stage_assessments_validation_plan_json_array'
    ) THEN
        ALTER TABLE project_stage_assessments
            ADD CONSTRAINT project_stage_assessments_validation_plan_json_array
            CHECK (jsonb_typeof(validation_plan_json) = 'array');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_diagnosis_json_object'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_diagnosis_json_object
            CHECK (jsonb_typeof(diagnosis_json) = 'object');
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'project_reports_validation_plan_json_array'
    ) THEN
        ALTER TABLE project_reports
            ADD CONSTRAINT project_reports_validation_plan_json_array
            CHECK (jsonb_typeof(validation_plan_json) = 'array');
    END IF;
END;
$$;
