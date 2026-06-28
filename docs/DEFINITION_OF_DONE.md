# Definition of Done

## Status
- Applies repo-wide across backend, frontend, database, and documentation changes.

## Quality Gates (Current / Enforced)
Source of truth: `Makefile` and `.github/workflows/ci.yml`.

- Backend syntax and tests (compileall + pytest): `make backend-check`.
- Architecture guard for duplicate routes and single-owner helpers: `make architecture-check`.
- Frontend lint: `make frontend-lint`.
- Frontend Node tests: `make frontend-test`.
- Frontend typecheck + build: `make frontend-build`.
- Manual public-entry Playwright smoke: `make frontend-e2e-smoke`.
- Aggregate gate: `make check` passes.

## Quality Gates (Target / Planned)
Not enforced yet (track and implement as needed):

- Backend lint and format check: `make backend-lint`.
- Backend type check: included in `make backend-lint`.
- Contract check: `make backend-contract`.

## Testing and Edge Cases
- Add or update tests for new behavior, including edge cases and negative paths.
- For DB changes, validate schema + seed impact and update contract checks if needed.

## Regression Checks
- Re-run the full quality gate (`make check`) before merging.
- Verify any API contract changes against `docs/spec/MASTER_SPEC.md` in the
  private repository, or `docs/spec/PUBLIC_SPEC.md` in public-safe exports.
- If schema changes are required, update `database/migrations/` and refresh `database/schema/` snapshots.

## Documentation
- Update `docs/ARCHITECTURE.md` for module or data flow changes.
- Update `docs/spec/MASTER_SPEC.md` for private contract changes and bump
  version; mirror public-safe summaries into `docs/spec/PUBLIC_SPEC.md` when the
  public contract description changes.
