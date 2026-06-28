-- 027) idempotency_keys
CREATE TABLE idempotency_keys (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    user_id       UUID NOT NULL REFERENCES users(id),
    scope         TEXT NOT NULL,
    key           TEXT NOT NULL,
    request_hash  TEXT NULL,
    response_ref  JSONB NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NULL,
    deleted_at    TIMESTAMPTZ NULL,
    CHECK (scope = lower(btrim(scope))),
    CHECK (scope <> ''),
    CHECK (scope !~ '\s'),
    CHECK (key = btrim(key)),
    CHECK (key <> ''),
    CHECK (key ~ '^[A-Za-z0-9_.:-]+$'),
    CHECK (expires_at IS NULL OR expires_at > created_at)
);

CREATE UNIQUE INDEX idempotency_keys_unique
    ON idempotency_keys (org_id, scope, key)
    WHERE deleted_at IS NULL;

CREATE INDEX idempotency_keys_user_created_idx
    ON idempotency_keys (user_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_idempotency_key_consistency()
RETURNS trigger AS $$
BEGIN
    IF OLD.request_hash IS NOT NULL
        AND NEW.request_hash IS DISTINCT FROM OLD.request_hash THEN
        RAISE EXCEPTION 'request_hash mismatch for idempotency key %', OLD.id
            USING ERRCODE = '23514';
    END IF;

    IF OLD.response_ref IS NOT NULL
        AND NEW.response_ref IS DISTINCT FROM OLD.response_ref THEN
        RAISE EXCEPTION 'response_ref already set for idempotency key %', OLD.id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER idempotency_keys_consistency_guard
    BEFORE UPDATE ON idempotency_keys
    FOR EACH ROW
    EXECUTE FUNCTION enforce_idempotency_key_consistency();
