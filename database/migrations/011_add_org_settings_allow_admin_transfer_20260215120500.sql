-- 011) Org setting: allow admins to transfer ownership

ALTER TABLE organizations
    ALTER COLUMN settings SET DEFAULT '{
        "org_type": "institution",
        "allow_cohorts": true,
        "allow_mentor_assignments": true,
        "default_mentor_visibility": "summaries_only",
        "allow_admin_transfer_ownership": false
    }'::jsonb;

UPDATE organizations
SET settings = jsonb_set(
    COALESCE(settings, '{}'::jsonb),
    '{allow_admin_transfer_ownership}',
    'false'::jsonb,
    true
)
WHERE NOT (settings ? 'allow_admin_transfer_ownership');
