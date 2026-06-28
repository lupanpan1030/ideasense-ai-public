# Deep Dive: Prompt Task Registry

## 一句话结论
Prompt task registry 是 IdeaSense AI 的 AI 调用控制面。它把每个 prompt 调用声明成可测试、可路由、可降级、可审计的任务，而不是散落在 route 里的临时 prompt 字符串。

## 背景
同一个创业评估流程里有很多不同 prompt：

- `answer_gate`
- `extract_answer`
- `question_compose`
- `followup_compose`
- `qa_digest`
- `stage_summary`
- `dvf_scoring`
- `final_report`
- `claim_verification`

这些 prompt 不应拥有同样权限。

## 设计目标
- 每个任务声明 system/user template。
- 每个任务声明 provider task 和 timeout。
- 每个任务声明 output contract / parse strategy。
- 每个任务声明 allowed mutation class。
- 所有调用经过同一套 prepare/execute/trace 路径。

## 当前实现
- `backend/app/services/prompt_runtime.py`
- `backend/app/services/prompt_output_parsers.py`
- `backend/app/services/prompt_templates.py`
- `backend/app/prompts/`
- `backend/tests/test_prompt_runtime.py`

## 关键决策
- route/service 调用 prompt 时传入 expected mutation，prompt runtime 负责 guard。
- trace 记录 redacted metadata，不直接保存 raw prompt。
- parser failure 是显式 failure，不应当作成功文本使用。

## 风险与权衡
- 新增 prompt 需要补 registry 配置和测试。
- registry 会让实验速度变慢，但减少生产事故。
- prompt task 和 provider task 需要保持命名一致，否则 routing/runbook 会漂移。

## 验证方式
- 检查 task inventory。
- 测试 mutation guard。
- 测试 timeout 和 fallback。
- 测试 parser error path。

## 可公开摘要
IdeaSense uses a prompt task registry to make AI behavior governable. Each prompt task declares what it can do, how it is routed, how it is parsed, and what state boundary it is allowed to affect.
