-- 009) projects
CREATE TABLE projects (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    cohort_id                UUID NULL,
    owner_user_id            UUID NOT NULL REFERENCES users(id),
    title                    TEXT NOT NULL,
    description              TEXT NULL,
    question_bank_version_id UUID NOT NULL REFERENCES question_bank_versions(id),
    current_stage            TEXT NOT NULL,
    current_variant          TEXT NOT NULL DEFAULT 'default',
    stage_status             TEXT NOT NULL DEFAULT 'in_progress',
    settings                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived              BOOLEAN NOT NULL DEFAULT false,
    archived_at              TIMESTAMPTZ NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at               TIMESTAMPTZ,
    CONSTRAINT projects_org_id_id_unique UNIQUE (org_id, id),
    CHECK (current_stage IN ('problem','market','tech','report')),
    CHECK (current_variant IN ('default','router','pro','lite')),
    CHECK (stage_status IN ('in_progress','awaiting_confirm','passed')),
    CHECK (
        (is_archived AND archived_at IS NOT NULL)
        OR (NOT is_archived AND archived_at IS NULL)
    ),
    FOREIGN KEY (org_id, cohort_id)
        REFERENCES cohorts (org_id, id),
    FOREIGN KEY (current_stage, current_variant)
        REFERENCES question_bank_stage_variants (stage, variant)
);

CREATE INDEX projects_org_id_idx
    ON projects (org_id)
    WHERE deleted_at IS NULL;

CREATE INDEX projects_owner_user_id_idx
    ON projects (owner_user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX projects_cohort_id_idx
    ON projects (cohort_id)
    WHERE deleted_at IS NULL;

CREATE INDEX projects_question_bank_version_idx
    ON projects (question_bank_version_id)
    WHERE deleted_at IS NULL;

CREATE INDEX projects_org_stage_idx
    ON projects (org_id, current_stage)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_owner_membership()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.owner_user_id
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'owner_user_id % is not an active member of org %',
            NEW.owner_user_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.cohort_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM cohort_memberships cm
            WHERE cm.org_id = NEW.org_id
              AND cm.cohort_id = NEW.cohort_id
              AND cm.user_id = NEW.owner_user_id
              AND cm.role_in_cohort = 'student'
              AND cm.status = 'active'
              AND cm.deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'owner_user_id % is not an active student in cohort %',
                NEW.owner_user_id, NEW.cohort_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER projects_owner_membership_guard
    BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_owner_membership();

CREATE OR REPLACE FUNCTION enforce_project_question_bank_scope()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM question_bank_versions qbv
        WHERE qbv.id = NEW.question_bank_version_id
          AND qbv.deleted_at IS NULL
          AND (qbv.org_id IS NULL OR qbv.org_id = NEW.org_id)
    ) THEN
        RAISE EXCEPTION 'question_bank_version_id % is not scoped to org %',
            NEW.question_bank_version_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER projects_question_bank_scope_guard
    BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_question_bank_scope();

CREATE OR REPLACE FUNCTION set_project_archive_timestamps()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.is_archived THEN
            NEW.archived_at := COALESCE(NEW.archived_at, now());
        ELSE
            NEW.archived_at := NULL;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.is_archived AND NOT OLD.is_archived THEN
        NEW.archived_at := COALESCE(NEW.archived_at, now());
    ELSIF NOT NEW.is_archived AND OLD.is_archived THEN
        NEW.archived_at := NULL;
    ELSIF NEW.is_archived AND NEW.archived_at IS NULL THEN
        NEW.archived_at := now();
    ELSIF NOT NEW.is_archived AND NEW.archived_at IS NOT NULL THEN
        NEW.archived_at := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER projects_archive_guard
    BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_project_archive_timestamps();
