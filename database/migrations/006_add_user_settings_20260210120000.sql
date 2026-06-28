-- 006) user settings
CREATE TABLE user_settings (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN NOT NULL DEFAULT true,
    weekly_summary      BOOLEAN NOT NULL DEFAULT true,
    time_zone           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (time_zone IS NULL OR time_zone = btrim(time_zone)),
    CHECK (time_zone IS NULL OR time_zone <> '')
);

CREATE TRIGGER user_settings_set_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings FORCE ROW LEVEL SECURITY;

CREATE POLICY user_settings_self_select ON user_settings
    FOR SELECT USING (user_id = app_user_id());

CREATE POLICY user_settings_self_insert ON user_settings
    FOR INSERT WITH CHECK (user_id = app_user_id());

CREATE POLICY user_settings_self_update ON user_settings
    FOR UPDATE USING (user_id = app_user_id())
    WITH CHECK (user_id = app_user_id());

CREATE POLICY user_settings_system_select ON user_settings
    FOR SELECT USING (app_actor_type() = 'system');

CREATE POLICY user_settings_system_insert ON user_settings
    FOR INSERT WITH CHECK (app_actor_type() = 'system');

CREATE POLICY user_settings_system_update ON user_settings
    FOR UPDATE USING (app_actor_type() = 'system')
    WITH CHECK (app_actor_type() = 'system');
