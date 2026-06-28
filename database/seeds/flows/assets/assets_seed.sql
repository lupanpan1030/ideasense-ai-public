-- Documents and notifications.
INSERT INTO documents (
    id,
    org_id,
    project_id,
    file_name,
    content_type,
    storage_key,
    status,
    error_message
)
VALUES
    (
        '123e4567-e89b-12d3-a456-426614174030',
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'problem_notes.pdf',
        'application/pdf',
        'seed/11111111-2222-3333-4444-555555555555/problem_notes.pdf',
        'uploaded',
        NULL
    ),
    (
        '123e4567-e89b-12d3-a456-426614174031',
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        'market_notes.pdf',
        'application/pdf',
        'seed/66666666-7777-8888-9999-aaaaaaaaaaaa/market_notes.pdf',
        'uploaded',
        NULL
    ),
    (
        '123e4567-e89b-12d3-a456-426614174032',
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        'pricing_draft.docx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'seed/88888888-8888-8888-8888-888888888888/pricing_draft.docx',
        'failed',
        'OCR parsing failed'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174033',
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        'pilot_notes.txt',
        'text/plain',
        'seed/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb/pilot_notes.txt',
        'indexed',
        NULL
    )
ON CONFLICT (org_id, storage_key) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO documents (
    id,
    org_id,
    project_id,
    file_name,
    content_type,
    storage_key,
    status,
    error_message
)
VALUES
    (
        '223e4567-e89b-12d3-a456-426614174330',
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        'interview_notes.md',
        'text/markdown',
        'seed/12121212-2222-3333-4444-555555555556/interview_notes.md',
        'uploaded',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174331',
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        'market_brief.pdf',
        'application/pdf',
        'seed/13131313-2222-3333-4444-555555555557/market_brief.pdf',
        'uploaded',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174332',
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        'tech_stack_choices.docx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'seed/15151515-2222-3333-4444-555555555559/tech_stack_choices.docx',
        'uploaded',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174333',
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        'engagement_metrics.csv',
        'text/csv',
        'seed/16161616-2222-3333-4444-555555555560/engagement_metrics.csv',
        'indexed',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174334',
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        'gtm_assumptions.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'seed/17171717-2222-3333-4444-555555555561/gtm_assumptions.xlsx',
        'uploaded',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174335',
        '66666666-6666-6666-6666-666666666666',
        '18181818-2222-3333-4444-555555555562',
        'clinic_workflows.txt',
        'text/plain',
        'seed/18181818-2222-3333-4444-555555555562/clinic_workflows.txt',
        'uploaded',
        NULL
    ),
    (
        '223e4567-e89b-12d3-a456-426614174336',
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        'sustainability_sources.pdf',
        'application/pdf',
        'seed/19191919-2222-3333-4444-555555555563/sustainability_sources.pdf',
        'failed',
        'Scan incomplete'
    )
ON CONFLICT (org_id, storage_key) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid,
    'mentor.assignment',
    'New student assigned',
    'You have been assigned to Sam Student.',
    '/app/mentor/students',
    '{}'::jsonb,
    NULL
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid
       AND type = 'mentor.assignment'
       AND link = '/app/mentor/students'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '11111111-1111-1111-1111-111111111111'::uuid,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    'report.ready',
    'Report ready',
    'Your Stage 1 report is ready to review.',
    '/app/projects/11111111-2222-3333-4444-555555555555/report',
    '{}'::jsonb,
    now() - interval '1 day'
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid
       AND type = 'report.ready'
       AND link = '/app/projects/11111111-2222-3333-4444-555555555555/report'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '33333333-3333-3333-3333-333333333333'::uuid,
    '77777777-8888-8888-8888-888888888888'::uuid,
    'mentor.message',
    'New mentor message',
    'Your mentor left a comment on the pilot report.',
    '/app/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb/report',
    '{}'::jsonb,
    NULL
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = '77777777-8888-8888-8888-888888888888'::uuid
       AND type = 'mentor.message'
       AND link = '/app/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb/report'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '44444444-4444-4444-4444-444444444444'::uuid,
    '44444444-dddd-dddd-dddd-dddddddddddd'::uuid,
    'report.ready',
    'Report ready',
    'Your cohort report is ready to review.',
    '/app/projects/16161616-2222-3333-4444-555555555560/report',
    '{}'::jsonb,
    NULL
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = '44444444-dddd-dddd-dddd-dddddddddddd'::uuid
       AND type = 'report.ready'
       AND link = '/app/projects/16161616-2222-3333-4444-555555555560/report'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '55555555-5555-5555-5555-555555555555'::uuid,
    '55555555-dddd-dddd-dddd-dddddddddddd'::uuid,
    'mentor.assignment',
    'Mentor assigned',
    'You have been assigned a mentor for Nimbus Launchpad.',
    '/app/projects/17171717-2222-3333-4444-555555555561',
    '{}'::jsonb,
    NULL
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = '55555555-dddd-dddd-dddd-dddddddddddd'::uuid
       AND type = 'mentor.assignment'
       AND link = '/app/projects/17171717-2222-3333-4444-555555555561'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '66666666-6666-6666-6666-666666666666'::uuid,
    '66666666-cccc-cccc-cccc-cccccccccccc'::uuid,
    'mentor.message',
    'New mentor message',
    'Your mentor left feedback on your draft.',
    '/app/projects/18181818-2222-3333-4444-555555555562/report',
    '{}'::jsonb,
    NULL
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = '66666666-cccc-cccc-cccc-cccccccccccc'::uuid
       AND type = 'mentor.message'
       AND link = '/app/projects/18181818-2222-3333-4444-555555555562/report'
       AND deleted_at IS NULL
);

INSERT INTO notifications (
    org_id,
    recipient_user_id,
    type,
    title,
    body,
    link,
    payload,
    read_at
)
SELECT
    '77777777-7777-7777-7777-777777777777'::uuid,
    '77777777-cccc-cccc-cccc-cccccccccccc'::uuid,
    'report.ready',
    'Report ready',
    'Your report is ready to review.',
    '/app/projects/19191919-2222-3333-4444-555555555563/report',
    '{}'::jsonb,
    now() - interval '2 hours'
WHERE NOT EXISTS (
    SELECT 1
      FROM notifications
     WHERE recipient_user_id = '77777777-cccc-cccc-cccc-cccccccccccc'::uuid
       AND type = 'report.ready'
       AND link = '/app/projects/19191919-2222-3333-4444-555555555563/report'
       AND deleted_at IS NULL
);
