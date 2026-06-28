-- 023) evaluation_rubrics
CREATE TABLE evaluation_rubrics (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope_org_id UUID GENERATED ALWAYS AS (
        COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid)
    ) STORED NOT NULL,
    rubric_key   TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    scope        TEXT NOT NULL,
    definition_json JSONB NOT NULL,
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    CHECK (scope IN ('answer','message'))
);

CREATE UNIQUE INDEX evaluation_rubrics_unique
    ON evaluation_rubrics (scope_org_id, rubric_key, rubric_version)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX evaluation_rubrics_active_unique
    ON evaluation_rubrics (scope_org_id, rubric_key, scope)
    WHERE is_active AND deleted_at IS NULL;
