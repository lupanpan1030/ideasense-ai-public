-- 000) Baseline schema snapshot
-- Generated on 2026-02-06
-- This file replaces the historical migration chain.
-- ------------------------------------------------------------------
-- Source: 001_create_organizations_20260117164158.sql
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

-- ------------------------------------------------------------------
-- Source: 002_create_users_and_identities_20260117164159.sql
-- 002) users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL,
    display_name    TEXT,
    primary_org_id  UUID NULL REFERENCES organizations(id) ON DELETE SET NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CHECK (email = btrim(email)),
    CHECK (email !~ '\s')
);

CREATE UNIQUE INDEX users_email_unique
    ON users (email)
    WHERE deleted_at IS NULL;

-- 002) user_identities
CREATE TABLE user_identities (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    provider_subject  TEXT NULL,
    email             CITEXT NULL,
    password_hash     TEXT NULL,
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    CHECK (provider IN ('local','clerk','nextauth','sso')),
    CHECK (status IN ('active','disabled')),
    CHECK (provider = 'local' OR provider_subject IS NOT NULL),
    CHECK (provider <> 'local' OR password_hash IS NOT NULL),
    CHECK (email IS NULL OR (email = btrim(email) AND email !~ '\s'))
);

CREATE UNIQUE INDEX user_identities_provider_subject_unique
    ON user_identities (provider, provider_subject)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 003_create_org_memberships_and_invitations_20260117164200.sql
-- 003) organization_memberships
CREATE TABLE organization_memberships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_role    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    created_by  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CHECK (org_role IN ('owner','admin','mentor','student')),
    CHECK (status IN ('invited','active','removed'))
);

CREATE UNIQUE INDEX organization_memberships_org_user_unique
    ON organization_memberships (org_id, user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX organization_memberships_user_id_idx
    ON organization_memberships (user_id)
    WHERE deleted_at IS NULL;

-- 003) organization_invitations
CREATE TABLE organization_invitations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invitee_email    CITEXT NOT NULL,
    invited_role     TEXT NOT NULL,
    invited_by       UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    token            TEXT NOT NULL,
    expires_at       TIMESTAMPTZ NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    accepted_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,
    CHECK (invited_role IN ('mentor','student','admin')),
    CHECK (status IN ('pending','accepted','expired','revoked')),
    CHECK (invitee_email = btrim(invitee_email)),
    CHECK (invitee_email !~ '\s')
);

CREATE UNIQUE INDEX organization_invitations_org_token_unique
    ON organization_invitations (org_id, token)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 004_create_cohorts_and_memberships_20260117164210.sql
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

-- ------------------------------------------------------------------
-- Source: 005_create_mentor_student_assignments_20260118012210.sql
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

-- ------------------------------------------------------------------
-- Source: 006_create_question_bank_versions_20260118013228.sql
-- 006) question_bank_versions
CREATE TABLE question_bank_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope_org_id    UUID GENERATED ALWAYS AS (
        COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid)
    ) STORED NOT NULL,
    bank_key        TEXT NOT NULL,
    version         TEXT NOT NULL,
    source          TEXT NULL,
    raw_yaml         TEXT NULL,
    raw_json        JSONB NULL,
    content_hash    TEXT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    activated_at    TIMESTAMPTZ NULL,
    deactivated_at  TIMESTAMPTZ NULL,
    CHECK (bank_key = lower(btrim(bank_key))),
    CHECK (bank_key <> ''),
    CHECK (bank_key !~ '\s'),
    CHECK (version = btrim(version)),
    CHECK (version <> ''),
    CHECK (NOT is_active OR (activated_at IS NOT NULL AND deactivated_at IS NULL))
);

CREATE UNIQUE INDEX question_bank_versions_scope_key_version_unique
    ON question_bank_versions (scope_org_id, bank_key, version)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_versions_scope_key_active_unique
    ON question_bank_versions (scope_org_id, bank_key)
    WHERE is_active AND deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_versions_scope_content_hash_unique
    ON question_bank_versions (scope_org_id, content_hash)
    WHERE content_hash IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX question_bank_versions_scope_key_idx
    ON question_bank_versions (scope_org_id, bank_key);

CREATE OR REPLACE FUNCTION set_question_bank_version_activation()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.is_active THEN
            NEW.activated_at := COALESCE(NEW.activated_at, now());
            NEW.deactivated_at := NULL;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.is_active AND NOT OLD.is_active THEN
        NEW.activated_at := COALESCE(NEW.activated_at, now());
        NEW.deactivated_at := NULL;
    ELSIF NOT NEW.is_active AND OLD.is_active THEN
        NEW.deactivated_at := COALESCE(NEW.deactivated_at, now());
    ELSIF NEW.is_active THEN
        NEW.activated_at := COALESCE(NEW.activated_at, now());
        NEW.deactivated_at := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER question_bank_versions_activation_guard
    BEFORE INSERT OR UPDATE ON question_bank_versions
    FOR EACH ROW
    EXECUTE FUNCTION set_question_bank_version_activation();

-- ------------------------------------------------------------------
-- Source: 007_create_question_bank_stage_variants_20260118013228.sql
-- 007) question_bank_stage_variants
CREATE TABLE question_bank_stage_variants (
    stage   TEXT NOT NULL,
    variant TEXT NOT NULL,
    PRIMARY KEY (stage, variant),
    CHECK (stage IN ('problem','market','tech','report')),
    CHECK (variant IN ('default','router','pro','lite'))
);

INSERT INTO question_bank_stage_variants (stage, variant) VALUES
    ('problem','default'),
    ('market','default'),
    ('report','default'),
    ('tech','default'),
    ('tech','router'),
    ('tech','pro'),
    ('tech','lite');

-- ------------------------------------------------------------------
-- Source: 008_create_question_bank_questions_20260118013228.sql
-- 008) question_bank_questions
CREATE TABLE question_bank_questions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_version_id         UUID NOT NULL REFERENCES question_bank_versions(id) ON DELETE CASCADE,
    stage                  TEXT NOT NULL,
    variant                TEXT NOT NULL,
    question_id            TEXT NOT NULL,
    order_index            INT NOT NULL,
    title                  TEXT NOT NULL,
    type_raw               TEXT NOT NULL,
    prompt                 TEXT NOT NULL,
    standard_question      TEXT NULL,
    consultant_tactic      TEXT NULL,
    instruction            TEXT NULL,
    validation_rule        TEXT NULL,
    schema_paths           TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    capture_intent         TEXT NULL,
    capture_spec           JSONB NOT NULL DEFAULT '{}'::jsonb,
    answer_examples        JSONB[] NOT NULL DEFAULT ARRAY[]::jsonb[],
    expected_patch_example JSONB NULL,
    display_if             JSONB NULL,
    meta                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active              BOOLEAN NOT NULL DEFAULT true,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ,
    FOREIGN KEY (stage, variant)
        REFERENCES question_bank_stage_variants (stage, variant)
);

CREATE UNIQUE INDEX question_bank_questions_unique_id
    ON question_bank_questions (bank_version_id, stage, variant, question_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_questions_unique_order
    ON question_bank_questions (bank_version_id, stage, variant, order_index)
    WHERE deleted_at IS NULL;

CREATE INDEX question_bank_questions_next_idx
    ON question_bank_questions (bank_version_id, stage, variant, order_index)
    WHERE deleted_at IS NULL;

CREATE INDEX question_bank_questions_schema_paths_gin
    ON question_bank_questions USING gin (schema_paths)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 009_create_projects_20260118014505.sql
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

-- ------------------------------------------------------------------
-- Source: 010_create_project_runtime_20260118014505.sql
-- 010) project_runtime
CREATE TABLE project_runtime (
    project_id                       UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    org_id                           UUID NOT NULL,
    stage                            TEXT NOT NULL,
    variant                          TEXT NOT NULL,
    current_question_bank_question_id UUID NOT NULL REFERENCES question_bank_questions(id),
    next_question_bank_question_id   UUID NULL REFERENCES question_bank_questions(id),
    turn_state                       TEXT NOT NULL DEFAULT 'draft',
    missing_paths                    TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    runtime_version                  INT NOT NULL DEFAULT 0,
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                       TIMESTAMPTZ,
    CHECK (turn_state IN ('draft','updated','needs_info')),
    CHECK (runtime_version >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id),
    FOREIGN KEY (stage, variant)
        REFERENCES question_bank_stage_variants (stage, variant)
);

CREATE INDEX project_runtime_org_stage_idx
    ON project_runtime (org_id, stage, variant)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    SELECT question_bank_version_id, current_stage, current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects
     WHERE id = NEW.project_id
       AND deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    SELECT bank_version_id, stage, variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions
     WHERE id = NEW.current_question_bank_question_id
       AND deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT bank_version_id, stage, variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions
         WHERE id = NEW.next_question_bank_question_id
           AND deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_runtime_question_guard
    BEFORE INSERT OR UPDATE ON project_runtime
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_runtime_questions();

-- ------------------------------------------------------------------
-- Source: 011_create_prompt_templates_20260118021312.sql
-- 011) prompt_templates
CREATE TABLE prompt_templates (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope_org_id UUID GENERATED ALWAYS AS (
        COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid)
    ) STORED NOT NULL,
    template_key TEXT NOT NULL,
    purpose      TEXT NOT NULL,
    stage        TEXT NULL,
    variant      TEXT NULL,
    version      TEXT NOT NULL,
    content      TEXT NOT NULL,
    params       JSONB NULL,
    is_active    BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    CHECK (purpose IN ('chat','extract','summary','score','evaluate','report')),
    CHECK (
        template_key = lower(btrim(template_key))
        AND template_key <> ''
        AND template_key ~ '^[a-z0-9_.-]+$'
    ),
    CHECK (variant IS NULL OR stage IS NOT NULL),
    CHECK (stage IS NULL OR stage IN ('problem','market','tech','report'))
);

CREATE UNIQUE INDEX prompt_templates_scope_unique
    ON prompt_templates (scope_org_id, template_key, version)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX prompt_templates_scope_active_unique
    ON prompt_templates (scope_org_id, template_key)
    WHERE is_active AND deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_prompt_template_stage_variant()
RETURNS trigger AS $$
BEGIN
    IF NEW.variant IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM question_bank_stage_variants
            WHERE stage = NEW.stage
              AND variant = NEW.variant
        ) THEN
            RAISE EXCEPTION 'invalid stage/variant for prompt template: %/%',
                NEW.stage, NEW.variant
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prompt_templates_stage_variant_guard
    BEFORE INSERT OR UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION enforce_prompt_template_stage_variant();

-- ------------------------------------------------------------------
-- Source: 012_create_project_question_instances_20260118021313.sql
-- 012) project_question_instances
CREATE TABLE project_question_instances (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                    UUID NOT NULL,
    project_id                UUID NOT NULL,
    question_bank_question_id UUID NOT NULL REFERENCES question_bank_questions(id),
    status                    TEXT NOT NULL DEFAULT 'pending',
    asked_count               INT NOT NULL DEFAULT 0,
    last_asked_at             TIMESTAMPTZ NULL,
    answered_at               TIMESTAMPTZ NULL,
    final_answer_text         TEXT NULL,
    extracted_patch_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_status         TEXT NOT NULL DEFAULT 'not_validated',
    validation_errors         JSONB NOT NULL DEFAULT '[]'::jsonb,
    extract_model             TEXT NULL,
    extract_prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    extract_confidence        NUMERIC(4,3) NULL,
    meta                      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    CHECK (status IN ('pending','asked','answered','needs_info','skipped','invalid','autofilled')),
    CHECK (asked_count >= 0),
    CHECK (validation_status IN ('not_validated','valid','invalid','needs_info')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX project_question_instances_unique
    ON project_question_instances (project_id, question_bank_question_id)
    WHERE deleted_at IS NULL;

CREATE INDEX project_question_instances_status_idx
    ON project_question_instances (project_id, status, updated_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_question_instance_bank()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    question_bank_id UUID;
BEGIN
    SELECT question_bank_version_id
      INTO project_bank_id
      FROM projects
     WHERE id = NEW.project_id
       AND deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    SELECT bank_version_id
      INTO question_bank_id
      FROM question_bank_questions
     WHERE id = NEW.question_bank_question_id
       AND deleted_at IS NULL;

    IF question_bank_id IS NULL THEN
        RAISE EXCEPTION 'question_bank_question_id % not found', NEW.question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF question_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'question_bank_question_id % does not match project bank %',
            NEW.question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_question_instances_bank_guard
    BEFORE INSERT OR UPDATE ON project_question_instances
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_question_instance_bank();

-- ------------------------------------------------------------------
-- Source: 013_create_conversation_messages_20260118021314.sql
-- 013) conversation_messages
CREATE TABLE conversation_messages (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    author_user_id     UUID NULL REFERENCES users(id),
    role               TEXT NOT NULL,
    is_visible         BOOLEAN NOT NULL DEFAULT true,
    stage              TEXT NOT NULL,
    variant            TEXT NULL,
    question_instance_id UUID NULL REFERENCES project_question_instances(id),
    client_message_id  UUID NULL,
    request_id         UUID NULL,
    content            TEXT NOT NULL,
    content_format     TEXT NOT NULL DEFAULT 'markdown',
    model_name         TEXT NULL,
    prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    token_prompt       INT NULL,
    token_output       INT NULL,
    latency_ms         INT NULL,
    meta               JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    redacted_at        TIMESTAMPTZ NULL,
    deleted_at         TIMESTAMPTZ NULL,
    CHECK (role IN ('user','assistant','system','tool')),
    CHECK (stage IN ('problem','market','tech','report')),
    CHECK (content_format IN ('markdown','text','json')),
    CHECK (token_prompt IS NULL OR token_prompt >= 0),
    CHECK (token_output IS NULL OR token_output >= 0),
    CHECK (latency_ms IS NULL OR latency_ms >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX conversation_messages_client_unique
    ON conversation_messages (project_id, client_message_id)
    WHERE client_message_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX conversation_messages_project_created_idx
    ON conversation_messages (project_id, created_at)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_conversation_message_integrity()
RETURNS trigger AS $$
DECLARE
    project_owner_id UUID;
    runtime_stage TEXT;
    runtime_variant TEXT;
    instance_project_id UUID;
    instance_org_id UUID;
BEGIN
    IF NEW.question_instance_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO instance_project_id, instance_org_id
          FROM project_question_instances
         WHERE id = NEW.question_instance_id
           AND deleted_at IS NULL;

        IF instance_project_id IS NULL THEN
            RAISE EXCEPTION 'question_instance % not found or deleted',
                NEW.question_instance_id
                USING ERRCODE = '23514';
        END IF;

        IF instance_project_id <> NEW.project_id
            OR instance_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'question_instance % does not belong to project %',
                NEW.question_instance_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.role = 'user' THEN
        IF NEW.author_user_id IS NULL THEN
            RAISE EXCEPTION 'author_user_id is required for role=user'
                USING ERRCODE = '23514';
        END IF;

        SELECT owner_user_id
          INTO project_owner_id
          FROM projects
         WHERE id = NEW.project_id
           AND deleted_at IS NULL;

        IF project_owner_id IS NULL THEN
            RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.author_user_id <> project_owner_id THEN
            RAISE EXCEPTION 'author_user_id % does not match project owner %',
                NEW.author_user_id, project_owner_id
                USING ERRCODE = '23514';
        END IF;

        SELECT stage, variant
          INTO runtime_stage, runtime_variant
          FROM project_runtime
         WHERE project_id = NEW.project_id
           AND deleted_at IS NULL;

        IF runtime_stage IS NULL THEN
            RAISE EXCEPTION 'project_runtime not found for project %', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        NEW.stage := runtime_stage;
        NEW.variant := runtime_variant;
    ELSE
        IF NEW.variant IS NOT NULL THEN
            IF NOT EXISTS (
                SELECT 1
                FROM question_bank_stage_variants
                WHERE stage = NEW.stage
                  AND variant = NEW.variant
            ) THEN
                RAISE EXCEPTION 'invalid stage/variant for message: %/%',
                    NEW.stage, NEW.variant
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversation_messages_integrity_guard
    BEFORE INSERT OR UPDATE ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION enforce_conversation_message_integrity();

-- ------------------------------------------------------------------
-- Source: 014_create_project_states_20260118021315.sql
-- 014) project_states
CREATE TABLE project_states (
    project_id          UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL,
    bank_version_id     UUID NOT NULL REFERENCES question_bank_versions(id),
    state_schema_version TEXT NOT NULL DEFAULT 'v1',
    state_json          JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_version       INT NOT NULL DEFAULT 0,
    state_meta          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    CHECK (state_version >= 0),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION enforce_project_state_bank_version()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
BEGIN
    SELECT question_bank_version_id
      INTO project_bank_id
      FROM projects
     WHERE id = NEW.project_id
       AND deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.bank_version_id <> project_bank_id THEN
        RAISE EXCEPTION 'bank_version_id % does not match project bank %',
            NEW.bank_version_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_states_bank_guard
    BEFORE INSERT OR UPDATE ON project_states
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_state_bank_version();

-- ------------------------------------------------------------------
-- Source: 015_create_project_state_events_20260118021316.sql
-- 015) project_state_events
CREATE TABLE project_state_events (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id              UUID NOT NULL,
    project_id          UUID NOT NULL,
    question_instance_id UUID NULL REFERENCES project_question_instances(id),
    event_type          TEXT NOT NULL,
    patch_json          JSONB NULL,
    actor_type          TEXT NOT NULL,
    actor_user_id       UUID NULL REFERENCES users(id),
    model_name          TEXT NULL,
    prompt_template_id  UUID NULL REFERENCES prompt_templates(id),
    prev_state_version  INT NULL,
    next_state_version  INT NULL,
    request_id          UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (actor_type IN ('user','system','ai')),
    CHECK (actor_type <> 'user' OR actor_user_id IS NOT NULL),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_state_events_project_created_idx
    ON project_state_events (project_id, created_at DESC);

CREATE OR REPLACE FUNCTION enforce_project_state_event_integrity()
RETURNS trigger AS $$
DECLARE
    instance_project_id UUID;
BEGIN
    IF NEW.question_instance_id IS NOT NULL THEN
        SELECT project_id
          INTO instance_project_id
          FROM project_question_instances
         WHERE id = NEW.question_instance_id
           AND deleted_at IS NULL;

        IF instance_project_id IS NULL THEN
            RAISE EXCEPTION 'question_instance_id % not found', NEW.question_instance_id
                USING ERRCODE = '23514';
        END IF;

        IF instance_project_id <> NEW.project_id THEN
            RAISE EXCEPTION 'question_instance_id % does not belong to project %',
                NEW.question_instance_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.event_type = 'apply_patch' THEN
        IF NEW.prev_state_version IS NULL OR NEW.next_state_version IS NULL THEN
            RAISE EXCEPTION 'apply_patch requires prev_state_version and next_state_version'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.next_state_version <> NEW.prev_state_version + 1 THEN
            RAISE EXCEPTION 'apply_patch requires next_state_version = prev_state_version + 1'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_state_events_integrity_guard
    BEFORE INSERT OR UPDATE ON project_state_events
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_state_event_integrity();

-- ------------------------------------------------------------------
-- Source: 016_create_documents_20260118021317.sql
-- 016) documents
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL,
    project_id   UUID NOT NULL,
    file_name    TEXT NOT NULL,
    content_type TEXT NULL,
    storage_key  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'uploaded',
    error_message TEXT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    meta         JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (status IN ('uploaded','extracting','extracted','chunked','embedded','indexed','failed')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX documents_storage_key_unique
    ON documents (org_id, storage_key)
    WHERE deleted_at IS NULL;

CREATE INDEX documents_project_status_idx
    ON documents (project_id, status)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 017_create_analytics_events_20260118021318.sql
-- 017) analytics_events
CREATE TABLE analytics_events (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    project_id    UUID NULL REFERENCES projects(id) ON DELETE SET NULL,
    actor_user_id UUID NULL REFERENCES users(id),
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX analytics_events_org_created_idx
    ON analytics_events (org_id, created_at DESC);

CREATE INDEX analytics_events_project_created_idx
    ON analytics_events (project_id, created_at DESC);

CREATE INDEX analytics_events_org_type_created_idx
    ON analytics_events (org_id, event_type, created_at DESC);

-- ------------------------------------------------------------------
-- Source: 018_create_audit_events_20260118021318.sql
-- 018) audit_events
CREATE TABLE audit_events (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    actor_user_id UUID NULL REFERENCES users(id),
    actor_type    TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    target_type   TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (actor_type IN ('user','system'))
);

CREATE INDEX audit_events_org_created_idx
    ON audit_events (org_id, created_at DESC);

CREATE INDEX audit_events_org_type_created_idx
    ON audit_events (org_id, event_type, created_at DESC);

CREATE INDEX audit_events_org_target_idx
    ON audit_events (org_id, target_type, target_id, created_at DESC);

CREATE INDEX audit_events_org_actor_idx
    ON audit_events (org_id, actor_user_id, created_at DESC);

-- ------------------------------------------------------------------
-- Source: 019_create_project_stage_assessments_20260118021319.sql
-- 019) project_stage_assessments
CREATE TABLE project_stage_assessments (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                       UUID NOT NULL,
    project_id                   UUID NOT NULL,
    stage                        TEXT NOT NULL,
    draft_summary_markdown       TEXT NULL,
    final_summary_markdown       TEXT NULL,
    confirmed                    BOOLEAN NOT NULL DEFAULT false,
    confirmed_at                 TIMESTAMPTZ NULL,
    confirmed_by_user_id         UUID NULL REFERENCES users(id),
    generated_from_state_version INT NULL,
    generator_model              TEXT NULL,
    generator_prompt_template_id UUID NULL REFERENCES prompt_templates(id),
    scores_json                  JSONB NULL,
    total_score                  NUMERIC NULL,
    risk_matrix                  JSONB NULL,
    diagram_mermaid              TEXT NULL,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    CHECK (
        (confirmed AND confirmed_at IS NOT NULL AND confirmed_by_user_id IS NOT NULL)
        OR (NOT confirmed AND confirmed_at IS NULL AND confirmed_by_user_id IS NULL)
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX project_stage_assessments_unique
    ON project_stage_assessments (project_id, stage)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_stage_assessment_confirmer()
RETURNS trigger AS $$
DECLARE
    project_owner_id UUID;
    member_role TEXT;
BEGIN
    IF NEW.confirmed THEN
        SELECT owner_user_id
          INTO project_owner_id
          FROM projects
         WHERE id = NEW.project_id
           AND deleted_at IS NULL;

        IF project_owner_id IS NULL THEN
            RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        SELECT org_role
          INTO member_role
          FROM organization_memberships
         WHERE org_id = NEW.org_id
           AND user_id = NEW.confirmed_by_user_id
           AND status = 'active'
           AND deleted_at IS NULL;

        IF member_role IS NULL THEN
            RAISE EXCEPTION 'confirmed_by_user_id % is not an active member of org %',
                NEW.confirmed_by_user_id, NEW.org_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.confirmed_by_user_id <> project_owner_id
           AND member_role NOT IN ('owner','admin') THEN
            RAISE EXCEPTION 'confirmed_by_user_id % cannot confirm stage assessments',
                NEW.confirmed_by_user_id
                USING ERRCODE = '23514';
        END IF;

        NEW.confirmed_at := COALESCE(NEW.confirmed_at, now());
    ELSE
        NEW.confirmed_at := NULL;
        NEW.confirmed_by_user_id := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enforce_project_stage_assessment_state_version()
RETURNS trigger AS $$
DECLARE
    current_state_version INT;
BEGIN
    IF NEW.generated_from_state_version IS NOT NULL THEN
        SELECT state_version
          INTO current_state_version
          FROM project_states
         WHERE project_id = NEW.project_id
           AND deleted_at IS NULL;

        IF current_state_version IS NULL THEN
            RAISE EXCEPTION 'project_state not found for project %', NEW.project_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.generated_from_state_version > current_state_version THEN
            RAISE EXCEPTION 'generated_from_state_version % exceeds current state_version %',
                NEW.generated_from_state_version, current_state_version
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_stage_assessments_confirmer_guard
    BEFORE INSERT OR UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_stage_assessment_confirmer();

CREATE TRIGGER project_stage_assessments_state_version_guard
    BEFORE INSERT OR UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_stage_assessment_state_version();

-- ------------------------------------------------------------------
-- Source: 020_create_project_reports_20260118021320.sql
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

-- ------------------------------------------------------------------
-- Source: 021_create_project_comments_20260118021321.sql
-- 021) project_comments
CREATE TABLE project_comments (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                    UUID NOT NULL,
    project_id                UUID NOT NULL,
    author_user_id            UUID NOT NULL REFERENCES users(id),
    visibility                TEXT NOT NULL DEFAULT 'student_and_mentors',
    status                    TEXT NOT NULL DEFAULT 'open',
    content                   TEXT NOT NULL,
    content_format            TEXT NOT NULL DEFAULT 'markdown',
    target_stage              TEXT NULL,
    target_question_instance_id UUID NULL REFERENCES project_question_instances(id),
    target_message_id         BIGINT NULL REFERENCES conversation_messages(id),
    target_report_id          UUID NULL REFERENCES project_reports(id),
    target_section_key        TEXT NULL,
    parent_comment_id         UUID NULL REFERENCES project_comments(id),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    CHECK (visibility IN ('student_and_mentors','mentors_only','private')),
    CHECK (status IN ('open','resolved','archived')),
    CHECK (content_format IN ('markdown','text')),
    CHECK (target_stage IS NULL OR target_stage IN ('problem','market','tech','report')),
    CHECK (
        num_nonnulls(
            target_stage,
            target_question_instance_id,
            target_message_id,
            target_report_id,
            target_section_key
        ) <= 1
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_comments_project_created_idx
    ON project_comments (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_comments_project_status_idx
    ON project_comments (project_id, status)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_comment_author_membership()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.author_user_id
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'author_user_id % is not an active member of org %',
            NEW.author_user_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_comments_author_guard
    BEFORE INSERT OR UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_comment_author_membership();

CREATE OR REPLACE FUNCTION enforce_project_comment_targets()
RETURNS trigger AS $$
DECLARE
    target_project_id UUID;
    target_org_id UUID;
BEGIN
    IF NEW.target_question_instance_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM project_question_instances
         WHERE id = NEW.target_question_instance_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'question_instance % not found or deleted',
                NEW.target_question_instance_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'question_instance % does not belong to project %',
                NEW.target_question_instance_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.target_message_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM conversation_messages
         WHERE id = NEW.target_message_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'message % not found or deleted',
                NEW.target_message_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'message % does not belong to project %',
                NEW.target_message_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.target_report_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM project_reports
         WHERE id = NEW.target_report_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'report % not found or deleted',
                NEW.target_report_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'report % does not belong to project %',
                NEW.target_report_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_comments_targets_guard
    BEFORE INSERT OR UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_comment_targets();

-- ------------------------------------------------------------------
-- Source: 022_create_notifications_20260118021322.sql
-- 022) notifications
CREATE TABLE notifications (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id            UUID NOT NULL,
    recipient_user_id UUID NOT NULL REFERENCES users(id),
    type              TEXT NOT NULL,
    title             TEXT NULL,
    body              TEXT NULL,
    link              TEXT NULL,
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at           TIMESTAMPTZ NULL,
    deleted_at        TIMESTAMPTZ NULL,
    CHECK (type = lower(btrim(type))),
    CHECK (type <> ''),
    CHECK (type ~ '^[a-z0-9_.-]+$'),
    CHECK (link IS NULL OR length(link) <= 2000)
);

CREATE INDEX notifications_recipient_unread_idx
    ON notifications (recipient_user_id, read_at, created_at DESC)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 023_create_evaluation_rubrics_20260118021323.sql
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

-- ------------------------------------------------------------------
-- Source: 024_create_answer_evaluations_20260118021324.sql
-- 024) answer_evaluations
CREATE TABLE answer_evaluations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL,
    project_id          UUID NOT NULL,
    question_instance_id UUID NOT NULL REFERENCES project_question_instances(id),
    rubric_id           UUID NOT NULL REFERENCES evaluation_rubrics(id),
    scores_json         JSONB NOT NULL,
    overall_score       NUMERIC NULL,
    feedback_markdown   TEXT NULL,
    evaluator_type      TEXT NOT NULL,
    evaluator_model     TEXT NULL,
    request_id          UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ NULL,
    CHECK (evaluator_type IN ('ai','human','system')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX answer_evaluations_request_unique
    ON answer_evaluations (request_id)
    WHERE request_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX answer_evaluations_project_created_idx
    ON answer_evaluations (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_answer_evaluation_scope()
RETURNS trigger AS $$
DECLARE
    instance_project_id UUID;
    instance_org_id UUID;
BEGIN
    SELECT project_id, org_id
      INTO instance_project_id, instance_org_id
      FROM project_question_instances
     WHERE id = NEW.question_instance_id
       AND deleted_at IS NULL;

    IF instance_project_id IS NULL THEN
        RAISE EXCEPTION 'question_instance % not found or deleted',
            NEW.question_instance_id
            USING ERRCODE = '23514';
    END IF;

    IF instance_project_id <> NEW.project_id
        OR instance_org_id <> NEW.org_id THEN
        RAISE EXCEPTION 'question_instance % does not belong to project %',
            NEW.question_instance_id, NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER answer_evaluations_scope_guard
    BEFORE INSERT OR UPDATE ON answer_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION enforce_answer_evaluation_scope();

-- ------------------------------------------------------------------
-- Source: 025_create_message_evaluations_20260118021324.sql
-- 025) message_evaluations
CREATE TABLE message_evaluations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL,
    project_id        UUID NOT NULL,
    message_id        BIGINT NOT NULL REFERENCES conversation_messages(id),
    rubric_id         UUID NOT NULL REFERENCES evaluation_rubrics(id),
    scores_json       JSONB NOT NULL,
    overall_score     NUMERIC NULL,
    feedback_markdown TEXT NULL,
    evaluator_type    TEXT NOT NULL,
    evaluator_model   TEXT NULL,
    request_id        UUID NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ NULL,
    CHECK (evaluator_type IN ('ai','human','system')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX message_evaluations_request_unique
    ON message_evaluations (request_id)
    WHERE request_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX message_evaluations_project_created_idx
    ON message_evaluations (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_message_evaluation_scope()
RETURNS trigger AS $$
DECLARE
    message_project_id UUID;
    message_org_id UUID;
BEGIN
    SELECT project_id, org_id
      INTO message_project_id, message_org_id
      FROM conversation_messages
     WHERE id = NEW.message_id
       AND deleted_at IS NULL;

    IF message_project_id IS NULL THEN
        RAISE EXCEPTION 'message % not found or deleted',
            NEW.message_id
            USING ERRCODE = '23514';
    END IF;

    IF message_project_id <> NEW.project_id
        OR message_org_id <> NEW.org_id THEN
        RAISE EXCEPTION 'message % does not belong to project %',
            NEW.message_id, NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER message_evaluations_scope_guard
    BEFORE INSERT OR UPDATE ON message_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION enforce_message_evaluation_scope();

-- ------------------------------------------------------------------
-- Source: 026_create_background_jobs_20260118022743.sql
-- 026) background_jobs
CREATE TABLE background_jobs (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id           UUID NOT NULL,
    project_id       UUID NULL,
    job_type         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'queued',
    priority         INT NOT NULL DEFAULT 100,
    payload          JSONB NOT NULL,
    idempotency_key  TEXT NULL,
    attempts         INT NOT NULL DEFAULT 0,
    max_attempts     INT NOT NULL DEFAULT 5,
    run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at        TIMESTAMPTZ NULL,
    lock_expires_at  TIMESTAMPTZ NULL,
    locked_by        TEXT NULL,
    started_at       TIMESTAMPTZ NULL,
    completed_at     TIMESTAMPTZ NULL,
    last_error       TEXT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ NULL,
    CHECK (job_type = lower(btrim(job_type))),
    CHECK (job_type <> ''),
    CHECK (job_type ~ '^[a-z0-9_.-]+$'),
    CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
    CHECK (priority >= 0),
    CHECK (attempts >= 0),
    CHECK (max_attempts >= 0),
    CHECK (
        (locked_at IS NULL AND locked_by IS NULL AND lock_expires_at IS NULL)
        OR (locked_at IS NOT NULL AND locked_by IS NOT NULL AND lock_expires_at IS NOT NULL)
    ),
    CHECK (
        status <> 'running'
        OR (started_at IS NOT NULL AND completed_at IS NULL)
    ),
    CHECK (
        status IN ('succeeded','failed','cancelled')
        OR completed_at IS NULL
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX background_jobs_idempotency_unique
    ON background_jobs (org_id, job_type, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX background_jobs_queue_idx
    ON background_jobs (status, run_at, priority)
    WHERE deleted_at IS NULL;

CREATE INDEX background_jobs_locked_idx
    ON background_jobs (locked_at)
    WHERE deleted_at IS NULL;

CREATE INDEX background_jobs_project_created_idx
    ON background_jobs (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION set_background_job_timestamps()
RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'running' AND NEW.started_at IS NULL THEN
        NEW.started_at := now();
        NEW.completed_at := NULL;
    ELSIF NEW.status IN ('succeeded','failed','cancelled') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, now());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER background_jobs_timestamps_guard
    BEFORE INSERT OR UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION set_background_job_timestamps();

-- ------------------------------------------------------------------
-- Source: 027_create_idempotency_keys_20260118022744.sql
-- 027) idempotency_keys
CREATE TABLE idempotency_keys (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    user_id       UUID NOT NULL REFERENCES users(id),
    scope         TEXT NOT NULL,
    key           TEXT NOT NULL,
    request_hash  TEXT NULL,
    response_ref  JSONB NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NULL,
    deleted_at    TIMESTAMPTZ NULL,
    CHECK (scope = lower(btrim(scope))),
    CHECK (scope <> ''),
    CHECK (scope !~ '\s'),
    CHECK (key = btrim(key)),
    CHECK (key <> ''),
    CHECK (key ~ '^[A-Za-z0-9_.:-]+$'),
    CHECK (expires_at IS NULL OR expires_at > created_at)
);

CREATE UNIQUE INDEX idempotency_keys_unique
    ON idempotency_keys (org_id, scope, key)
    WHERE deleted_at IS NULL;

CREATE INDEX idempotency_keys_user_created_idx
    ON idempotency_keys (user_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_idempotency_key_consistency()
RETURNS trigger AS $$
BEGIN
    IF OLD.request_hash IS NOT NULL
        AND NEW.request_hash IS DISTINCT FROM OLD.request_hash THEN
        RAISE EXCEPTION 'request_hash mismatch for idempotency key %', OLD.id
            USING ERRCODE = '23514';
    END IF;

    IF OLD.response_ref IS NOT NULL
        AND NEW.response_ref IS DISTINCT FROM OLD.response_ref THEN
        RAISE EXCEPTION 'response_ref already set for idempotency key %', OLD.id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER idempotency_keys_consistency_guard
    BEFORE UPDATE ON idempotency_keys
    FOR EACH ROW
    EXECUTE FUNCTION enforce_idempotency_key_consistency();

-- ------------------------------------------------------------------
-- Source: 028_enable_rls_policies_20260118022745.sql
-- 028) Row Level Security policies
-- NOTE: Policies assume the app sets these session variables:
--   app.user_id, app.org_id, app.actor_type

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohort_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_student_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_stage_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_runtime ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_question_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_state_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_rubrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE answer_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE cohorts FORCE ROW LEVEL SECURITY;
ALTER TABLE cohort_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE mentor_student_assignments FORCE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE user_identities FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_stage_variants FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions FORCE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
ALTER TABLE project_runtime FORCE ROW LEVEL SECURITY;
ALTER TABLE project_question_instances FORCE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE project_states FORCE ROW LEVEL SECURITY;
ALTER TABLE project_state_events FORCE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates FORCE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_events FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE project_stage_assessments FORCE ROW LEVEL SECURITY;
ALTER TABLE project_reports FORCE ROW LEVEL SECURITY;
ALTER TABLE project_comments FORCE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
ALTER TABLE evaluation_rubrics FORCE ROW LEVEL SECURITY;
ALTER TABLE answer_evaluations FORCE ROW LEVEL SECURITY;
ALTER TABLE message_evaluations FORCE ROW LEVEL SECURITY;
ALTER TABLE background_jobs FORCE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION app_user_id()
RETURNS uuid AS $$
BEGIN
    RETURN NULLIF(current_setting('app.user_id', true), '')::uuid;
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION app_org_id()
RETURNS uuid AS $$
BEGIN
    RETURN NULLIF(current_setting('app.org_id', true), '')::uuid;
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION app_actor_type()
RETURNS text AS $$
BEGIN
    RETURN NULLIF(current_setting('app.actor_type', true), '');
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION has_org_membership(target_org uuid)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = target_org
          AND om.user_id = app_user_id()
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_org_admin(target_org uuid)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = target_org
          AND om.user_id = app_user_id()
          AND om.status = 'active'
          AND om.org_role IN ('owner','admin')
          AND om.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF app_user_id() IS NULL THEN
        RETURN FALSE;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project_messages(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_view_messages = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project_facts(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_view_facts = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_comment_on_project(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_comment = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Basic org-scoped tables: allow access if org_id matches app.org_id
CREATE POLICY org_scoped_select ON organizations
    FOR SELECT USING (id = app_org_id());

CREATE POLICY org_scoped_select ON organization_memberships
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON organization_invitations
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON cohorts
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON cohort_memberships
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON users
    FOR SELECT USING (id = app_user_id());

CREATE POLICY org_scoped_select ON user_identities
    FOR SELECT USING (user_id = app_user_id());

CREATE POLICY question_bank_select ON question_bank_versions
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY question_bank_select ON question_bank_stage_variants
    FOR SELECT USING (true);

CREATE POLICY question_bank_select ON question_bank_questions
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND (qbv.org_id IS NULL OR qbv.org_id = app_org_id())
        )
    );

CREATE POLICY projects_select ON projects
    FOR SELECT USING (can_view_project(id, org_id));

CREATE POLICY project_runtime_select ON project_runtime
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_question_instances_select ON project_question_instances
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY conversation_messages_select ON conversation_messages
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

CREATE POLICY project_states_select ON project_states
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_state_events_select ON project_state_events
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY prompt_templates_select ON prompt_templates
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY documents_select ON documents
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY analytics_events_select ON analytics_events
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY audit_events_select ON audit_events
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY project_stage_assessments_select ON project_stage_assessments
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_reports_select ON project_reports
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_comments_select ON project_comments
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY notifications_select ON notifications
    FOR SELECT USING (recipient_user_id = app_user_id());

CREATE POLICY evaluation_rubrics_select ON evaluation_rubrics
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY answer_evaluations_select ON answer_evaluations
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY message_evaluations_select ON message_evaluations
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

CREATE POLICY background_jobs_select ON background_jobs
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY idempotency_keys_select ON idempotency_keys
    FOR SELECT USING (org_id = app_org_id() AND user_id = app_user_id());

-- Writes: default deny, with narrow allowances for comments and notifications.
CREATE POLICY project_runtime_system_insert ON project_runtime
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_runtime_system_update ON project_runtime
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_question_instances_system_insert ON project_question_instances
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_question_instances_system_update ON project_question_instances
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY conversation_messages_system_insert ON conversation_messages
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
        AND role <> 'user'
    );

CREATE POLICY project_states_system_insert ON project_states
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_states_system_update ON project_states
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_state_events_system_insert ON project_state_events
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_assessments_system_insert ON project_stage_assessments
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_assessments_system_update ON project_stage_assessments
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_reports_system_insert ON project_reports
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_reports_system_update ON project_reports
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY answer_evaluations_system_insert ON answer_evaluations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY answer_evaluations_system_update ON answer_evaluations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY message_evaluations_system_insert ON message_evaluations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY message_evaluations_system_update ON message_evaluations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY background_jobs_system_insert ON background_jobs
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY background_jobs_system_update ON background_jobs
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY organizations_update_admin ON organizations
    FOR UPDATE USING (is_org_admin(id))
    WITH CHECK (is_org_admin(id));

CREATE POLICY organizations_delete_admin ON organizations
    FOR DELETE USING (is_org_admin(id));

CREATE POLICY organization_memberships_admin_write ON organization_memberships
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_memberships_admin_update ON organization_memberships
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_memberships_admin_delete ON organization_memberships
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_write ON organization_invitations
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_update ON organization_invitations
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_delete ON organization_invitations
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY cohorts_admin_write ON cohorts
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohorts_admin_update ON cohorts
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohorts_admin_delete ON cohorts
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_write ON cohort_memberships
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_update ON cohort_memberships
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_delete ON cohort_memberships
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY projects_insert_owner_or_admin ON projects
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id))
    );

CREATE POLICY projects_update_owner_or_admin ON projects
    FOR UPDATE USING (org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id)))
    WITH CHECK (org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id)));

CREATE POLICY conversation_messages_insert_owner ON conversation_messages
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND role = 'user'
        AND author_user_id = app_user_id()
        AND EXISTS (
            SELECT 1
            FROM projects p
            WHERE p.id = project_id
              AND p.org_id = org_id
              AND p.owner_user_id = app_user_id()
              AND p.deleted_at IS NULL
        )
    );

CREATE POLICY documents_insert_owner_or_admin ON documents
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND (
            is_org_admin(org_id)
            OR EXISTS (
                SELECT 1
                FROM projects p
                WHERE p.id = project_id
                  AND p.org_id = org_id
                  AND p.owner_user_id = app_user_id()
                  AND p.deleted_at IS NULL
            )
        )
    );

CREATE POLICY documents_system_update ON documents
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY documents_delete_owner_or_admin ON documents
    FOR DELETE USING (
        org_id = app_org_id()
        AND (
            is_org_admin(org_id)
            OR EXISTS (
                SELECT 1
                FROM projects p
                WHERE p.id = project_id
                  AND p.org_id = org_id
                  AND p.owner_user_id = app_user_id()
                  AND p.deleted_at IS NULL
            )
        )
    );

CREATE POLICY idempotency_keys_insert_owner ON idempotency_keys
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND user_id = app_user_id()
    );

CREATE POLICY idempotency_keys_update_owner ON idempotency_keys
    FOR UPDATE USING (
        org_id = app_org_id()
        AND user_id = app_user_id()
    )
    WITH CHECK (
        org_id = app_org_id()
        AND user_id = app_user_id()
    );

CREATE POLICY project_comments_insert ON project_comments
    FOR INSERT WITH CHECK (can_comment_on_project(project_id, org_id)
        AND author_user_id = app_user_id());

CREATE POLICY notifications_update ON notifications
    FOR UPDATE USING (recipient_user_id = app_user_id())
    WITH CHECK (recipient_user_id = app_user_id());

-- ------------------------------------------------------------------
-- Source: 029_fix_evaluation_rubrics_unique_20260118024000.sql
-- 029) Fix evaluation_rubrics uniqueness to include scope
DROP INDEX IF EXISTS evaluation_rubrics_unique;

CREATE UNIQUE INDEX evaluation_rubrics_unique
    ON evaluation_rubrics (scope_org_id, scope, rubric_key, rubric_version)
    WHERE deleted_at IS NULL;

-- ------------------------------------------------------------------
-- Source: 030_add_updated_at_triggers_20260118024010.sql
-- 030) Ensure updated_at is maintained on updates
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER organizations_set_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER user_identities_set_updated_at
    BEFORE UPDATE ON user_identities
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organization_memberships_set_updated_at
    BEFORE UPDATE ON organization_memberships
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organization_invitations_set_updated_at
    BEFORE UPDATE ON organization_invitations
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cohorts_set_updated_at
    BEFORE UPDATE ON cohorts
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cohort_memberships_set_updated_at
    BEFORE UPDATE ON cohort_memberships
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER mentor_student_assignments_set_updated_at
    BEFORE UPDATE ON mentor_student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER question_bank_versions_set_updated_at
    BEFORE UPDATE ON question_bank_versions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER question_bank_questions_set_updated_at
    BEFORE UPDATE ON question_bank_questions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER projects_set_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_runtime_set_updated_at
    BEFORE UPDATE ON project_runtime
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER prompt_templates_set_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_question_instances_set_updated_at
    BEFORE UPDATE ON project_question_instances
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_states_set_updated_at
    BEFORE UPDATE ON project_states
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER documents_set_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_stage_assessments_set_updated_at
    BEFORE UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_reports_set_updated_at
    BEFORE UPDATE ON project_reports
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_comments_set_updated_at
    BEFORE UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER evaluation_rubrics_set_updated_at
    BEFORE UPDATE ON evaluation_rubrics
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER background_jobs_set_updated_at
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ------------------------------------------------------------------
-- Source: 031_add_mentor_student_assignments_policies_20260118024140.sql
-- 031) mentor_student_assignments RLS policies and update rules
CREATE POLICY mentor_student_assignments_select ON mentor_student_assignments
    FOR SELECT USING (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_insert ON mentor_student_assignments
    FOR INSERT WITH CHECK (
        is_org_admin(org_id)
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_update ON mentor_student_assignments
    FOR UPDATE USING (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    )
    WITH CHECK (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_delete ON mentor_student_assignments
    FOR DELETE USING (is_org_admin(org_id));

CREATE OR REPLACE FUNCTION enforce_assignment_write_rules()
RETURNS trigger AS $$
DECLARE
    actor_id UUID;
    actor_is_admin BOOLEAN;
BEGIN
    actor_id := app_user_id();
    IF actor_id IS NULL THEN
        RAISE EXCEPTION 'app.user_id is required for assignment writes'
            USING ERRCODE = '23514';
    END IF;

    actor_is_admin := is_org_admin(NEW.org_id);

    IF TG_OP = 'INSERT' THEN
        IF actor_is_admin THEN
            RETURN NEW;
        END IF;

        IF NEW.student_user_id <> actor_id THEN
            RAISE EXCEPTION 'only student can self-invite a mentor'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.status <> 'pending' THEN
            RAISE EXCEPTION 'student invitation must be pending'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.can_view_messages OR NEW.can_view_facts THEN
            RAISE EXCEPTION 'student invitation cannot grant view permissions'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.created_by IS NULL THEN
            NEW.created_by := actor_id;
        ELSIF NEW.created_by <> actor_id THEN
            RAISE EXCEPTION 'created_by must match actor for student invite'
                USING ERRCODE = '23514';
        END IF;

        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF actor_is_admin THEN
            RETURN NEW;
        END IF;

        IF NEW.org_id IS DISTINCT FROM OLD.org_id
            OR NEW.cohort_id IS DISTINCT FROM OLD.cohort_id
            OR NEW.mentor_user_id IS DISTINCT FROM OLD.mentor_user_id
            OR NEW.student_user_id IS DISTINCT FROM OLD.student_user_id
            OR NEW.created_by IS DISTINCT FROM OLD.created_by
            OR NEW.created_at IS DISTINCT FROM OLD.created_at
            OR NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
            RAISE EXCEPTION 'immutable assignment fields cannot be changed'
                USING ERRCODE = '23514';
        END IF;

        IF actor_id = NEW.mentor_user_id THEN
            IF NEW.can_view_messages IS DISTINCT FROM OLD.can_view_messages
                OR NEW.can_view_facts IS DISTINCT FROM OLD.can_view_facts
                OR NEW.can_comment IS DISTINCT FROM OLD.can_comment THEN
                RAISE EXCEPTION 'mentor cannot change permission flags'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT (
                    (OLD.status = 'pending' AND NEW.status IN ('active','revoked'))
                    OR (OLD.status = 'active' AND NEW.status = 'revoked')
                ) THEN
                    RAISE EXCEPTION 'invalid status transition for mentor'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            RETURN NEW;
        END IF;

        IF actor_id = NEW.student_user_id THEN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT (
                    (OLD.status = 'pending' AND NEW.status = 'revoked')
                    OR (OLD.status = 'active' AND NEW.status = 'revoked')
                ) THEN
                    RAISE EXCEPTION 'invalid status transition for student'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'actor not permitted to update assignment'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mentor_student_assignments_write_guard
    BEFORE INSERT OR UPDATE ON mentor_student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_assignment_write_rules();

-- ------------------------------------------------------------------
-- Source: 032_add_users_admin_select_policy_20260118024210.sql
-- 032) users admin/system select policy
CREATE POLICY users_admin_select ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND is_org_admin(app_org_id())
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users.id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

CREATE POLICY users_system_select ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND app_actor_type() = 'system'
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users.id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

-- ------------------------------------------------------------------
-- Source: 033_tighten_event_job_select_policies_20260118024230.sql
-- 033) Tighten analytics/audit/background_jobs select policies
DROP POLICY IF EXISTS analytics_events_select ON analytics_events;
CREATE POLICY analytics_events_select ON analytics_events
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
        OR (
            project_id IS NOT NULL
            AND can_view_project(project_id, org_id)
        )
    );

DROP POLICY IF EXISTS audit_events_select ON audit_events;
CREATE POLICY audit_events_select ON audit_events
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
    );

DROP POLICY IF EXISTS background_jobs_select ON background_jobs;
CREATE POLICY background_jobs_select ON background_jobs
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
        OR (
            project_id IS NOT NULL
            AND can_view_project(project_id, org_id)
        )
    );

-- ------------------------------------------------------------------
-- Source: 034_add_provisioning_policies_20260118024240.sql
-- 034) System provisioning policies
CREATE POLICY users_system_insert ON users
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY users_system_update ON users
    FOR UPDATE USING (
        app_actor_type() = 'system'
    )
    WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY user_identities_system_insert ON user_identities
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY user_identities_system_update ON user_identities
    FOR UPDATE USING (
        app_actor_type() = 'system'
    )
    WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY organizations_system_insert ON organizations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY organization_memberships_system_insert ON organization_memberships
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY organization_invitations_system_update ON organization_invitations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

-- ------------------------------------------------------------------
-- Source: 035_align_fact_message_rls_20260118024250.sql
-- 035) Align fact/message select policies with A-4 permissions
DROP POLICY IF EXISTS project_stage_assessments_select ON project_stage_assessments;
CREATE POLICY project_stage_assessments_select ON project_stage_assessments
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

DROP POLICY IF EXISTS project_reports_select ON project_reports;
CREATE POLICY project_reports_select ON project_reports
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

DROP POLICY IF EXISTS project_question_instances_select ON project_question_instances;
CREATE POLICY project_question_instances_select ON project_question_instances
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

DROP POLICY IF EXISTS documents_select ON documents;
CREATE POLICY documents_select ON documents
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

DROP POLICY IF EXISTS answer_evaluations_select ON answer_evaluations;
CREATE POLICY answer_evaluations_select ON answer_evaluations
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

-- ------------------------------------------------------------------
-- Source: 036_add_users_public_profiles_20260118024300.sql
-- 036) Add users_public_profiles for mentor-safe access
CREATE TABLE users_public_profiles (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

INSERT INTO users_public_profiles (user_id, display_name, created_at, updated_at, deleted_at)
SELECT id, display_name, created_at, updated_at, deleted_at
FROM users;

CREATE OR REPLACE FUNCTION sync_users_public_profiles()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM users_public_profiles WHERE user_id = OLD.id;
        RETURN OLD;
    END IF;

    INSERT INTO users_public_profiles (user_id, display_name, created_at, updated_at, deleted_at)
    VALUES (NEW.id, NEW.display_name, NEW.created_at, NEW.updated_at, NEW.deleted_at)
    ON CONFLICT (user_id) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        updated_at = EXCLUDED.updated_at,
        deleted_at = EXCLUDED.deleted_at;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_public_profiles_sync
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION sync_users_public_profiles();

ALTER TABLE users_public_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_public_profiles FORCE ROW LEVEL SECURITY;

CREATE POLICY users_public_profiles_self_select ON users_public_profiles
    FOR SELECT USING (user_id = app_user_id() AND deleted_at IS NULL);

CREATE POLICY users_public_profiles_admin_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND is_org_admin(app_org_id())
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_system_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND app_actor_type() = 'system'
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_mentor_select_assigned_students ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND EXISTS (
            SELECT 1
            FROM mentor_student_assignments msa
            WHERE msa.org_id = app_org_id()
              AND msa.mentor_user_id = app_user_id()
              AND msa.student_user_id = users_public_profiles.user_id
              AND msa.status IN ('pending','active')
              AND msa.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_system_insert ON users_public_profiles
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY users_public_profiles_system_update ON users_public_profiles
    FOR UPDATE USING (
        app_actor_type() = 'system'
    )
    WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY users_public_profiles_system_delete ON users_public_profiles
    FOR DELETE USING (
        app_actor_type() = 'system'
    );

-- ------------------------------------------------------------------
-- Source: 037_fix_project_runtime_trigger_20260118024410.sql
-- 037) Fix enforce_project_runtime_questions ambiguity
CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    SELECT p.question_bank_version_id, p.current_stage, p.current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects p
     WHERE p.id = NEW.project_id
       AND p.deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    SELECT q.bank_version_id, q.stage, q.variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions q
     WHERE q.id = NEW.current_question_bank_question_id
       AND q.deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT q.bank_version_id, q.stage, q.variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions q
         WHERE q.id = NEW.next_question_bank_question_id
           AND q.deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------------
-- Source: 038_allow_removed_members_admin_select_20260118024530.sql
-- 038) Allow admins to view removed org members in user lookups
DROP POLICY IF EXISTS users_admin_select ON users;
CREATE POLICY users_admin_select ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND is_org_admin(app_org_id())
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users.id
              AND om.status IN ('active','invited','removed')
              AND om.deleted_at IS NULL
        )
    );

DROP POLICY IF EXISTS users_system_select ON users;
CREATE POLICY users_system_select ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND app_actor_type() = 'system'
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users.id
              AND om.status IN ('active','invited','removed')
              AND om.deleted_at IS NULL
        )
    );

DROP POLICY IF EXISTS users_public_profiles_admin_select ON users_public_profiles;
CREATE POLICY users_public_profiles_admin_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND is_org_admin(app_org_id())
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited','removed')
              AND om.deleted_at IS NULL
        )
    );

DROP POLICY IF EXISTS users_public_profiles_system_select ON users_public_profiles;
CREATE POLICY users_public_profiles_system_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND app_actor_type() = 'system'
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited','removed')
              AND om.deleted_at IS NULL
        )
    );

-- ------------------------------------------------------------------
-- Source: 039_project_comments_admin_moderation_20260118024610.sql
-- 039) Allow org admins to moderate project comments
DROP POLICY IF EXISTS project_comments_admin_update ON project_comments;
CREATE POLICY project_comments_admin_update ON project_comments
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

DROP POLICY IF EXISTS project_comments_admin_delete ON project_comments;
CREATE POLICY project_comments_admin_delete ON project_comments
    FOR DELETE USING (is_org_admin(org_id));

-- ------------------------------------------------------------------
-- Source: 040_project_comments_admin_insert_20260118024730.sql
-- 040) Allow org admins to add project comments
DROP POLICY IF EXISTS project_comments_admin_insert ON project_comments;
CREATE POLICY project_comments_admin_insert ON project_comments
    FOR INSERT WITH CHECK (
        is_org_admin(org_id)
        AND author_user_id = app_user_id()
    );

-- ------------------------------------------------------------------
-- Source: 041_allow_report_runtime_null_current_question_20260121050000.sql
-- 041) Allow report runtime without a current question
ALTER TABLE project_runtime
    ALTER COLUMN current_question_bank_question_id DROP NOT NULL;

CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    SELECT p.question_bank_version_id, p.current_stage, p.current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects p
     WHERE p.id = NEW.project_id
       AND p.deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    IF NEW.stage = 'report' AND NEW.current_question_bank_question_id IS NULL THEN
        NEW.next_question_bank_question_id := NULL;
        RETURN NEW;
    END IF;

    IF NEW.current_question_bank_question_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id is required'
            USING ERRCODE = '23514';
    END IF;

    SELECT q.bank_version_id, q.stage, q.variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions q
     WHERE q.id = NEW.current_question_bank_question_id
       AND q.deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT q.bank_version_id, q.stage, q.variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions q
         WHERE q.id = NEW.next_question_bank_question_id
           AND q.deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------------
-- Source: 042_add_email_verification_20260122000000.sql
-- 042) email verification + usage buckets
ALTER TABLE users
    ADD COLUMN email_verified_at TIMESTAMPTZ;

CREATE TABLE email_verification_tokens (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email         CITEXT NOT NULL,
    token_hash    TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed_at   TIMESTAMPTZ,
    CHECK (email = btrim(email)),
    CHECK (email !~ '\s')
);

CREATE UNIQUE INDEX email_verification_tokens_token_hash_unique
    ON email_verification_tokens (token_hash);

CREATE INDEX email_verification_tokens_user_id_idx
    ON email_verification_tokens (user_id)
    WHERE consumed_at IS NULL;

CREATE TABLE llm_usage_buckets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_type   TEXT NOT NULL,
    bucket_start  TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (bucket_type IN ('minute', 'day'))
);

CREATE UNIQUE INDEX llm_usage_buckets_unique
    ON llm_usage_buckets (user_id, bucket_type, bucket_start);

-- ------------------------------------------------------------------
-- Source: 043_add_expected_key_points_20260201000000.sql
-- 043) add expected_key_points to question_bank_questions
ALTER TABLE question_bank_questions
    ADD COLUMN expected_key_points TEXT[];

-- ------------------------------------------------------------------
-- Source: 044_create_stage_qa_digest_and_verification_claims_20260201012000.sql
-- 044) project_stage_qa_digests + project_stage_verification_claims
CREATE TABLE project_stage_qa_digests (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    assessment_id      UUID NOT NULL REFERENCES project_stage_assessments(id) ON DELETE CASCADE,
    stage              TEXT NOT NULL,
    question_id        TEXT NOT NULL,
    answer_summary     TEXT NULL,
    key_points         TEXT[] NULL,
    source_message_id  BIGINT NULL REFERENCES conversation_messages(id),
    model              TEXT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_stage_qa_digests_project_stage_created_idx
    ON project_stage_qa_digests (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_stage_qa_digests_assessment_idx
    ON project_stage_qa_digests (assessment_id)
    WHERE deleted_at IS NULL;

CREATE TRIGGER project_stage_qa_digests_set_updated_at
    BEFORE UPDATE ON project_stage_qa_digests
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE project_stage_qa_digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_qa_digests FORCE ROW LEVEL SECURITY;

CREATE POLICY project_stage_qa_digests_select ON project_stage_qa_digests
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_stage_qa_digests_system_insert ON project_stage_qa_digests
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_qa_digests_system_update ON project_stage_qa_digests
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE TABLE project_stage_verification_claims (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL,
    project_id         UUID NOT NULL,
    assessment_id      UUID NOT NULL REFERENCES project_stage_assessments(id) ON DELETE CASCADE,
    stage              TEXT NOT NULL,
    claim              TEXT NOT NULL,
    verdict            TEXT NOT NULL,
    confidence         TEXT NULL,
    rationale          TEXT NULL,
    sources            JSONB NULL,
    evidence_mode      TEXT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    CHECK (verdict IN ('supported','contradicted','uncertain')),
    CHECK (confidence IS NULL OR confidence IN ('High','Medium','Low')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_stage_verification_claims_project_stage_created_idx
    ON project_stage_verification_claims (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_stage_verification_claims_assessment_idx
    ON project_stage_verification_claims (assessment_id)
    WHERE deleted_at IS NULL;

ALTER TABLE project_stage_verification_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_verification_claims FORCE ROW LEVEL SECURITY;

CREATE POLICY project_stage_verification_claims_select ON project_stage_verification_claims
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_stage_verification_claims_system_insert ON project_stage_verification_claims
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

-- ------------------------------------------------------------------
-- Source: 045_add_question_prompt_meta_20260201013000.sql
-- 045) add prompt_meta to question_bank_questions
ALTER TABLE question_bank_questions
    ADD COLUMN prompt_meta JSONB NOT NULL DEFAULT '{}'::jsonb;

-- ------------------------------------------------------------------
-- Source: 046_add_rate_limits_and_usage_tokens_20260201030000.sql
-- 046) rate limits + LLM token usage + report usage buckets
ALTER TABLE llm_usage_buckets
    ADD COLUMN prompt_tokens INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN completion_tokens INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN total_tokens INTEGER NOT NULL DEFAULT 0;

CREATE TABLE rate_limit_buckets (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope          TEXT NOT NULL,
    key_hash       TEXT NOT NULL,
    window_seconds INTEGER NOT NULL,
    bucket_start   TIMESTAMPTZ NOT NULL,
    request_count  INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (scope = lower(btrim(scope))),
    CHECK (scope <> ''),
    CHECK (scope !~ '\s'),
    CHECK (key_hash <> ''),
    CHECK (window_seconds > 0)
);

CREATE UNIQUE INDEX rate_limit_buckets_unique
    ON rate_limit_buckets (scope, key_hash, window_seconds, bucket_start);

CREATE TABLE report_usage_buckets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_start TIMESTAMPTZ NOT NULL,
    report_count INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (report_count >= 0)
);

CREATE UNIQUE INDEX report_usage_buckets_unique
    ON report_usage_buckets (user_id, bucket_start);

CREATE INDEX report_usage_buckets_user_id_idx
    ON report_usage_buckets (user_id, bucket_start DESC);

-- ------------------------------------------------------------------
-- Source: 047_add_question_plans_20260201060000.sql
-- 047) question_plans for AI question planning
CREATE TABLE question_plans (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID NOT NULL,
    project_id                  UUID NOT NULL,
    stage                       TEXT NOT NULL,
    variant                     TEXT NOT NULL,
    question_instance_id         UUID NULL REFERENCES project_question_instances(id) ON DELETE SET NULL,
    question_bank_question_ids  UUID[] NOT NULL,
    question_ids                TEXT[] NULL,
    schema_paths                TEXT[] NULL,
    prompt                      TEXT NOT NULL,
    model                       TEXT NULL,
    latency_ms                  INTEGER NULL,
    meta                        JSONB NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    CHECK (stage IN ('problem','market','tech')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX question_plans_project_stage_created_idx
    ON question_plans (project_id, stage, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX question_plans_project_created_idx
    ON question_plans (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TRIGGER question_plans_set_updated_at
    BEFORE UPDATE ON question_plans
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE question_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_plans FORCE ROW LEVEL SECURITY;

CREATE POLICY question_plans_select ON question_plans
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY question_plans_system_insert ON question_plans
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY question_plans_system_update ON question_plans
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

-- ------------------------------------------------------------------
-- Source: 048_backfill_question_meta_router_20260201080000.sql
-- 048) backfill question_meta for router quick options (S3Q0)
UPDATE conversation_messages cm
SET meta = jsonb_set(
    COALESCE(cm.meta, '{}'::jsonb),
    '{question_meta}',
    jsonb_build_object(
        'question_id', q.question_id,
        'stage', q.stage,
        'variant', q.variant,
        'ui', q.prompt_meta->'ui'
    ),
    true
)
FROM projects p
JOIN question_bank_questions q
  ON q.bank_version_id = p.question_bank_version_id
 AND q.deleted_at IS NULL
WHERE cm.project_id = p.id
  AND cm.org_id = p.org_id
  AND cm.deleted_at IS NULL
  AND cm.role = 'assistant'
  AND (cm.meta->>'question_id') = 'S3Q0'
  AND q.question_id = (cm.meta->>'question_id')
  AND NOT (COALESCE(cm.meta, '{}'::jsonb) ? 'question_meta')
  AND (cm.meta IS NULL OR jsonb_typeof(cm.meta) = 'object')
  AND q.prompt_meta ? 'ui';

-- ------------------------------------------------------------------
-- Source: 049_drop_users_public_profiles_trigger_20260203130000.sql
-- 049) Drop users_public_profiles sync trigger (handled in app logic)
DROP TRIGGER IF EXISTS users_public_profiles_sync ON users;

-- ------------------------------------------------------------------
-- Source: 050_allow_system_select_for_auth_20260204120000.sql
-- 050) Allow system actor to select auth tables without org context
DROP POLICY IF EXISTS users_system_select_any ON users;
CREATE POLICY users_system_select_any ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND app_actor_type() = 'system'
    );

DROP POLICY IF EXISTS user_identities_system_select_any ON user_identities;
CREATE POLICY user_identities_system_select_any ON user_identities
    FOR SELECT USING (
        user_identities.deleted_at IS NULL
        AND app_actor_type() = 'system'
    );

DROP POLICY IF EXISTS organization_memberships_system_select_any ON organization_memberships;
CREATE POLICY organization_memberships_system_select_any ON organization_memberships
    FOR SELECT USING (
        organization_memberships.deleted_at IS NULL
        AND app_actor_type() = 'system'
    );

DROP POLICY IF EXISTS organizations_system_select_any ON organizations;
CREATE POLICY organizations_system_select_any ON organizations
    FOR SELECT USING (
        organizations.deleted_at IS NULL
        AND app_actor_type() = 'system'
    );

-- ------------------------------------------------------------------
-- Source: 051_create_sample_projects_20260204153000.sql
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

-- ------------------------------------------------------------------
-- Source: 052_fix_project_runtime_rls_recursion_20260206090000.sql
-- 052) Avoid RLS recursion in project_runtime trigger
CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    PERFORM set_config('row_security', 'off', true);

    SELECT p.question_bank_version_id, p.current_stage, p.current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects p
     WHERE p.id = NEW.project_id
       AND p.deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    SELECT q.bank_version_id, q.stage, q.variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions q
     WHERE q.id = NEW.current_question_bank_question_id
       AND q.deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT q.bank_version_id, q.stage, q.variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions q
         WHERE q.id = NEW.next_question_bank_question_id
           AND q.deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- ------------------------------------------------------------------
-- Source: 053_allow_owner_bypass_rls_projects_20260206093000.sql
-- 053) Allow owner to bypass RLS for internal trigger reads
ALTER TABLE projects NO FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions NO FORCE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------
-- Source: 054_scope_row_security_off_in_runtime_trigger_20260206100000.sql
-- 054) Scope row_security=off to the runtime trigger function only
CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET row_security = off
AS $$
DECLARE
    project_bank_id UUID;
    project_stage TEXT;
    project_variant TEXT;
    current_bank_id UUID;
    current_stage TEXT;
    current_variant TEXT;
    next_bank_id UUID;
    next_stage TEXT;
    next_variant TEXT;
BEGIN
    SELECT p.question_bank_version_id, p.current_stage, p.current_variant
      INTO project_bank_id, project_stage, project_variant
      FROM projects p
     WHERE p.id = NEW.project_id
       AND p.deleted_at IS NULL;

    IF project_bank_id IS NULL THEN
        RAISE EXCEPTION 'project % not found or deleted', NEW.project_id
            USING ERRCODE = '23514';
    END IF;

    NEW.stage := project_stage;
    NEW.variant := project_variant;

    SELECT q.bank_version_id, q.stage, q.variant
      INTO current_bank_id, current_stage, current_variant
      FROM question_bank_questions q
     WHERE q.id = NEW.current_question_bank_question_id
       AND q.deleted_at IS NULL;

    IF current_bank_id IS NULL THEN
        RAISE EXCEPTION 'current_question_bank_question_id % not found',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF current_bank_id <> project_bank_id THEN
        RAISE EXCEPTION 'current question % does not belong to project bank %',
            NEW.current_question_bank_question_id, project_bank_id
            USING ERRCODE = '23514';
    END IF;

    IF current_stage <> NEW.stage OR current_variant <> NEW.variant THEN
        RAISE EXCEPTION 'current question % does not match runtime stage/variant',
            NEW.current_question_bank_question_id
            USING ERRCODE = '23514';
    END IF;

    IF NEW.next_question_bank_question_id IS NOT NULL THEN
        SELECT q.bank_version_id, q.stage, q.variant
          INTO next_bank_id, next_stage, next_variant
          FROM question_bank_questions q
         WHERE q.id = NEW.next_question_bank_question_id
           AND q.deleted_at IS NULL;

        IF next_bank_id IS NULL THEN
            RAISE EXCEPTION 'next_question_bank_question_id % not found',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;

        IF next_bank_id <> project_bank_id THEN
            RAISE EXCEPTION 'next question % does not belong to project bank %',
                NEW.next_question_bank_question_id, project_bank_id
                USING ERRCODE = '23514';
        END IF;

        IF next_stage <> NEW.stage OR next_variant <> NEW.variant THEN
            RAISE EXCEPTION 'next question % does not match runtime stage/variant',
                NEW.next_question_bank_question_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- ------------------------------------------------------------------
-- Source: 055_seed_default_evaluation_rubrics_20260206103000.sql
-- 055) Seed default evaluation rubrics for answer/message
ALTER TABLE evaluation_rubrics NO FORCE ROW LEVEL SECURITY;
SET row_security = off;

INSERT INTO evaluation_rubrics (
    id,
    org_id,
    rubric_key,
    rubric_version,
    scope,
    definition_json,
    is_active
)
VALUES
    (
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        NULL,
        'default',
        'v1',
        'answer',
        '{"dimensions":["clarity","completeness","evidence"],"scale":"0-1"}'::jsonb,
        true
    ),
    (
        'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
        NULL,
        'default',
        'v1',
        'message',
        '{"dimensions":["tone","helpfulness","specificity"],"scale":"0-1"}'::jsonb,
        true
    )
ON CONFLICT (id) DO NOTHING;

RESET row_security;
ALTER TABLE evaluation_rubrics FORCE ROW LEVEL SECURITY;
