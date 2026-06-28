-- 013) Platform admins can manage orgs and memberships across orgs

CREATE POLICY organizations_platform_select ON organizations
    FOR SELECT USING (is_platform_admin());

CREATE POLICY organizations_platform_insert ON organizations
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY organizations_platform_update ON organizations
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

CREATE POLICY organizations_platform_delete ON organizations
    FOR DELETE USING (is_platform_admin());

CREATE POLICY organization_memberships_platform_select ON organization_memberships
    FOR SELECT USING (is_platform_admin());

CREATE POLICY organization_memberships_platform_insert ON organization_memberships
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY organization_memberships_platform_update ON organization_memberships
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

CREATE POLICY organization_memberships_platform_delete ON organization_memberships
    FOR DELETE USING (is_platform_admin());

CREATE POLICY organization_invitations_platform_select ON organization_invitations
    FOR SELECT USING (is_platform_admin());

CREATE POLICY organization_invitations_platform_insert ON organization_invitations
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY organization_invitations_platform_update ON organization_invitations
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

CREATE POLICY organization_invitations_platform_delete ON organization_invitations
    FOR DELETE USING (is_platform_admin());
