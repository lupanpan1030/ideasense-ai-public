-- Cohorts and memberships.
INSERT INTO cohorts (id, org_id, name, description, start_at, end_at)
VALUES
    (
        '22222222-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111',
        'Spring 2026',
        'Seed cohort for local testing.',
        now() - interval '30 days',
        now() + interval '90 days'
    ),
    (
        '33333333-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111',
        'Fall 2026',
        'Second cohort with more students.',
        now() - interval '10 days',
        now() + interval '120 days'
    ),
    (
        '55555555-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111',
        'Winter 2026',
        'Short cohort for onboarding projects.',
        now() - interval '5 days',
        now() + interval '45 days'
    ),
    (
        '66666666-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111',
        'Summer 2027',
        'Longer cohort with mixed roles.',
        now() - interval '2 days',
        now() + interval '120 days'
    ),
    (
        '44444444-2222-2222-2222-222222222222',
        '33333333-3333-3333-3333-333333333333',
        'Labs Alpha',
        'Sandbox cohort for org2.',
        now() - interval '5 days',
        now() + interval '60 days'
    ),
    (
        '77777777-2222-2222-2222-222222222222',
        '33333333-3333-3333-3333-333333333333',
        'Labs Beta',
        'Extended pilots for Labs org.',
        now() - interval '15 days',
        now() + interval '75 days'
    ),
    (
        '88888888-2222-2222-2222-222222222222',
        '44444444-4444-4444-4444-444444444444',
        'Northwind Cohort 1',
        'Initial cohort for Northwind Academy.',
        now() - interval '20 days',
        now() + interval '90 days'
    ),
    (
        '99999999-2222-2222-2222-222222222222',
        '44444444-4444-4444-4444-444444444444',
        'Northwind Cohort 2',
        'Follow-up cohort with new intake.',
        now() + interval '7 days',
        now() + interval '120 days'
    ),
    (
        'aaaaaaaa-2222-2222-2222-222222222222',
        '55555555-5555-5555-5555-555555555555',
        'Nimbus Launchpad',
        'Go-to-market cohort for Nimbus.',
        now() - interval '12 days',
        now() + interval '60 days'
    ),
    (
        'bbbbbbbb-2222-2222-2222-222222222222',
        '66666666-6666-6666-6666-666666666666',
        'Aurora Pilot',
        'Healthcare research pilot cohort.',
        now() - interval '25 days',
        now() + interval '30 days'
    ),
    (
        'cccccccc-2222-2222-2222-222222222222',
        '77777777-7777-7777-7777-777777777777',
        'Cedar Spring',
        'Startup exploration cohort.',
        now() - interval '8 days',
        now() + interval '80 days'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO cohort_memberships (org_id, cohort_id, user_id, role_in_cohort, status)
VALUES
    ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active'),
    ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '33333333-2222-2222-2222-222222222222', '22222222-3333-3333-3333-333333333333', 'mentor', 'active'),
    ('11111111-1111-1111-1111-111111111111', '33333333-2222-2222-2222-222222222222', '33333333-4444-4444-4444-444444444444', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '33333333-2222-2222-2222-222222222222', '44444444-5555-5555-5555-555555555555', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '33333333-2222-2222-2222-222222222222', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'student', 'removed'),
    ('11111111-1111-1111-1111-111111111111', '55555555-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active'),
    ('11111111-1111-1111-1111-111111111111', '55555555-2222-2222-2222-222222222222', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'assistant', 'active'),
    ('11111111-1111-1111-1111-111111111111', '55555555-2222-2222-2222-222222222222', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '55555555-2222-2222-2222-222222222222', '33333333-4444-4444-4444-444444444444', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '66666666-2222-2222-2222-222222222222', '22222222-3333-3333-3333-333333333333', 'mentor', 'active'),
    ('11111111-1111-1111-1111-111111111111', '66666666-2222-2222-2222-222222222222', '44444444-5555-5555-5555-555555555555', 'student', 'active'),
    ('11111111-1111-1111-1111-111111111111', '66666666-2222-2222-2222-222222222222', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'student', 'removed'),
    ('33333333-3333-3333-3333-333333333333', '44444444-2222-2222-2222-222222222222', '66666666-7777-7777-7777-777777777777', 'mentor', 'active'),
    ('33333333-3333-3333-3333-333333333333', '44444444-2222-2222-2222-222222222222', '77777777-8888-8888-8888-888888888888', 'student', 'active'),
    ('33333333-3333-3333-3333-333333333333', '77777777-2222-2222-2222-222222222222', '55555555-6666-6666-6666-666666666666', 'assistant', 'active'),
    ('33333333-3333-3333-3333-333333333333', '77777777-2222-2222-2222-222222222222', '66666666-7777-7777-7777-777777777777', 'mentor', 'active'),
    ('33333333-3333-3333-3333-333333333333', '77777777-2222-2222-2222-222222222222', '77777777-8888-8888-8888-888888888888', 'student', 'active'),
    ('44444444-4444-4444-4444-444444444444', '88888888-2222-2222-2222-222222222222', '44444444-cccc-cccc-cccc-cccccccccccc', 'mentor', 'active'),
    ('44444444-4444-4444-4444-444444444444', '88888888-2222-2222-2222-222222222222', '44444444-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'assistant', 'active'),
    ('44444444-4444-4444-4444-444444444444', '88888888-2222-2222-2222-222222222222', '44444444-dddd-dddd-dddd-dddddddddddd', 'student', 'active'),
    ('44444444-4444-4444-4444-444444444444', '99999999-2222-2222-2222-222222222222', '44444444-cccc-cccc-cccc-cccccccccccc', 'mentor', 'active'),
    ('44444444-4444-4444-4444-444444444444', '99999999-2222-2222-2222-222222222222', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'assistant', 'active'),
    ('44444444-4444-4444-4444-444444444444', '99999999-2222-2222-2222-222222222222', '44444444-dddd-dddd-dddd-dddddddddddd', 'student', 'removed'),
    ('55555555-5555-5555-5555-555555555555', 'aaaaaaaa-2222-2222-2222-222222222222', '55555555-cccc-cccc-cccc-cccccccccccc', 'mentor', 'active'),
    ('55555555-5555-5555-5555-555555555555', 'aaaaaaaa-2222-2222-2222-222222222222', '55555555-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'assistant', 'active'),
    ('55555555-5555-5555-5555-555555555555', 'aaaaaaaa-2222-2222-2222-222222222222', '55555555-dddd-dddd-dddd-dddddddddddd', 'student', 'active'),
    ('66666666-6666-6666-6666-666666666666', 'bbbbbbbb-2222-2222-2222-222222222222', '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'assistant', 'active'),
    ('66666666-6666-6666-6666-666666666666', 'bbbbbbbb-2222-2222-2222-222222222222', '66666666-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active'),
    ('66666666-6666-6666-6666-666666666666', 'bbbbbbbb-2222-2222-2222-222222222222', '66666666-cccc-cccc-cccc-cccccccccccc', 'student', 'active'),
    ('77777777-7777-7777-7777-777777777777', 'cccccccc-2222-2222-2222-222222222222', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'assistant', 'active'),
    ('77777777-7777-7777-7777-777777777777', 'cccccccc-2222-2222-2222-222222222222', '77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active'),
    ('77777777-7777-7777-7777-777777777777', 'cccccccc-2222-2222-2222-222222222222', '77777777-cccc-cccc-cccc-cccccccccccc', 'student', 'active')
ON CONFLICT (cohort_id, user_id) WHERE deleted_at IS NULL DO NOTHING;
