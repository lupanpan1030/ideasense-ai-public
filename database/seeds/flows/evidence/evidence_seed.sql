-- Messages and state.
INSERT INTO conversation_messages (
    org_id,
    project_id,
    author_user_id,
    role,
    stage,
    variant,
    question_instance_id,
    client_message_id,
    content,
    content_format
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'user',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174100',
        '00000000-0000-0000-0000-000000000001',
        'We are building a mentor matching platform for student founders.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        NULL,
        'assistant',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174100',
        '00000000-0000-0000-0000-000000000002',
        'Got it. What is the core pain point you are addressing?',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'user',
        'market',
        'default',
        '123e4567-e89b-12d3-a456-426614174110',
        '00000000-0000-0000-0000-000000000003',
        'We target student founders inside university incubators.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        NULL,
        'assistant',
        'market',
        'default',
        '123e4567-e89b-12d3-a456-426614174110',
        '00000000-0000-0000-0000-000000000004',
        'Which incubators are you planning to start with?',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '77777777-7777-7777-7777-777777777777',
        '33333333-4444-4444-4444-444444444444',
        'user',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174120',
        '00000000-0000-0000-0000-000000000005',
        'We are exploring a peer-led mentorship marketplace.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '77777777-7777-7777-7777-777777777777',
        NULL,
        'assistant',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174120',
        '00000000-0000-0000-0000-000000000006',
        'Can you specify the primary student segment you want to serve?',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        '44444444-5555-5555-5555-555555555555',
        'user',
        'market',
        'default',
        '123e4567-e89b-12d3-a456-426614174130',
        '00000000-0000-0000-0000-000000000007',
        'We focus on students at incubators; pricing is still unknown.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        NULL,
        'assistant',
        'market',
        'default',
        '123e4567-e89b-12d3-a456-426614174130',
        '00000000-0000-0000-0000-000000000008',
        'Please clarify your pricing unit and who pays.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999998',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'user',
        'tech',
        'router',
        '123e4567-e89b-12d3-a456-426614174140',
        '00000000-0000-0000-0000-000000000009',
        'I can follow technical topics but prefer plain language.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999998',
        NULL,
        'assistant',
        'tech',
        'router',
        '123e4567-e89b-12d3-a456-426614174140',
        '00000000-0000-0000-0000-000000000010',
        'Thanks. I will use plain language for the tech section.',
        'markdown'
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        '77777777-8888-8888-8888-888888888888',
        'user',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174150',
        '00000000-0000-0000-0000-000000000011',
        'We help local student founders find advisors fast.',
        'markdown'
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        NULL,
        'assistant',
        'problem',
        'default',
        '123e4567-e89b-12d3-a456-426614174150',
        '00000000-0000-0000-0000-000000000012',
        'What is the top pain point your founders face today?',
        'markdown'
    )
ON CONFLICT (project_id, client_message_id)
    WHERE client_message_id IS NOT NULL AND deleted_at IS NULL
    DO NOTHING;

INSERT INTO conversation_messages (
    org_id,
    project_id,
    author_user_id,
    role,
    stage,
    variant,
    question_instance_id,
    client_message_id,
    content,
    content_format
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'user',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174160',
        '00000000-0000-0000-0000-000000000013',
        'We are interviewing first-time founders to map onboarding pain.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        NULL,
        'assistant',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174160',
        '00000000-0000-0000-0000-000000000014',
        'Which part of onboarding is most painful: ideation, validation, or fundraising?',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        '33333333-4444-4444-4444-444444444444',
        'user',
        'market',
        'default',
        '223e4567-e89b-12d3-a456-426614174170',
        '00000000-0000-0000-0000-000000000015',
        'Our early adopters are student teams in accelerator cohorts.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        NULL,
        'assistant',
        'market',
        'default',
        '223e4567-e89b-12d3-a456-426614174170',
        '00000000-0000-0000-0000-000000000016',
        'How will you reach them and what pricing anchor will you test first?',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '14141414-2222-3333-4444-555555555558',
        '44444444-5555-5555-5555-555555555555',
        'user',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174180',
        '00000000-0000-0000-0000-000000000017',
        'We want to connect campus labs to shared equipment access.',
        'markdown'
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '14141414-2222-3333-4444-555555555558',
        NULL,
        'assistant',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174180',
        '00000000-0000-0000-0000-000000000018',
        'Which labs are most underserved and why now?',
        'markdown'
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        NULL,
        'assistant',
        'tech',
        'router',
        '223e4567-e89b-12d3-a456-426614174190',
        '00000000-0000-0000-0000-000000000020',
        'What is the fastest path to validate with your cohort?',
        'markdown'
    ),
    (
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        '44444444-dddd-dddd-dddd-dddddddddddd',
        'user',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174200',
        '00000000-0000-0000-0000-000000000021',
        'We want to improve engagement in weekly cohort check-ins.',
        'markdown'
    ),
    (
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        NULL,
        'assistant',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174200',
        '00000000-0000-0000-0000-000000000022',
        'What engagement metric matters most to your program today?',
        'markdown'
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        '55555555-dddd-dddd-dddd-dddddddddddd',
        'user',
        'market',
        'default',
        '223e4567-e89b-12d3-a456-426614174210',
        '00000000-0000-0000-0000-000000000023',
        'We target seed-stage teams in regional startup hubs.',
        'markdown'
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        NULL,
        'assistant',
        'market',
        'default',
        '223e4567-e89b-12d3-a456-426614174210',
        '00000000-0000-0000-0000-000000000024',
        'How will you validate willingness to pay with those teams?',
        'markdown'
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        '77777777-cccc-cccc-cccc-cccccccccccc',
        'user',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174230',
        '00000000-0000-0000-0000-000000000027',
        'We aim to help labs track sustainability metrics.',
        'markdown'
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        NULL,
        'assistant',
        'problem',
        'default',
        '223e4567-e89b-12d3-a456-426614174230',
        '00000000-0000-0000-0000-000000000028',
        'What data sources will you start with?',
        'markdown'
    )
ON CONFLICT (project_id, client_message_id)
    WHERE client_message_id IS NOT NULL AND deleted_at IS NULL
    DO NOTHING;

WITH bank AS (
    SELECT id AS bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1
)
INSERT INTO project_states (
    project_id,
    org_id,
    bank_version_id,
    state_schema_version,
    state_json,
    state_version,
    state_meta
)
SELECT
    '11111111-2222-3333-4444-555555555555'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Mentor matching platform for student founders"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '66666666-7777-8888-9999-aaaaaaaaaaaa'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"market":{"summary":"University incubator teams as early adopters"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '77777777-7777-7777-7777-777777777777'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Peer-led mentorship marketplace for student founders"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '88888888-8888-8888-8888-888888888888'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"market":{"summary":"Incubator students, pricing still unclear"}}'::jsonb,
    1,
    '{"flags":["needs_pricing"]}'::jsonb
FROM bank
UNION ALL
SELECT
    '99999999-9999-9999-9999-999999999998'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"tech":{"summary":"Plain-language technical guidance required"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Fast advisor matching for local founders"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
ON CONFLICT (project_id) DO NOTHING;

WITH bank AS (
    SELECT id AS bank_id
      FROM question_bank_versions
     WHERE bank_key = 'default'
       AND is_active
       AND deleted_at IS NULL
     ORDER BY created_at DESC
     LIMIT 1
)
INSERT INTO project_states (
    project_id,
    org_id,
    bank_version_id,
    state_schema_version,
    state_json,
    state_version,
    state_meta
)
SELECT
    '12121212-2222-3333-4444-555555555556'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Interview workflow pain for first-time founders"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '13131313-2222-3333-4444-555555555557'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"market":{"summary":"Student accelerator cohorts as early adopters"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '14141414-2222-3333-4444-555555555558'::uuid,
    '11111111-1111-1111-1111-111111111111'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Campus labs need shared equipment access"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '15151515-2222-3333-4444-555555555559'::uuid,
    '33333333-3333-3333-3333-333333333333'::uuid,
    bank.bank_id,
    'v1',
    '{"tech":{"summary":"Choosing between no-code and custom build"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '16161616-2222-3333-4444-555555555560'::uuid,
    '44444444-4444-4444-4444-444444444444'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Improve engagement in cohort check-ins"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '17171717-2222-3333-4444-555555555561'::uuid,
    '55555555-5555-5555-5555-555555555555'::uuid,
    bank.bank_id,
    'v1',
    '{"market":{"summary":"Seed-stage teams in regional startup hubs"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '18181818-2222-3333-4444-555555555562'::uuid,
    '66666666-6666-6666-6666-666666666666'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Reduce admin load for clinic coordinators"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
UNION ALL
SELECT
    '19191919-2222-3333-4444-555555555563'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    bank.bank_id,
    'v1',
    '{"problem":{"summary":"Track sustainability metrics for labs"}}'::jsonb,
    1,
    '{}'::jsonb
FROM bank
ON CONFLICT (project_id) DO NOTHING;

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '11111111-2222-3333-4444-555555555555'::uuid,
    '123e4567-e89b-12d3-a456-426614174100'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Mentor matching platform for student founders"}'::jsonb,
    'user',
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000101'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000101'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '77777777-7777-7777-7777-777777777777'::uuid,
    '123e4567-e89b-12d3-a456-426614174120'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Peer-led mentorship marketplace"}'::jsonb,
    'user',
    '33333333-4444-4444-4444-444444444444'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000102'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000102'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '88888888-8888-8888-8888-888888888888'::uuid,
    '123e4567-e89b-12d3-a456-426614174130'::uuid,
    'validation_failed',
    '{"path":"market.pricing","value":null}'::jsonb,
    'system',
    NULL,
    1,
    1,
    '00000000-0000-0000-0000-000000000103'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000103'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '12121212-2222-3333-4444-555555555556'::uuid,
    '223e4567-e89b-12d3-a456-426614174160'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Interview workflow pain for first-time founders"}'::jsonb,
    'user',
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000104'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000104'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '13131313-2222-3333-4444-555555555557'::uuid,
    '223e4567-e89b-12d3-a456-426614174170'::uuid,
    'validation_failed',
    '{"path":"market.competitors","value":null}'::jsonb,
    'system',
    NULL,
    1,
    1,
    '00000000-0000-0000-0000-000000000105'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000105'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    '14141414-2222-3333-4444-555555555558'::uuid,
    '223e4567-e89b-12d3-a456-426614174180'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Campus labs need shared equipment access"}'::jsonb,
    'user',
    '44444444-5555-5555-5555-555555555555'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000106'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000106'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '44444444-4444-4444-4444-444444444444'::uuid,
    '16161616-2222-3333-4444-555555555560'::uuid,
    '223e4567-e89b-12d3-a456-426614174200'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Improve engagement in cohort check-ins"}'::jsonb,
    'user',
    '44444444-dddd-dddd-dddd-dddddddddddd'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000107'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000107'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '55555555-5555-5555-5555-555555555555'::uuid,
    '17171717-2222-3333-4444-555555555561'::uuid,
    '223e4567-e89b-12d3-a456-426614174210'::uuid,
    'validation_failed',
    '{"path":"market.pricing","value":null}'::jsonb,
    'system',
    NULL,
    1,
    1,
    '00000000-0000-0000-0000-000000000108'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000108'::uuid
);

INSERT INTO project_state_events (
    org_id,
    project_id,
    question_instance_id,
    event_type,
    patch_json,
    actor_type,
    actor_user_id,
    prev_state_version,
    next_state_version,
    request_id
)
SELECT
    '77777777-7777-7777-7777-777777777777'::uuid,
    '19191919-2222-3333-4444-555555555563'::uuid,
    '223e4567-e89b-12d3-a456-426614174230'::uuid,
    'answer_submitted',
    '{"path":"problem.summary","value":"Track sustainability metrics for labs"}'::jsonb,
    'user',
    '77777777-cccc-cccc-cccc-cccccccccccc'::uuid,
    0,
    1,
    '00000000-0000-0000-0000-000000000109'::uuid
WHERE NOT EXISTS (
    SELECT 1
      FROM project_state_events
     WHERE request_id = '00000000-0000-0000-0000-000000000109'::uuid
);
