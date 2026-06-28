# Latency And Background Jobs Case Study

## 一句话结论
IdeaSense AI 的等待体验问题不只是“模型慢”，而是前台请求串联了太多不必立即完成的工作。当前方向是保留最小可见路径，把抽取、验证、阶段确认后的 enrichment 和报告生成移到可恢复后台任务，并给用户明确进度。

## 背景
分阶段 AI 产品很容易形成一条很长的同步链：

```txt
answer gate -> extraction -> missing path update -> next question -> stage summary -> DVF -> report
```

如果所有工作都发生在用户当前请求里，用户会看到“AI 正在想”很久，甚至误以为页面卡死。这个问题在 Stage Gate 和报告生成阶段尤其明显。

## 设计目标
- 聊天前台只等待继续对话所必需的最小判断。
- `answer_gate` 继续保留在可见路径，因为它决定是否继续追问。
- extraction、verification、summary、stage finalize、report 这类较慢任务应通过 `background_jobs` 或等价可恢复状态处理。
- 前端显示 product-level progress，不显示 provider/model/trace/secrets。
- 后台任务失败时可重试，不能静默失败。
- 状态权威仍然是项目 runtime、project states、stage assessments 和 reports，不是进度文案。

## 当前实现
当前稳定分支已有的基础：

- `backend/app/api/routes/chat.py`: SSE chat 主入口、answer gate、抽取队列、stage gate readiness。
- `backend/app/services/stage_finalize_jobs.py`: 阶段确认后入队 `stage_finalize_v0`，用于评分、context card、validation plan、QA digest 和验证补充。
- `backend/app/services/report_jobs.py`: 入队 `report_generation_v0`，并提供 `not_started`、`queued`、`running`、`finalizing`、`ready`、`failed`、`stale` 状态合同。
- `backend/app/worker.py`: 消费 `background_jobs`，支持 `extract_answer_v0`、`stage_summary_v0`、`stage_finalize_v0`、`verify_question_claims_v0` 和 `report_generation_v0`。
- `database/schema/schema.sql`: `background_jobs` 表包含 job type、status、priority、payload、idempotency key、attempts、lock 等字段。
- `frontend/features/chat/chat-stream.ts`: 解析 SSE event。
- `frontend/features/chat/use-chat-thread.ts`: 管理 chat streaming、report status polling 和进入 report page 的状态。
- `frontend/features/reports/report-viewer.tsx`: 报告页轮询 report status，并区分准备中、失败、stale 和 ready。

当前仍要继续沉淀的方向：

- 前台 chat path 不等待非必要 extraction。
- Stage confirm 的同步路径只做确认、状态推进和入队，重 AI enrichment 交给 `stage_finalize_v0`。
- Report generation 使用 background job、progress phases、retry 和 context version stale 判断。
- 对 real-path first token、stage gate、report generation 分别测量，不只看单元测试。

## 关键决策
- 进度提示不是性能优化本身，只是减少用户不确定感。
- 真正的优化是移除 visible path 中不必要的同步等待。
- 低风险 deterministic heuristics 可以用于即时路由，但不能替代正式 extraction 状态写入。
- report usage accounting 应在报告成功持久化后记录，不应在用户点击按钮时提前记账。

## 风险与权衡
- 下一题可能在一个 turn 内基于旧状态生成，因此需要 worker 后续修正 missing paths 或进入 stage-ready 状态。
- 后台任务会引入 polling/retry UI 和状态一致性问题。
- 如果只做 status label，不拆同步链，用户体验不会根本改善。
- 如果过早把所有东西异步化，用户可能不知道当前阶段到底是否完成。

## 验证方式
需要分层验证：

- 单元测试：slow extraction 不阻塞 passing chat response。
- worker 测试：后台 extraction、stage finalize 和 report generation 仍能写回 project state、stage artifact 或 report artifact。
- frontend 测试：status event 能正确显示、清除、错误恢复。
- real-path 测量：send-to-first-token、stream completion、Stage Gate 准备、Report ready。
- 回归命令：`make backend-check`、`make frontend-lint`、`make frontend-build`、`git diff --check`。

## 可公开摘要
The latency case study shows that AI product performance is not only a model-selection problem. The larger issue is visible-path design: which decisions must block the user, and which AI work can run behind a recoverable job system. IdeaSense keeps answer gating and confirmation checks in the foreground, while extraction, verification, post-confirm enrichment, and report generation run through background workflows with product-level progress.
