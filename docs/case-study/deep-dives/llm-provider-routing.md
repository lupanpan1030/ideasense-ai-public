# Deep Dive: LLM Provider Routing

## 一句话结论
LLM provider routing 让 IdeaSense AI 可以按任务选择模型和 fallback chain。低延迟任务、抽取任务、报告任务可以使用不同 provider，而不是把所有 AI 调用绑定到单一模型。

## 背景
不同任务的要求不同：

- 用户可见的下一题和追问需要低延迟、自然语言质量。
- answer gate 和 extraction 需要稳定、便宜、可解析。
- stage summary、DVF scoring、final report 更需要综合能力和结构化输出。

单一模型配置很难同时满足成本、速度和质量。

## 设计目标
- 支持 task-specific provider chain。
- 支持 OpenAI-compatible provider。
- 支持 Gemini 和 Bedrock。
- 支持 task-specific model env override。
- provider 不可用时跳过，全部失败时显式报错。

## 当前实现
- `backend/app/core/llm_router.py`
- `backend/README.md`
- `docs/production-env.md`
- `backend/tests/test_llm_router.py`

当前稳定分支支持：

- `openai`
- `deepseek`
- `qwen`
- `gemini`
- `bedrock`

## 关键决策
- provider chain 由 `LLM_PROVIDER_<TASK>` 或 `LLM_PROVIDER_DEFAULT` 配置。
- 如果 task 有默认顺序，可以覆盖全局 default。
- OpenAI-compatible provider 共用部分调用路径，但模型和 base URL 分开配置。
- secrets 只读取后端环境变量，不进入前端。

## 风险与权衡
- provider 越多，配置错误和模型权限问题越多。
- fallback chain 不能掩盖质量问题，需要 trace 和测试观察真实 provider/model。
- 公开文档不能暴露真实 key、账号、失败响应详情。

## 验证方式
- `backend/tests/test_llm_router.py`
- 本地 `.env` 先验证，再考虑部署环境。
- 对真实 provider 的连通性测试只记录 provider/model/latency，不记录 secret。

## 可公开摘要
IdeaSense routes AI tasks across multiple providers so fast, cheap, and high-quality tasks can use different models. The provider router gives the product cost control, resilience, and a cleaner upgrade path without changing product workflows.
