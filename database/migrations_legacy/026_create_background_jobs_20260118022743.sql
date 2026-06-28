-- 026) background_jobs
CREATE TABLE background_jobs (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id           UUID NOT NULL,
    project_id       UUID NULL,
    job_type         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'queued',
    priority         INT NOT NULL DEFAULT 100,
    payload          JSONB NOT NULL,
    idempotency_key  TEXT NULL,
    attempts         INT NOT NULL DEFAULT 0,
    max_attempts     INT NOT NULL DEFAULT 5,
    run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at        TIMESTAMPTZ NULL,
    lock_expires_at  TIMESTAMPTZ NULL,
    locked_by        TEXT NULL,
    started_at       TIMESTAMPTZ NULL,
    completed_at     TIMESTAMPTZ NULL,
    last_error       TEXT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ NULL,
    CHECK (job_type = lower(btrim(job_type))),
    CHECK (job_type <> ''),
    CHECK (job_type ~ '^[a-z0-9_.-]+$'),
    CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
    CHECK (priority >= 0),
    CHECK (attempts >= 0),
    CHECK (max_attempts >= 0),
    CHECK (
        (locked_at IS NULL AND locked_by IS NULL AND lock_expires_at IS NULL)
        OR (locked_at IS NOT NULL AND locked_by IS NOT NULL AND lock_expires_at IS NOT NULL)
    ),
    CHECK (
        status <> 'running'
        OR (started_at IS NOT NULL AND completed_at IS NULL)
    ),
    CHECK (
        status IN ('succeeded','failed','cancelled')
        OR completed_at IS NULL
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX background_jobs_idempotency_unique
    ON background_jobs (org_id, job_type, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX background_jobs_queue_idx
    ON background_jobs (status, run_at, priority)
    WHERE deleted_at IS NULL;

CREATE INDEX background_jobs_locked_idx
    ON background_jobs (locked_at)
    WHERE deleted_at IS NULL;

CREATE INDEX background_jobs_project_created_idx
    ON background_jobs (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION set_background_job_timestamps()
RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'running' AND NEW.started_at IS NULL THEN
        NEW.started_at := now();
        NEW.completed_at := NULL;
    ELSIF NEW.status IN ('succeeded','failed','cancelled') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, now());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER background_jobs_timestamps_guard
    BEFORE INSERT OR UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION set_background_job_timestamps();
