-- 008) Allow multiple stage labels on prompt templates

ALTER TABLE prompt_templates
    DROP CONSTRAINT IF EXISTS prompt_templates_stage_check;

ALTER TABLE prompt_templates
    ADD CONSTRAINT prompt_templates_stage_check
    CHECK (
        stage IS NULL
        OR stage ~ '^(problem|market|tech|report)(\\s*,\\s*(problem|market|tech|report))*$'
    );
