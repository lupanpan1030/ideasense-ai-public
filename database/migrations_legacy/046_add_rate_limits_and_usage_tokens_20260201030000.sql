-- 046) rate limits + LLM token usage + report usage buckets
ALTER TABLE llm_usage_buckets
    ADD COLUMN prompt_tokens INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN completion_tokens INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN total_tokens INTEGER NOT NULL DEFAULT 0;

CREATE TABLE rate_limit_buckets (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope          TEXT NOT NULL,
    key_hash       TEXT NOT NULL,
    window_seconds INTEGER NOT NULL,
    bucket_start   TIMESTAMPTZ NOT NULL,
    request_count  INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (scope = lower(btrim(scope))),
    CHECK (scope <> ''),
    CHECK (scope !~ '\s'),
    CHECK (key_hash <> ''),
    CHECK (window_seconds > 0)
);

CREATE UNIQUE INDEX rate_limit_buckets_unique
    ON rate_limit_buckets (scope, key_hash, window_seconds, bucket_start);

CREATE TABLE report_usage_buckets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_start TIMESTAMPTZ NOT NULL,
    report_count INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (report_count >= 0)
);

CREATE UNIQUE INDEX report_usage_buckets_unique
    ON report_usage_buckets (user_id, bucket_start);

CREATE INDEX report_usage_buckets_user_id_idx
    ON report_usage_buckets (user_id, bucket_start DESC);
