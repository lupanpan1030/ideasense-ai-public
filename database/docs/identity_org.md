# Identity + Organization Schema

Defines the core identity, organization, and cohort tables used for auth, tenancy,
and access control boundaries.

## Scope
- `users` + `user_identities`
- `organizations` + `organization_memberships` + `organization_invitations`
- `cohorts` + `cohort_memberships`
- `mentor_student_assignments`

## Conventions
- Soft deletes use `deleted_at`; business uniqueness is enforced with partial
  indexes on `deleted_at IS NULL`.
- Email/slug inputs are normalized via trim + no-whitespace checks; slugs are
  lowercase.
- Email columns are `CITEXT` for case-insensitive comparisons.

## Notes
- `organizations.settings` carries org policy switches, including:
  `org_type`, `allow_cohorts`, `allow_mentor_assignments`,
  `default_mentor_visibility`. For private orgs, set `org_type=private`,
  `allow_cohorts=false`, and `allow_mentor_assignments=false` at creation time.
- `cohort_memberships` uses a composite FK `(org_id, cohort_id)` that references
  `cohorts (org_id, id)` to keep org boundaries consistent. This requires a
  non-partial unique constraint on `cohorts (org_id, id)`.
- `mentor_student_assignments` enforces org/cohort membership via a trigger that
  checks active (or invited) org memberships and active cohort memberships.
