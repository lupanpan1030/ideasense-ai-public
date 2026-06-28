-- 012) Allow org admins / platform admins to write question banks and prompts

-- Question bank versions (org admins for org scope, platform admins for all)
CREATE POLICY question_bank_versions_admin_insert ON question_bank_versions
    FOR INSERT WITH CHECK (is_org_admin(org_id));

CREATE POLICY question_bank_versions_admin_update ON question_bank_versions
    FOR UPDATE USING (is_org_admin(org_id))
    WITH CHECK (is_org_admin(org_id));

CREATE POLICY question_bank_versions_platform_insert ON question_bank_versions
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY question_bank_versions_platform_update ON question_bank_versions
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

-- Question bank questions (validate bank_version scope)
CREATE POLICY question_bank_questions_admin_insert ON question_bank_questions
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND qbv.org_id = app_org_id()
              AND is_org_admin(qbv.org_id)
        )
    );

CREATE POLICY question_bank_questions_admin_update ON question_bank_questions
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND qbv.org_id = app_org_id()
              AND is_org_admin(qbv.org_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM question_bank_versions qbv
            WHERE qbv.id = question_bank_questions.bank_version_id
              AND qbv.deleted_at IS NULL
              AND qbv.org_id = app_org_id()
              AND is_org_admin(qbv.org_id)
        )
    );

CREATE POLICY question_bank_questions_platform_insert ON question_bank_questions
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY question_bank_questions_platform_update ON question_bank_questions
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

-- Prompt templates (platform admins can manage any scope)
CREATE POLICY prompt_templates_platform_insert ON prompt_templates
    FOR INSERT WITH CHECK (is_platform_admin());

CREATE POLICY prompt_templates_platform_update ON prompt_templates
    FOR UPDATE USING (is_platform_admin())
    WITH CHECK (is_platform_admin());
