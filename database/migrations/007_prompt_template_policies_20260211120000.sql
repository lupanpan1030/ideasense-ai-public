-- 007) Allow org admins and system actors to write prompt templates

CREATE POLICY prompt_templates_admin_insert ON prompt_templates
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY prompt_templates_admin_update ON prompt_templates
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY prompt_templates_system_insert ON prompt_templates
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id IS NULL
    );

CREATE POLICY prompt_templates_system_update ON prompt_templates
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id IS NULL
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id IS NULL
    );
