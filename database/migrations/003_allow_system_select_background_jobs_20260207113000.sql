-- Allow system actor to select background jobs without org context.
-- This lets the worker claim jobs before it knows org_id.

DROP POLICY IF EXISTS background_jobs_select ON background_jobs;
CREATE POLICY background_jobs_select ON background_jobs
    FOR SELECT USING (
        org_id = app_org_id()
        OR app_actor_type() = 'system'
    );
