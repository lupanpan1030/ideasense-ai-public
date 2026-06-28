-- 010) Platform admins (global operators)

CREATE TABLE platform_admins (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'admin',
    status      TEXT NOT NULL DEFAULT 'active',
    created_by  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CHECK (role IN ('admin','superadmin')),
    CHECK (status IN ('active','disabled'))
);

CREATE UNIQUE INDEX platform_admins_user_unique
    ON platform_admins (user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX platform_admins_status_idx
    ON platform_admins (status)
    WHERE deleted_at IS NULL;

ALTER TABLE platform_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_admins FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_admins_self_select ON platform_admins
    FOR SELECT USING (user_id = app_user_id());

CREATE POLICY platform_admins_system_select ON platform_admins
    FOR SELECT USING (app_actor_type() = 'system');

CREATE POLICY platform_admins_system_insert ON platform_admins
    FOR INSERT WITH CHECK (app_actor_type() = 'system');

CREATE POLICY platform_admins_system_update ON platform_admins
    FOR UPDATE USING (app_actor_type() = 'system')
    WITH CHECK (app_actor_type() = 'system');

CREATE TRIGGER platform_admins_set_updated_at
    BEFORE UPDATE ON platform_admins
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION is_platform_admin()
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM platform_admins pa
        WHERE pa.user_id = app_user_id()
          AND pa.status = 'active'
          AND pa.deleted_at IS NULL
    );
END;
$$;
