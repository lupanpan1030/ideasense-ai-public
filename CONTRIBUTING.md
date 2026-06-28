# Contributing

IdeaSense AI is developed from the private production/IP repository. Changes
should preserve the product boundary:

`project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report`

Do not reposition the product as a generic chatbot, survey builder, task
manager, calendar, autonomous agent platform, or CRM.

## Before You Change Code

Read the local guidance relevant to the change:

- `README.md` for setup and project status.
- `docs/ARCHITECTURE.md` for the current system shape.
- `docs/CONVENTIONS.md` for backend layering and ownership.
- `docs/OWNERSHIP_MAP.md` before moving logic or adding shared helpers.
- `docs/DEFINITION_OF_DONE.md` for verification expectations.
- `docs/spec/PUBLIC_SPEC.md` for the public-safe contract summary. Private
  production contract changes use `docs/spec/MASTER_SPEC.md` in the private
  source repository.
- `docs/adr/0001-public-private-content-boundary.md` before public/export work.

## Scope Discipline

- Keep each change scoped to one product or technical boundary.
- Do not mix public-export cleanup, product behavior, auth, admin, report, and
  infrastructure changes in one commit.
- Do not add duplicate route handlers, duplicate client helpers, or route-local
  copies of service-owned logic.
- Temporary dual paths need an owner, a removal condition, and tests.

## Public / Private Content

This repository may contain proprietary production content. Do not move, copy,
or paraphrase private assessment content into public-safe files.

Public-safe examples must be synthetic and clearly labeled. See:

- `docs/adr/0001-public-private-content-boundary.md`
- `resources/question_bank.example.yaml`
- `docs/spec/PUBLIC_SPEC.md`
- `backend/app/prompts.example/README.md`

## Verification

Use the smallest meaningful check first:

```bash
git diff --check
make architecture-check
make backend-check
make frontend-lint
make frontend-build
```

For broad changes, run:

```bash
make check
```

State exactly which checks were run before marking work complete.
