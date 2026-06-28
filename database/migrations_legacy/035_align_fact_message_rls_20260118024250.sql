-- 035) Align fact/message select policies with A-4 permissions
DROP POLICY IF EXISTS project_stage_assessments_select ON project_stage_assessments;
CREATE POLICY project_stage_assessments_select ON project_stage_assessments
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

DROP POLICY IF EXISTS project_reports_select ON project_reports;
CREATE POLICY project_reports_select ON project_reports
    FOR SELECT USING (can_view_project_facts(project_id, org_id));

DROP POLICY IF EXISTS project_question_instances_select ON project_question_instances;
CREATE POLICY project_question_instances_select ON project_question_instances
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

DROP POLICY IF EXISTS documents_select ON documents;
CREATE POLICY documents_select ON documents
    FOR SELECT USING (can_view_project_messages(project_id, org_id));

DROP POLICY IF EXISTS answer_evaluations_select ON answer_evaluations;
CREATE POLICY answer_evaluations_select ON answer_evaluations
    FOR SELECT USING (can_view_project_messages(project_id, org_id));
