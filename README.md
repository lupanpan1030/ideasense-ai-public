# IdeaSense AI — Public-Safe Case Study

IdeaSense AI is an AI startup-assessment assistant for early-stage software
founders and student teams. Instead of producing more open-ended chat, it
constrains an idea discussion into a flow that can be advanced, confirmed,
scored, and reviewed:

```text
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

This repository is a **public-safe snapshot** of that product: the application
shell, architecture, API shape, data contracts, and maintainability practices —
without the private production repository, prompts, or question banks.

## What This Demonstrates

This snapshot is meant to show the engineering shape behind IdeaSense AI:

- **Next.js workspace UI** for staged assessment, chat, context panels, and
  report flows.
- **FastAPI orchestration** for auth, project lifecycle, SSE chat, context
  extraction, stage gates, DVF scoring, and report generation.
- **PostgreSQL-backed state contracts** — migrations, seeds, RLS-aware tooling,
  and confirmed-artifact boundaries that keep probabilistic AI output anchored
  to deterministic state.
- **Bounded AI runtime design** — task-specific prompt registry, provider
  routing, parser/fallback behavior, and explicit mutation boundaries.
- **Background jobs** for the work that must not block the visible request path.
- **CI and delivery gates** — backend tests, frontend lint/build, an
  architecture check, and a public-export leak scan.

## Public-Safe Boundary

**Included**

- Next.js frontend and FastAPI backend applications.
- PostgreSQL schema, migrations, and synthetic demo seeds.
- Public API and architecture documentation, plus the case-study docs.
- Synthetic prompt placeholders generated for the public export.
- `resources/question_bank.example.yaml` for the question-bank data shape.

**Excluded**

- Production question banks and production prompt text.
- Private Master Spec details and internal planning/audit documents.
- Real reports, dogfooding evidence, and production smoke artifacts.
- Deployment secrets, provider keys, real users, and real project data.

The public demo can build and boot on synthetic content. It does **not**
represent production assessment quality, scoring method, interview script, or
prompt quality.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Next.js 16 App Router UI (marketing, auth, workspace, chat, reports). |
| `backend/` | FastAPI service (auth, project lifecycle, SSE chat, stage gates, scoring, reports, worker). |
| `database/` | Schema, migrations, seeds, RLS roles, and bootstrap/reset tooling. |
| `schema/` | Stage-data JSON schema contracts. |
| `docs/case-study/` | Portfolio-facing case study (product, architecture, AI runtime, delivery). |
| `docs/spec/`, `docs/ARCHITECTURE.md` | Public-safe spec and system-shape references. |

## Quick Verification

Static checks only — **no database required**:

```bash
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
make architecture-check
make backend-check
make frontend-lint
make frontend-build
```

`npm ci` installs from the committed lockfile for a reproducible tree. It may
report dependency-audit findings; treat those separately from the
build/lint/test gate.

## Requirements

- Node.js 20.9+ (lockfile requires `>=20.9.0`; CI uses Node 20)
- npm
- Python 3.11+ (CI uses Python 3.12)
- PostgreSQL — only for the full local API/database flow

## Run Locally

### 1. Configure environment

```bash
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
```

The example backend env uses local dummy values. Replace only your local
database credentials. Do not add real provider keys unless you are intentionally
testing live LLM behavior.

### 2. Set up the database

`bootstrap_db.py` runs `CREATE DATABASE` by **connecting to the database named in
`DATABASE_URL_ADMIN`**, so that admin DSN must point at an *existing maintenance
database* (e.g. `postgres`) — not at the target database you are about to
create. The connecting role also needs privileges to create databases and apply
roles.

```bash
DATABASE_URL_ADMIN=postgresql+psycopg2://<admin-role>@localhost:5432/postgres \
  python database/scripts/bootstrap_db.py \
  --db-name ideasense_ai_dev \
  --question-bank-yaml resources/question_bank.example.yaml
```

This connects to `postgres`, creates `ideasense_ai_dev`, runs migrations, applies
the `app_runtime` / `app_worker` / `app_migrations` role grants, and imports the
synthetic question bank (falling back to `resources/question_bank.example.yaml`
when the private production bank is absent).

After bootstrap, point `backend/.env` at a local role that can connect to
`ideasense_ai_dev`. The `ideasense_user` / `ideasense_pwd` values in
`backend/.env.example` are placeholders; create that login role yourself or
replace the DSN with your own local development role.

To (re)import only the example question bank into an existing database:

```bash
python database/scripts/import_question_bank.py \
  --dsn "postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev" \
  --yaml resources/question_bank.example.yaml
```

### 3. Start the services

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Worker (separate terminal, for background jobs)
cd backend && python -m app.worker

# Frontend
cd frontend && npm run dev
```

Open `http://localhost:3000`.

## Case Study Reading Path

Start here if you are reviewing this as a portfolio project. The case study is
the part written for reviewers; the spec/architecture files are the engineering
references it points back to.

1. [`docs/case-study/00-overview.md`](docs/case-study/00-overview.md) — scope, boundaries, and the full doc map.
2. [`docs/case-study/01-product-methodology.md`](docs/case-study/01-product-methodology.md) — positioning, DVF, stage gates, uncertainty handling.
3. [`docs/case-study/02-architecture-overview.md`](docs/case-study/02-architecture-overview.md) — system shape and main data flow.
4. [`docs/case-study/03-ai-runtime.md`](docs/case-study/03-ai-runtime.md) — prompt task registry, provider routing, fallback, AI output bounds.
5. [`docs/case-study/04-state-and-data-contract.md`](docs/case-study/04-state-and-data-contract.md) — stage state machine and database contracts.
6. [`docs/case-study/05-latency-case-study.md`](docs/case-study/05-latency-case-study.md) — visible wait paths and sync/async boundaries.
7. [`docs/case-study/06-security-reliability-delivery.md`](docs/case-study/06-security-reliability-delivery.md) — permissions, RLS, testing, delivery evidence.

Deeper technical evidence lives in [`docs/case-study/deep-dives/`](docs/case-study/deep-dives/).

## Prompt And Question Content

Public export prompts are synthetic placeholders — they exist so the app can load
prompt files and pass runtime checks without shipping production prompt
contracts. The example question bank is synthetic and shape-only: suitable for
demo setup and development wiring, not for real startup assessment.

## Reference Documentation

- [`docs/spec/PUBLIC_SPEC.md`](docs/spec/PUBLIC_SPEC.md) — public-safe flow and contract summary.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system shape and ownership boundaries.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution expectations.
- [`SECURITY.md`](SECURITY.md) — vulnerability reporting and data-handling boundaries.

## License

Code and documentation in this public-safe snapshot are licensed under the
Apache License 2.0. See [`LICENSE`](LICENSE).

This license applies to the exported public-safe repository contents only. It
does not publish or relicense the private production repository, production
prompts, deployment configuration, real project data, internal planning
documents, or private Git history.
