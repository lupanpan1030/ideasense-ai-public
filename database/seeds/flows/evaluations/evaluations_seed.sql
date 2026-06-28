-- Evaluation rubrics and scores.
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

INSERT INTO answer_evaluations (
    id,
    org_id,
    project_id,
    question_instance_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
VALUES
    (
        'aaaa1111-2222-3333-4444-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        '123e4567-e89b-12d3-a456-426614174100',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.9,"completeness":0.95,"evidence":0.9}'::jsonb,
        0.92,
        'Strong, focused answer with clear target user.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000201'
    ),
    (
        'bbbb1111-2222-3333-4444-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        '123e4567-e89b-12d3-a456-426614174130',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.4,"completeness":0.2,"evidence":0.3}'::jsonb,
        0.30,
        'Missing pricing unit and buyer role; answer is incomplete.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000202'
    ),
    (
        'cccc1111-2222-3333-4444-555555555555',
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        '123e4567-e89b-12d3-a456-426614174150',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.7,"completeness":0.6,"evidence":0.6}'::jsonb,
        0.65,
        'Decent start, but needs clearer pain articulation.',
        'human',
        NULL,
        '00000000-0000-0000-0000-000000000203'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO answer_evaluations (
    id,
    org_id,
    project_id,
    question_instance_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
VALUES
    (
        'aaaa2222-2222-3333-4444-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        '223e4567-e89b-12d3-a456-426614174160',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.8,"completeness":0.75,"evidence":0.7}'::jsonb,
        0.75,
        'Good overview; add two concrete interview insights.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000206'
    ),
    (
        'bbbb2222-2222-3333-4444-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        '223e4567-e89b-12d3-a456-426614174170',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.5,"completeness":0.4,"evidence":0.3}'::jsonb,
        0.40,
        'Missing competitor snapshot and pricing anchor.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000207'
    ),
    (
        'cccc2222-2222-3333-4444-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '14141414-2222-3333-4444-555555555558',
        '223e4567-e89b-12d3-a456-426614174180',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.86,"completeness":0.8,"evidence":0.78}'::jsonb,
        0.81,
        'Clear pain statement; add a quantified example.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000208'
    ),
    (
        'dddd2222-2222-3333-4444-555555555555',
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        '223e4567-e89b-12d3-a456-426614174200',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.78,"completeness":0.74,"evidence":0.7}'::jsonb,
        0.74,
        'Solid insight; add specific engagement metrics.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000209'
    ),
    (
        'eeee2222-2222-3333-4444-555555555555',
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        '223e4567-e89b-12d3-a456-426614174210',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.42,"completeness":0.35,"evidence":0.25}'::jsonb,
        0.34,
        'Needs a clearer target segment and pricing assumptions.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000210'
    ),
    (
        'ffff2222-2222-3333-4444-555555555555',
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        '223e4567-e89b-12d3-a456-426614174230',
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        '{"clarity":0.84,"completeness":0.8,"evidence":0.76}'::jsonb,
        0.80,
        'Strong start; capture initial data sources.',
        'ai',
        'gpt-4',
        '00000000-0000-0000-0000-000000000211'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO message_evaluations (
    id,
    org_id,
    project_id,
    message_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
SELECT
    'dddd1111-2222-3333-4444-555555555555'::uuid,
    m.org_id,
    m.project_id,
    m.id,
    'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
    '{"tone":0.9,"helpfulness":0.85,"specificity":0.8}'::jsonb,
    0.85,
    'Concise and actionable follow-up.',
    'ai',
    'gpt-4',
    '00000000-0000-0000-0000-000000000204'::uuid
FROM conversation_messages m
WHERE m.client_message_id = '00000000-0000-0000-0000-000000000002'::uuid
ON CONFLICT (id) DO NOTHING;

INSERT INTO message_evaluations (
    id,
    org_id,
    project_id,
    message_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
SELECT
    'eeee1111-2222-3333-4444-555555555555'::uuid,
    m.org_id,
    m.project_id,
    m.id,
    'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
    '{"tone":0.4,"helpfulness":0.3,"specificity":0.2}'::jsonb,
    0.30,
    'Too vague; needs concrete next steps.',
    'ai',
    'gpt-4',
    '00000000-0000-0000-0000-000000000205'::uuid
FROM conversation_messages m
WHERE m.client_message_id = '00000000-0000-0000-0000-000000000008'::uuid
ON CONFLICT (id) DO NOTHING;

INSERT INTO message_evaluations (
    id,
    org_id,
    project_id,
    message_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
SELECT
    'ffff1111-2222-3333-4444-555555555555'::uuid,
    m.org_id,
    m.project_id,
    m.id,
    'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
    '{"tone":0.92,"helpfulness":0.86,"specificity":0.84}'::jsonb,
    0.87,
    'Clear follow-up that narrows the next step.',
    'ai',
    'gpt-4',
    '00000000-0000-0000-0000-000000000212'::uuid
FROM conversation_messages m
WHERE m.client_message_id = '00000000-0000-0000-0000-000000000014'::uuid
ON CONFLICT (id) DO NOTHING;

INSERT INTO message_evaluations (
    id,
    org_id,
    project_id,
    message_id,
    rubric_id,
    scores_json,
    overall_score,
    feedback_markdown,
    evaluator_type,
    evaluator_model,
    request_id
)
SELECT
    '11111111-2222-3333-4444-555555555556'::uuid,
    m.org_id,
    m.project_id,
    m.id,
    'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
    '{"tone":0.78,"helpfulness":0.7,"specificity":0.62}'::jsonb,
    0.70,
    'Decent prompt; add a clearer success metric.',
    'ai',
    'gpt-4',
    '00000000-0000-0000-0000-000000000213'::uuid
FROM conversation_messages m
WHERE m.client_message_id = '00000000-0000-0000-0000-000000000024'::uuid
ON CONFLICT (id) DO NOTHING;
