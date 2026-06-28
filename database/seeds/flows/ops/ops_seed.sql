-- Ops data: background jobs, analytics, audit.
INSERT INTO background_jobs (
    org_id,
    project_id,
    job_type,
    status,
    priority,
    payload,
    idempotency_key,
    attempts,
    max_attempts,
    run_at,
    last_error
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'report.generate',
        'succeeded',
        50,
        '{"scope":"stage1"}'::jsonb,
        'report:11111111-2222-3333-4444-555555555555:v1',
        1,
        3,
        now() - interval '2 days',
        NULL
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        'report.generate',
        'failed',
        50,
        '{"scope":"stage2"}'::jsonb,
        'report:88888888-8888-8888-8888-888888888888:v1',
        3,
        3,
        now() - interval '1 day',
        'LLM timeout'
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        'document.extract',
        'running',
        75,
        '{"document":"pilot_notes.txt"}'::jsonb,
        'doc:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb:pilot_notes.txt',
        1,
        5,
        now() - interval '2 hours',
        NULL
    )
ON CONFLICT (org_id, job_type, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL
    DO NOTHING;

INSERT INTO background_jobs (
    org_id,
    project_id,
    job_type,
    status,
    priority,
    payload,
    idempotency_key,
    attempts,
    max_attempts,
    run_at,
    last_error
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        'report.generate',
        'succeeded',
        50,
        '{"scope":"stage1"}'::jsonb,
        'report:12121212-2222-3333-4444-555555555556:v1',
        1,
        3,
        now() - interval '1 day',
        NULL
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        'report.generate',
        'running',
        60,
        '{"scope":"tech"}'::jsonb,
        'report:15151515-2222-3333-4444-555555555559:v1',
        1,
        3,
        now() - interval '3 hours',
        NULL
    ),
    (
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        'document.extract',
        'succeeded',
        70,
        '{"document":"engagement_metrics.csv"}'::jsonb,
        'doc:16161616-2222-3333-4444-555555555560:engagement_metrics.csv',
        1,
        5,
        now() - interval '6 hours',
        NULL
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        'report.generate',
        'failed',
        50,
        '{"scope":"stage2"}'::jsonb,
        'report:17171717-2222-3333-4444-555555555561:v1',
        2,
        3,
        now() - interval '5 hours',
        'Missing pricing inputs'
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        'report.generate',
        'succeeded',
        50,
        '{"scope":"stage1"}'::jsonb,
        'report:19191919-2222-3333-4444-555555555563:v1',
        1,
        3,
        now() - interval '4 hours',
        NULL
    )
ON CONFLICT (org_id, job_type, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL
    DO NOTHING;

INSERT INTO analytics_events (
    org_id,
    project_id,
    actor_user_id,
    event_type,
    payload
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'project.created',
        '{"source":"seed"}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        '44444444-5555-5555-5555-555555555555',
        'report.viewed',
        '{"version":1}'::jsonb
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        '77777777-8888-8888-8888-888888888888',
        'message.sent',
        '{"channel":"mentor"}'::jsonb
    )
ON CONFLICT DO NOTHING;

INSERT INTO analytics_events (
    org_id,
    project_id,
    actor_user_id,
    event_type,
    payload
)
VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        '44444444-dddd-dddd-dddd-dddddddddddd',
        'project.created',
        '{"source":"seed"}'::jsonb
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        '55555555-dddd-dddd-dddd-dddddddddddd',
        'report.viewed',
        '{"version":1}'::jsonb
    ),
    (
        '66666666-6666-6666-6666-666666666666',
        '18181818-2222-3333-4444-555555555562',
        '66666666-cccc-cccc-cccc-cccccccccccc',
        'message.sent',
        '{"channel":"mentor"}'::jsonb
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        '77777777-cccc-cccc-cccc-cccccccccccc',
        'project.created',
        '{"source":"seed"}'::jsonb
    )
ON CONFLICT DO NOTHING;

INSERT INTO audit_events (
    org_id,
    actor_user_id,
    actor_type,
    event_type,
    target_type,
    target_id,
    payload
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999999',
        'user',
        'assignment.created',
        'mentor_student_assignments',
        'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
        '{"seed":true}'::jsonb
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        NULL,
        'system',
        'report.failed',
        'project_reports',
        '123e4567-e89b-12d3-a456-426614174003',
        '{"reason":"validation_failed"}'::jsonb
    )
ON CONFLICT DO NOTHING;

INSERT INTO audit_events (
    org_id,
    actor_user_id,
    actor_type,
    event_type,
    target_type,
    target_id,
    payload
)
VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'user',
        'assignment.created',
        'mentor_student_assignments',
        '56565656-5656-5656-5656-565656565656',
        '{"seed":true}'::jsonb
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'user',
        'assignment.created',
        'mentor_student_assignments',
        '67676767-6767-6767-6767-676767676767',
        '{"seed":true}'::jsonb
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'user',
        'assignment.created',
        'mentor_student_assignments',
        '89898989-8989-8989-8989-898989898989',
        '{"seed":true}'::jsonb
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        NULL,
        'system',
        'report.failed',
        'project_reports',
        '223e4567-e89b-12d3-a456-426614174204',
        '{"reason":"missing_pricing"}'::jsonb
    )
ON CONFLICT DO NOTHING;
