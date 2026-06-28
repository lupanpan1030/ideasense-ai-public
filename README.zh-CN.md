# IdeaSense AI

**一个 AI 创业评估助手，把粗糙想法转成结构化、可审阅的评估案例。**

IdeaSense AI 帮助早期软件创业者和学生团队从“我有一个想法”推进到具体评估：产品是什么、面向谁、哪些假设仍然薄弱，以及这个想法在 desirability、viability、feasibility 三个维度上如何评分。

核心设计判断很简单：

> **AI 提议，产品状态裁决。**

助手可以提问、抽取上下文、起草评估内容。但它不能静默推进项目、覆盖已确认上下文，也不能把不确定的模型输出直接写入持久化产品状态，除非通过确定性检查。

```text
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

这个仓库是该产品的**公开安全快照**。它包含应用外壳、架构形态、API 形状、数据库合同、CI 检查和 case-study 文档。它**不包含**私有生产仓库、生产 prompts、真实问题库、真实用户数据、secrets 或内部规划文档。

**在线产品：** [ideasenseai.com](https://www.ideasenseai.com)

**无需注册查看输出：** [示例报告](https://www.ideasenseai.com/zh/sample-report) · [示例工作区](https://www.ideasenseai.com/zh/sample) · [案例研究](docs/case-study/00-overview.md)

[![CI](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml/badge.svg)](https://github.com/lupanpan1030/ideasense-ai-public/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**语言：** [English](README.md) · 中文

**License：** Apache 2.0

## 产品预览

来自在线产品的公开预览：

| 官网工作流 | 示例报告滚动预览 |
| --- | --- |
| [![IdeaSense AI 官网首页产品演示](docs/assets/readme/ideasense-homepage-preview.gif)](https://www.ideasenseai.com/zh) | [![IdeaSense AI 示例报告滚动展示评估章节](docs/assets/readme/ideasense-sample-report-scroll.gif)](https://www.ideasenseai.com/zh/sample-report) |

在线首页：[ideasenseai.com](https://www.ideasenseai.com/zh) · 无需登录页面：[示例报告](https://www.ideasenseai.com/zh/sample-report) · [示例工作区](https://www.ideasenseai.com/zh/sample)

## 为什么做这个项目

很多 AI 产品 demo 停在“模型能回答问题”。对这个产品来说，这不够。

对于创业评估助手，真正困难的是产品控制问题：

- 系统到底从 founder 那里学到了什么？
- 哪些内容已经由用户确认，哪些仍然只是推断？
- 项目什么时候允许进入下一阶段？
- 如何阻止流畅的模型回复污染持久化状态？
- 如何生成一份有用、可追踪、足够可复盘的评估报告？

IdeaSense AI 把 assessment 当成 workflow，而不是自由聊天。模型有价值，但它被 stage contracts、parser contracts、显式 mutation rules 和 confirmation gates 约束。

## 从这里开始

如果你是 reviewer，最快路径是：

1. 打开 [示例报告](https://www.ideasenseai.com/zh/sample-report)，先看这个 workflow 最终产出的 artifact。
2. 快速浏览 [00-overview.md](docs/case-study/00-overview.md)，了解公开安全范围和阅读地图。
3. 阅读 [02-architecture-overview.md](docs/case-study/02-architecture-overview.md)，理解主系统流程。

最有信号量的技术部分是：

- **AI workflow governance** — 按任务拆分的 prompt registry、provider routing、parser contract、fallback policy 和显式 mutation boundary。([03-ai-runtime.md](docs/case-study/03-ai-runtime.md))
- **Deterministic state contracts** — stage engine 和 Stage Gate，防止 AI 静默推进项目状态。([04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md))
- **Latency split** — SSE 保持聊天路径可见，extraction、scoring 和 report work 进入 background jobs。([05-latency-case-study.md](docs/case-study/05-latency-case-study.md))
- **Public-export safety** — CI 检查帮助把生产 prompts、私有文档和 secrets 留在公开快照之外。([06-security-reliability-delivery.md](docs/case-study/06-security-reliability-delivery.md))

## 架构概览

```mermaid
flowchart TD
    UI["Browser / Next.js 工作区<br/>chat · context board · stage gate · reports"]
    API["FastAPI 编排层<br/>/api/v1 routes · auth · projects · chat · reports"]
    Workflow["确定性 workflow 层<br/>stage runtime · permissions · scoring"]
    DB[("PostgreSQL + RLS<br/>projects · project_runtime · project_states<br/>conversation_messages<br/>project_stage_assessments<br/>project_reports")]
    Queue[("background_jobs 队列")]
    Worker["Background worker<br/>extract · summarize · finalize<br/>verify claims · generate reports"]
    Prompt["受约束的 AI runtime<br/>task registry · parser contracts<br/>fallback policy · mutation classes"]
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

关键边界在模型输出和产品状态之间。模型可以生成候选文本或结构化输出，但应用决定这些输出是否有效、可以存到哪里，以及是否允许改变项目阶段。worker 不是被数据库主动推送触发，而是领取 queued `background_jobs`，再通过受控后端路径把 artifact 写回数据库。

完整说明：[02-architecture-overview.md](docs/case-study/02-architecture-overview.md)。

## IdeaSense 如何记住上下文

IdeaSense 的“记忆”不是向量库，也不是简单回放聊天记录。它会把对话逐步提升为带版本边界的产品状态，并区分确定性的用户回答和不确定的 AI 建议。

```mermaid
flowchart LR
    Chat["1. Conversation"]
    Extract["2. Extract + guard"]
    Direct["确定性用户回答"]
    Suggest["AI 建议"]
    Pending["3. pending_confirm"]
    State[("4. Versioned state<br/>project_states")]
    Gate{"5. Stage Gate"}
    Artifacts[("6. Confirmed artifacts<br/>stage assessments · context cards · reports")]
    Drop["丢弃"]

    Chat --> Extract
    Extract --> Direct --> State
    Extract --> Suggest --> Pending --> State
    Pending -.-> Drop
    State --> Gate --> Artifacts

    classDef input fill:#eef6ff,stroke:#2563eb,color:#0f172a;
    classDef review fill:#f5f3ff,stroke:#7c3aed,color:#0f172a;
    classDef state fill:#ecfdf5,stroke:#059669,color:#0f172a;
    classDef gate fill:#fff7ed,stroke:#ea580c,color:#0f172a;
    classDef artifact fill:#fff1f2,stroke:#e11d48,color:#0f172a;
    classDef drop fill:#f8fafc,stroke:#94a3b8,color:#475569;
    class Chat,Extract,Direct input;
    class Suggest,Pending review;
    class State state;
    class Gate gate;
    class Artifacts artifact;
    class Drop drop;
```

底层实现里，`project_states` 携带 `state_json`、`state_meta` 和 `state_version`；confirmed artifacts 会保留生成时对应的 state version。

详细状态合同：[04-state-and-data-contract.md](docs/case-study/04-state-and-data-contract.md)。

## 这个项目展示了什么

| 产品/工程问题 | IdeaSense AI 的处理方式 |
| --- | --- |
| LLM 输出是概率性的，可能悄悄漂移 | 确定性的 stage engine 和 Stage Gate confirmation 决定项目什么时候可以推进。 |
| 模型输出不能污染持久化状态 | AI runtime 被 task-specific prompts、parser contracts、fallback policy 和显式 mutation classes 约束。 |
| 聊天体验要快，但真实工作可能很慢 | request path 用 SSE 做可见流式响应；较慢的 extraction、scoring、report generation 通过 background worker 执行。 |
| 状态需要可审计、可恢复 | PostgreSQL 是事实源，配合 migrations、RLS、confirmed-artifact contracts 和 context-version contracts。 |
| provider 可用性、行为和成本会变化 | per-task provider chains 支持 OpenAI-compatible providers、Gemini 和 Bedrock，并带有 fallback behavior。 |
| 公开作品集仓库需要显式泄漏防护 | CI gates 覆盖 backend tests、frontend lint/build、architecture checks 和 public-export leak scanning。 |

## 公开安全边界

这个仓库用于展示工程判断，而不是发布私有生产系统。

| 包含 | 不包含 |
| --- | --- |
| Next.js 前端和 FastAPI 后端应用 | 生产问题库和生产 prompt 文本 |
| PostgreSQL schema、migrations、synthetic seeds 和 RLS roles | 私有 Master Spec 和内部规划/审计文档 |
| 公开 API shape、架构文档和 case-study 文档 | 私有报告、未公开 dogfooding 证据、production smoke artifacts |
| 合成 prompt placeholders | 部署 secrets、provider keys、真实用户/数据 |
| `resources/question_bank.example.yaml` shape-only example | 私有生产评估方法 |

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
