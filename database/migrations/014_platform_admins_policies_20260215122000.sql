-- 014) Allow platform admins to manage platform_admins

CREATE POLICY platform_admins_platform_select ON platform_admins
    FOR SELECT USING (is_platform_admin());

CREATE POLICY platform_admins_platform_insert ON platform_admins
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY platform_admins_platform_update ON platform_admins
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());
