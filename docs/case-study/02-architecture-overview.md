# Architecture Overview

## 一句话结论
IdeaSense AI 的架构重点不是“前端输入框调用 LLM”，而是把 AI 对话接入一个确定性的产品工作流。系统用 Next.js 承载工作区体验，FastAPI 编排业务流程，PostgreSQL 作为状态权威，SSE 支撑可见对话体验，background worker 处理慢任务，LLM task runtime 则把模型输出限制在明确的输入、输出和 mutation boundary 内。

## 背景
这篇文档面向招聘方和 portfolio reviewer，重点证明的是 AI workflow / full-stack product engineering 能力：不仅能搭建前后端，还能把不稳定的 AI 输出放进可恢复、可验证、可审计的产品系统里。

这个产品不能只做“前端输入框 + 后端调用模型”。它需要同时支持：

- 用户连续对话和 SSE 流式回复。
- 阶段状态和问题银行驱动的访谈流程。
- AI 抽取出来的结构化上下文。
- 用户确认后的阶段摘要和最终报告。
- 缺失项、unknown、assumption、verification status 等证据层。
- 组织、成员、权限、admin 管理。
- 多 provider LLM 路由和降级。

架构难点在于：用户看到的是自然语言访谈，但系统内部必须知道当前项目处在哪个阶段、哪些字段已经回答、哪些只是 AI 推断、哪些需要用户确认、哪些慢任务可以放到后台，以及最终报告能引用哪些数据。

## 设计目标
- Full-stack boundary: 前端负责交互、可见状态和反馈；后端负责权限、阶段推进、状态写入和报告生成。
- State authority: PostgreSQL 保存项目事实、阶段状态、消息、上下文、阶段评估、报告和后台任务。
- AI workflow control: LLM 输出必须经过指定 task、parser、fallback 和 mutation boundary，不能直接随意改项目状态。
- Deterministic stage engine: 阶段推进由 `current_stage`、`stage_status`、context version 和 Stage Gate 控制，而不是由聊天文本自由决定。
- Visible latency control: SSE 保障用户能快速看到对话反馈；worker 把抽取、验证、阶段确认后的 enrichment 和报告生成等慢任务移出可见等待路径。
- Permission boundary: org/admin/mentor/student 能力存在，但保持在权限和管理边界，不抢走学生主流程。

## 当前实现
高层组件：

```txt
Next.js workspace UI
  -> chat, live context board, stage gate modal, reports, admin shell
  -> API client + SSE event handling

FastAPI orchestration
  -> auth/session/project/chat/assessment/report routes
  -> service layer for stage runtime, prompt runtime, verification, scoring
  -> core infrastructure for database, security, permissions, LLM routing

PostgreSQL state authority
  -> projects, runtime, state JSON, messages, assessments, reports
  -> row-level security, org ownership, artifact boundaries

Background worker
  -> background_jobs
  -> extraction, stage summary, post-confirm finalize, verification, report generation

LLM task runtime
  -> prompt registry, task-specific provider routing, parse contracts
  -> trace metadata, fallback policy, mutation class
```

主要文件：

- `backend/app/main.py`: FastAPI app、CORS 和 `/api/v1` router 挂载。
- `backend/app/api/routes/__init__.py`: public/admin/sample routers 注册。
- `backend/app/api/routes/chat.py`: SSE chat 主入口。
- `backend/app/api/routes/projects.py`: 项目、上下文和报告读取。
- `backend/app/api/routes/assessments.py`: 阶段摘要、确认、验证和报告相关流程。
- `backend/app/services/prompt_runtime.py`: prompt task registry、context builder、mutation guard 和 execution primitives。
- `backend/app/services/stage_transition.py`: 纯阶段决策，约束 answer/draft/confirm/report completion。
- `backend/app/services/stage_runtime.py`: 阶段状态写入路径，消费 stage transition decision。
- `backend/app/core/llm_router.py`: OpenAI-compatible、Gemini、Bedrock 等 provider routing。
- `backend/app/services/stage_finalize_jobs.py`: 阶段确认后的 enrichment job 入队和幂等 key。
- `backend/app/services/report_jobs.py`: 报告生成 job 入队、状态合同和轮询响应。
- `backend/app/worker.py`: `background_jobs` 消费和后台抽取、验证、stage finalize、report generation。
- `database/schema/schema.sql`: 数据库合同快照。

## 核心运行流
用户发送一条回答时，典型流程是：

```txt
1. Frontend sends POST /api/v1/chat/stream.
2. Backend verifies auth, org membership, project runtime, usage limits.
3. Backend persists the user message.
4. Answer gate / deterministic guards decide whether the answer is enough.
5. Backend streams assistant output or emits stage-gate readiness through SSE.
6. Backend queues extraction / verification / summary work where appropriate.
7. Worker writes extracted context, verification claims, or prepared summaries through controlled paths.
8. Frontend refreshes chat, context board, verification state, and Stage Gate UI from API/SSE payloads.
```

阶段确认时，典型流程是：

```txt
1. User reviews stage summary.
2. Backend checks project stage/status, context version, and summary consistency.
3. Backend persists the confirmed assessment artifact.
4. Stage runtime advances current_stage / stage_status through deterministic rules.
5. Backend enqueues `stage_finalize_v0` for post-confirm scoring, context card, validation plan, QA digest, and verification enrichment.
6. When tech confirmation moves the project to report, backend enqueues `report_generation_v0`; report status is exposed as not_started/queued/running/finalizing/ready/failed/stale.
7. Report ready means a matching `project_reports.status = 'final'` artifact exists for the current context version, not merely that a background job finished.
```

## 关键决策
- SSE over WebSocket: 当前需求是 server-to-client chat streaming 和控制事件，SSE 更贴合 HTTP auth/request 生命周期，也降低了实时通道复杂度。
- Postgres as source of truth: 前端事件和 LLM 输出都不是事实源。项目阶段、上下文、报告和权限必须落到数据库合同里。
- Stage Gate as architecture boundary: Stage Gate 不只是 UI 弹窗，而是阻止 AI 静默推进的状态边界。
- Worker for slow/retryable work: 抽取、验证、阶段摘要、stage finalize 和报告生成可以进入后台路径，减少可见等待，并为失败重试留下空间。
- Prompt registry for LLM governance: 不同 AI 任务有不同 provider chain、timeout、输出 contract、parser、fallback 和 mutation class。
- Admin as explicit override: admin 管理能力存在，但要与自动 stage engine 分离，避免 privileged override 变成普通用户流程的一部分。

## 风险与权衡
- `chat.py` 和 `assessments.py` 承载了较多历史演进逻辑，case study 应承认这是稳定化中的模块，而不是假装已经完美分层。
- SSE 足够支撑当前聊天体验，但如果未来需要多人协作实时编辑或双向 presence，可能需要重新评估 WebSocket 或实时服务。
- 后台任务提高可恢复性，但要求 UI 有 queued/running/failed/ready 反馈，否则用户会感觉系统“卡住”。
- 多 provider routing 提高可用性和成本弹性，但会增加模型兼容、输出稳定性和测试复杂度。
- 架构页不应该把 admin/org/mentor 能力写成主卖点；它们更适合作为权限边界和产品扩展性的证据。

## 验证方式
- `make backend-check`: 编译后端并运行后端检查。
- `make frontend-lint`: 检查前端 lint。
- `make frontend-build`: 前端 typecheck 和 build。
- `make check`: 聚合 gate。
- 对涉及架构或 API 合同的变更，补充 OpenSpec、私有 `docs/spec/MASTER_SPEC.md` 或 public-safe `docs/spec/PUBLIC_SPEC.md` 更新。
- 对架构叙事中的实现事实，核对 `docs/ARCHITECTURE.md`、`docs/spec/PUBLIC_SPEC.md`、私有 Master Spec、`backend/app/api/routes/*`、`backend/app/services/*`、`frontend/features/*` 和数据库 schema。

## 可公开摘要
IdeaSense AI is a full-stack AI workflow system: Next.js workspace UI, FastAPI orchestration, PostgreSQL state authority, SSE chat streaming, background workers, and an LLM task runtime. The hard part is not calling a model; it is constraining model output inside deterministic product state, stage-gate confirmation, context extraction, evidence layers, and report artifacts.
