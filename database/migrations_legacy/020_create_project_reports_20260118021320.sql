-- 020) project_reports
CREATE TABLE project_reports (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                       UUID NOT NULL,
    project_id                   UUID NOT NULL,
    report_version               INT NOT NULL,
    status                       TEXT NOT NULL DEFAULT 'draft',
    content_markdown             TEXT NULL,
    content_json                 JSONB NULL,
    generated_from_state_version INT NOT NULL,
    generator_model              TEXT NULL,
    generator_prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    confirmed                    BOOLEAN NOT NULL DEFAULT false,
    confirmed_at                 TIMESTAMPTZ NULL,
    export_storage_key           TEXT NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ,
    CHECK (report_version >= 1),
    CHECK (status IN ('draft','final','archived')),
    CHECK (
        (confirmed AND confirmed_at IS NOT NULL)
        OR (NOT confirmed AND confirmed_at IS NULL)
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX project_reports_unique
    ON project_reports (project_id, report_version)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION set_project_report_confirmed_at()
RETURNS trigger AS $$
BEGIN
    IF NEW.confirmed THEN
        NEW.confirmed_at := COALESCE(NEW.confirmed_at, now());
    ELSE
        NEW.confirmed_at := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_reports_confirmed_guard
    BEFORE INSERT OR UPDATE ON project_reports
    FOR EACH ROW
    EXECUTE FUNCTION set_project_report_confirmed_at();
