-- 018) audit_events
CREATE TABLE audit_events (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    actor_user_id UUID NULL REFERENCES users(id),
    actor_type    TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    target_type   TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (actor_type IN ('user','system'))
);

CREATE INDEX audit_events_org_created_idx
    ON audit_events (org_id, created_at DESC);

CREATE INDEX audit_events_org_type_created_idx
    ON audit_events (org_id, event_type, created_at DESC);

CREATE INDEX audit_events_org_target_idx
    ON audit_events (org_id, target_type, target_id, created_at DESC);

CREATE INDEX audit_events_org_actor_idx
    ON audit_events (org_id, actor_user_id, created_at DESC);
