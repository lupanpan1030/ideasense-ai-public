-- 022) notifications
CREATE TABLE notifications (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id            UUID NOT NULL,
    recipient_user_id UUID NOT NULL REFERENCES users(id),
    type              TEXT NOT NULL,
    title             TEXT NULL,
    body              TEXT NULL,
    link              TEXT NULL,
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at           TIMESTAMPTZ NULL,
    deleted_at        TIMESTAMPTZ NULL,
    CHECK (type = lower(btrim(type))),
    CHECK (type <> ''),
    CHECK (type ~ '^[a-z0-9_.-]+$'),
    CHECK (link IS NULL OR length(link) <= 2000)
);

CREATE INDEX notifications_recipient_unread_idx
    ON notifications (recipient_user_id, read_at, created_at DESC)
    WHERE deleted_at IS NULL;
