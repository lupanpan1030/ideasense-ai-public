-- Projects, runtime, and question instances.
WITH bank AS (
    SELECT id AS bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1
)
INSERT INTO projects (
    id,
    org_id,
    cohort_id,
    owner_user_id,
    title,
    description,
    question_bank_version_id,
    current_stage,
    current_variant,
    stage_status,
    settings
)
SELECT
    '11111111-2222-3333-4444-555555555555'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '22222222-2222-2222-2222-222222222222'::uuid,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    'Problem Discovery - Student 1',
    'Seed project for student 1.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '66666666-7777-8888-9999-aaaaaaaaaaaa'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '22222222-2222-2222-2222-222222222222'::uuid,
    'dddddddd-dddd-dddd-dddd-dddddddddddd'::uuid,
    'Market Discovery - Student 2',
    'Seed project for student 2.',
    bank.bank_id,
    'market',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '77777777-7777-7777-7777-777777777777'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '33333333-2222-2222-2222-222222222222'::uuid,
    '33333333-4444-4444-4444-444444444444'::uuid,
    'Problem Discovery - Student 3',
    'Second cohort problem exploration.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '88888888-8888-8888-8888-888888888888'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '33333333-2222-2222-2222-222222222222'::uuid,
    '44444444-5555-5555-5555-555555555555'::uuid,
    'Market Discovery - Student 4',
    'Second cohort market positioning.',
    bank.bank_id,
    'market',
    'default',
    'awaiting_confirm',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '99999999-9999-9999-9999-999999999998'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '22222222-2222-2222-2222-222222222222'::uuid,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    'Tech Discovery - Student 1',
    'Router question for tech track.',
    bank.bank_id,
    'tech',
    'router',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    '44444444-2222-2222-2222-222222222222'::uuid,
    '77777777-8888-8888-8888-888888888888'::uuid,
    'Problem Discovery - Student 5',
    'Org2 pilot project.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '12121212-2222-3333-4444-555555555556'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '55555555-2222-2222-2222-222222222222'::uuid,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    'Winter 2026 - Student 1',
    'Winter cohort project for Student 1.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '13131313-2222-3333-4444-555555555557'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '55555555-2222-2222-2222-222222222222'::uuid,
    '33333333-4444-4444-4444-444444444444'::uuid,
    'Winter 2026 - Student 3',
    'Market validation for Winter cohort.',
    bank.bank_id,
    'market',
    'default',
    'awaiting_confirm',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '14141414-2222-3333-4444-555555555558'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '66666666-2222-2222-2222-222222222222'::uuid,
    '44444444-5555-5555-5555-555555555555'::uuid,
    'Summer 2027 - Student 4',
    'Summer cohort problem framing.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '15151515-2222-3333-4444-555555555559'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    '77777777-2222-2222-2222-222222222222'::uuid,
    '77777777-8888-8888-8888-888888888888'::uuid,
    'Labs Beta - Student 5',
    'Tech exploration for Labs Beta.',
    bank.bank_id,
    'tech',
    'router',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '16161616-2222-3333-4444-555555555560'::uuid,
    '44444444-4444-4444-4444-444444444444'::uuid,
    '88888888-2222-2222-2222-222222222222'::uuid,
    '44444444-dddd-dddd-dddd-dddddddddddd'::uuid,
    'Northwind Cohort 1 - Student',
    'Initial cohort project for Northwind.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '17171717-2222-3333-4444-555555555561'::uuid,
    '55555555-5555-5555-5555-555555555555'::uuid,
    'aaaaaaaa-2222-2222-2222-222222222222'::uuid,
    '55555555-dddd-dddd-dddd-dddddddddddd'::uuid,
    'Nimbus Launchpad - Student',
    'GTM hypothesis testing.',
    bank.bank_id,
    'market',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '18181818-2222-3333-4444-555555555562'::uuid,
    '66666666-6666-6666-6666-666666666666'::uuid,
    'bbbbbbbb-2222-2222-2222-222222222222'::uuid,
    '66666666-cccc-cccc-cccc-cccccccccccc'::uuid,
    'Aurora Pilot - Student',
    'Pilot cohort discovery work.',
    bank.bank_id,
    'problem',
    'default',
    'awaiting_confirm',
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '19191919-2222-3333-4444-555555555563'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    'cccccccc-2222-2222-2222-222222222222'::uuid,
    '77777777-cccc-cccc-cccc-cccccccccccc'::uuid,
    'Cedar Spring - Student',
    'Early validation interviews.',
    bank.bank_id,
    'problem',
    'default',
    'in_progress',
    '{}'::jsonb
FROM bank
ON CONFLICT (id) DO NOTHING;

WITH bank AS (
    SELECT id AS bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1
),
problem_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'problem'
       AND variant = 'default'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
),
market_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'market'
       AND variant = 'default'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
),
tech_router_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'tech'
       AND variant = 'router'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
)
INSERT INTO project_runtime (
    project_id,
    org_id,
    stage,
    variant,
    current_question_bank_question_id,
    next_question_bank_question_id
)
SELECT
    '11111111-2222-3333-4444-555555555555'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '66666666-7777-8888-9999-aaaaaaaaaaaa'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'market',
    'default',
    (SELECT id FROM market_q1),
    NULL::uuid
UNION ALL
SELECT
    '77777777-7777-7777-7777-777777777777'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '88888888-8888-8888-8888-888888888888'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'market',
    'default',
    (SELECT id FROM market_q1),
    NULL::uuid
UNION ALL
SELECT
    '99999999-9999-9999-9999-999999999998'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'tech',
    'router',
    (SELECT id FROM tech_router_q1),
    NULL::uuid
UNION ALL
SELECT
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '12121212-2222-3333-4444-555555555556'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '13131313-2222-3333-4444-555555555557'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'market',
    'default',
    (SELECT id FROM market_q1),
    NULL::uuid
UNION ALL
SELECT
    '14141414-2222-3333-4444-555555555558'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '15151515-2222-3333-4444-555555555559'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    'tech',
    'router',
    (SELECT id FROM tech_router_q1),
    NULL::uuid
UNION ALL
SELECT
    '16161616-2222-3333-4444-555555555560'::uuid,
    '44444444-4444-4444-4444-444444444444'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '17171717-2222-3333-4444-555555555561'::uuid,
    '55555555-5555-5555-5555-555555555555'::uuid,
    'market',
    'default',
    (SELECT id FROM market_q1),
    NULL::uuid
UNION ALL
SELECT
    '18181818-2222-3333-4444-555555555562'::uuid,
    '66666666-6666-6666-6666-666666666666'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
UNION ALL
SELECT
    '19191919-2222-3333-4444-555555555563'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    'problem',
    'default',
    (SELECT id FROM problem_q1),
    NULL::uuid
ON CONFLICT (project_id) DO NOTHING;

WITH bank AS (
    SELECT id AS bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1
),
problem_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'problem'
       AND variant = 'default'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
),
market_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'market'
       AND variant = 'default'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
),
tech_router_q1 AS (
    SELECT id
      FROM question_bank_questions
     WHERE bank_version_id = (SELECT bank_id FROM bank)
       AND stage = 'tech'
       AND variant = 'router'
       AND deleted_at IS NULL
     ORDER BY order_index
     LIMIT 1
)
INSERT INTO project_question_instances (
    id,
    org_id,
    project_id,
    question_bank_question_id,
    status,
    asked_count,
    last_asked_at,
    answered_at,
    final_answer_text,
    validation_status,
    validation_errors
)
SELECT
    '123e4567-e89b-12d3-a456-426614174100'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '11111111-2222-3333-4444-555555555555'::uuid,
    (SELECT id FROM problem_q1),
    'answered',
    1,
    now() - interval '3 days',
    now() - interval '3 days',
    'We are building a simple mentor matching platform for student founders.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '123e4567-e89b-12d3-a456-426614174110'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '66666666-7777-8888-9999-aaaaaaaaaaaa'::uuid,
    (SELECT id FROM market_q1),
    'answered',
    1,
    now() - interval '2 days',
    now() - interval '2 days',
    'Target market is early-stage student teams in incubators.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '123e4567-e89b-12d3-a456-426614174120'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    (SELECT id FROM problem_q1),
    'needs_info',
    2,
    now() - interval '1 day',
    NULL,
    NULL,
    'needs_info',
    '["missing_customer_segment"]'::jsonb
UNION ALL
SELECT
    '123e4567-e89b-12d3-a456-426614174130'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '88888888-8888-8888-8888-888888888888'::uuid,
    (SELECT id FROM market_q1),
    'invalid',
    1,
    now() - interval '6 hours',
    now() - interval '6 hours',
    'Response was off-topic and missing pricing details.',
    'invalid',
    '["missing_pricing_unit","off_topic_answer"]'::jsonb
UNION ALL
SELECT
    '123e4567-e89b-12d3-a456-426614174140'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '99999999-9999-9999-9999-999999999998'::uuid,
    (SELECT id FROM tech_router_q1),
    'answered',
    1,
    now() - interval '4 hours',
    now() - interval '4 hours',
    'I can follow technical topics but prefer plain language.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '123e4567-e89b-12d3-a456-426614174150'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb'::uuid,
    (SELECT id FROM problem_q1),
    'pending',
    0,
    NULL,
    NULL,
    NULL,
    'not_validated',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174160'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '12121212-2222-3333-4444-555555555556'::uuid,
    (SELECT id FROM problem_q1),
    'answered',
    1,
    now() - interval '2 days',
    now() - interval '2 days',
    'Exploring interview workflows for first-time founders.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174170'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '13131313-2222-3333-4444-555555555557'::uuid,
    (SELECT id FROM market_q1),
    'needs_info',
    2,
    now() - interval '1 day',
    NULL,
    NULL,
    'needs_info',
    '["missing_competitor_snapshot"]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174180'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    '14141414-2222-3333-4444-555555555558'::uuid,
    (SELECT id FROM problem_q1),
    'answered',
    1,
    now() - interval '12 hours',
    now() - interval '12 hours',
    'Building a community marketplace for student labs.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174190'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    '15151515-2222-3333-4444-555555555559'::uuid,
    (SELECT id FROM tech_router_q1),
    'asked',
    1,
    now() - interval '6 hours',
    NULL,
    NULL,
    'not_validated',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174200'::uuid,
    '44444444-4444-4444-4444-444444444444'::uuid,
    '16161616-2222-3333-4444-555555555560'::uuid,
    (SELECT id FROM problem_q1),
    'answered',
    1,
    now() - interval '4 days',
    now() - interval '4 days',
    'Testing cohort engagement for academy partners.',
    'valid',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174210'::uuid,
    '55555555-5555-5555-5555-555555555555'::uuid,
    '17171717-2222-3333-4444-555555555561'::uuid,
    (SELECT id FROM market_q1),
    'invalid',
    1,
    now() - interval '4 hours',
    now() - interval '4 hours',
    'Missing pricing assumptions and target segment.',
    'invalid',
    '["missing_pricing_unit","missing_target_segment"]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174220'::uuid,
    '66666666-6666-6666-6666-666666666666'::uuid,
    '18181818-2222-3333-4444-555555555562'::uuid,
    (SELECT id FROM problem_q1),
    'pending',
    0,
    NULL,
    NULL,
    NULL,
    'not_validated',
    '[]'::jsonb
UNION ALL
SELECT
    '223e4567-e89b-12d3-a456-426614174230'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    '19191919-2222-3333-4444-555555555563'::uuid,
    (SELECT id FROM problem_q1),
    'answered',
    1,
    now() - interval '3 days',
    now() - interval '3 days',
    'Validating early adopters for sustainability tooling.',
    'valid',
    '[]'::jsonb
ON CONFLICT (project_id, question_bank_question_id) WHERE deleted_at IS NULL DO NOTHING;
