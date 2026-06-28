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
