-- Local auth identities (dev only).
INSERT INTO user_identities (
    id,
    user_id,
    provider,
    provider_subject,
    email,
    password_hash,
    status
)
VALUES
    (
        '99999999-0000-0000-0000-000000000001',
        '99999999-9999-9999-9999-999999999999',
        'local',
        NULL,
        'superadmin@demo.local',
        crypt('12345678', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000002',
        'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'local',
        NULL,
        'student2@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000003',
        '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'local',
        NULL,
        'northwind.owner@demo.local',
        crypt('northwind123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000004',
        '44444444-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'local',
        NULL,
        'northwind.admin@demo.local',
        crypt('northwind123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000005',
        '44444444-cccc-cccc-cccc-cccccccccccc',
        'local',
        NULL,
        'northwind.mentor@demo.local',
        crypt('northwind123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000006',
        '44444444-dddd-dddd-dddd-dddddddddddd',
        'local',
        NULL,
        'northwind.student@demo.local',
        crypt('northwind123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000007',
        '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'local',
        NULL,
        'nimbus.owner@demo.local',
        crypt('nimbus123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000008',
        '55555555-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'local',
        NULL,
        'nimbus.admin@demo.local',
        crypt('nimbus123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000009',
        '55555555-cccc-cccc-cccc-cccccccccccc',
        'local',
        NULL,
        'nimbus.mentor@demo.local',
        crypt('nimbus123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000010',
        '55555555-dddd-dddd-dddd-dddddddddddd',
        'local',
        NULL,
        'nimbus.student@demo.local',
        crypt('nimbus123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000011',
        '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'local',
        NULL,
        'aurora.owner@demo.local',
        crypt('aurora123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000012',
        '66666666-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'local',
        NULL,
        'aurora.mentor@demo.local',
        crypt('aurora123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000013',
        '66666666-cccc-cccc-cccc-cccccccccccc',
        'local',
        NULL,
        'aurora.student@demo.local',
        crypt('aurora123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000014',
        '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'local',
        NULL,
        'cedar.owner@demo.local',
        crypt('cedar123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000015',
        '77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'local',
        NULL,
        'cedar.admin@demo.local',
        crypt('cedar123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000016',
        '77777777-cccc-cccc-cccc-cccccccccccc',
        'local',
        NULL,
        'cedar.student@demo.local',
        crypt('cedar123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000017',
        '77777777-dddd-dddd-dddd-dddddddddddd',
        'local',
        NULL,
        'cedar.invited@demo.local',
        crypt('cedar123', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000018',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'local',
        NULL,
        'admin@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000019',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'local',
        NULL,
        'mentor@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000020',
        '22222222-3333-3333-3333-333333333333',
        'local',
        NULL,
        'mentor2@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000021',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'local',
        NULL,
        'student1@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000022',
        '33333333-4444-4444-4444-444444444444',
        'local',
        NULL,
        'student3@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000023',
        '44444444-5555-5555-5555-555555555555',
        'local',
        NULL,
        'student4@demo.local',
        crypt('demo12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000024',
        '55555555-6666-6666-6666-666666666666',
        'local',
        NULL,
        'admin2@demo.local',
        crypt('labs12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000025',
        '66666666-7777-7777-7777-777777777777',
        'local',
        NULL,
        'mentor3@demo.local',
        crypt('labs12345', gen_salt('bf')),
        'active'
    ),
    (
        '99999999-0000-0000-0000-000000000026',
        '77777777-8888-8888-8888-888888888888',
        'local',
        NULL,
        'student5@demo.local',
        crypt('labs12345', gen_salt('bf')),
        'active'
    )
ON CONFLICT (id) DO NOTHING;
