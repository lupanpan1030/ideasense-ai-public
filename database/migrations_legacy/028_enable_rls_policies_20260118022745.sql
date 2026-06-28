-- 028) Row Level Security policies
-- NOTE: Policies assume the app sets these session variables:
--   app.user_id, app.org_id, app.actor_type

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohort_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_student_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_stage_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_runtime ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_question_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_state_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_stage_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_rubrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE answer_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE cohorts FORCE ROW LEVEL SECURITY;
ALTER TABLE cohort_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE mentor_student_assignments FORCE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE user_identities FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_stage_variants FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions FORCE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
ALTER TABLE project_runtime FORCE ROW LEVEL SECURITY;
ALTER TABLE project_question_instances FORCE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE project_states FORCE ROW LEVEL SECURITY;
ALTER TABLE project_state_events FORCE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates FORCE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_events FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
ALTER TABLE project_stage_assessments FORCE ROW LEVEL SECURITY;
ALTER TABLE project_reports FORCE ROW LEVEL SECURITY;
ALTER TABLE project_comments FORCE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
ALTER TABLE evaluation_rubrics FORCE ROW LEVEL SECURITY;
ALTER TABLE answer_evaluations FORCE ROW LEVEL SECURITY;
ALTER TABLE message_evaluations FORCE ROW LEVEL SECURITY;
ALTER TABLE background_jobs FORCE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION app_user_id()
RETURNS uuid AS $$
BEGIN
    RETURN NULLIF(current_setting('app.user_id', true), '')::uuid;
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION app_org_id()
RETURNS uuid AS $$
BEGIN
    RETURN NULLIF(current_setting('app.org_id', true), '')::uuid;
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION app_actor_type()
RETURNS text AS $$
BEGIN
    RETURN NULLIF(current_setting('app.actor_type', true), '');
EXCEPTION WHEN others THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION has_org_membership(target_org uuid)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = target_org
          AND om.user_id = app_user_id()
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_org_admin(target_org uuid)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = target_org
          AND om.user_id = app_user_id()
          AND om.status = 'active'
          AND om.org_role IN ('owner','admin')
          AND om.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF app_user_id() IS NULL THEN
        RETURN FALSE;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project_messages(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_view_messages = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_view_project_facts(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_view_facts = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION can_comment_on_project(target_project uuid, target_org uuid)
RETURNS boolean AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM projects p
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND p.owner_user_id = app_user_id()
          AND p.deleted_at IS NULL
    ) THEN
        RETURN TRUE;
    END IF;

    IF is_org_admin(target_org) THEN
        RETURN TRUE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM mentor_student_assignments msa
        JOIN projects p ON p.owner_user_id = msa.student_user_id
        WHERE p.id = target_project
          AND p.org_id = target_org
          AND msa.org_id = target_org
          AND msa.mentor_user_id = app_user_id()
          AND msa.status = 'active'
          AND msa.can_comment = true
          AND msa.deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Basic org-scoped tables: allow access if org_id matches app.org_id
CREATE POLICY org_scoped_select ON organizations
    FOR SELECT USING (id = app_org_id());

CREATE POLICY org_scoped_select ON organization_memberships
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON organization_invitations
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON cohorts
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON cohort_memberships
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY org_scoped_select ON users
    FOR SELECT USING (id = app_user_id());

CREATE POLICY org_scoped_select ON user_identities
    FOR SELECT USING (user_id = app_user_id());

CREATE POLICY question_bank_select ON question_bank_versions
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY question_bank_select ON question_bank_stage_variants
    FOR SELECT USING (true);

CREATE POLICY question_bank_select ON question_bank_questions
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND (qbv.org_id IS NULL OR qbv.org_id = app_org_id())
        )
    );

CREATE POLICY projects_select ON projects
    FOR SELECT USING (can_view_project(id, org_id));

CREATE POLICY project_runtime_select ON project_runtime
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_question_instances_select ON project_question_instances
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY conversation_messages_select ON conversation_messages
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

CREATE POLICY project_states_select ON project_states
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY project_state_events_select ON project_state_events
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

CREATE POLICY prompt_templates_select ON prompt_templates
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY documents_select ON documents
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY analytics_events_select ON analytics_events
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY audit_events_select ON audit_events
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY project_stage_assessments_select ON project_stage_assessments
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_reports_select ON project_reports
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY project_comments_select ON project_comments
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY notifications_select ON notifications
    FOR SELECT USING (recipient_user_id = app_user_id());

CREATE POLICY evaluation_rubrics_select ON evaluation_rubrics
    FOR SELECT USING (org_id IS NULL OR org_id = app_org_id());

CREATE POLICY answer_evaluations_select ON answer_evaluations
    FOR SELECT USING (can_view_project(project_id, org_id));

CREATE POLICY message_evaluations_select ON message_evaluations
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

CREATE POLICY background_jobs_select ON background_jobs
    FOR SELECT USING (org_id = app_org_id());

CREATE POLICY idempotency_keys_select ON idempotency_keys
    FOR SELECT USING (org_id = app_org_id() AND user_id = app_user_id());

-- Writes: default deny, with narrow allowances for comments and notifications.
CREATE POLICY project_runtime_system_insert ON project_runtime
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_runtime_system_update ON project_runtime
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_question_instances_system_insert ON project_question_instances
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_question_instances_system_update ON project_question_instances
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY conversation_messages_system_insert ON conversation_messages
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
        AND role <> 'user'
    );

CREATE POLICY project_states_system_insert ON project_states
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_states_system_update ON project_states
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_state_events_system_insert ON project_state_events
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_assessments_system_insert ON project_stage_assessments
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_stage_assessments_system_update ON project_stage_assessments
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_reports_system_insert ON project_reports
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY project_reports_system_update ON project_reports
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY answer_evaluations_system_insert ON answer_evaluations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY answer_evaluations_system_update ON answer_evaluations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY message_evaluations_system_insert ON message_evaluations
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY message_evaluations_system_update ON message_evaluations
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY background_jobs_system_insert ON background_jobs
    FOR INSERT WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY background_jobs_system_update ON background_jobs
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY organizations_update_admin ON organizations
    FOR UPDATE USING (is_org_admin(id))
    WITH CHECK (is_org_admin(id));

CREATE POLICY organizations_delete_admin ON organizations
    FOR DELETE USING (is_org_admin(id));

CREATE POLICY organization_memberships_admin_write ON organization_memberships
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_memberships_admin_update ON organization_memberships
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_memberships_admin_delete ON organization_memberships
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_write ON organization_invitations
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_update ON organization_invitations
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY organization_invitations_admin_delete ON organization_invitations
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY cohorts_admin_write ON cohorts
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohorts_admin_update ON cohorts
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohorts_admin_delete ON cohorts
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_write ON cohort_memberships
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_update ON cohort_memberships
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY cohort_memberships_admin_delete ON cohort_memberships
    FOR DELETE USING (is_org_admin(org_id));

CREATE POLICY projects_insert_owner_or_admin ON projects
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id))
    );

CREATE POLICY projects_update_owner_or_admin ON projects
    FOR UPDATE USING (org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id)))
    WITH CHECK (org_id = app_org_id()
        AND (owner_user_id = app_user_id() OR is_org_admin(org_id)));

CREATE POLICY conversation_messages_insert_owner ON conversation_messages
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND role = 'user'
        AND author_user_id = app_user_id()
        AND EXISTS (
            SELECT 1
            FROM projects p
            WHERE p.id = project_id
              AND p.org_id = org_id
              AND p.owner_user_id = app_user_id()
              AND p.deleted_at IS NULL
        )
    );

CREATE POLICY documents_insert_owner_or_admin ON documents
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND (
            is_org_admin(org_id)
            OR EXISTS (
                SELECT 1
                FROM projects p
                WHERE p.id = project_id
                  AND p.org_id = org_id
                  AND p.owner_user_id = app_user_id()
                  AND p.deleted_at IS NULL
            )
        )
    );

CREATE POLICY documents_system_update ON documents
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
    );

CREATE POLICY documents_delete_owner_or_admin ON documents
    FOR DELETE USING (
        org_id = app_org_id()
        AND (
            is_org_admin(org_id)
            OR EXISTS (
                SELECT 1
                FROM projects p
                WHERE p.id = project_id
                  AND p.org_id = org_id
                  AND p.owner_user_id = app_user_id()
                  AND p.deleted_at IS NULL
            )
        )
    );

CREATE POLICY idempotency_keys_insert_owner ON idempotency_keys
    FOR INSERT WITH CHECK (
        org_id = app_org_id()
        AND user_id = app_user_id()
    );

CREATE POLICY idempotency_keys_update_owner ON idempotency_keys
    FOR UPDATE USING (
        org_id = app_org_id()
        AND user_id = app_user_id()
    )
    WITH CHECK (
        org_id = app_org_id()
        AND user_id = app_user_id()
    );

CREATE POLICY project_comments_insert ON project_comments
    FOR INSERT WITH CHECK (can_comment_on_project(project_id, org_id)
        AND author_user_id = app_user_id());

CREATE POLICY notifications_update ON notifications
    FOR UPDATE USING (recipient_user_id = app_user_id())
    WITH CHECK (recipient_user_id = app_user_id());
