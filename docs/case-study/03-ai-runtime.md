# AI Runtime And Prompt Governance

## 一句话结论
IdeaSense AI 的 AI runtime 重点不是“写一个好 prompt”，而是治理 AI 在产品里的权限和边界。系统把模型调用拆成多个受限 prompt tasks，每个 task 都声明输入结构、输出合同、timeout、parser、fallback、provider chain 和 mutation boundary，避免模型输出随意改变项目状态。

## 背景
我一直认为，管理好 AI 比单纯用好 AI 更重要。创业评估产品里的 AI 任务不是一种：

- 判断用户回答是否足够。
- 抽取结构化字段。
- 改写下一题或组合追问。
- 生成阶段摘要。
- 生成 DVF 评分。
- 生成最终报告。
- 验证 claims。

这些任务的延迟、成本、可靠性和数据修改权限都不同。如果全部走一个通用 `call_model(prompt)`，系统很快会失去治理能力：哪个任务能改状态、哪个任务只是生成文案、哪个任务失败后能 fallback、哪个输出必须 JSON parse，都很难说清楚。

因此，IdeaSense 不把 AI 当成一个拥有全部权限的自动代理，而是把 AI 拆成一组 bounded task roles：AI 可以参与判断、抽取、总结和报告，但每一种参与方式都有不同权限。

## 设计目标
- 每类 AI 任务有明确 task key 和 provider task。
- prompt 输入由 sectioned context builder 构造，减少散落字符串拼接。
- 输出必须经过 parser 或 fallback，不能静默失败。
- 每个 task 声明允许的 mutation boundary，模型输出不能直接越权修改产品状态。
- trace 记录 latency / parse status / provider / model，但不暴露 raw prompts 给普通用户。
- provider routing 支持按任务选择 provider chain 和 fallback，而不是所有任务都强行走同一个模型。

## 当前实现
核心文件：

- `backend/app/services/prompt_runtime.py`
- `backend/app/core/llm_router.py`
- `backend/app/services/prompt_output_parsers.py`
- `backend/app/prompts/chat/*`
- `backend/app/prompts/report/*`
- `backend/app/prompts/shared/*`
- `backend/tests/test_prompt_runtime.py`
- `backend/tests/test_llm_router.py`

核心概念：

- `PromptTaskSpec`: 定义 task 的模板、provider task、timeout、parse strategy、fallback、allowed mutation 等。
- `PromptContext`: 保存变量和 prompt sections，并为 trace 生成 redacted metadata。
- `PromptOutputGuard`: 检查调用方期望的 mutation class 是否匹配 task 声明。
- `execute_prompt_task`: 渲染 prompt、调用 provider、处理 timeout、解析输出、返回 trace。
- `call_llm` / `call_llm_stream`: 按任务解析 provider chain，逐个 fallback。

AI task 权限示例：

- `answer_gate`: 判断回答是否足够，属于 hidden decision，不应直接改项目事实。
- `question_compose` / `followup_compose`: 生成用户可见文案，只能影响 visible copy。
- `extract`: 产出结构化字段更新，但必须进入 validated context update 路径。
- `stage_summary_problem` / `stage_summary_market` / `stage_summary_tech`: 生成阶段摘要 artifact，但摘要不等于用户已确认。
- `stage_finalize_v0`: 确认后触发的后台 enrichment 工作，负责阶段 DVF、context card、validation plan、QA digest 和验证补充；它不能推进阶段，也不能完成报告。
- `dvf_scoring` / `final_report` / `report_generation_v0`: 生成报告 artifact，但必须基于提供的 report input、当前 context version 和既定持久化路径。
- `claim_verification`: 判断外部证据支持程度，但不能直接改变 user-confirmed inputs。

mutation class 用于表达 AI 输出最多能影响什么：

- `NONE`: 不应改变业务状态。
- `VISIBLE_COPY_ONLY`: 只能作为用户可见文案。
- `DECISION_ONLY`: 只能作为隐藏判断输入。
- `VALIDATED_CONTEXT_UPDATE`: 需要经过验证/确认路径后才进入结构化状态。
- `REPORT_ARTIFACT`: 可生成报告类 artifact，但仍要走报告持久化路径。
- `USAGE_ONLY`: 只影响用量统计。

## 关键决策
- AI 输出默认不是事实。只有通过项目状态、pending confirm、stage assessment 或 report artifact 的既定路径，才能成为产品状态的一部分。
- AI 不是一个全权限 agent，而是一组可测试、可限制、可替换的任务角色。
- 快速任务和重任务分开路由。回答判断、抽取、题目组合可以使用更快或更适合可见等待的 provider；stage summary、stage finalize、DVF、report 可以使用更适合长输出和结构化结果的 provider 或后台 job。
- Provider routing 只应该公开到 task-specific chain 和 fallback 的层面，不公开真实 API key、账号、模型访问故障或内部环境细节。
- Prompt runtime trace 是 admin/debug 能力，用来诊断 latency、provider、model、parse status 和 fallback；普通学生视图不应看到 raw prompts、完整用户回答、provider keys、tokens 或 secrets。
- Fallback 不是“假装成功”，而是返回带 reason 的失败、跳过非关键 payload，或使用 deterministic fallback。

## 风险与权衡
- 任务 registry 会让新增 prompt 变得更慢，但换来可测试、可审计和可替换。
- 多 provider 增加配置复杂度，需要 runbook 和测试覆盖。
- mutation boundary 增加开发约束，但能防止模型把“建议”直接变成项目事实。
- 对可见聊天来说，过多 hidden AI step 会拉长等待，因此可见路径只保留必要判断，stage finalize 和 report generation 通过后台状态反馈承接。
- 即使有 runtime governance，也不能声称 AI 输出完全可靠；它只是把风险变成可追踪、可测试、可降级的工程边界。

## 验证方式
- `backend/tests/test_prompt_runtime.py`: task inventory、mutation guard、timeout、parse/fallback 等。
- `backend/tests/test_llm_router.py`: provider chain、模型选择、fallback、环境变量。
- `make backend-check`: 后端编译与测试聚合。
- 手动检查 admin debug trace 时，确认没有 raw prompts、secrets 或普通用户不应看到的 provider 细节暴露。
- 核对 prompt task 与调用点是否一致，避免新增模型调用绕过 registry 或 mutation guard。

## 可公开摘要
IdeaSense AI treats AI as a set of bounded task roles, not a single all-powerful agent. Each model call declares what it is allowed to do, how it should be parsed, how it can fail, and which provider chain it can use. Model output cannot mutate product state unless it passes through the intended task boundary, which makes the system more reliable than ad-hoc prompt calls.
