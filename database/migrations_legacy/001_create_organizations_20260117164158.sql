-- 001) Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- 001) organizations
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    settings    JSONB NOT NULL DEFAULT '{
        "org_type": "institution",
        "allow_cohorts": true,
        "allow_mentor_assignments": true,
        "default_mentor_visibility": "summaries_only"
    }'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CHECK (slug = lower(slug)),
    CHECK (slug = btrim(slug)),
    CHECK (slug !~ '\s')
);

CREATE UNIQUE INDEX organizations_slug_unique
    ON organizations (slug)
    WHERE deleted_at IS NULL;
