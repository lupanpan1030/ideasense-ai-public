-- 060) Force RLS on projects for owner-connected tenant isolation

DROP POLICY IF EXISTS projects_select ON projects;
DROP POLICY IF EXISTS projects_system_select ON projects;

CREATE POLICY projects_select ON projects
    FOR SELECT USING (
        (
            app_user_id() IS NOT NULL
            AND owner_user_id = app_user_id()
            AND deleted_at IS NULL
        )
        OR is_org_admin(org_id)
        OR EXISTS (
            SELECT 1
            FROM mentor_student_assignments msa
            WHERE msa.org_id = projects.org_id
              AND msa.student_user_id = projects.owner_user_id
              AND msa.mentor_user_id = app_user_id()
              AND msa.status = 'active'
              AND msa.deleted_at IS NULL
        )
    );

CREATE POLICY projects_system_select ON projects
    FOR SELECT USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

ALTER TABLE projects FORCE ROW LEVEL SECURITY;
