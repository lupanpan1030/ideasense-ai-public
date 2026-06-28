-- 040) Allow org admins to add project comments
DROP POLICY IF EXISTS project_comments_admin_insert ON project_comments;
CREATE POLICY project_comments_admin_insert ON project_comments
    FOR INSERT WITH CHECK (
        is_org_admin(org_id)
        AND author_user_id = app_user_id()
    );
