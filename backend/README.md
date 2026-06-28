# Backend

FastAPI backend for the active IdeaSenseAI product flow.

Current scope includes auth, project lifecycle, staged chat, SSE streaming,
context extraction, DVF scoring/report generation, sample workspace endpoints,
and organization/admin operations.

## Requirements
- Python 3.11+ (CI uses 3.12)
- PostgreSQL with IdeaSenseAI schema (see `database/README.md`)
- Core packages: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `python-dotenv`, `PyJWT`, `psycopg2`
- Provider/email SDKs (used by optional features): `openai`, `botocore`, `PyYAML`, `resend`

## Quick Start (JWT login)
1) Seed org/users + local auth identities:
```
psql "<dsn>" -f database/seeds/flows/org/org_seed.sql
psql "<dsn>" -f database/seeds/flows/auth/auth_seed.sql
```
2) Export env vars (example admin user):
   See `backend/.env.example` for a fuller template.
```
export DATABASE_URL="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export DATABASE_URL_ADMIN="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export JWT_SECRET="dev-secret-change-me"
export JWT_EXPIRES_MINUTES=60
export JWT_REFRESH_THRESHOLD_MINUTES=10
export DEV_LOGIN_ENABLED=1
```
3) Install deps:
```
python -m pip install -r requirements.txt
```
4) Run server:
```
cd backend
uvicorn app.main:app --reload --port 8000
```
5) Verify:
```
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@demo.local","password":"12345678"}'
```

## Background Jobs Worker (S6)
The extraction worker is a separate process that consumes `background_jobs`
and writes extracted context into `project_states`.

1) Ensure env vars are set (either export them or run from `backend/` so `.env` is loaded):
```
export DATABASE_URL="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export DATABASE_URL_ADMIN="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export OPENAI_API_KEY="sk-..."
export OPENAI_CHAT_MODEL="gpt-4o-mini"
```
2) Start the API server:
```
cd backend
uvicorn app.main:app --reload --port 8000
```
3) Start the worker in another terminal:
```
cd backend
python -m app.worker
```

Notes:
- The worker polls every 2s and uses a 60s lock TTL by default.
- Configure via `WORKER_POLL_INTERVAL_SEC` and `WORKER_LOCK_TTL_SEC` if needed.

## LLM Providers
The backend can route different tasks to different providers using env vars.
If no provider routing is set, it auto-detects available keys and uses
task-specific defaults.

Supported providers: `openai`, `deepseek`, `qwen`, `gemini`, `bedrock`.

Routing (comma-separated fallback chains):
```
LLM_PROVIDER_DEFAULT=deepseek,qwen,gemini,bedrock,openai
LLM_PROVIDER_AI_ASSIST=deepseek,qwen,gemini,openai
LLM_PROVIDER_EXTRACT=deepseek,qwen,gemini,openai
LLM_PROVIDER_FOLLOWUP_COMPOSE=qwen,gemini,deepseek,openai
LLM_PROVIDER_QUESTION_COMPOSE=qwen,gemini,deepseek,openai
LLM_PROVIDER_QUESTION_REWRITE=qwen,deepseek,gemini,openai
LLM_PROVIDER_ROUTER=deepseek,qwen,gemini,openai
LLM_PROVIDER_QA_DIGEST=deepseek,qwen,gemini,openai
LLM_PROVIDER_ANSWER_GATE=deepseek,qwen,gemini,openai
LLM_PROVIDER_STAGE_SUMMARY=deepseek,qwen,gemini,openai
LLM_PROVIDER_DVF_SCORING=deepseek,qwen,gemini,openai
LLM_PROVIDER_REPORT=qwen,deepseek,gemini,openai
```

Latency guards:
```
ANSWER_GATE_TIMEOUT_MS=3000
SYNC_EXTRACT_TIMEOUT_MS=2500
QUESTION_COMPOSE_START_TIMEOUT_MS=3500
QUESTION_PLANNER_TIMEOUT_MS=1000
QUESTION_PLANNER_MIN_MISSING_PATHS=2
QUESTION_PLANNER_MIN_CANDIDATES=2
```

`SYNC_EXTRACT_TIMEOUT_MS` now applies to the background `extract_answer_v0`
worker path only; chat responses do not poll or wait for extraction before
streaming the next visible assistant response. Stage summaries use the
`stage_summary` prompt task timeout while they are prepared in the background.

This cost-optimized routing keeps high-volume assistant, gate, and extraction
work on DeepSeek first, uses fast Qwen/Gemini for visible interview
composition, and keeps OpenAI as the final reliability fallback. DeepSeek Pro,
Qwen Pro, and Gemini Pro can be used for stage summaries, DVF scoring, and
final reports through their pro model env vars.
If Qwen model access is not enabled for the deployment account, set
`LLM_PROVIDER_FOLLOWUP_COMPOSE` and `LLM_PROVIDER_QUESTION_COMPOSE` to
`gemini,qwen,deepseek,openai` until access is fixed.

Provider env vars:
- OpenAI: `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_REPORT_MODEL`,
  `OPENAI_ANSWER_GATE_MODEL`, `OPENAI_EXTRACT_MODEL`, `OPENAI_ROUTER_MODEL`,
  `OPENAI_QUESTION_REWRITE_MODEL`, optional `OPENAI_BASE_URL`.
- DeepSeek (OpenAI-compatible): `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`,
  `DEEPSEEK_PRO_MODEL`, `DEEPSEEK_BASE_URL`. Recommended split:
  `DEEPSEEK_MODEL=deepseek-v4-flash`,
  `DEEPSEEK_PRO_MODEL=deepseek-v4-pro`,
  `DEEPSEEK_BASE_URL=https://api.deepseek.com`.
  Optional task overrides use `DEEPSEEK_<TASK>_MODEL`, for example
  `DEEPSEEK_REPORT_MODEL`.
- Qwen (OpenAI-compatible): `QWEN_API_KEY`, `QWEN_MODEL`, `QWEN_PRO_MODEL`,
  `QWEN_BASE_URL`. Recommended defaults:
  `QWEN_MODEL=qwen3.5-plus`,
  `QWEN_PRO_MODEL=qwen3-max`,
  `QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
  For China (Beijing) region keys, set
  `QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`.
  If an older local `.env` uses `Qwen=...`, rename that variable to
  `QWEN_API_KEY=...`; do not keep both names.
  Optional task overrides use `QWEN_<TASK>_MODEL`, for example
  `QWEN_REPORT_MODEL`.
- Gemini: `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_PRO_MODEL`.
  Recommended split: `GEMINI_MODEL=gemini-3.1-flash-lite` for chat-speed
  fallbacks and `GEMINI_PRO_MODEL=gemini-3.5-flash` for heavier assessment
  outputs. Optional task overrides use `GEMINI_<TASK>_MODEL`, for example
  `GEMINI_REPORT_MODEL`.
- Bedrock: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`,
  `AWS_REGION`, `BEDROCK_MODEL_ID_CHAT`, `BEDROCK_MODEL_ID_STAGE_EVAL`,
  `BEDROCK_MODEL_ID_REPORT`, `BEDROCK_MODEL_ID_DEFAULT`,
  `BEDROCK_MODEL_ID_FALLBACK`.

## Org Permission Matrix
Org roles: `owner`, `admin`, `mentor`, `student`.

Capabilities are returned by `/api/v1/session` and defined in
`backend/app/core/permissions.py`.

| Capability | Owner | Admin | Mentor | Student |
| --- | --- | --- | --- | --- |
| is_org_admin | ✅ | ✅ | ❌ | ❌ |
| can_manage_org_settings | ✅ | ✅ | ❌ | ❌ |
| can_manage_prompts | ✅ | ✅ | ❌ | ❌ |
| can_manage_question_bank | ✅ | ✅ | ❌ | ❌ |
| can_manage_members | ✅ | ✅ | ❌ | ❌ |
| can_manage_invites | ✅ | ✅ | ❌ | ❌ |
| can_manage_cohorts | ✅ | ✅ | ❌ | ❌ |
| can_manage_assignments | ✅ | ✅ | ❌ | ❌ |
| can_manage_projects | ✅ | ✅ | ❌ | ❌ |
| can_manage_reports | ✅ | ✅ | ❌ | ❌ |
| can_transfer_ownership | ✅ | Configurable | ❌ | ❌ |

Notes:
- Owner/Admin have full management rights.
- Mentor/Student currently have no admin capabilities (product-side access is
  controlled separately).
- Admin `can_transfer_ownership` is controlled by org setting
  `settings.allow_admin_transfer_ownership` (default false).
- Platform Admins are stored in `platform_admins`; `/api/v1/session` returns
  `is_platform_admin`.
- Platform Admins must also have at least one active org membership as Owner/Admin.

## Admin APIs (Highlights)
- Platform Admin API: `/platform-api/*` (org/global prompt management + platform
  settings). Requires `platform_admins` membership.
- Platform settings: `/platform-api/settings` (get/patch global config).
- Question Bank Admin API: `/admin-api/question-banks/*` (draft/edit/import YAML/JSON,
  reorder, publish). Requires `can_manage_question_bank`.

## Quick Start (DEV_AUTH_BYPASS)
1) Seed org/users (no question bank required):
```
psql "<dsn>" -f database/seeds/flows/org/org_seed.sql
```
2) Export env vars (example admin user):
```
export DATABASE_URL="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export DEV_AUTH_BYPASS=1
export DEV_ORG_ID=11111111-1111-1111-1111-111111111111
export DEV_USER_ID=99999999-9999-9999-9999-999999999999
```
3) Install deps:
```
python -m pip install -r requirements.txt
```
4) Run server:
```
cd backend
uvicorn app.main:app --reload --port 8000
```
5) Verify:
```
curl http://localhost:8000/api/v1/admin/health
curl http://localhost:8000/api/v1/session
```

## Notes
- `DATABASE_URL_ADMIN` should point to a role with `BYPASSRLS` for auth (RLS is forced on `user_identities`).
- Set `ADMIN_API_ENABLED=0` to disable `/api/v1/admin/*` routes (routers not mounted, returns 404). `ADMIN_ENABLED=0` still works.
- `SAMPLE_PUBLIC_ENABLED` controls `/api/v1/sample/*` routes. If unset, sample routes are enabled in non-production and disabled in production.
- `APP_ENV=production` refuses to start if `DEV_AUTH_BYPASS=1` or `DEV_LOGIN_ENABLED=1` are set.
- Organization invites: set `APP_BASE_URL` to the public frontend origin in production. Invite links refuse missing or localhost app URLs in production.
- Email verification: set `RESEND_API_KEY`, `EMAIL_FROM`, and `EMAIL_VERIFY_BASE_URL`. Optionally set `EMAIL_REPLY_TO` so replies go to a monitored inbox. Unverified users can only complete the problem stage and cannot access stage summaries/reports.
- LLM rate limits: `LLM_RATE_LIMIT_MINUTE_UNVERIFIED`, `LLM_RATE_LIMIT_DAY_UNVERIFIED`, `LLM_RATE_LIMIT_MINUTE_VERIFIED`, `LLM_RATE_LIMIT_DAY_VERIFIED`.
- CORS: default allows `http://localhost:3000` and `http://127.0.0.1:3000` in non-production. Override with `CORS_ALLOW_ORIGINS` (comma-separated). In production, `CORS_ALLOW_ORIGINS` is required.
- `.env` is auto-loaded via `python-dotenv` when running from `backend/`. Use `--env-file` if you run from elsewhere.
