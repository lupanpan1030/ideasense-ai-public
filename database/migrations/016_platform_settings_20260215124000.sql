-- 016) Platform settings (global configuration)

CREATE TABLE platform_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (key = btrim(key)),
    CHECK (key <> '')
);

ALTER TABLE platform_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_settings FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_settings_select ON platform_settings
    FOR SELECT USING (is_platform_admin());

CREATE POLICY platform_settings_insert ON platform_settings
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY platform_settings_update ON platform_settings
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

CREATE TRIGGER platform_settings_set_updated_at
    BEFORE UPDATE ON platform_settings
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
