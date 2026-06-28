-- 005) password reset tokens
CREATE TABLE password_reset_tokens (
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

CREATE UNIQUE INDEX password_reset_tokens_token_hash_unique
    ON password_reset_tokens (token_hash);

CREATE INDEX password_reset_tokens_user_id_idx
    ON password_reset_tokens (user_id)
    WHERE consumed_at IS NULL;
