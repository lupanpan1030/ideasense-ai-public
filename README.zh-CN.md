# IdeaSense AI — 公开安全案例研究

IdeaSense AI 是一个面向早期软件创业者和学生团队的 AI 创业评估助手。它不是继续生成开放式聊天内容，而是把一个想法讨论约束进一个可以推进、确认、评分和复盘的流程：

```text
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

这个仓库是该产品的**公开安全快照**：展示应用外壳、架构形态、API 形状、数据合同和可维护性实践，但不公开私有生产仓库、生产 prompts 或生产问题库。

**在线体验：** [ideasenseai.com](https://www.ideasenseai.com) · **无需注册查看输出：** [示例报告](https://www.ideasenseai.com/en/sample-report) · [示例工作区](https://www.ideasenseai.com/en/sample) · [案例研究](docs/case-study/00-overview.md)

[![CI](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml/badge.svg)](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**语言：** [English](README.md) · 中文

## 架构概览

```mermaid
flowchart LR
    U["Browser · Next.js 工作区 UI<br/>chat · context board · stage gate · reports"]
    API["FastAPI 编排层<br/>auth · projects · chat · assessment · reports<br/>stage runtime · prompt runtime · scoring"]
    DB[("PostgreSQL — 状态权威 + RLS<br/>projects · messages · assessments<br/>reports · background_jobs")]
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

这个项目的难点不是“调用一个模型”，而是把模型输出约束在确定性的产品状态、Stage Gate 确认和可审计 artifact 之内。完整说明见 [02-architecture-overview.md](docs/case-study/02-architecture-overview.md)。

## 给审阅者

如果你把它作为作品集项目来评估，最值得优先看的部分是：

- **AI workflow governance** — 按任务拆分的 prompt registry、provider routing、parser contract 和显式 mutation boundary。([03-ai-runtime.md](docs/case-study/03-ai-runtime.md))
- **Deterministic state contracts** — stage engine + Stage Gate，防止 AI 静默推进项目状态。([04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md))
- **SSE + worker latency split** — 可见聊天走 request path 的流式响应，慢任务进入 background jobs。([05-latency-case-study.md](docs/case-study/05-latency-case-study.md))
- **Public-export leak gate** — CI 检查帮助防止生产 prompts/IP 进入公开快照。([06-security-reliability-delivery.md](docs/case-study/06-security-reliability-delivery.md))

**5 分钟阅读路径：** 打开 [示例报告](https://www.ideasenseai.com/en/sample-report) -> 快速浏览 [00-overview.md](docs/case-study/00-overview.md) -> 阅读 [architecture overview](docs/case-study/02-architecture-overview.md)。完整阅读顺序见下方 [案例研究阅读路径](#案例研究阅读路径)。

## 这个项目展示了什么

| 工程问题 | IdeaSense AI 的处理方式 |
| --- | --- |
| LLM 输出是概率性的，可能悄悄漂移 | 确定性的 stage engine + Stage Gate 确认；AI 不能自行推进项目状态。 |
| 模型输出不能污染项目状态 | Bounded AI runtime：按任务声明 prompt registry、parser contract、fallback policy 和显式 mutation boundary。 |
| 聊天体验需要响应快，但真实工作可能很慢 | SSE 负责可见流式响应；background worker 把 extraction、scoring 和 report generation 移出 request path。 |
| 状态需要可审计、可恢复 | PostgreSQL 作为事实源：migrations、RLS、confirmed artifact 和 context version 合同。 |
| provider 可用性和成本会变化 | 多 provider routing（OpenAI-compatible / Gemini / Bedrock），按任务配置 chain 和 fallback。 |
| 公开快照需要显式 public-export 保护 | CI gates：backend tests、frontend lint/build、architecture check 和 public-export leak scan。 |

## 公开安全边界

| 包含 | 不包含 |
| --- | --- |
| Next.js 前端 + FastAPI 后端应用 | 生产问题库和生产 prompt 文本 |
| PostgreSQL schema、migrations、synthetic seeds | 私有 Master Spec 和内部规划/审计文档 |
| 公开 API、架构和 case-study 文档 | 真实报告、dogfooding 证据、production smoke artifacts |
| 合成 prompt placeholders | 部署 secrets、provider keys、真实用户/数据 |
| `resources/question_bank.example.yaml`（仅展示数据形状） | - |

公开 demo 可以用合成内容 build 和 boot。它**不代表**生产评估质量、评分方法、访谈脚本或 prompt 质量。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `frontend/` | Next.js 16 App Router UI（marketing、auth、workspace、chat、reports）。 |
| `backend/` | FastAPI 服务（auth、project lifecycle、SSE chat、stage gates、scoring、reports、worker）。 |
| `database/` | Schema、migrations、seeds、RLS roles 和 bootstrap/reset 工具。 |
| `schema/` | 阶段数据 JSON schema 合同。 |
| `docs/case-study/` | 面向作品集审阅者的 case study（product、architecture、AI runtime、delivery）。 |
| `docs/spec/`, `docs/ARCHITECTURE.md` | 公开安全 spec 和系统形态参考。 |

## 快速验证

只运行静态检查，**不需要数据库**：

```bash
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
make architecture-check
make backend-check
make frontend-lint
make frontend-build
```

`npm ci` 会基于已提交的 lockfile 安装可复现依赖树。它可能报告 dependency audit findings；这些应和 build/lint/test gate 分开处理。

## 环境要求

- Node.js 20.9+（lockfile 要求 `>=20.9.0`；CI 使用 Node 20）
- npm
- Python 3.11+（CI 使用 Python 3.12）
- PostgreSQL — 仅完整本地 API/database 流程需要

## 本地运行

### 1. 配置环境

```bash
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
```

示例 backend env 使用本地 dummy values。只替换你本机的数据库凭据。除非你明确要测试真实 LLM 行为，否则不要加入真实 provider keys。

### 2. 设置数据库

`bootstrap_db.py` 会通过 `DATABASE_URL_ADMIN` 指向的数据库连接来执行 `CREATE DATABASE`，所以 admin DSN 必须指向一个**已经存在的 maintenance database**（例如 `postgres`），而不是你准备创建的目标库。连接角色还需要具备创建数据库和应用 roles 的权限。

```bash
DATABASE_URL_ADMIN=postgresql+psycopg2://<admin-role>@localhost:5432/postgres \
  python database/scripts/bootstrap_db.py \
  --db-name ideasense_ai_dev \
  --question-bank-yaml resources/question_bank.example.yaml
```

这会连接到 `postgres`，创建 `ideasense_ai_dev`，运行 migrations，应用 `app_runtime` / `app_worker` / `app_migrations` role grants，并导入合成问题库（当私有生产问题库不存在时，会 fallback 到 `resources/question_bank.example.yaml`）。

bootstrap 完成后，把 `backend/.env` 指向一个可以连接 `ideasense_ai_dev` 的本地角色。`backend/.env.example` 中的 `ideasense_user` / `ideasense_pwd` 是 placeholders；你可以自己创建这个 login role，或把 DSN 替换成你自己的本地开发角色。

如果只想把示例问题库重新导入一个已有数据库：

```bash
python database/scripts/import_question_bank.py \
  --dsn "postgresql+psycopg2://ideasense_user:ideasense_pwd@localhost:5432/ideasense_ai_dev" \
  --yaml resources/question_bank.example.yaml
```

### 3. 启动服务

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Worker（单独终端，用于 background jobs）
cd backend && python -m app.worker

# Frontend
cd frontend && npm run dev
```

打开 `http://localhost:3000`。

## 案例研究阅读路径

如果你把它作为作品集项目审阅，建议从这里开始。case study 是面向审阅者的材料；spec/architecture 文件是它引用的工程事实来源。

1. [`docs/case-study/00-overview.md`](docs/case-study/00-overview.md) — 范围、边界和完整文档地图。
2. [`docs/case-study/01-product-methodology.md`](docs/case-study/01-product-methodology.md) — 定位、DVF、Stage Gate、不确定性处理。
3. [`docs/case-study/02-architecture-overview.md`](docs/case-study/02-architecture-overview.md) — 系统形态和主数据流。
4. [`docs/case-study/03-ai-runtime.md`](docs/case-study/03-ai-runtime.md) — prompt task registry、provider routing、fallback、AI 输出边界。
5. [`docs/case-study/04-state-and-data-contract.md`](docs/case-study/04-state-and-data-contract.md) — stage state machine 和数据库合同。
6. [`docs/case-study/05-latency-case-study.md`](docs/case-study/05-latency-case-study.md) — 可见等待路径和 sync/async 边界。
7. [`docs/case-study/06-security-reliability-delivery.md`](docs/case-study/06-security-reliability-delivery.md) — permissions、RLS、testing、delivery evidence。

更深的技术证据在 [`docs/case-study/deep-dives/`](docs/case-study/deep-dives/)。

## Prompt 和问题内容

公开导出的 prompts 是合成 placeholders：它们用于让应用可以加载 prompt 文件并通过 runtime checks，但不会公开生产 prompt contracts。示例问题库也是合成且只展示数据形状：适合 demo setup 和开发 wiring，不适合真实创业评估。

## 参考文档

- [`docs/spec/PUBLIC_SPEC.md`](docs/spec/PUBLIC_SPEC.md) — 公开安全 flow 和 contract summary。
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 系统形态和 ownership boundaries。
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 贡献说明。
- [`SECURITY.md`](SECURITY.md) — 漏洞报告和数据处理边界。

## License

这个公开安全快照中的代码和文档使用 Apache License 2.0。见 [`LICENSE`](LICENSE)。

该 license 只适用于导出的公开安全仓库内容。它不公开、也不重新授权私有生产仓库、生产 prompts、部署配置、真实项目数据、内部规划文档或私有 Git 历史。
