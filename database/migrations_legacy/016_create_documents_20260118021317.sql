-- 016) documents
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL,
    project_id   UUID NOT NULL,
    file_name    TEXT NOT NULL,
    content_type TEXT NULL,
    storage_key  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'uploaded',
    error_message TEXT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    meta         JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (status IN ('uploaded','extracting','extracted','chunked','embedded','indexed','failed')),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX documents_storage_key_unique
    ON documents (org_id, storage_key)
    WHERE deleted_at IS NULL;

CREATE INDEX documents_project_status_idx
    ON documents (project_id, status)
    WHERE deleted_at IS NULL;
