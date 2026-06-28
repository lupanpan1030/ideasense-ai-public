-- 052) Private org constraints + restrict platform admins from private orgs

CREATE OR REPLACE FUNCTION is_private_org(target_org uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM organizations o
        WHERE o.id = target_org
          AND o.deleted_at IS NULL
          AND COALESCE(o.settings->>'org_type', 'institution') = 'private'
    );
END;
$$;

CREATE OR REPLACE FUNCTION enforce_private_org_memberships()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF is_private_org(NEW.org_id) THEN
        IF NEW.deleted_at IS NOT NULL OR NEW.status = 'removed' THEN
            RETURN NEW;
        END IF;
        IF NEW.org_role <> 'owner' THEN
            RAISE EXCEPTION 'Private organizations only allow owner memberships.'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS organization_memberships_enforce_private
    ON organization_memberships;
CREATE TRIGGER organization_memberships_enforce_private
    BEFORE INSERT OR UPDATE ON organization_memberships
    FOR EACH ROW
    EXECUTE FUNCTION enforce_private_org_memberships();

CREATE OR REPLACE FUNCTION enforce_private_org_invitations()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF is_private_org(NEW.org_id) THEN
        RAISE EXCEPTION 'Private organizations do not allow invitations.'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS organization_invitations_enforce_private
    ON organization_invitations;
CREATE TRIGGER organization_invitations_enforce_private
    BEFORE INSERT ON organization_invitations
    FOR EACH ROW
    EXECUTE FUNCTION enforce_private_org_invitations();

-- Platform admin RLS policies should exclude private orgs
DROP POLICY IF EXISTS organizations_platform_select ON organizations;
DROP POLICY IF EXISTS organizations_platform_insert ON organizations;
DROP POLICY IF EXISTS organizations_platform_update ON organizations;
DROP POLICY IF EXISTS organizations_platform_delete ON organizations;

CREATE POLICY organizations_platform_select ON organizations
    FOR SELECT USING (
        is_platform_admin()
        AND COALESCE(settings->>'org_type', 'institution') <> 'private'
    );

CREATE POLICY organizations_platform_insert ON organizations
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND COALESCE(settings->>'org_type', 'institution') <> 'private'
    );

CREATE POLICY organizations_platform_update ON organizations
    FOR UPDATE USING (
        is_platform_admin()
        AND COALESCE(settings->>'org_type', 'institution') <> 'private'
    )
    WITH CHECK (
        is_platform_admin()
        AND COALESCE(settings->>'org_type', 'institution') <> 'private'
    );

CREATE POLICY organizations_platform_delete ON organizations
    FOR DELETE USING (
        is_platform_admin()
        AND COALESCE(settings->>'org_type', 'institution') <> 'private'
    );

DROP POLICY IF EXISTS organization_memberships_platform_select
    ON organization_memberships;
DROP POLICY IF EXISTS organization_memberships_platform_insert
    ON organization_memberships;
DROP POLICY IF EXISTS organization_memberships_platform_update
    ON organization_memberships;
DROP POLICY IF EXISTS organization_memberships_platform_delete
    ON organization_memberships;

CREATE POLICY organization_memberships_platform_select
    ON organization_memberships
    FOR SELECT USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_memberships.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_memberships_platform_insert
    ON organization_memberships
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_memberships.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_memberships_platform_update
    ON organization_memberships
    FOR UPDATE USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_memberships.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    )
    WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_memberships.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_memberships_platform_delete
    ON organization_memberships
    FOR DELETE USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_memberships.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

DROP POLICY IF EXISTS organization_invitations_platform_select
    ON organization_invitations;
DROP POLICY IF EXISTS organization_invitations_platform_insert
    ON organization_invitations;
DROP POLICY IF EXISTS organization_invitations_platform_update
    ON organization_invitations;
DROP POLICY IF EXISTS organization_invitations_platform_delete
    ON organization_invitations;

CREATE POLICY organization_invitations_platform_select
    ON organization_invitations
    FOR SELECT USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_invitations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_invitations_platform_insert
    ON organization_invitations
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_invitations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_invitations_platform_update
    ON organization_invitations
    FOR UPDATE USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_invitations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    )
    WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_invitations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

CREATE POLICY organization_invitations_platform_delete
    ON organization_invitations
    FOR DELETE USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM organizations o
            WHERE o.id = organization_invitations.org_id
              AND o.deleted_at IS NULL
              AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
        )
    );

-- Platform admin question bank / prompt template access must exclude private orgs
DROP POLICY IF EXISTS question_bank_versions_platform_insert
    ON question_bank_versions;
DROP POLICY IF EXISTS question_bank_versions_platform_update
    ON question_bank_versions;

CREATE POLICY question_bank_versions_platform_insert
    ON question_bank_versions
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = question_bank_versions.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    );

CREATE POLICY question_bank_versions_platform_update
    ON question_bank_versions
    FOR UPDATE USING (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = question_bank_versions.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    )
    WITH CHECK (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = question_bank_versions.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    );

DROP POLICY IF EXISTS question_bank_questions_platform_insert
    ON question_bank_questions;
DROP POLICY IF EXISTS question_bank_questions_platform_update
    ON question_bank_questions;

CREATE POLICY question_bank_questions_platform_insert
    ON question_bank_questions
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            LEFT JOIN organizations o ON o.id = qbv.org_id
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND (
                  qbv.org_id IS NULL
                  OR (
                      o.id IS NOT NULL
                      AND o.deleted_at IS NULL
                      AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
                  )
              )
        )
    );

CREATE POLICY question_bank_questions_platform_update
    ON question_bank_questions
    FOR UPDATE USING (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            LEFT JOIN organizations o ON o.id = qbv.org_id
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND (
                  qbv.org_id IS NULL
                  OR (
                      o.id IS NOT NULL
                      AND o.deleted_at IS NULL
                      AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
                  )
              )
        )
    )
    WITH CHECK (
        is_platform_admin()
        AND EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            LEFT JOIN organizations o ON o.id = qbv.org_id
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND (
                  qbv.org_id IS NULL
                  OR (
                      o.id IS NOT NULL
                      AND o.deleted_at IS NULL
                      AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
                  )
              )
        )
    );

DROP POLICY IF EXISTS prompt_templates_platform_insert
    ON prompt_templates;
DROP POLICY IF EXISTS prompt_templates_platform_update
    ON prompt_templates;

CREATE POLICY prompt_templates_platform_insert
    ON prompt_templates
    FOR INSERT WITH CHECK (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = prompt_templates.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    );

CREATE POLICY prompt_templates_platform_update
    ON prompt_templates
    FOR UPDATE USING (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = prompt_templates.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    )
    WITH CHECK (
        is_platform_admin()
        AND (
            org_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = prompt_templates.org_id
                  AND o.deleted_at IS NULL
                  AND COALESCE(o.settings->>'org_type', 'institution') <> 'private'
            )
        )
    );
