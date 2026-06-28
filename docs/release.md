# Release Guide

This guide describes the private repository release flow. It does not authorize
making this repository public.

## Pre-Release Checks

Run the relevant quality gates:

```bash
git diff --check
make architecture-check
make backend-check
make frontend-lint
make frontend-test
make frontend-build
```

For broad changes, run:

```bash
make check
```

## Environment Review

Before deploying, confirm:

- `APP_ENV=production`.
- Development bypass flags are disabled.
- `CORS_ALLOW_ORIGINS` is set to the production frontend origin.
- Provider keys and database URLs are configured only in the deployment
  environment.
- Captcha and email settings match the production requirements.
- Admin routes are enabled only when intended.

See `docs/production-env.md` for environment details.

## Deployment Notes

The private repository remains the production source of truth. Deployment
evidence, smoke artifacts, and dogfooding recordings should stay private unless
they are explicitly reviewed and approved for public use.

## Rollback

Rollback should restore the last known-good application version and matching
database contract. Do not roll back schema-dependent application code without
checking migration compatibility.

## Public Export

Public-safe export is a separate release path:

- Export to a new repository or directory.
- Use a clean initial commit.
- Exclude private assessment content and private evidence.
- Verify public-safe replacement content before publishing.

See `docs/adr/0001-public-private-content-boundary.md`.
