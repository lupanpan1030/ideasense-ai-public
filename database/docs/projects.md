# Projects Schema

Defines project ownership, stage state, and runtime pointers for the interview
flow.

## Scope
- `projects`
- `project_runtime`

## Conventions
- `projects` uses a composite FK `(org_id, cohort_id)` to keep org/cohort
  consistency without triggers.
- `project_runtime` uses a composite FK `(org_id, project_id)` to keep org
  boundaries aligned with the parent project.
- Runtime question pointers are validated by a trigger to ensure the referenced
  questions match the project's question bank and the runtime stage/variant.
