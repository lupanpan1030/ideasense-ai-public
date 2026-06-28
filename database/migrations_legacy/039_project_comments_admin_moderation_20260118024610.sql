-- 039) Allow org admins to moderate project comments
DROP POLICY IF EXISTS project_comments_admin_update ON project_comments;
CREATE POLICY project_comments_admin_update ON project_comments
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

DROP POLICY IF EXISTS project_comments_admin_delete ON project_comments;
CREATE POLICY project_comments_admin_delete ON project_comments
    FOR DELETE USING (is_org_admin(org_id));
