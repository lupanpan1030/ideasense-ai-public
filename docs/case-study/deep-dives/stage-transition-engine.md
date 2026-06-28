# Deep Dive: Stage Transition Engine

## 一句话结论
Stage transition engine 把“用户现在能不能继续回答、生成草稿、确认阶段、进入报告”变成可测试的纯决策，再由 runtime writer 写入数据库。它是防止 AI 聊天越过产品流程的关键边界。

## 背景
聊天产品看似自由，但 IdeaSense 的核心流程必须被约束：

```txt
problem -> market -> tech -> report
```

每个阶段都需要在 `in_progress`、`awaiting_confirm`、`passed` 之间转换。没有明确状态机时，最常见的问题是：

- 阶段已等待确认，用户仍能继续回答普通问题。
- 阶段已通过，后续消息仍修改旧阶段。
- 报告阶段被当成普通 interview stage。
- admin override 和自动 stage engine 混在一起。

## 设计目标
- 决策逻辑和数据库写入分离。
- 所有 stage/status 先 normalize。
- stage mismatch、not awaiting confirm、passed、report blocked 等原因可测试。
- 普通用户路径和 admin override 边界分开。

## 当前实现
- `backend/app/services/stage_transition.py`
- `backend/app/services/stage_runtime.py`
- `backend/tests/test_stage_transition.py`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/assessments.py`

## 关键决策
- `decide_stage_question_answer`: 控制当前 stage 是否允许继续回答问题。
- `decide_stage_draft_generation`: 控制是否允许生成 stage draft。
- `decide_stage_confirmation_advance`: 控制用户确认是否能推进下一阶段。
- `decide_report_confirmation_complete`: 控制报告阶段完成。
- writer 函数只消费 decision，不重新发明业务规则。

## 风险与权衡
- 纯决策服务会增加一层抽象，但显著提高测试和 review 清晰度。
- 过度自动推进会让用户失去控制，所以确认边界必须保留。
- 如果 missing paths 和 state_json 不同步，阶段 readiness 可能误判，需要 worker/context tests 兜底。

## 验证方式
- `backend/tests/test_stage_transition.py`
- `backend/tests/test_chat_sync_extraction.py`
- `backend/tests/test_assessments_stage_payload.py`
- `make backend-check`

## 可公开摘要
IdeaSense uses an explicit stage transition engine so the product does not become an uncontrolled chat. The engine decides when users can answer, review, confirm, advance, or complete a report, while database writers persist only allowed transitions.
