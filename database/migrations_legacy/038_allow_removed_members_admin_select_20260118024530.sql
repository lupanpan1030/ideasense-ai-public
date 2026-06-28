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
