-- 051) Sample projects (public read-only previews)
CREATE TABLE sample_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_project_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    stage TEXT NOT NULL,
    project_updated_at TIMESTAMPTZ,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    report JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX sample_projects_stage_idx ON sample_projects (stage);
CREATE UNIQUE INDEX sample_projects_source_project_id_unique
    ON sample_projects (source_project_id)
    WHERE source_project_id IS NOT NULL;

CREATE TRIGGER sample_projects_set_updated_at
    BEFORE UPDATE ON sample_projects
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
