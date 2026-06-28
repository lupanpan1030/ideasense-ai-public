-- 017) analytics_events
CREATE TABLE analytics_events (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id        UUID NOT NULL,
    project_id    UUID NULL REFERENCES projects(id) ON DELETE SET NULL,
    actor_user_id UUID NULL REFERENCES users(id),
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX analytics_events_org_created_idx
    ON analytics_events (org_id, created_at DESC);

CREATE INDEX analytics_events_project_created_idx
    ON analytics_events (project_id, created_at DESC);

CREATE INDEX analytics_events_org_type_created_idx
    ON analytics_events (org_id, event_type, created_at DESC);
