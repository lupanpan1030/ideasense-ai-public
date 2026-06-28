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

**Live:** [ideasenseai.com](https://www.ideasenseai.com) · **See output without signing up:** [Sample report](https://www.ideasenseai.com/en/sample-report) · [Sample workspace](https://www.ideasenseai.com/en/sample) · [Case study](docs/case-study/00-overview.md)

[![CI](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml/badge.svg)](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## Architecture at a Glance

```mermaid
flowchart LR
    U["Browser · Next.js workspace UI<br/>chat · context board · stage gate · reports"]
    API["FastAPI orchestration<br/>auth · projects · chat · assessment · reports<br/>stage runtime · prompt runtime · scoring"]
    DB[("PostgreSQL — state authority + RLS<br/>projects · messages · assessments<br/>reports · background_jobs")]
    W["Background worker<br/>extraction · stage summary<br/>finalize · verification · report gen"]
    LLM["LLM task runtime<br/>prompt registry · provider routing<br/>parser · fallback · mutation class"]
    P["Providers<br/>OpenAI-compatible · Gemini · Bedrock"]

    U -->|"POST /chat/stream"| API
    API -->|"SSE stream + control events"| U
    API <--> DB
    DB -.->|"background_jobs"| W
    W <--> DB
    API --> LLM
    W --> LLM
    LLM --> P
```

The hard part is not calling a model — it is constraining model output inside
deterministic product state, stage-gate confirmation, and auditable artifacts.
Full walkthrough in [02-architecture-overview.md](docs/case-study/02-architecture-overview.md).

## For Reviewers

If you are evaluating this as a portfolio project, the highest-signal pieces are:

- **AI workflow governance** — a task-specific prompt registry with provider routing, parser contracts, and explicit mutation boundaries. ([03-ai-runtime.md](docs/case-study/03-ai-runtime.md))
- **Deterministic state contracts** — a stage engine + Stage Gate that stop the AI from silently advancing project state. ([04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md))
- **SSE + worker latency split** — visible streaming on the request path, slow work moved to background jobs. ([05-latency-case-study.md](docs/case-study/05-latency-case-study.md))
- **Public-export leak gate** — CI checks help prevent production prompts/IP from entering the public snapshot. ([06-security-reliability-delivery.md](docs/case-study/06-security-reliability-delivery.md))

**5-minute path:** open the [sample report](https://www.ideasenseai.com/en/sample-report) → skim [00-overview.md](docs/case-study/00-overview.md) → read the [architecture overview](docs/case-study/02-architecture-overview.md). The full reading order is in [Case Study Reading Path](#case-study-reading-path) below.

## What This Demonstrates

| Engineering problem | How IdeaSense AI handles it |
| --- | --- |
| LLM output is probabilistic and can silently drift | Deterministic stage engine + Stage Gate confirmation; the AI cannot advance project state on its own. |
| Model output must not corrupt project state | Bounded AI runtime: task-specific prompt registry, parser contracts, fallback policy, explicit mutation boundaries. |
| Chat must feel responsive while real work is slow | SSE for visible streaming; a background worker moves extraction, scoring, and report generation off the request path. |
| State must be auditable and recoverable | PostgreSQL as source of truth — migrations, RLS, confirmed-artifact and context-version contracts. |
| Provider availability and cost vary | Multi-provider routing (OpenAI-compatible / Gemini / Bedrock) with per-task chains and fallback. |
| A public snapshot needs explicit public-export safeguards | CI gates: backend tests, frontend lint/build, an architecture check, and a public-export leak scan. |

## Public-Safe Boundary

| Included | Excluded |
| --- | --- |
| Next.js frontend + FastAPI backend apps | Production question banks and prompt text |
| PostgreSQL schema, migrations, synthetic seeds | Private Master Spec and internal planning/audit docs |
| Public API, architecture, and case-study docs | Real reports, dogfooding evidence, smoke artifacts |
| Synthetic prompt placeholders | Deployment secrets, provider keys, real users/data |
| `resources/question_bank.example.yaml` (shape only) | — |

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
