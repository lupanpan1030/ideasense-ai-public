# IdeaSense AI Case Study Overview

## 一句话结论
IdeaSense AI 是一个面向 0-1 阶段软件创业者和学生团队的 AI 创业评估助手。它把开放式想法讨论约束进一个可推进、可确认、可评分、可复盘的产品流程：

```txt
project -> staged interview -> context extraction -> stage gate confirmation -> DVF scoring -> report
```

这组 case-study 文档用于沉淀 IdeaSense AI 的产品判断和工程实现。完整事实源留在本私有仓库；个人网站只抽取适合公开展示的内容；IdeaSense 官网只抽取用户价值和方法论内容。

## 背景
普通 AI 聊天可以帮助用户头脑风暴，但很难保证创业评估流程持续围绕同一组关键事实推进。IdeaSense AI 的产品目标不是生成更多文本，而是帮助用户把模糊想法沉淀成结构化判断：

- 先明确问题和 P0 用户，再进入商业和技术判断。
- 允许用户说 unknown / unsure / not applicable，但系统要保存不确定性，而不是强行编造。
- 每个阶段进入 Stage Gate，由用户确认摘要后再推进。
- 最终报告基于已确认的项目状态、阶段摘要和 DVF 评分生成。

## My Role
I designed and built IdeaSense AI independently from 0 to 1 as an AI product engineering project.

The idea originated from a university mock-internship brief on using GenAI to assess new software product ideas. I later reworked the concept and rebuilt it independently as a live AI-guided startup assessment product, covering product definition, workflow design, frontend experience, backend architecture, database contracts, AI runtime design, prompt/task governance, and deployment-facing reliability work.

The project is currently primarily built by me, with future collaboration planned as the product matures.

## 设计目标
- 对外能在 5-10 分钟内解释清楚这个 AI 产品是什么、为什么成立、技术难点在哪里。
- 对内能保存工程事实，避免以后只剩零散代码和临时聊天记录。
- 为个人 portfolio 提供可裁剪素材，证明产品设计、全栈实现、AI runtime、数据建模和可靠性治理能力。
- 为 IdeaSense 官网提供可裁剪素材，解释方法论、样例流程和信任边界。

## 当前实现
主要模块：

- `frontend/`: Next.js 16 App Router 前端，负责营销页、认证页、项目工作区、聊天体验、上下文面板、报告展示和导出。
- `backend/`: FastAPI 后端，负责认证、项目生命周期、SSE 聊天、上下文抽取、阶段确认、DVF 评分、报告生成、验证和管理接口。
- `database/`: PostgreSQL schema、migrations、seeds、RLS 策略和 bootstrap/reset 工具。
- `schema/`: 阶段数据 JSON schema 合同。
- `docs/spec/PUBLIC_SPEC.md`: public-safe 产品流程、边界和 API 合同摘要。
- 私有 `docs/spec/MASTER_SPEC.md`: 完整阶段脚本、字段映射和生产运行约束。
- `openspec/changes/`: 架构或行为变更的 proposal/design/tasks。

## 文档地图
第一层是对外展示层，控制在 7 篇：

- `00-overview.md`: 本文件，说明 case study 的边界和阅读路径。
- `01-product-methodology.md`: 产品定位、目标用户、DVF、Stage Gate 和不确定性治理。
- `02-architecture-overview.md`: 系统架构、模块边界和主链路数据流。
- `03-ai-runtime.md`: Prompt task registry、provider routing、fallback、trace 和 AI 输出边界。
- `04-state-and-data-contract.md`: 阶段状态机、项目状态、数据库合同和确认边界。
- `05-latency-case-study.md`: 可见等待链路、同步/异步边界和 background jobs 优化方向。
- `06-security-reliability-delivery.md`: 权限、安全、RLS、测试和交付证据。

第二层是技术深挖层：

- `deep-dives/chat-sse-streaming.md`
- `deep-dives/prompt-task-registry.md`
- `deep-dives/llm-provider-routing.md`
- `deep-dives/stage-transition-engine.md`
- `deep-dives/background-jobs-worker.md`
- `deep-dives/product-system-flowcharts.md`

第三层是内部 runbook：

- `../runbooks/local-dev.md`
- `../runbooks/env-and-provider-routing.md`
- `../runbooks/worker-operations.md`

## 关键决策
- 私有仓库保存完整事实，不把 runbook、环境变量细节、内部路径和 OpenSpec 过程直接公开。
- 个人网站展示“我如何设计并实现这个 AI 产品”，强调工程能力和 case study。
- IdeaSense 官网展示“产品如何帮助用户评估创业想法”，强调用户价值和方法论。
- case study 不写成 API 手册；API、命令和排障放到 runbook 或现有 README。

## 风险与权衡
- 文档太少会像项目介绍，无法证明技术深度。
- 文档太多会让读者迷路，所以主入口只保留 7 篇，deep dive 作为证据库。
- 当前仓库仍有快迭代痕迹，文档必须标明事实源和待验证项，避免把计划写成已完成事实。

## 验证方式
- 文档中引用的实现事实应能在 `README.md`、`docs/ARCHITECTURE.md`、`docs/spec/PUBLIC_SPEC.md`、`backend/README.md`、`database/schema/schema.sql` 或对应代码文件中找到；生产/IP 细节以私有 `MASTER_SPEC` 为准。
- 文档改动至少运行 `git diff --check`。
- 后续若文档声明新的行为已实现，应补充对应测试命令和真实流程证据。

## 可公开摘要
IdeaSense AI is an AI startup assessment assistant that turns early-stage ideas into a structured DVF review. I designed and implemented the full product flow: staged interview, context extraction, stage-gate confirmation, DVF scoring, and report generation. The technical case study focuses on how probabilistic AI output is constrained by deterministic state, database contracts, prompt runtime governance, and user-confirmed artifacts.
