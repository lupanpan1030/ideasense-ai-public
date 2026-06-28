-- 004) cohorts
CREATE TABLE cohorts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NULL,
    start_at    TIMESTAMPTZ NULL,
    end_at      TIMESTAMPTZ NULL,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CONSTRAINT cohorts_org_id_id_unique UNIQUE (org_id, id)
);

CREATE UNIQUE INDEX cohorts_org_name_unique
    ON cohorts (org_id, name)
    WHERE deleted_at IS NULL;

-- 004) cohort_memberships
CREATE TABLE cohort_memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    cohort_id       UUID NOT NULL,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_cohort  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CHECK (role_in_cohort IN ('student','mentor','assistant')),
    CHECK (status IN ('active','removed')),
    FOREIGN KEY (org_id, cohort_id)
        REFERENCES cohorts (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX cohort_memberships_cohort_user_unique
    ON cohort_memberships (cohort_id, user_id)
    WHERE deleted_at IS NULL;
