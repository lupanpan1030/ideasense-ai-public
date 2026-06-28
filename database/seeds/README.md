# Seed Data

Purpose: baseline data for local/dev environments. Apply manually or via `database/scripts/reset_db.py`.

Suggested use:
- keep data idempotent
- avoid production secrets
- document how to load in project tooling

Seed script:
- `database/seeds/seed_dev.sql`
- Seed flows live under `database/seeds/flows/` and are included by the master script.

Prerequisite:
- Import the question bank first (seed uses `question_bank_versions` + `question_bank_questions`).

Apply with psql:
```
psql "postgres://USER:PASSWORD@HOST:PORT/DBNAME" -f database/seeds/seed_dev.sql
```

To run a single flow:
```
psql "postgres://USER:PASSWORD@HOST:PORT/DBNAME" -f database/seeds/flows/<flow>/<flow>_seed.sql
```

Dev super admin:
- Email: `superadmin@demo.local`
- Password: `12345678`
- Stored in `user_identities` using `crypt(..., gen_salt('bf'))` (pgcrypto/bcrypt).

Seed login accounts (local auth):
- IdeaSenseAI Demo (`demo12345`): `admin@demo.local`, `mentor@demo.local`, `mentor2@demo.local`, `student1@demo.local`, `student2@demo.local`, `student3@demo.local`, `student4@demo.local`
- IdeaSenseAI Labs (`labs12345`): `admin2@demo.local`, `mentor3@demo.local`, `student5@demo.local`
- Northwind Academy (`northwind123`): `northwind.owner@demo.local`, `northwind.admin@demo.local`, `northwind.mentor@demo.local`, `northwind.student@demo.local`
- Nimbus Ventures (`nimbus123`): `nimbus.owner@demo.local`, `nimbus.admin@demo.local`, `nimbus.mentor@demo.local`, `nimbus.student@demo.local`
- Aurora Health (`aurora123`): `aurora.owner@demo.local`, `aurora.mentor@demo.local`, `aurora.student@demo.local`
- Cedar Labs (`cedar123`): `cedar.owner@demo.local`, `cedar.admin@demo.local`, `cedar.student@demo.local`
- Note: `cedar.invited@demo.local` uses `cedar123` but membership is invited (403 until accepted).

DEV auth bypass quick start (admin shell testing):
- Apply `database/seeds/flows/org/org_seed.sql` if you are not importing the question bank.
- Use `DEV_AUTH_BYPASS=1`.
- Use `DEV_ORG_ID=11111111-1111-1111-1111-111111111111`.
- Use `DEV_USER_ID=99999999-9999-9999-9999-999999999999` (owner) or `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` (admin).

Flow overview:
- `org/`: orgs, users, memberships (includes invited/removed members).
- `auth/`: local identities (includes disabled identity for failure cases).
- `cohorts/`: cohorts + cohort memberships (includes removed membership).
- `assignments/`: mentor assignments (active/pending/revoked).
- `projects/`: projects, runtime, question instances (answered/invalid/needs_info).
- `evidence/`: conversation messages + project states/events.
- `outputs/`: stage assessments + reports + comments (draft/final/confirmed).
- `evaluations/`: rubrics + answer/message evaluations (high/low scores).
- `assets/`: documents + notifications (uploaded/failed/indexed, read/unread).
- `ops/`: background jobs + analytics/audit events (succeeded/failed/running).
