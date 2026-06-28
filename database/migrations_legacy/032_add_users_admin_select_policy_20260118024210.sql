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
