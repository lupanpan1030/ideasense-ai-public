-- Reports, assessments, and comments.
INSERT INTO project_stage_assessments (
    id,
    org_id,
    project_id,
    stage,
    draft_summary_markdown,
    final_summary_markdown,
    confirmed,
    confirmed_by_user_id,
    generated_from_state_version
)
VALUES
    (
        '123e4567-e89b-12d3-a456-426614174010',
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'problem',
        'Student has a clear statement of problem and target users.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174011',
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        'market',
        'Target market is defined as university incubator programs.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174012',
        '11111111-1111-1111-1111-111111111111',
        '77777777-7777-7777-7777-777777777777',
        'problem',
        'Problem statement is promising; segment needs tightening.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174013',
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        'market',
        'Market draft incomplete; missing pricing details.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174014',
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999998',
        'tech',
        'Tech track started; awaiting deeper architecture details.',
        'Confirmed by admin.',
        true,
        '99999999-9999-9999-9999-999999999999',
        1
    )
ON CONFLICT (project_id, stage) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO project_stage_assessments (
    id,
    org_id,
    project_id,
    stage,
    draft_summary_markdown,
    final_summary_markdown,
    confirmed,
    confirmed_by_user_id,
    generated_from_state_version
)
VALUES
    (
        '223e4567-e89b-12d3-a456-426614174110',
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        'problem',
        'Interview plan is clear; gather five more founder quotes.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174111',
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        'market',
        'Market hypothesis is promising; add a competitor snapshot.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174112',
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        'tech',
        'Tech path drafted; validate build constraints with advisors.',
        'Confirmed: proceed with a fast prototype.',
        true,
        '55555555-6666-6666-6666-666666666666',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174113',
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        'problem',
        'Engagement baseline captured; define a success metric.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174114',
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        'market',
        'Market scope is broad; tighten the target segment definition.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174115',
        '66666666-6666-6666-6666-666666666666',
        '18181818-2222-3333-4444-555555555562',
        'problem',
        'Clinical workflow pain noted; map the top stakeholders.',
        NULL,
        false,
        NULL,
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174116',
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        'problem',
        'Sustainability scope is clear; gather initial data sources.',
        NULL,
        false,
        NULL,
        1
    )
ON CONFLICT (project_id, stage) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO project_reports (
    id,
    org_id,
    project_id,
    report_version,
    status,
    content_markdown,
    generated_from_state_version
)
VALUES
    (
        '123e4567-e89b-12d3-a456-426614174000',
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        1,
        'final',
        '## Summary\n\nProblem framing is solid. Next step: validate pain with 5 interviews.',
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174001',
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        1,
        'final',
        '## Summary\n\nMarket definition is clear. Next step: test outreach channels.',
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174002',
        '11111111-1111-1111-1111-111111111111',
        '77777777-7777-7777-7777-777777777777',
        1,
        'final',
        '## Summary\n\nGood problem clarity. Next step: validate willingness to pay.',
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174003',
        '11111111-1111-1111-1111-111111111111',
        '88888888-8888-8888-8888-888888888888',
        1,
        'draft',
        '## Draft\n\nPricing and buyer roles need clarification.',
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174004',
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999998',
        1,
        'final',
        '## Summary\n\nTech routing complete. Next: detailed architecture choices.',
        1
    ),
    (
        '123e4567-e89b-12d3-a456-426614174005',
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        1,
        'final',
        '## Summary\n\nPromising pilot. Next: run 3 advisor interviews.',
        1
    )
ON CONFLICT (project_id, report_version) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO project_reports (
    id,
    org_id,
    project_id,
    report_version,
    status,
    content_markdown,
    generated_from_state_version
)
VALUES
    (
        '223e4567-e89b-12d3-a456-426614174200',
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        1,
        'draft',
        '## Draft\n\nInterview script ready. Next: conduct five founder calls.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174201',
        '11111111-1111-1111-1111-111111111111',
        '13131313-2222-3333-4444-555555555557',
        1,
        'draft',
        '## Draft\n\nNeed a competitor matrix and pricing test plan.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174202',
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        1,
        'draft',
        '## Draft\n\nExplore no-code for a two-week prototype; list required integrations.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174203',
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        1,
        'final',
        '## Summary\n\nCohort engagement friction identified. Next: pilot weekly check-ins.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174204',
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        1,
        'draft',
        '## Draft\n\nRefine target hub list and pricing assumptions.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174205',
        '66666666-6666-6666-6666-666666666666',
        '18181818-2222-3333-4444-555555555562',
        1,
        'draft',
        '## Draft\n\nMap top three coordinator workflows and time spent.',
        1
    ),
    (
        '223e4567-e89b-12d3-a456-426614174206',
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        1,
        'final',
        '## Summary\n\nEarly adopters identified; next step is a data ingestion pilot.',
        1
    )
ON CONFLICT (project_id, report_version) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO project_comments (
    id,
    org_id,
    project_id,
    author_user_id,
    visibility,
    status,
    content,
    content_format,
    target_report_id
)
VALUES
    (
        '123e4567-e89b-12d3-a456-426614174020',
        '11111111-1111-1111-1111-111111111111',
        '11111111-2222-3333-4444-555555555555',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'student_and_mentors',
        'open',
        'Nice progress. Add 2-3 concrete pain quotes in the report.',
        'markdown',
        '123e4567-e89b-12d3-a456-426614174000'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174021',
        '11111111-1111-1111-1111-111111111111',
        '66666666-7777-8888-9999-aaaaaaaaaaaa',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'student_and_mentors',
        'open',
        'Great market definition. Try to quantify top 3 channels.',
        'markdown',
        '123e4567-e89b-12d3-a456-426614174001'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174022',
        '11111111-1111-1111-1111-111111111111',
        '77777777-7777-7777-7777-777777777777',
        '22222222-3333-3333-3333-333333333333',
        'student_and_mentors',
        'open',
        'Clarify the initial segment before moving to pricing.',
        'markdown',
        '123e4567-e89b-12d3-a456-426614174002'
    ),
    (
        '123e4567-e89b-12d3-a456-426614174023',
        '33333333-3333-3333-3333-333333333333',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaabbbb',
        '66666666-7777-7777-7777-777777777777',
        'student_and_mentors',
        'open',
        'Pilot looks strong. Capture 2 mentor testimonials.',
        'markdown',
        '123e4567-e89b-12d3-a456-426614174005'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO project_comments (
    id,
    org_id,
    project_id,
    author_user_id,
    visibility,
    status,
    content,
    content_format,
    target_report_id
)
VALUES
    (
        '223e4567-e89b-12d3-a456-426614174320',
        '11111111-1111-1111-1111-111111111111',
        '12121212-2222-3333-4444-555555555556',
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'student_and_mentors',
        'open',
        'Nice start. Capture two direct quotes from founders.',
        'markdown',
        '223e4567-e89b-12d3-a456-426614174200'
    ),
    (
        '223e4567-e89b-12d3-a456-426614174321',
        '33333333-3333-3333-3333-333333333333',
        '15151515-2222-3333-4444-555555555559',
        '66666666-7777-7777-7777-777777777777',
        'student_and_mentors',
        'open',
        'Define the quickest validation milestone before choosing the stack.',
        'markdown',
        '223e4567-e89b-12d3-a456-426614174202'
    ),
    (
        '223e4567-e89b-12d3-a456-426614174322',
        '44444444-4444-4444-4444-444444444444',
        '16161616-2222-3333-4444-555555555560',
        '44444444-cccc-cccc-cccc-cccccccccccc',
        'student_and_mentors',
        'open',
        'Add a simple engagement KPI to measure the pilot.',
        'markdown',
        '223e4567-e89b-12d3-a456-426614174203'
    ),
    (
        '223e4567-e89b-12d3-a456-426614174323',
        '55555555-5555-5555-5555-555555555555',
        '17171717-2222-3333-4444-555555555561',
        '55555555-cccc-cccc-cccc-cccccccccccc',
        'student_and_mentors',
        'open',
        'Pick one hub and run five outreach calls.',
        'markdown',
        '223e4567-e89b-12d3-a456-426614174204'
    ),
    (
        '223e4567-e89b-12d3-a456-426614174324',
        '77777777-7777-7777-7777-777777777777',
        '19191919-2222-3333-4444-555555555563',
        '77777777-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'student_and_mentors',
        'open',
        'Clarify which lab systems you can integrate first.',
        'markdown',
        '223e4567-e89b-12d3-a456-426614174206'
    )
ON CONFLICT (id) DO NOTHING;
