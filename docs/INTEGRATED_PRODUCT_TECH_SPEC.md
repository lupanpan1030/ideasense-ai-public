# IdeaSenseAI Integrated Product & Technical Specification

> 状态：当前仓库对齐版<br>
> 更新日期：2026-04-09<br>
> 用途：提供一份面向产品、设计、工程共同阅读的整合说明<br>
> 详细阶段合同仍以私有仓库中的 `docs/spec/MASTER_SPEC.md`、`schema/*.json` 和当前实现代码为准；公开导出仓库以 `docs/spec/PUBLIC_SPEC.md` 作为可见摘要。

## 1. 文档定位

这份文档是当前仓库的一级总览文档。它吸收了早期产品提案里仍然有价值的部分，例如产品愿景、用户画像、DVF 方法论和风险视角，但内容本身已经按当前仓库实现、私有 `MASTER_SPEC` 与 `schema/*.json` 重写。

本文件的目标不是保存历史痕迹，而是：

- 保留仍然有价值的产品定义、方法论和设计意图
- 用当前仓库真实实现替换掉过时技术设定
- 给出一份“现在这套产品到底是什么”的完整说明

## 2. 历史文档审查结论

### 2.1 历史 integrated proposal 的价值

历史 integrated proposal 在这些方面明显有价值：

- 有完整的产品愿景与用户画像
- 把 DVF 方法论讲清楚了
- 把“为什么不是普通 ChatGPT wrapper”说清楚了
- 有系统架构、路线图、成功指标和风险管理视角
- 更接近一份真正的“产品提案 + 技术说明”

### 2.2 但它不能直接当当前事实源

这份早期文档与当前仓库有多处明显不一致：

- 以 `LangGraph` 为核心编排引擎的表述，没有在当前仓库中作为事实源得到对应
- `Supabase Auth / NextAuth` 已不符合当前后端 JWT、本地 auth identity 与 org membership 的实现
- 对话入口写成 `WebSocket/REST`，当前主链路是 `SSE`
- 阶段运行态数据写成 `assessments.scorebreakdown`，当前主状态以 `project_states.state_json/state_meta` 为主
- 多处 schema path、Stage Data Model、数据库表设计仍是旧命名
- “后端生成 PDF”不是当前最清晰的已落地事实；当前用户可直接在前端 `Print PDF`，并导出 `JSON/Markdown`
- 文档尾部混入大段 base64 图片数据，不适合作为长期维护文档

### 2.3 本次融合策略

- 产品叙事层：保留
- 方法论层：保留，但以私有 `MASTER_SPEC` 为准修正阶段逻辑，公开导出中以 `PUBLIC_SPEC` 摘要为准
- 架构层：重写为当前 repo reality
- 数据层：重写为当前 `project_states + assessments + report payload` 模型
- 路线图与风险：保留核心思路，但去掉已经与当前仓库冲突的实施假设

## 3. 产品定义

IdeaSenseAI 是一个面向 0–1 阶段软件创业者、学生团队和导师的 AI 创业评估产品。它通过结构化对话、Stage Gate、DVF 评分与最终报告，帮助用户在 30–60 分钟内完成一次更接近真实咨询过程的项目体检。

它要解决的不是“帮用户把想法写得更好看”，而是：

- 逼用户把问题讲清楚
- 区分事实、估计、假设和未知
- 在需求、商业和技术三个维度上给出更可辩护的判断
- 产出可继续讨论、打印、导出和复盘的结构化结果

核心价值不是生成更多文本，而是把用户从“模糊想法”推进到“结构化判断”。

## 4. 目标用户

### 4.1 核心用户

- 学生创业团队
- 独立开发者
- 早期软件创业者

这类用户通常具备至少一个特征：

- 技术强但商业验证弱
- 有方向但没有系统验证方法
- 容易过早进入构建阶段
- 缺少持续、严谨、可重复的反馈回路

### 4.2 次级用户

- 创业课程导师
- 孵化器或项目制教学管理者
- 需要批量比较项目质量的 mentor / admin

当前仓库里已经能看到与组织、成员、cohort、assignment、admin report 相关的系统能力，说明产品已经不只是单人 demo，而是具备了组织场景的落地基础。

## 5. 产品范围

### 5.1 当前已落地主链路

当前仓库已打通以下能力：

- 注册、登录、登出、忘记密码、重置密码、邮箱验证、邀请加入
- 项目创建、项目列表、项目设置
- 分阶段对话
- Stage Gate 确认
- 上下文抽取与后台 worker 同步
- DVF 评分
- 报告查看
- 报告打印与导出
- Sample Workspace / Sample Report 公共演示链路
- 组织与管理后台能力

### 5.2 当前公开页面

当前产品的公开表面包括：

- 首页
- Methodology 页面
- Sample Workspace
- Sample Report
- Privacy
- Terms

这意味着产品对外叙事已经不只是一个 landing page，而是围绕方法、样例、信任和注册转化组织起来的一组页面。

## 6. 核心方法论

### 6.1 DVF 三阶段

IdeaSense 以 `Desirability / Viability / Feasibility` 为主框架。

- Stage 1 `problem`：验证问题、用户、场景、痛感、替代方案与证据
- Stage 2 `market`：验证价值主张、商业模式、市场逻辑、竞争、渠道和关键假设
- Stage 3 `tech`：验证 MVP 边界、技术方案、依赖、数据与合规、团队与执行风险
- Stage 4 `report`：系统内部综合阶段，用于汇总报告与项目快照

### 6.2 Stage Gate 原则

产品不是自由聊天，而是带有阶段门禁的结构化流程：

- 每阶段都有锚点字段
- 阶段结束必须经过 summary/confirm
- 用户可以修正 AI 总结
- 阶段推进不要求“答满所有字段”
- 但关键锚点字段不能全部停留在未知状态

### 6.3 不确定性治理

这是当前实现相较于早期文档最关键的升级之一。

系统现在明确区分：

- `state_json`：当前可用于流程推进和报告的结构化内容
- `state_meta.answer_meta`：字段级可靠性信息
- `pending_confirm`：AI 候选值，待用户确认

这使得系统可以允许 Unknown，同时避免把 AI 推断直接写成正式结论。

## 7. 当前系统架构

### 7.1 技术栈

当前仓库事实：

- Frontend: `Next.js 16`, App Router, TypeScript, Tailwind CSS
- Backend: `FastAPI`, Python 3.11+, async SQLAlchemy, Uvicorn
- Database: `PostgreSQL`
- Streaming: `SSE`
- LLM: 支持 `openai / deepseek / gemini / bedrock` 的环境变量路由

### 7.2 架构分层

- 前端负责营销页、认证页、项目工作区、聊天体验、样例页、报告展示和导出交互
- 后端负责认证、项目生命周期、SSE 聊天、上下文更新、阶段确认、评分、报告 payload 构建、验证与管理接口
- worker 负责消费后台任务并把抽取后的结构化状态写回 `project_states`
- 报告能力由后端 report builder 与前端 report viewer 共同完成

### 7.3 当前不是事实源的旧架构说法

以下说法来自早期文档，但不应再写成当前实现事实：

- `LangGraph` 是当前主编排层
- `Supabase Auth` 或 `NextAuth` 是当前认证实现
- 主聊天依赖 `WebSocket`
- `assessments.scorebreakdown` 是运行时唯一状态容器

## 8. 核心运行流

### 8.1 项目与对话

用户创建项目后，系统维护：

- `current_stage`
- `current_variant`
- `stage_status`
- `missing_paths`
- 当前 question instance / runtime 状态

聊天主入口是后端 `POST /api/v1/chat/stream`，返回 `text/event-stream`。

### 8.2 阶段数据与状态存储

当前运行态的核心不是旧 proposal 中的单表 assessment，而是：

- `project_states.state_json`
- `project_states.state_meta`

其中：

- `state_json` 保存已经进入正式状态的结构化字段
- `state_meta` 保存 answer meta、pending confirm、summary locale 等元数据

### 8.3 阶段完成与报告

阶段完成后，系统会：

- 锁定阶段关键信息
- 计算或刷新评分
- 汇总 verification 信息
- 构建报告快照

当前报告展示层已支持：

- DVF scoreboard
- Lean Canvas
- Market evidence
- Verification summary
- Key risks
- Architecture diagram
- Overall summary
- Export JSON
- Export Markdown
- Print PDF

## 9. 数据合同与事实源

### 9.1 当前正式事实源层级

建议按以下优先级理解系统：

1. 私有仓库中的 `docs/spec/MASTER_SPEC.md`
   公开导出仓库可参照 `docs/spec/PUBLIC_SPEC.md`
2. `schema/stage1.problem_user.json`
3. `schema/stage2.market_strategy.json`
4. `schema/stage3.tech_execution.json`
5. 当前实现代码
6. 本文档
7. 历史提案材料与专项计划文档

### 9.2 当前阶段合同的关键变化

相对于早期 integrated proposal，当前合同已经演进出以下关键差异：

- Stage 1 使用 `market_type_inferred`，而不是旧的二元 B2B 标记
- Stage 2 支持 `market_type_override` 与 `assisted_research` 合同
- Stage 3 明确区分 `lite/pro` 路径
- 报告、验证和阶段完成 payload 已有清晰 SSE / API 合同
- 风险、证据、Unknown、pending_confirm 都有更正式的元信息结构

### 9.3 对历史 schema 的处理原则

早期文档中的这些旧字段仍有参考价值，但不能直接当现合同使用：

- `targetuser.core`
- `targetuser.segments[]`
- `problem.problemstatement`
- `problem.existingalternatives[]`
- `pricinghypothesis`
- `techstack`
- `architecturenotes`

如果需要看旧字段如何迁移到现合同，应优先看：

- `docs/mapping/stage_field_mapping.csv`

## 10. 认证、权限与组织能力

当前产品已经超出“个人问答工具”的范围，具备组织能力：

- 用户认证采用当前后端 JWT + identity/session 体系
- 支持 email verification
- 支持 org membership 与 capability model
- 当前 org role 包括 `owner / admin / mentor / student`
- 平台侧还有 `platform admin`
- 后端已有组织设置、成员、邀请、cohort、assignment、question bank、prompt template、report 管理相关接口

这部分是早期 integrated proposal 没有真正写清楚、但当前仓库已经较实在的能力。

## 11. 质量、风险与控制

### 11.1 当前仍然成立的核心风险

- AI 过度自信或错误总结
- 用户输入质量不足
- 长链路对话带来的延迟和流失
- 文档承诺与实际实现不一致
- 用户把分数误解为“成功率保证”

### 11.2 当前仓库里的主要控制手段

- Stage Gate + user confirmation
- `pending_confirm` 与 `answer_meta`
- Unknown/undecided/not_applicable 的显式状态
- 阶段锚点字段控制
- SSE 流式输出降低等待感
- 报告中分离分数、风险、验证与总结
- 邮箱验证门槛限制未验证用户的高价值能力访问

## 12. 当前版本下的路线图理解

如果把早期 proposal 的路线图和当前仓库结合，当前更合理的优先级不是“从零搭骨架”，而是：

- 稳定性与测试覆盖
- 文档收口与命名统一
- 欢迎页正式素材替换与品牌收敛
- 多语言与 artifact locale 继续打磨
- 报告、验证与阶段逻辑的一致性继续增强
- 管理后台和 question bank 运营能力继续收口

不应再把系统描述成“即将开始搭建的 capstone skeleton”。

## 13. 文档治理建议

建议把当前 `docs/` 中与产品和实现相关的文档角色固定下来：

- `docs/INTEGRATED_PRODUCT_TECH_SPEC.md`
  用于产品、设计、工程共同阅读的总览文档，负责解释产品定位、范围、系统现实和当前优先级。
- 私有仓库中的 `docs/spec/MASTER_SPEC.md`
  公开导出仓库可参照 `docs/spec/PUBLIC_SPEC.md`
  用于阶段逻辑、字段合同、SSE 控制 payload 和实现契约，是最接近执行合同的文档。
- `schema/*.json`
  用于阶段结构化数据合同和兼容性约束。
- 各类专项计划文档
  例如欢迎页、双语、设计系统、可靠性计划，只处理单个主题，不再重复定义整产品。

维护规则建议如下：

- 不再新增新的顶层“integrated proposal/spec”并行文档，除非明确要替换本文件。
- 任何跨阶段字段、路由或阶段门禁变化，先改私有 `MASTER_SPEC` 和 `schema`，再回写本文件；公开导出摘要需要同步到 `PUBLIC_SPEC`。
- 本文件只写稳定的当前事实、明确差异和可执行的优先级，不再记录一次性的清理过程。

## 14. 与当前仓库的具体对比

### 14.1 已经一致的部分

本文件与当前仓库已经一致的核心事实包括：

- 主链路已经打通，不再是 capstone 计划稿，而是可运行产品
- 真实主流程为 `auth -> projects -> staged chat -> stage gate -> scoring -> report`
- 对话主通道是 `SSE`
- 运行时主状态以 `project_states.state_json/state_meta` 为主
- 报告查看、`Export JSON`、`Export Markdown`、`Print PDF` 均已存在
- 公开页面不止首页，还包括 `methodology / sample / sample-report / privacy / terms`
- 组织与管理侧能力已经进入产品现实，而不是未来假设
- 双语基础设施、语言切换和 artifact locale 规则已经大体成型

### 14.2 仍然存在的差异

尽管本文件已经按当前仓库重写，但和仓库现状相比，仍有几类“文档说得通、代码还没完全收口”的地方：

1. 欢迎页正式素材体系还没完成。
   - `frontend/components/marketing/HomePage.tsx` 仍在使用 `TEMP_ASSETS`
   - 资源仍指向 `frontpage.mp4`、`homepageimage1.png`、`homeimage3.png`、`homeimage4.png`、`team/head1.png`
   - `resources/welcome-page/` 目录目前基本只有 `.gitkeep`

2. 营销 FAQ 仍有超前于可证实实现的承诺。
   - `Consultant Mode with a cyclic graph architecture`
   - `downloadable Mermaid.js system architecture diagram`
   - `PII masking where applicable`
   这些说法在 `frontend/components/marketing/content.ts` 中仍然存在，但不能都作为当前实现事实强承诺

3. 双语工作还差最后一个运营收口步骤。
   - `docs/MULTILINGUAL_READINESS_AUDIT_AND_PLAN.md` 已明确写明只剩 1 个 operational task
   - 该任务是对目标 live 环境执行 bilingual release checklist，或补 CD 保证发布可验证

4. 文档治理还没有完全收束成单一入口。
   - 现在已经有 `INTEGRATED_PRODUCT_TECH_SPEC.md`
   - 也有私有 `MASTER_SPEC` 作为完整合同
   - 还有若干专项计划文档
   这本身不是错误，但如果继续扩张而不定义角色，后面还会再次漂移

### 14.3 接下来最应该做什么

基于当前仓库状态，下一步优先级建议是：

1. 收紧营销承诺。
   - 先改 `frontend/components/marketing/content.ts`
   - 把没有足够实现证据的 FAQ 说法降级为更稳妥表述
   - 这是最直接的“文案与实现对齐”动作

2. 完成欢迎页正式素材接入。
   - 把 `resources/welcome-page/` 和 `frontend/public/marketing/welcome/` 真正填起来
   - 替换 `HomePage.tsx` 里的 `TEMP_ASSETS`
   - 这是当前最明显的产品表层未收口项

3. 完成双语上线验证。
   - 跑 `docs/MULTILINGUAL_RELEASE_CHECKLIST.md`
   - 执行 `scripts/verify_multilingual_release.sh`
   - 这会把“基础设施已完成”变成“上线质量已验证”

4. 继续做稳定性与测试覆盖收口。
   - 当前 README 和 backend README 都明确产品已在“稳定性、测试、部署、文档收口”阶段
   - 所以后续工作重心不应再是发明新大功能，而是把已有主链路打磨扎实

### 14.4 简化判断

如果只用一句话概括当前差别：

- 产品内核已经成型
- 文档合同已经较清晰
- 但市场表层文案、欢迎页正式资产和上线验证这三件事还没有完全收口

## 15. 结论

当前最适合继续维护的一级总览文档就是本文件。

它保留了早期提案里真正有价值的产品叙事和方法论，但已经把实现层内容改写成当前仓库现实。后续如果只保留一份面向产品、设计、工程共同阅读的总文档，应继续维护本文件，而不是再生成新的并行总文档。

## 16. 主要依据

- 私有仓库中的 `docs/spec/MASTER_SPEC.md`
  公开导出仓库可参照 `docs/spec/PUBLIC_SPEC.md`
- `docs/ARCHITECTURE.md`
- `README.md`
- `backend/README.md`
- `docs/VENTURE_REVIEW_RELIABILITY_STRATEGY.md`
- `docs/mapping/stage_field_mapping.csv`
- `frontend/features/reports/report-viewer.tsx`
- `frontend/features/reports/report-export.ts`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/assessments.py`
- `backend/app/core/report_builder.py`
