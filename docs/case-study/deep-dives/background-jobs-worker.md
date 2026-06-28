# Deep Dive: Background Jobs Worker

## 一句话结论
Background jobs worker 负责把较慢、可重试、非前台必须完成的 AI 工作移出用户请求。它是改善等待体验和提高恢复能力的基础。

## 背景
AI 产品中很多任务不适合阻塞用户当前请求：

- context extraction
- claim verification
- stage summary generation
- report generation

当前稳定分支已经有 `background_jobs` 表和 worker，覆盖聊天抽取、阶段摘要、阶段确认后的 enrichment、claim verification 和报告生成。

## 设计目标
- job 可排队、可锁定、可重试、可失败记录。
- worker 设置系统 actor 和 org context，遵守 RLS 边界。
- job payload 使用稳定 ID，不保存 raw prompts 或 secrets。
- job idempotency key 防止重复执行造成重复状态写入。

## 当前实现
- `database/schema/schema.sql`: `background_jobs` 表。
- `backend/app/worker.py`: claim job、reset expired locks、process job、finalize job。
- 当前 job type:
  - `extract_answer_v0`
  - `stage_summary_v0`
  - `stage_finalize_v0`
  - `verify_question_claims_v0`
  - `report_generation_v0`
- `backend/app/services/stage_finalize_jobs.py`: 阶段确认后的 enrichment job 入队和幂等 key。
- `backend/app/services/report_jobs.py`: report generation 入队、状态合同和 stale/ready 判断。
- `backend/tests/test_worker_authoritative_extract.py`
- `backend/tests/test_worker_transactions.py`
- `backend/tests/test_background_jobs_conflict_sql.py`
- `backend/tests/test_report_jobs.py`

## 关键决策
- worker 使用 `FOR UPDATE SKIP LOCKED` claim job，支持多 worker 时避免重复领取。
- job status 包含 queued/running/succeeded/failed/cancelled。
- lock TTL 支持过期恢复。
- system actor 写入状态，普通用户不能直接越权执行后台写入。
- `stage_finalize_v0` 不推进阶段，只补充已确认阶段的 artifact 和验证层。
- `report_generation_v0` 的 ready 判断来自匹配当前 context version 的 final `project_reports` artifact。

## 风险与权衡
- 后台任务失败必须能被 UI 或 admin 观察，否则用户会卡在准备状态。
- job payload schema 需要稳定，否则 worker 版本升级会破坏旧 job。
- 不同 job 的 idempotency 边界要明确，例如 project/stage/context_version/locale。

## 验证方式
- worker 单元测试覆盖成功、失败、重试、事务边界。
- 手动启动 `python -m app.worker` 检查 queued job 能被消费。
- 对扩展 job type，新增 payload validation 和 retry 测试。

## 可公开摘要
The background worker turns slow AI work into recoverable jobs. This lets the product respond faster while still applying authoritative extraction, verification, post-confirm enrichment, and report generation through controlled backend state paths.
