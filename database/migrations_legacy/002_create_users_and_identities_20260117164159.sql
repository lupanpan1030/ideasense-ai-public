-- 002) users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL,
    display_name    TEXT,
    primary_org_id  UUID NULL REFERENCES organizations(id) ON DELETE SET NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    CHECK (email = btrim(email)),
    CHECK (email !~ '\s')
);

CREATE UNIQUE INDEX users_email_unique
    ON users (email)
    WHERE deleted_at IS NULL;

-- 002) user_identities
CREATE TABLE user_identities (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    provider_subject  TEXT NULL,
    email             CITEXT NULL,
    password_hash     TEXT NULL,
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    CHECK (provider IN ('local','clerk','nextauth','sso')),
    CHECK (status IN ('active','disabled')),
    CHECK (provider = 'local' OR provider_subject IS NOT NULL),
    CHECK (provider <> 'local' OR password_hash IS NOT NULL),
    CHECK (email IS NULL OR (email = btrim(email) AND email !~ '\s'))
);

CREATE UNIQUE INDEX user_identities_provider_subject_unique
    ON user_identities (provider, provider_subject)
    WHERE deleted_at IS NULL;
