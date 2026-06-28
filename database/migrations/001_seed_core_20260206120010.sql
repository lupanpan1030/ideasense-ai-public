-- 001) Seed core lookup data
ALTER TABLE evaluation_rubrics NO FORCE ROW LEVEL SECURITY;
SET row_security = off;

INSERT INTO evaluation_rubrics (
    id,
    org_id,
    rubric_key,
    rubric_version,
    scope,
    definition_json,
    is_active
)
VALUES
    (
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        NULL,
        'default',
        'v1',
        'answer',
        '{"dimensions":["clarity","completeness","evidence"],"scale":"0-1"}'::jsonb,
        true
    ),
    (
        'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
        NULL,
        'default',
        'v1',
        'message',
        '{"dimensions":["tone","helpfulness","specificity"],"scale":"0-1"}'::jsonb,
        true
    )
ON CONFLICT (id) DO NOTHING;

RESET row_security;
ALTER TABLE evaluation_rubrics FORCE ROW LEVEL SECURITY;
