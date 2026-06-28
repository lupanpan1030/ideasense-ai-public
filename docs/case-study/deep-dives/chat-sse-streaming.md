# Deep Dive: Chat SSE Streaming

## 一句话结论
聊天体验使用 SSE 承载 token、metadata、question meta、stage gate readiness 和 done/error event。这样可以保留流式 AI 体验，同时保持 HTTP 请求边界和后端状态控制。

## 背景
IdeaSense 的聊天不是普通消息流。一个用户回答可能触发：

- 用户消息持久化。
- answer gate 判断。
- context extraction 或后台任务。
- 下一题生成。
- stage gate readiness。
- 前端 context board / stage gate UI 更新。

SSE 足够支持这些事件，同时比 WebSocket 更简单。

## 设计目标
- 流式输出 assistant token。
- 支持非 token 事件，例如 `question_meta`、`stage_gate_ready`、`done`、`error`。
- 前端能够在流结束后刷新 history 和 context。
- 不让前端成为状态权威。

## 当前实现
- `backend/app/api/routes/chat.py`: `POST /api/v1/chat/stream` 和 `_sse_event`。
- `frontend/features/chat/chat-stream.ts`: SSE block 解析和 event dispatch。
- `frontend/features/chat/chat-stream-handlers.ts`: token/status/done/error handler。
- `frontend/features/chat/use-chat-thread.ts`: streaming lifecycle 和 UI 状态。
- `frontend/tests/chat-stream-events.test.mjs`
- `frontend/tests/chat-stream-flow.test.mjs`

## 关键决策
- 用 event name 区分 token、metadata、stage gate、error，而不是把所有内容塞进 assistant text。
- `done` 表示 stream 生命周期完成，不表示所有后台状态都已经完成。
- `stage_gate_ready` 是 UI 信号；真正的阶段推进仍由 confirm API 和后端状态写入控制。

## 风险与权衡
- SSE parser 要处理 chunk 边界和 JSON parse failure。
- 如果缺少 idle timeout，前端可能一直等一个断掉的流。
- 如果 event 语义混乱，UI 会误把 progress 当成状态完成。

## 验证方式
- 前端 SSE 解析测试。
- 手动 real-path 检查：用户发送回答后 token 能流式出现，done 后 history 可刷新。
- 后端 focused tests 覆盖 stage gate readiness 和 error payload。

## 可公开摘要
The chat surface is streamed with Server-Sent Events, but token text is only one event type. The stream also carries safe product events such as question metadata and stage-gate readiness while the backend remains the authority for state transitions.
