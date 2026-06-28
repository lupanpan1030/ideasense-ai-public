-- 029) Fix evaluation_rubrics uniqueness to include scope
DROP INDEX IF EXISTS evaluation_rubrics_unique;

CREATE UNIQUE INDEX evaluation_rubrics_unique
    ON evaluation_rubrics (scope_org_id, scope, rubric_key, rubric_version)
    WHERE deleted_at IS NULL;
