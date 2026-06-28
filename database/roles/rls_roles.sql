-- Runtime/worker roles must NOT be table owner and must NOT have BYPASSRLS.
-- Use a separate migration/owner role to run migrations.

CREATE ROLE app_runtime NOINHERIT;
CREATE ROLE app_worker NOINHERIT;
CREATE ROLE app_migrations NOINHERIT;

GRANT CONNECT ON DATABASE your_db_name TO app_runtime;
GRANT CONNECT ON DATABASE your_db_name TO app_worker;
GRANT USAGE ON SCHEMA public TO app_runtime;
GRANT USAGE ON SCHEMA public TO app_worker;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO app_runtime;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_worker;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO app_worker;

-- Minimal write grants for runtime API.
GRANT UPDATE, DELETE ON organizations TO app_runtime;

GRANT INSERT, UPDATE, DELETE ON organization_memberships TO app_runtime;
GRANT INSERT, UPDATE, DELETE ON organization_invitations TO app_runtime;
GRANT INSERT, UPDATE, DELETE ON cohorts TO app_runtime;
GRANT INSERT, UPDATE, DELETE ON cohort_memberships TO app_runtime;
GRANT INSERT, UPDATE, DELETE ON mentor_student_assignments TO app_runtime;

GRANT INSERT ON projects TO app_runtime;
GRANT UPDATE (title, description, settings, is_archived, archived_at, updated_at)
    ON projects TO app_runtime;

GRANT INSERT ON conversation_messages TO app_runtime;
GRANT INSERT, DELETE ON documents TO app_runtime;
GRANT INSERT ON project_comments TO app_runtime;
GRANT UPDATE ON notifications TO app_runtime;

GRANT INSERT ON idempotency_keys TO app_runtime;
GRANT UPDATE (response_ref) ON idempotency_keys TO app_runtime;

-- Minimal write grants for worker/system tasks.
GRANT INSERT, UPDATE ON project_runtime TO app_worker;
GRANT INSERT, UPDATE ON project_question_instances TO app_worker;
GRANT INSERT ON conversation_messages TO app_worker;
GRANT INSERT, UPDATE ON project_states TO app_worker;
GRANT INSERT ON project_state_events TO app_worker;
GRANT INSERT, UPDATE ON project_stage_assessments TO app_worker;
GRANT INSERT, UPDATE ON project_reports TO app_worker;
GRANT INSERT, UPDATE ON answer_evaluations TO app_worker;
GRANT INSERT, UPDATE ON message_evaluations TO app_worker;
GRANT INSERT, UPDATE ON background_jobs TO app_worker;
GRANT UPDATE (status, error_message, updated_at) ON documents TO app_worker;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_runtime;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_worker;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_worker;

-- Ensure the runtime role cannot bypass RLS.
ALTER ROLE app_runtime NOBYPASSRLS;
ALTER ROLE app_worker NOBYPASSRLS;
