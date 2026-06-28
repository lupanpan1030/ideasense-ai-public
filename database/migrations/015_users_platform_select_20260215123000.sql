-- 015) Allow platform admins to select users across orgs

CREATE POLICY users_platform_select ON users
    FOR SELECT USING (
        users.deleted_at IS NULL
        AND is_platform_admin()
    );
