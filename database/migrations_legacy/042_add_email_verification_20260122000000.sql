-- 042) email verification + usage buckets
ALTER TABLE users
    ADD COLUMN email_verified_at TIMESTAMPTZ;

CREATE TABLE email_verification_tokens (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email         CITEXT NOT NULL,
    token_hash    TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed_at   TIMESTAMPTZ,
    CHECK (email = btrim(email)),
    CHECK (email !~ '\s')
);

CREATE UNIQUE INDEX email_verification_tokens_token_hash_unique
    ON email_verification_tokens (token_hash);

CREATE INDEX email_verification_tokens_user_id_idx
    ON email_verification_tokens (user_id)
    WHERE consumed_at IS NULL;

CREATE TABLE llm_usage_buckets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_type   TEXT NOT NULL,
    bucket_start  TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (bucket_type IN ('minute', 'day'))
);

CREATE UNIQUE INDEX llm_usage_buckets_unique
    ON llm_usage_buckets (user_id, bucket_type, bucket_start);
