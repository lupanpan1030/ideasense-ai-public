-- 033) Tighten analytics/audit/background_jobs select policies
DROP POLICY IF EXISTS analytics_events_select ON analytics_events;
CREATE POLICY analytics_events_select ON analytics_events
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
        OR (
            project_id IS NOT NULL
            AND can_view_project(project_id, org_id)
        )
    );

DROP POLICY IF EXISTS audit_events_select ON audit_events;
CREATE POLICY audit_events_select ON audit_events
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
    );

DROP POLICY IF EXISTS background_jobs_select ON background_jobs;
CREATE POLICY background_jobs_select ON background_jobs
    FOR SELECT USING (
        app_actor_type() = 'system'
        OR is_org_admin(app_org_id())
        OR (
            project_id IS NOT NULL
            AND can_view_project(project_id, org_id)
        )
    );
