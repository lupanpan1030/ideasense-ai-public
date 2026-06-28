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
