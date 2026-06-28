-- 006) question_bank_versions
CREATE TABLE question_bank_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope_org_id    UUID GENERATED ALWAYS AS (
        COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid)
    ) STORED NOT NULL,
    bank_key        TEXT NOT NULL,
    version         TEXT NOT NULL,
    source          TEXT NULL,
    raw_yaml         TEXT NULL,
    raw_json        JSONB NULL,
    content_hash    TEXT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    activated_at    TIMESTAMPTZ NULL,
    deactivated_at  TIMESTAMPTZ NULL,
    CHECK (bank_key = lower(btrim(bank_key))),
    CHECK (bank_key <> ''),
    CHECK (bank_key !~ '\s'),
    CHECK (version = btrim(version)),
    CHECK (version <> ''),
    CHECK (NOT is_active OR (activated_at IS NOT NULL AND deactivated_at IS NULL))
);

CREATE UNIQUE INDEX question_bank_versions_scope_key_version_unique
    ON question_bank_versions (scope_org_id, bank_key, version)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_versions_scope_key_active_unique
    ON question_bank_versions (scope_org_id, bank_key)
    WHERE is_active AND deleted_at IS NULL;

CREATE UNIQUE INDEX question_bank_versions_scope_content_hash_unique
    ON question_bank_versions (scope_org_id, content_hash)
    WHERE content_hash IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX question_bank_versions_scope_key_idx
    ON question_bank_versions (scope_org_id, bank_key);

CREATE OR REPLACE FUNCTION set_question_bank_version_activation()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.is_active THEN
            NEW.activated_at := COALESCE(NEW.activated_at, now());
            NEW.deactivated_at := NULL;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.is_active AND NOT OLD.is_active THEN
        NEW.activated_at := COALESCE(NEW.activated_at, now());
        NEW.deactivated_at := NULL;
    ELSIF NOT NEW.is_active AND OLD.is_active THEN
        NEW.deactivated_at := COALESCE(NEW.deactivated_at, now());
    ELSIF NEW.is_active THEN
        NEW.activated_at := COALESCE(NEW.activated_at, now());
        NEW.deactivated_at := NULL;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER question_bank_versions_activation_guard
    BEFORE INSERT OR UPDATE ON question_bank_versions
    FOR EACH ROW
    EXECUTE FUNCTION set_question_bank_version_activation();
