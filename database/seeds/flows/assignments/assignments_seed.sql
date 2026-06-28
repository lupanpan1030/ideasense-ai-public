-- Mentor assignments.
SELECT set_config('app.user_id', '99999999-9999-9999-9999-999999999999', true);
SELECT set_config('app.org_id', '11111111-1111-1111-1111-111111111111', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
        '11111111-1111-1111-1111-111111111111',
        '22222222-2222-2222-2222-222222222222',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'active',
        false,
        true,
        true,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        'ffffffff-ffff-ffff-ffff-ffffffffffff',
        '11111111-1111-1111-1111-111111111111',
        '22222222-2222-2222-2222-222222222222',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'active',
        true,
        true,
        true,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        'abababab-abab-abab-abab-abababababab',
        '11111111-1111-1111-1111-111111111111',
        '33333333-2222-2222-2222-222222222222',
        '22222222-3333-3333-3333-333333333333',
        '33333333-4444-4444-4444-444444444444',
        'pending',
        false,
        false,
        true,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        'cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd',
        '11111111-1111-1111-1111-111111111111',
        '33333333-2222-2222-2222-222222222222',
        '22222222-3333-3333-3333-333333333333',
        '44444444-5555-5555-5555-555555555555',
        'revoked',
        false,
        true,
        false,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        '12121212-1212-1212-1212-121212121212',
        '11111111-1111-1111-1111-111111111111',
        '55555555-2222-2222-2222-222222222222',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'active',
        false,
        true,
        true,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        '23232323-2323-2323-2323-232323232323',
        '11111111-1111-1111-1111-111111111111',
        '55555555-2222-2222-2222-222222222222',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '33333333-4444-4444-4444-444444444444',
        'pending',
        false,
        false,
        true,
        '99999999-9999-9999-9999-999999999999'
    ),
    (
        '34343434-3434-3434-3434-343434343434',
        '11111111-1111-1111-1111-111111111111',
        '66666666-2222-2222-2222-222222222222',
        '22222222-3333-3333-3333-333333333333',
        '44444444-5555-5555-5555-555555555555',
        'active',
        true,
        true,
        true,
        '99999999-9999-9999-9999-999999999999'
    )
ON CONFLICT (id) DO NOTHING;

SELECT set_config('app.user_id', '55555555-6666-6666-6666-666666666666', true);
SELECT set_config('app.org_id', '33333333-3333-3333-3333-333333333333', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        'efefefef-efef-efef-efef-efefefefefef',
        '33333333-3333-3333-3333-333333333333',
        '44444444-2222-2222-2222-222222222222',
        '66666666-7777-7777-7777-777777777777',
        '77777777-8888-8888-8888-888888888888',
        'active',
        true,
        true,
        true,
        '55555555-6666-6666-6666-666666666666'
    ),
    (
        '45454545-4545-4545-4545-454545454545',
        '33333333-3333-3333-3333-333333333333',
        '77777777-2222-2222-2222-222222222222',
        '66666666-7777-7777-7777-777777777777',
        '77777777-8888-8888-8888-888888888888',
        'pending',
        false,
        false,
        true,
        '55555555-6666-6666-6666-666666666666'
    )
ON CONFLICT (id) DO NOTHING;

SELECT set_config('app.user_id', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true);
SELECT set_config('app.org_id', '44444444-4444-4444-4444-444444444444', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        '56565656-5656-5656-5656-565656565656',
        '44444444-4444-4444-4444-444444444444',
        '88888888-2222-2222-2222-222222222222',
        '44444444-cccc-cccc-cccc-cccccccccccc',
        '44444444-dddd-dddd-dddd-dddddddddddd',
        'active',
        true,
        true,
        false,
        '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    )
ON CONFLICT (id) DO NOTHING;

SELECT set_config('app.user_id', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true);
SELECT set_config('app.org_id', '55555555-5555-5555-5555-555555555555', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        '67676767-6767-6767-6767-676767676767',
        '55555555-5555-5555-5555-555555555555',
        'aaaaaaaa-2222-2222-2222-222222222222',
        '55555555-cccc-cccc-cccc-cccccccccccc',
        '55555555-dddd-dddd-dddd-dddddddddddd',
        'active',
        false,
        true,
        true,
        '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    )
ON CONFLICT (id) DO NOTHING;

SELECT set_config('app.user_id', '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true);
SELECT set_config('app.org_id', '66666666-6666-6666-6666-666666666666', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        '78787878-7878-7878-7878-787878787878',
        '66666666-6666-6666-6666-666666666666',
        'bbbbbbbb-2222-2222-2222-222222222222',
        '66666666-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '66666666-cccc-cccc-cccc-cccccccccccc',
        'pending',
        false,
        false,
        true,
        '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    )
ON CONFLICT (id) DO NOTHING;

SELECT set_config('app.user_id', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa', true);
SELECT set_config('app.org_id', '77777777-7777-7777-7777-777777777777', true);

INSERT INTO mentor_student_assignments (
    id,
    org_id,
    cohort_id,
    mentor_user_id,
    student_user_id,
    status,
    can_view_messages,
    can_view_facts,
    can_comment,
    created_by
)
VALUES
    (
        '89898989-8989-8989-8989-898989898989',
        '77777777-7777-7777-7777-777777777777',
        'cccccccc-2222-2222-2222-222222222222',
        '77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '77777777-cccc-cccc-cccc-cccccccccccc',
        'active',
        true,
        true,
        true,
        '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    )
ON CONFLICT (id) DO NOTHING;
