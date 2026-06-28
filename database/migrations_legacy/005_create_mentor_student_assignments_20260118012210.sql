-- 005) mentor_student_assignments
CREATE TABLE mentor_student_assignments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    cohort_id         UUID NULL,
    mentor_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'pending',
    can_view_messages BOOLEAN NOT NULL DEFAULT false,
    can_view_facts    BOOLEAN NOT NULL DEFAULT false,
    can_comment       BOOLEAN NOT NULL DEFAULT true,
    created_by        UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    CHECK (status IN ('pending','active','revoked')),
    CHECK (mentor_user_id <> student_user_id),
    CHECK (can_view_messages IS FALSE OR can_view_facts IS TRUE),
    FOREIGN KEY (org_id, cohort_id)
        REFERENCES cohorts (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX mentor_student_assignments_unique
    ON mentor_student_assignments (
        org_id,
        mentor_user_id,
        student_user_id,
        COALESCE(cohort_id, '00000000-0000-0000-0000-000000000000'::uuid)
    )
    WHERE deleted_at IS NULL;

CREATE INDEX mentor_student_assignments_mentor_idx
    ON mentor_student_assignments (org_id, mentor_user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX mentor_student_assignments_student_idx
    ON mentor_student_assignments (org_id, student_user_id)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_assignment_membership()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.mentor_user_id
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'mentor_user_id % is not a member of org %', NEW.mentor_user_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.student_user_id
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'student_user_id % is not a member of org %', NEW.student_user_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.created_by IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.created_by
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'created_by % is not a member of org %', NEW.created_by, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.cohort_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM cohort_memberships cm
            WHERE cm.org_id = NEW.org_id
              AND cm.cohort_id = NEW.cohort_id
              AND cm.user_id = NEW.mentor_user_id
              AND cm.status = 'active'
              AND cm.deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'mentor_user_id % is not in cohort %', NEW.mentor_user_id, NEW.cohort_id
                USING ERRCODE = '23514';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM cohort_memberships cm
            WHERE cm.org_id = NEW.org_id
              AND cm.cohort_id = NEW.cohort_id
              AND cm.user_id = NEW.student_user_id
              AND cm.status = 'active'
              AND cm.deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'student_user_id % is not in cohort %', NEW.student_user_id, NEW.cohort_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mentor_student_assignments_membership_guard
    BEFORE INSERT OR UPDATE ON mentor_student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_assignment_membership();
