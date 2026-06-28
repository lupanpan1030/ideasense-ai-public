-- Allow system actor to update background_jobs without org context for locking.
-- We still require org context for WITH CHECK to keep updates scoped.

DROP POLICY IF EXISTS background_jobs_system_update ON background_jobs;
CREATE POLICY background_jobs_system_update ON background_jobs
    FOR UPDATE USING (
        app_actor_type() = 'system'
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );
