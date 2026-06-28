# IdeaSense AI

**An AI startup-assessment assistant that turns a rough idea into a structured, reviewable case.**

IdeaSense AI helps early-stage software founders and student teams move from “I have an idea” to a concrete assessment: what the product is, who it is for, what assumptions are still weak, and how the idea scores across desirability, viability, and feasibility.

The key design choice is simple:

> **AI proposes; product state decides.**

The assistant can ask questions, extract context, and draft assessments. It cannot silently advance the project, overwrite confirmed context, or turn uncertain model output into permanent product state without deterministic checks.

```text
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

This repository is a **public-safe snapshot** of the product. It includes the application shell, architecture, API shape, database contracts, CI checks, and case-study documentation. It does **not** include the private production repository, production prompts, real question banks, real user data, secrets, or internal planning docs.

**Live product:** [ideasenseai.com](https://www.ideasenseai.com)

**See output without signing up:** [Sample report](https://www.ideasenseai.com/en/sample-report) · [Sample workspace](https://www.ideasenseai.com/en/sample) · [Case study](docs/case-study/00-overview.md)

[![CI](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml/badge.svg)](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Languages:** English · [中文](README.zh-CN.md)

**License:** Apache 2.0

## Product Preview

Public live surfaces from the product:

| Homepage workflow | Sample report scroll |
| --- | --- |
| [![IdeaSense AI homepage product walkthrough](docs/assets/readme/ideasense-homepage-preview.gif)](https://www.ideasenseai.com) | [![IdeaSense AI sample report scrolling through assessment sections](docs/assets/readme/ideasense-sample-report-scroll.gif)](https://www.ideasenseai.com/en/sample-report) |

Live homepage: [ideasenseai.com](https://www.ideasenseai.com) · No-login pages: [Sample report](https://www.ideasenseai.com/en/sample-report) · [Sample workspace](https://www.ideasenseai.com/en/sample)

## Why This Project Exists

A lot of AI product demos stop at “the model can answer questions.” That was not enough for this product.

For a startup-assessment assistant, the hard problems are product-control problems:

- What exactly did the system learn from the founder?
- Which parts were confirmed by the user, and which parts are still inferred?
- When is the project allowed to move to the next stage?
- How do we stop a fluent model response from corrupting durable state?
- How do we generate a report that is useful, traceable, and repeatable enough to review?

IdeaSense AI treats assessment as a workflow, not a free-form chat. The model is useful, but it is bounded by stage contracts, parser contracts, explicit mutation rules, and confirmation gates.

## Start Here

For reviewers, the fastest path is:

1. Open the [sample report](https://www.ideasenseai.com/en/sample-report) to see the kind of artifact the workflow produces.
2. Skim [00-overview.md](docs/case-study/00-overview.md) for the public-safe scope and reading map.
3. Read [02-architecture-overview.md](docs/case-study/02-architecture-overview.md) for the main system flow.

The highest-signal technical sections are:

- **AI workflow governance** — task-specific prompt registry, provider routing, parser contracts, fallback policy, and explicit mutation boundaries. ([03-ai-runtime.md](docs/case-study/03-ai-runtime.md))
- **Deterministic state contracts** — stage engine and Stage Gate logic that prevent the AI from silently advancing project state. ([04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md))
- **Latency split** — SSE keeps the chat path visible while extraction, scoring, and report work move to background jobs. ([05-latency-case-study.md](docs/case-study/05-latency-case-study.md))
- **Public-export safety** — CI checks help keep production prompts, private docs, and secrets out of this snapshot. ([06-security-reliability-delivery.md](docs/case-study/06-security-reliability-delivery.md))

## Architecture at a Glance

```mermaid
flowchart TD
    UI["Browser / Next.js workspace<br/>chat · context board · stage gate · reports"]
    API["FastAPI orchestration<br/>/api/v1 routes · auth · projects · chat · reports"]
    Workflow["Deterministic workflow layer<br/>stage runtime · permissions · scoring"]
    DB[("PostgreSQL + RLS<br/>projects · project_runtime · project_states<br/>conversation_messages<br/>project_stage_assessments<br/>project_reports")]
    Queue[("background_jobs queue")]
    Worker["Background worker<br/>extract · summarize · finalize<br/>verify claims · generate reports"]
    Prompt["Bounded AI runtime<br/>task registry · parser contracts<br/>fallback policy · mutation classes"]
    Providers["Provider chain<br/>OpenAI-compatible APIs<br/>OpenAI · DeepSeek · Qwen<br/>Gemini · Bedrock"]

    UI -->|"POST /api/v1/chat/stream"| API
    API -.->|"SSE tokens + control events"| UI
    API --> Workflow
    Workflow --> DB
    Workflow --> Queue
    Queue -->|"poll + claim"| Worker
    Worker --> DB
    Workflow --> Prompt
    Worker --> Prompt
    Prompt --> Providers

    classDef ui fill:#eef6ff,stroke:#2563eb,color:#0f172a;
    classDef api fill:#f8fafc,stroke:#64748b,color:#0f172a;
    classDef state fill:#ecfdf5,stroke:#059669,color:#0f172a;
    classDef worker fill:#fff7ed,stroke:#ea580c,color:#0f172a;
    classDef ai fill:#f5f3ff,stroke:#7c3aed,color:#0f172a;
    class UI ui;
    class API,Workflow api;
    class DB,Queue state;
    class Worker worker;
    class Prompt,Providers ai;
```

The important boundary is between model output and product state. The model may produce candidate text or structured output, but the application decides whether that output is valid, where it may be stored, and whether it is allowed to change the project’s stage. The worker does not receive database pushes; it claims queued `background_jobs` and writes artifacts back through controlled backend paths.

Full walkthrough: [02-architecture-overview.md](docs/case-study/02-architecture-overview.md).

## How IdeaSense Remembers Context

IdeaSense does not treat memory as a vector store or raw chat replay. It promotes conversation into versioned product state. Open each layer to see where the system draws the boundary between model output, user confirmation, and durable artifacts.

<details open>
<summary><strong>1. Conversation</strong> — volatile input</summary>

User answers and assistant turns stay visible in `conversation_messages`, but they are not automatically trusted as durable product state.

</details>

<details>
<summary><strong>2. Extraction + guards</strong> — candidate structured fields</summary>

Extraction maps free-form answers to controlled schema paths. Direct user answers can update `project_states.state_json`; uncertain AI-suggested values are held back for confirmation.

</details>

<details>
<summary><strong>3. pending_confirm</strong> — field-level user review</summary>

AI-suggested or ambiguous fields can sit in `state_meta.pending_confirm` until the user accepts, edits, or rejects them. Accepting promotes the value into structured state; rejecting drops it.

</details>

<details>
<summary><strong>4. project_states</strong> — versioned product memory</summary>

`project_states` stores `state_json`, `state_meta`, and `state_version`. The version boundary prevents users from confirming stale summaries after the context has changed.

</details>

<details>
<summary><strong>5. Stage Gate</strong> — stage-level confirmation</summary>

Stage summaries become durable `project_stage_assessments` only after the user confirms the current context version. The AI can propose a summary, but it cannot silently advance the project stage.

</details>

<details>
<summary><strong>6. Final artifacts</strong> — auditable report output</summary>

Context cards and `project_reports` are generated from confirmed stage artifacts and carry the state version they were generated from, including assumptions, unknowns, and evidence gaps.

</details>

Detailed state contract: [04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md).

## What This Demonstrates

| Product/engineering problem | How IdeaSense AI handles it |
| --- | --- |
| LLM output is probabilistic and can drift silently | A deterministic stage engine and Stage Gate confirmation decide when the project may advance. |
| Model output must not corrupt durable state | The AI runtime is bounded by task-specific prompts, parser contracts, fallback policy, and explicit mutation classes. |
| Chat must feel responsive even when real work is slow | The request path uses SSE for visible streaming; slower extraction, scoring, and report generation run through a background worker. |
| State needs to be auditable and recoverable | PostgreSQL is the source of truth, with migrations, RLS, confirmed-artifact contracts, and context-version contracts. |
| Provider availability, behavior, and cost vary | Per-task provider chains support OpenAI-compatible providers, Gemini, and Bedrock with fallback behavior. |
| A public portfolio repo needs explicit leak safeguards | CI gates cover backend tests, frontend lint/build, architecture checks, and public-export leak scanning. |

## Public-Safe Boundary

This repository is intended to show engineering judgment without publishing the private production system.

| Included | Excluded |
| --- | --- |
| Next.js frontend and FastAPI backend apps | Production question banks and production prompt text |
| PostgreSQL schema, migrations, synthetic seeds, and RLS roles | Private Master Spec and internal planning/audit docs |
| Public API shape, architecture docs, and case-study docs | Private reports, non-public dogfooding evidence, smoke artifacts |
| Synthetic prompt placeholders | Deployment secrets, provider keys, real users/data |
| `resources/question_bank.example.yaml` shape-only example | Private production assessment methodology |

The public demo can build and boot on synthetic content. It does **not** represent production assessment quality, scoring method, interview script, or prompt quality.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Next.js 16 App Router UI for marketing, auth, workspace, chat, and reports. |
| `backend/` | FastAPI service for auth, project lifecycle, SSE chat, stage gates, scoring, reports, and worker jobs. |
| `database/` | Schema, migrations, seeds, RLS roles, and bootstrap/reset tooling. |
| `schema/` | Stage-data JSON schema contracts. |
| `docs/case-study/` | Portfolio-facing case study: product, architecture, AI runtime, state, latency, and delivery. |
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

`npm ci` installs from the committed lockfile for a reproducible tree. It may report dependency-audit findings; treat those separately from the build/lint/test gate.

## Requirements

- Node.js 20.9+ — the lockfile requires `>=20.9.0`; CI uses Node 20.
- npm
- Python 3.11+ — CI uses Python 3.12.
- PostgreSQL — only required for the full local API/database flow.

## Run Locally

### 1. Configure environment

```bash
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
```

The example backend env uses local dummy values. Replace only your local database credentials. Do not add real provider keys unless you are intentionally testing live LLM behavior.

### 2. Set up the database

`bootstrap_db.py` runs `CREATE DATABASE` by **connecting to the database named in `DATABASE_URL_ADMIN`**, so that admin DSN must point at an *existing maintenance database* such as `postgres`, not at the target database you are about to create. The connecting role also needs privileges to create databases and apply roles.

```bash
DATABASE_URL_ADMIN=postgresql+psycopg2://<admin-role>@localhost:5432/postgres \
  python database/scripts/bootstrap_db.py \
  --db-name ideasense_ai_dev \
  --question-bank-yaml resources/question_bank.example.yaml
```

This connects to `postgres`, creates `ideasense_ai_dev`, runs migrations, applies the `app_runtime` / `app_worker` / `app_migrations` role grants, and imports the synthetic question bank. It falls back to `resources/question_bank.example.yaml` when the private production bank is absent.

After bootstrap, point `backend/.env` at a local role that can connect to `ideasense_ai_dev`. The `ideasense_user` / `ideasense_pwd` values in `backend/.env.example` are placeholders; create that login role yourself or replace the DSN with your own local development role.

To import only the example question bank into an existing database:

```bash
python database/scripts/import_question_bank.py \
  --dsn "postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev" \
  --yaml resources/question_bank.example.yaml
```

### 3. Start the services

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Worker, in a separate terminal
cd backend && python -m app.worker

# Frontend
cd frontend && npm run dev
```

Open `http://localhost:3000`.

## Case Study Reading Path

Start here if you are reviewing this as a portfolio project. The case study is written for reviewers; the spec and architecture files are the engineering references it points back to.

1. [`docs/case-study/00-overview.md`](docs/case-study/00-overview.md) — scope, boundaries, and the full doc map.
2. [`docs/case-study/01-product-methodology.md`](docs/case-study/01-product-methodology.md) — positioning, DVF, stage gates, and uncertainty handling.
3. [`docs/case-study/02-architecture-overview.md`](docs/case-study/02-architecture-overview.md) — system shape and main data flow.
4. [`docs/case-study/03-ai-runtime.md`](docs/case-study/03-ai-runtime.md) — prompt task registry, provider routing, fallback, and AI output bounds.
5. [`docs/case-study/04-state-and-data-contract.md`](docs/case-study/04-state-and-data-contract.md) — stage state machine and database contracts.
6. [`docs/case-study/05-latency-case-study.md`](docs/case-study/05-latency-case-study.md) — visible wait paths and sync/async boundaries.
7. [`docs/case-study/06-security-reliability-delivery.md`](docs/case-study/06-security-reliability-delivery.md) — permissions, RLS, testing, and delivery evidence.

Deeper technical evidence lives in [`docs/case-study/deep-dives/`](docs/case-study/deep-dives/).

## Prompt and Question Content

Public export prompts are synthetic placeholders. They exist so the app can load prompt files and pass runtime checks without shipping production prompt contracts.

The example question bank is synthetic and shape-only. It is suitable for demo setup and development wiring, not for real startup assessment.

## Reference Documentation

- [`docs/spec/PUBLIC_SPEC.md`](docs/spec/PUBLIC_SPEC.md) — public-safe flow and contract summary.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system shape and ownership boundaries.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution expectations.
- [`SECURITY.md`](SECURITY.md) — vulnerability reporting and data-handling boundaries.

## License

Code and documentation in this public-safe snapshot are licensed under the Apache License 2.0. See [`LICENSE`](LICENSE).

This license applies to the exported public-safe repository contents only. It does not publish or relicense the private production repository, production prompts, deployment configuration, real project data, internal planning documents, or private Git history.
