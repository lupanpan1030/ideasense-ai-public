# Security, Reliability, And Delivery

## 一句话结论
IdeaSense AI 的交付可信度来自权限边界、RLS、环境 guardrails、usage limits、测试和明确的 Definition of Done。AI 产品不能只证明“会生成”，还要证明不会越权、不会泄露、不会把草稿当事实。

## 背景
IdeaSense AI 处理的是创业项目想法、用户访谈内容、阶段摘要和报告。这些数据可能包含未公开产品方向、商业假设和技术计划，所以安全边界和数据完整性是产品能力的一部分。

## 设计目标
- 普通用户只能访问自己组织和项目范围内的数据。
- admin/platform admin 能力走显式边界，不混入学生主流程。
- production 禁用 dev bypass 和不安全默认配置。
- LLM provider keys、database URLs、verification tokens 只留在后端环境。
- AI 生成内容必须经过 validation、confirmation 或 artifact 持久化路径。
- 每次完成工作都能说清楚跑了什么验证。

## 当前实现
安全和可靠性相关模块：

- `backend/app/core/security.py`: JWT primitives。
- `backend/app/api/deps.py`: actor/session context。
- `backend/app/core/permissions.py`: capability matrix。
- `backend/app/core/env.py`: 环境变量和 production guardrails。
- `backend/app/core/rate_limits.py`: rate limit。
- `backend/app/core/usage_limits.py`: LLM usage limit。
- `backend/app/core/email_verification.py`: 邮箱验证边界。
- `database/schema/schema.sql`: RLS、foreign keys、checks、triggers。
- `docs/production-env.md`: production environment guidance。
- `docs/DEFINITION_OF_DONE.md`: 当前质量门。

当前质量门：

- `make backend-check`
- `make frontend-lint`
- `make frontend-build`
- `make check`
- `git diff --check`

## 关键决策
- `DATABASE_URL_ADMIN` 只用于后端/admin/worker 需要的 privileged path。
- 前端不持有 provider secrets。
- production 环境拒绝 dev auth bypass。
- RLS 使用 `app.user_id`、`app.org_id`、`app.actor_type` 作为数据库会话上下文。
- prompt traces 是 redacted debug metadata，不暴露给普通用户视图。
- 报告和阶段摘要只能使用项目已有数据，不能凭空补事实。

## 风险与权衡
- RLS 和 privileged admin session 增加开发复杂度，但减少跨组织数据泄露风险。
- Usage limit 和 email verification 会增加 onboarding 摩擦，但能控制滥用和成本。
- Admin debug 能力有价值，但必须限制在 org/platform admin 权限内。
- 文档公开时不能泄露真实 env、provider access failure、内部账号或数据库地址。

## 验证方式
- `backend/tests/test_env_flags.py`
- `backend/tests/test_project_report_access.py`
- `backend/tests/test_assessment_safety_guards.py`
- `backend/tests/test_admin_reports.py`
- `backend/tests/test_email_sender_logging.py`
- `make backend-check`
- `git diff --check`

## 可公开摘要
IdeaSense treats reliability and security as product features. The system uses org-scoped permissions, PostgreSQL RLS, production environment guardrails, usage limits, and explicit confirmation paths so AI output cannot silently become accepted project truth.
