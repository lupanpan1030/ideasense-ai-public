-- 017) Fix recursive platform_admins policies (avoid is_platform_admin recursion)

DROP POLICY IF EXISTS platform_admins_platform_select ON platform_admins;
DROP POLICY IF EXISTS platform_admins_platform_insert ON platform_admins;
DROP POLICY IF EXISTS platform_admins_platform_update ON platform_admins;
