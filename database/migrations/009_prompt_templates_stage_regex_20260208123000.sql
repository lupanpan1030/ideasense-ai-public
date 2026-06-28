-- 009) Fix prompt template stage list regex (Postgres-compatible whitespace)

ALTER TABLE prompt_templates
    DROP CONSTRAINT IF EXISTS prompt_templates_stage_check;

ALTER TABLE prompt_templates
    ADD CONSTRAINT prompt_templates_stage_check
    CHECK (
        stage IS NULL
        OR stage ~ '^(problem|market|tech|report)([[:space:]]*,[[:space:]]*(problem|market|tech|report))*$'
    );
