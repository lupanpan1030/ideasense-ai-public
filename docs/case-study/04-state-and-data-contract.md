# State Machine And Data Contract

## 一句话结论
IdeaSense AI 的表层体验是对话，但底层行为是一个数据库约束的阶段状态机。AI 可以提问、总结、抽取和建议；用户可以确认、修正和推进；但项目真正处在哪个阶段、哪些内容能进入报告、哪些内容只是 founder assumption，都必须由后端流程和 PostgreSQL 合同决定。

## 背景
创业评估流程看起来像聊天，但底层必须解决确定性问题：

- 当前项目在哪个阶段？
- 用户还能不能继续回答问题？
- 哪些字段缺失？
- 哪些值是 AI 建议、用户确认、用户编辑或未知？
- 阶段摘要是否来自当前 context version？
- 报告是否来自已确认阶段？
- 用户确认是否只是 workflow input，还是被误写成客观事实？

如果这些问题只靠聊天上下文解决，产品会很快变得不可恢复。

这里还有一个更细的可靠性问题：用户确认可以防止 AI 漂移，但确认本身也可能被误用。如果系统为了讨好用户，把用户自述、AI 推断或缺少证据的说法都包装成“已验证事实”，最终报告会变得好看但不可信。因此，IdeaSense 必须把“用户确认的流程输入”和“外部支持的事实证据”分开。

## 设计目标
- stage/status/variant 使用有限集合，不允许任意字符串漂移。
- question bank 驱动访谈顺序和 schema paths。
- `project_states.state_json` 保存正式结构化状态。
- `project_states.state_meta` 保存 answer meta、pending confirm、locale 等元数据。
- `project_stage_assessments` 保存阶段摘要和确认记录。
- `project_reports` 保存最终报告 artifact。
- context card 保存 confirmed inputs、founder assumptions、AI inferences、unknowns、evidence gaps 和 verification summary。
- AI 推断或建议必须先进入待确认状态，不能直接升级成 confirmed input。
- 用户确认能推进流程，但不能把 founder claim 自动变成 externally verified fact。
- RLS 和 org/project 外键保护多租户边界。

## 当前实现
核心表：

- `projects`: 项目本体，包含 `current_stage`、`current_variant`、`stage_status`。
- `project_runtime`: 当前问题、下一问题、missing paths、turn state。
- `conversation_messages`: 聊天消息和关联 question instance。
- `project_states`: 结构化项目状态与 metadata。
- `project_stage_assessments`: 阶段摘要、评分、确认信息。
- `project_reports`: 最终报告内容、版本、Report v2 artifact 字段和生成时的 state version。
- `background_jobs`: 后台抽取、阶段摘要、stage finalize、验证和报告生成等可重试任务。

关键状态对象：

- `current_stage`: 当前阶段，只允许 `problem`、`market`、`tech`、`report`。
- `stage_status`: 阶段控制状态，只允许 `in_progress`、`awaiting_confirm`、`passed`。
- `context_version`: 上下文版本，用来避免用户在过期摘要上确认。
- `missing_paths`: 当前阶段仍缺的关键字段。
- `pending_confirm`: AI 推断出的待确认值，需要用户 accept / reject / edit。
- `context_card`: 报告前的证据分层卡片，区分 workflow-confirmed input、assumption、AI inference、unknown、evidence gap 和 verification result。
- `report_job_status`: 报告生成的产品状态，包含 `not_started`、`queued`、`running`、`finalizing`、`ready`、`failed`、`stale`。
- `artifact_schema_version`: 当前结构化报告 artifact 使用 `report_v2`，并持久化 decision snapshot、score rationales、risk register、experiment plan 和 evidence index。

核心服务/路由：

- `backend/app/api/routes/projects.py`: 项目创建、上下文读取、pending confirm 处理、报告读取。
- `backend/app/api/routes/chat.py`: 用户回答、SSE、抽取/队列、stage gate readiness。
- `backend/app/api/routes/assessments.py`: 阶段摘要、确认、验证、报告。
- `backend/app/services/stage_transition.py`: 阶段问题回答、草稿、确认、报告完成等纯决策规则。
- `backend/app/services/stage_runtime.py`: 将阶段决策写回 `projects` / `project_runtime`。
- `backend/app/services/stage_finalize_jobs.py`: 阶段确认后 enqueue enrichment job。
- `backend/app/services/report_jobs.py`: 报告生成 job、状态轮询和 context version stale/ready 判断。
- `database/schema/schema.sql`: schema、foreign keys、checks、triggers、RLS policies。

## 关键决策
- `in_progress`: 当前阶段可以继续回答问题。
- `awaiting_confirm`: 当前阶段不再接收普通回答，用户需要 review/confirm summary。
- `passed`: 阶段锁定，普通聊天不能继续修改该阶段。
- `report`: 不是普通 interview stage，不能继续走聊天问题回答。
- `report_generation_v0`: 通过 `project_id`、`context_version` 和 locale 幂等入队；`ready` 只在匹配当前 state version 的 final report artifact 存在时成立。
- `stage_finalize_v0`: 确认后补充 scoring、context card、validation plan、QA digest 和 verification，不负责推进 stage。
- 用户确认是状态推进边界；AI summary 生成不是确认。
- 用户确认提升的是 workflow reliability，不是把用户自述自动变成客观事实。
- 前端负责引导用户，LLM 负责建议和总结，但数据库支持的后端流程才决定什么内容真正进入项目状态。

这条边界很重要：

```txt
AI suggestion -> pending_confirm
User accepts -> workflow-confirmed input
External support -> verification_summary
Report -> must preserve assumptions, unknowns, and evidence gaps
```

也就是说，确认可以让项目进入下一阶段，但报告仍然需要说明哪些内容只是 founder assumption，哪些内容有外部支持，哪些内容缺证据。系统不应该为了让用户满意而把所有 confirmed answer 都写成 verified fact。

建议用这张表解释：

| Stage/status | Answer | Draft | Confirm | Result |
| --- | --- | --- | --- | --- |
| problem/market/tech + `in_progress` | Allowed | Blocked | Blocked | 缺失字段解决后可进入 `awaiting_confirm` |
| problem/market/tech + `awaiting_confirm` | Blocked | Allowed | Allowed | 用户确认后推进到下一阶段 |
| problem/market/tech + `passed` | Blocked | Blocked | Blocked | 阶段锁定 |
| report + `awaiting_confirm` | Blocked | Blocked | Report confirm only | 报告持久化并进入完成状态 |

## 风险与权衡
- 数据库约束越强，开发时需要处理更多 conflict 和 version mismatch，但这正是 AI 产品可恢复性的基础。
- `state_json` 灵活，但必须依赖 schema/spec/测试约束，否则会变成无结构 JSON dump。
- `state_meta` 能保存丰富元信息，但公开文档必须避免暴露内部 trace、provider 和敏感调试信息。
- 用户确认能防止 AI 静默漂移，但如果没有 evidence layering，也可能让系统过度相信用户自述。
- verification 能提高可信度，但不能当成万能判官；无法外部验证的 claim 应保留为 not applicable、uncertain 或 evidence gap。
- 这篇文档应证明状态建模能力，不应退化成数据库表结构说明。

## 验证方式
- `backend/tests/test_stage_transition.py`
- `backend/tests/test_project_runtime_schema.py`
- `backend/tests/test_project_pending_gate_sync.py`
- `backend/tests/test_assessments_stage_payload.py`
- `backend/tests/test_project_report_access.py`
- `backend/tests/test_report_jobs.py`
- `backend/tests/test_worker_authoritative_extract.py`
- `make backend-check`
- 核对 `docs/spec/PUBLIC_SPEC.md`、私有 Master Spec 和当前代码中 Stage Gate、pending confirm、context card、verification summary 和 report contract 的定义。

## 可公开摘要
IdeaSense AI feels like a chat product, but behaves like a state machine. PostgreSQL stores the authoritative project stage, structured context, pending confirmations, user-confirmed assessments, evidence layers, and final report artifacts. User confirmation moves the workflow forward, but it does not turn founder claims into verified facts; the report must still preserve assumptions, unknowns, and evidence gaps.
