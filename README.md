# IdeaSense AI Public-Safe Case Study

IdeaSense AI is an AI startup assessment assistant for early-stage software
founders and student teams. The core flow is:

```text
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

This repository is a public-safe case study and source snapshot. It is intended
to show the application shell, architecture, API shape, and maintainability
practices without exposing the private production repository.

## Public-Safe Boundary

Included:

- Next.js frontend application.
- FastAPI backend application.
- PostgreSQL schema, migrations, and synthetic demo seeds.
- Public API and architecture documentation.
- Synthetic prompt placeholders generated for the public export.
- `resources/question_bank.example.yaml` for question-bank data shape.

Excluded:

- Production question banks.
- Production prompt text.
- Private Master Spec details and internal planning/audit documents.
- Real reports, dogfooding evidence, and production smoke artifacts.
- Deployment secrets, provider keys, real users, and real project data.

The public demo can build and boot with synthetic content. It does not represent
the production assessment quality, scoring method, interview script, or prompt
quality.

## Requirements

- Node.js 18+
- npm
- Python 3.11+; CI currently uses Python 3.12
- PostgreSQL for full local API/database flows

## Install And Verify

Run the static checks first:

```bash
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
make architecture-check
make backend-check
make frontend-lint
make frontend-build
```

`npm install` may report dependency audit findings. Treat those separately from
the build/lint/test gate.

## Local Configuration

Frontend:

```bash
cp frontend/.env.local.example frontend/.env.local
```

Backend:

```bash
cp backend/.env.example backend/.env
```

The example backend env uses local dummy values. Replace only local database
credentials for your machine. Do not add real provider keys unless you are
intentionally testing live LLM behavior.

## Database Setup

Create or provide a local PostgreSQL database, then run:

```bash
DATABASE_URL_ADMIN=postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev \
  python database/scripts/bootstrap_db.py \
  --question-bank-yaml resources/question_bank.example.yaml
```

The bootstrap script also falls back to `resources/question_bank.example.yaml`
when the private production question bank is absent.

To import the public example question bank directly:

```bash
python database/scripts/import_question_bank.py \
  --dsn "postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev" \
  --yaml resources/question_bank.example.yaml
```

## Run Locally

Start the backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Start the worker in another terminal when testing background jobs:

```bash
cd backend
python -m app.worker
```

Start the frontend:

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Prompt And Question Content

Public export prompts are synthetic placeholders. They exist so the app can
load prompt files and pass runtime checks without shipping production prompt
contracts.

The example question bank is synthetic and shape-only. It is suitable for demo
setup and development wiring, not for real startup assessment.

## Documentation

- `docs/spec/PUBLIC_SPEC.md`: public-safe flow and contract summary.
- `docs/ARCHITECTURE.md`: system shape and ownership boundaries.
- `CONTRIBUTING.md`: contribution expectations.
- `SECURITY.md`: vulnerability reporting and data handling boundaries.

## License

Code and documentation in this public-safe source snapshot are licensed under
the Apache License 2.0. See `LICENSE`.

This license applies to the exported public-safe repository contents only. It
does not publish or relicense the private production repository, production
prompts, deployment configuration, real project data, internal planning
documents, or private Git history.
