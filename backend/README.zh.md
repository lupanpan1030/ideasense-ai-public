# 后端

当前生效的 IdeaSenseAI FastAPI 后端。

已覆盖认证、项目生命周期、分阶段对话、SSE 流式输出、上下文抽取、
DVF 评分与报告、Sample 预览接口，以及组织 / 管理后台相关能力。

## 依赖
- Python 3.11+（CI 使用 3.12）
- 已准备好 IdeaSenseAI 的 PostgreSQL schema（见 `database/README.md`）
- 核心依赖：`fastapi`、`uvicorn`、`sqlalchemy`、`asyncpg`、`python-dotenv`、`PyJWT`、`psycopg2`
- 可选能力依赖：`openai`、`botocore`、`PyYAML`、`resend`（LLM/邮件相关功能）

## 快速启动（JWT 登录）
1) 先种 org/users + 本地登录账号：
```
psql "<dsn>" -f database/seeds/flows/org/org_seed.sql
psql "<dsn>" -f database/seeds/flows/auth/auth_seed.sql
```
2) 导出环境变量（示例 admin 用户）：
   可参考 `backend/.env.example` 作为完整模板。
```
export DATABASE_URL="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export DATABASE_URL_ADMIN="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export JWT_SECRET="dev-secret-change-me"
export JWT_EXPIRES_MINUTES=60
export JWT_REFRESH_THRESHOLD_MINUTES=10
export DEV_LOGIN_ENABLED=1
```
3) 安装依赖：
```
python -m pip install -r requirements.txt
```
4) 启动服务：
```
cd backend
uvicorn app.main:app --reload --port 8000
```
5) 验证：
```
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@demo.local","password":"12345678"}'
```

## 快速启动（DEV_AUTH_BYPASS）
1) 只种 org/users（不依赖题库）：
```
psql "<dsn>" -f database/seeds/flows/org/org_seed.sql
```
2) 导出环境变量（示例 admin 用户）：
```
export DATABASE_URL="postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev"
export DEV_AUTH_BYPASS=1
export DEV_ORG_ID=11111111-1111-1111-1111-111111111111
export DEV_USER_ID=99999999-9999-9999-9999-999999999999
```
3) 安装依赖：
```
python -m pip install -r requirements.txt
```
4) 启动服务：
```
cd backend
uvicorn app.main:app --reload --port 8000
```
5) 验证：
```
curl http://localhost:8000/api/v1/admin/health
curl http://localhost:8000/api/v1/session
```

## LLM 多供应商路由
后端支持按任务路由到不同供应商。如果未设置路由，会自动检测可用 key 并使用默认排序。

支持的 provider：`openai`、`deepseek`、`qwen`、`gemini`、`bedrock`。

路由配置（逗号分隔的 fallback 链）：
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

这组成本优化策略是：高频隐藏任务（判断、抽取、辅助草稿和 digest）
优先走 DeepSeek；用户可见的自然访谈提问和追问优先走快速
Qwen/Gemini；OpenAI 作为最后可靠兜底。阶段总结、DVF 评分和最终报告
可通过 DeepSeek Pro / Qwen Pro / Gemini Pro 的模型环境变量走更强模型。
如果部署账号还没有开通 Qwen 模型权限，可以先把
`LLM_PROVIDER_FOLLOWUP_COMPOSE` 和 `LLM_PROVIDER_QUESTION_COMPOSE` 改成
`gemini,qwen,deepseek,openai`，等权限修复后再切回 Qwen 优先。

各供应商相关环境变量：
- OpenAI：`OPENAI_API_KEY`、`OPENAI_CHAT_MODEL`、`OPENAI_REPORT_MODEL`、
  `OPENAI_ANSWER_GATE_MODEL`、`OPENAI_EXTRACT_MODEL`、`OPENAI_ROUTER_MODEL`、
  `OPENAI_QUESTION_REWRITE_MODEL`，可选 `OPENAI_BASE_URL`。
- DeepSeek（OpenAI 兼容）：`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、
  `DEEPSEEK_PRO_MODEL`、`DEEPSEEK_BASE_URL`。建议分层默认值：
  `DEEPSEEK_MODEL=deepseek-v4-flash`、
  `DEEPSEEK_PRO_MODEL=deepseek-v4-pro`、
  `DEEPSEEK_BASE_URL=https://api.deepseek.com`。
  如需单独覆盖某类任务，可用 `DEEPSEEK_<TASK>_MODEL`，例如
  `DEEPSEEK_REPORT_MODEL`。
- Qwen / 通义千问（OpenAI 兼容）：`QWEN_API_KEY`、`QWEN_MODEL`、
  `QWEN_PRO_MODEL`、`QWEN_BASE_URL`。建议默认值：
  `QWEN_MODEL=qwen3.5-plus`、
  `QWEN_PRO_MODEL=qwen3-max`、
  `QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`。
  如果你的 key 是中国（北京）区域，改用
  `QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`。
  如果本地旧 `.env` 里用了 `Qwen=...`，请把变量名改成
  `QWEN_API_KEY=...`，不要同时保留两个名字。
  如需单独覆盖某类任务，可用 `QWEN_<TASK>_MODEL`，例如
  `QWEN_REPORT_MODEL`。
- Gemini：`GEMINI_API_KEY`、`GEMINI_MODEL`、`GEMINI_PRO_MODEL`。
  建议分层：`GEMINI_MODEL=gemini-3.1-flash-lite` 用于聊天速度优先的
  fallback，`GEMINI_PRO_MODEL=gemini-3.5-flash` 用于阶段总结、DVF 和报告
  这类更关键的输出。如需单独覆盖某类任务，可用 `GEMINI_<TASK>_MODEL`，
  例如 `GEMINI_REPORT_MODEL`。
- Bedrock：`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、
  `AWS_REGION`、`BEDROCK_MODEL_ID_CHAT`、`BEDROCK_MODEL_ID_STAGE_EVAL`、
  `BEDROCK_MODEL_ID_REPORT`、`BEDROCK_MODEL_ID_DEFAULT`、
  `BEDROCK_MODEL_ID_FALLBACK`。

## 说明
- `DATABASE_URL_ADMIN` 需要指向带 `BYPASSRLS` 权限的角色（`user_identities` 强制 RLS）。
- 设置 `ADMIN_API_ENABLED=0` 可禁用 `/api/v1/admin/*` 路由（不挂载 router，直接 404）。`ADMIN_ENABLED=0` 仍可用。
- `SAMPLE_PUBLIC_ENABLED` 控制 `/api/v1/sample/*` 路由；未设置时，非生产环境默认开启，生产环境默认关闭。
- `APP_ENV=production` 时若 `DEV_AUTH_BYPASS=1` 或 `DEV_LOGIN_ENABLED=1` 被开启，服务会直接拒绝启动。
- 组织邀请：生产环境需将 `APP_BASE_URL` 设置为公开前端地址；邀请链接会拒绝缺失或 localhost 地址。
- 邮箱验证：配置 `RESEND_API_KEY`、`EMAIL_FROM`、`EMAIL_VERIFY_BASE_URL`。未验证用户仅可完成 Problem 阶段，无法访问阶段总结/报告。
- LLM 限流：`LLM_RATE_LIMIT_MINUTE_UNVERIFIED`、`LLM_RATE_LIMIT_DAY_UNVERIFIED`、`LLM_RATE_LIMIT_MINUTE_VERIFIED`、`LLM_RATE_LIMIT_DAY_VERIFIED`。
- CORS：非生产环境默认允许 `http://localhost:3000` 和 `http://127.0.0.1:3000`，可用 `CORS_ALLOW_ORIGINS`（逗号分隔）覆盖。生产环境必须设置 `CORS_ALLOW_ORIGINS`。
- `.env` 会通过 `python-dotenv` 自动加载（从 `backend/` 目录启动时）。如从其他目录启动可用 `--env-file`。

## 权限矩阵（组织层）
组织成员角色：`owner`、`admin`、`mentor`、`student`。

能力字段由 `/api/v1/session` 下发，后端统一在 `backend/app/core/permissions.py` 维护。

| 能力 | Owner | Admin | Mentor | Student |
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
| can_transfer_ownership | ✅ | 可配置 | ❌ | ❌ |

说明：
- Owner/Admin 具备完整管理权限。
- Mentor/Student 目前不具备后台管理能力（仅产品使用与评论/建议在业务端控制）。
- `can_transfer_ownership` 对 Admin 是否开启由组织配置 `settings.allow_admin_transfer_ownership` 决定（默认关闭）。
- Platform Admin 通过 `platform_admins` 表维护，`/api/v1/session` 返回 `is_platform_admin`。
- Platform Admin 还必须至少拥有一个组织的 Owner/Admin 角色（active）。

## 管理端 API（重点）
- Platform Admin API：`/platform-api/*`（组织/全局模板管理 + 平台配置），需平台管理员权限。
- 平台配置：`/platform-api/settings`（读取/更新全局配置）。
- 题库管理 API：`/admin-api/question-banks/*`（draft/逐题编辑/导入 YAML/JSON/批量排序/发布），需 `can_manage_question_bank`。
