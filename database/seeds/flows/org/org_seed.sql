-- Orgs and users.
INSERT INTO organizations (id, name, slug)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'IdeaSenseAI Demo', 'ideasenseai-demo'),
    ('33333333-3333-3333-3333-333333333333', 'IdeaSenseAI Labs', 'ideasenseai-labs'),
    ('44444444-4444-4444-4444-444444444444', 'Northwind Academy', 'northwind-academy'),
    ('55555555-5555-5555-5555-555555555555', 'Nimbus Ventures', 'nimbus-ventures'),
    ('66666666-6666-6666-6666-666666666666', 'Aurora Health', 'aurora-health'),
    ('77777777-7777-7777-7777-777777777777', 'Cedar Labs', 'cedar-labs')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, email, display_name, primary_org_id)
VALUES
    ('99999999-9999-9999-9999-999999999999', 'superadmin@demo.local', 'Demo Admin', '11111111-1111-1111-1111-111111111111'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'admin@demo.local', 'Ava Admin', '11111111-1111-1111-1111-111111111111'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor@demo.local', 'Mia Mentor', '11111111-1111-1111-1111-111111111111'),
    ('22222222-3333-3333-3333-333333333333', 'mentor2@demo.local', 'Noah Mentor', '11111111-1111-1111-1111-111111111111'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'student1@demo.local', 'Sam Student', '11111111-1111-1111-1111-111111111111'),
    ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'student2@demo.local', 'Taylor Student', '11111111-1111-1111-1111-111111111111'),
    ('33333333-4444-4444-4444-444444444444', 'student3@demo.local', 'Riley Student', '11111111-1111-1111-1111-111111111111'),
    ('44444444-5555-5555-5555-555555555555', 'student4@demo.local', 'Jordan Student', '11111111-1111-1111-1111-111111111111'),
    ('55555555-aaaa-bbbb-cccc-dddddddddddd', 'former@demo.local', 'Casey Former', '11111111-1111-1111-1111-111111111111'),
    ('88888888-9999-9999-9999-999999999999', 'pending@demo.local', 'Pat Pending', '11111111-1111-1111-1111-111111111111'),
    ('55555555-6666-6666-6666-666666666666', 'admin2@demo.local', 'Quinn Owner', '33333333-3333-3333-3333-333333333333'),
    ('66666666-7777-7777-7777-777777777777', 'mentor3@demo.local', 'Sky Mentor', '33333333-3333-3333-3333-333333333333'),
    ('77777777-8888-8888-8888-888888888888', 'student5@demo.local', 'Alex Student', '33333333-3333-3333-3333-333333333333'),
    ('44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'northwind.owner@demo.local', 'Nora Northwind', '44444444-4444-4444-4444-444444444444'),
    ('44444444-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'northwind.admin@demo.local', 'Nolan Admin', '44444444-4444-4444-4444-444444444444'),
    ('44444444-cccc-cccc-cccc-cccccccccccc', 'northwind.mentor@demo.local', 'Nia Mentor', '44444444-4444-4444-4444-444444444444'),
    ('44444444-dddd-dddd-dddd-dddddddddddd', 'northwind.student@demo.local', 'Nico Student', '44444444-4444-4444-4444-444444444444'),
    ('55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'nimbus.owner@demo.local', 'Vera Nimbus', '55555555-5555-5555-5555-555555555555'),
    ('55555555-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'nimbus.admin@demo.local', 'Noah Admin', '55555555-5555-5555-5555-555555555555'),
    ('55555555-cccc-cccc-cccc-cccccccccccc', 'nimbus.mentor@demo.local', 'Nina Mentor', '55555555-5555-5555-5555-555555555555'),
    ('55555555-dddd-dddd-dddd-dddddddddddd', 'nimbus.student@demo.local', 'Niko Student', '55555555-5555-5555-5555-555555555555'),
    ('66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'aurora.owner@demo.local', 'Aria Aurora', '66666666-6666-6666-6666-666666666666'),
    ('66666666-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'aurora.mentor@demo.local', 'Avery Mentor', '66666666-6666-6666-6666-666666666666'),
    ('66666666-cccc-cccc-cccc-cccccccccccc', 'aurora.student@demo.local', 'Aiden Student', '66666666-6666-6666-6666-666666666666'),
    ('77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cedar.owner@demo.local', 'Cora Cedar', '77777777-7777-7777-7777-777777777777'),
    ('77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cedar.admin@demo.local', 'Cal Admin', '77777777-7777-7777-7777-777777777777'),
    ('77777777-cccc-cccc-cccc-cccccccccccc', 'cedar.student@demo.local', 'Casey Student', '77777777-7777-7777-7777-777777777777'),
    ('77777777-dddd-dddd-dddd-dddddddddddd', 'cedar.invited@demo.local', 'Cameron Invite', '77777777-7777-7777-7777-777777777777')
ON CONFLICT (id) DO NOTHING;

INSERT INTO organization_memberships (org_id, user_id, org_role, status, created_by)
VALUES
    ('11111111-1111-1111-1111-111111111111', '99999999-9999-9999-9999-999999999999', 'owner', 'active', NULL),
    ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'admin', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', '22222222-3333-3333-3333-333333333333', 'mentor', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'student', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'student', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', '33333333-4444-4444-4444-444444444444', 'student', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', '44444444-5555-5555-5555-555555555555', 'student', 'active', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', '55555555-aaaa-bbbb-cccc-dddddddddddd', 'student', 'removed', '99999999-9999-9999-9999-999999999999'),
    ('11111111-1111-1111-1111-111111111111', '88888888-9999-9999-9999-999999999999', 'student', 'invited', '99999999-9999-9999-9999-999999999999'),
    ('33333333-3333-3333-3333-333333333333', '55555555-6666-6666-6666-666666666666', 'owner', 'active', NULL),
    ('33333333-3333-3333-3333-333333333333', '66666666-7777-7777-7777-777777777777', 'mentor', 'active', '55555555-6666-6666-6666-666666666666'),
    ('33333333-3333-3333-3333-333333333333', '77777777-8888-8888-8888-888888888888', 'student', 'active', '55555555-6666-6666-6666-666666666666'),
    ('44444444-4444-4444-4444-444444444444', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner', 'active', NULL),
    ('44444444-4444-4444-4444-444444444444', '44444444-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'admin', 'active', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('44444444-4444-4444-4444-444444444444', '44444444-cccc-cccc-cccc-cccccccccccc', 'mentor', 'active', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('44444444-4444-4444-4444-444444444444', '44444444-dddd-dddd-dddd-dddddddddddd', 'student', 'active', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('44444444-4444-4444-4444-444444444444', '99999999-9999-9999-9999-999999999999', 'admin', 'active', '44444444-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('55555555-5555-5555-5555-555555555555', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner', 'active', NULL),
    ('55555555-5555-5555-5555-555555555555', '55555555-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'admin', 'active', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('55555555-5555-5555-5555-555555555555', '55555555-cccc-cccc-cccc-cccccccccccc', 'mentor', 'active', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('55555555-5555-5555-5555-555555555555', '55555555-dddd-dddd-dddd-dddddddddddd', 'student', 'active', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('55555555-5555-5555-5555-555555555555', '99999999-9999-9999-9999-999999999999', 'admin', 'active', '55555555-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('66666666-6666-6666-6666-666666666666', '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner', 'active', NULL),
    ('66666666-6666-6666-6666-666666666666', '66666666-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'mentor', 'active', '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('66666666-6666-6666-6666-666666666666', '66666666-cccc-cccc-cccc-cccccccccccc', 'student', 'active', '66666666-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('77777777-7777-7777-7777-777777777777', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner', 'active', NULL),
    ('77777777-7777-7777-7777-777777777777', '77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'admin', 'active', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('77777777-7777-7777-7777-777777777777', '77777777-cccc-cccc-cccc-cccccccccccc', 'student', 'active', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    ('77777777-7777-7777-7777-777777777777', '77777777-dddd-dddd-dddd-dddddddddddd', 'student', 'invited', '77777777-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
ON CONFLICT (org_id, user_id) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO platform_admins (user_id, role, status, created_by)
VALUES
    ('99999999-9999-9999-9999-999999999999', 'admin', 'active', NULL)
ON CONFLICT (user_id) WHERE deleted_at IS NULL DO NOTHING;
