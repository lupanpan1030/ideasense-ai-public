-- 030) Ensure updated_at is maintained on updates
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER organizations_set_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER user_identities_set_updated_at
    BEFORE UPDATE ON user_identities
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organization_memberships_set_updated_at
    BEFORE UPDATE ON organization_memberships
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER organization_invitations_set_updated_at
    BEFORE UPDATE ON organization_invitations
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cohorts_set_updated_at
    BEFORE UPDATE ON cohorts
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cohort_memberships_set_updated_at
    BEFORE UPDATE ON cohort_memberships
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER mentor_student_assignments_set_updated_at
    BEFORE UPDATE ON mentor_student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER question_bank_versions_set_updated_at
    BEFORE UPDATE ON question_bank_versions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER question_bank_questions_set_updated_at
    BEFORE UPDATE ON question_bank_questions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER projects_set_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_runtime_set_updated_at
    BEFORE UPDATE ON project_runtime
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER prompt_templates_set_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_question_instances_set_updated_at
    BEFORE UPDATE ON project_question_instances
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_states_set_updated_at
    BEFORE UPDATE ON project_states
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER documents_set_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_stage_assessments_set_updated_at
    BEFORE UPDATE ON project_stage_assessments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_reports_set_updated_at
    BEFORE UPDATE ON project_reports
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER project_comments_set_updated_at
    BEFORE UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER evaluation_rubrics_set_updated_at
    BEFORE UPDATE ON evaluation_rubrics
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER background_jobs_set_updated_at
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
