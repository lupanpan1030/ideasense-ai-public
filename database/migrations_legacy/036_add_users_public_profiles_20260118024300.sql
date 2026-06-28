-- 036) Add users_public_profiles for mentor-safe access
CREATE TABLE users_public_profiles (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

INSERT INTO users_public_profiles (user_id, display_name, created_at, updated_at, deleted_at)
SELECT id, display_name, created_at, updated_at, deleted_at
FROM users;

CREATE OR REPLACE FUNCTION sync_users_public_profiles()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM users_public_profiles WHERE user_id = OLD.id;
        RETURN OLD;
    END IF;

    INSERT INTO users_public_profiles (user_id, display_name, created_at, updated_at, deleted_at)
    VALUES (NEW.id, NEW.display_name, NEW.created_at, NEW.updated_at, NEW.deleted_at)
    ON CONFLICT (user_id) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        updated_at = EXCLUDED.updated_at,
        deleted_at = EXCLUDED.deleted_at;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_public_profiles_sync
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION sync_users_public_profiles();

ALTER TABLE users_public_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_public_profiles FORCE ROW LEVEL SECURITY;

CREATE POLICY users_public_profiles_self_select ON users_public_profiles
    FOR SELECT USING (user_id = app_user_id() AND deleted_at IS NULL);

CREATE POLICY users_public_profiles_admin_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND is_org_admin(app_org_id())
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_system_select ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND app_actor_type() = 'system'
        AND EXISTS (
            SELECT 1
            FROM organization_memberships om
            WHERE om.org_id = app_org_id()
              AND om.user_id = users_public_profiles.user_id
              AND om.status IN ('active','invited')
              AND om.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_mentor_select_assigned_students ON users_public_profiles
    FOR SELECT USING (
        deleted_at IS NULL
        AND EXISTS (
            SELECT 1
            FROM mentor_student_assignments msa
            WHERE msa.org_id = app_org_id()
              AND msa.mentor_user_id = app_user_id()
              AND msa.student_user_id = users_public_profiles.user_id
              AND msa.status IN ('pending','active')
              AND msa.deleted_at IS NULL
        )
    );

CREATE POLICY users_public_profiles_system_insert ON users_public_profiles
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY users_public_profiles_system_update ON users_public_profiles
    FOR UPDATE USING (
        app_actor_type() = 'system'
    )
    WITH CHECK (
        app_actor_type() = 'system'
    );

CREATE POLICY users_public_profiles_system_delete ON users_public_profiles
    FOR DELETE USING (
        app_actor_type() = 'system'
    );
