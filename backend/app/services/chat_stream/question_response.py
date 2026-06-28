import asyncio
import time
from typing import Any

from sqlalchemy import text

from app.api.deps import set_system_actor
from app.core.database_async import AdminAsyncSessionLocal
from app.core.llm_router import call_llm_stream
from app.services.chat_followup_compose import (
    QUESTION_COMPOSE_FALLBACK_SOURCE,
    QUESTION_COMPOSE_SOURCE,
    sanitize_composed_question,
)
from app.services.chat_runtime_settings import (
    resolve_question_compose_start_timeout_sec,
)
from app.services.chat_stream.events import (
    build_turn_event_meta,
    sse_event,
    stream_text_events,
)
from app.services.chat_stream.latency import record_latency_span
from app.services.chat_stream.message_persistence import (
    update_streamed_question_message,
)
from app.services.prompt_runtime import (
    PromptTaskPreparationResult,
    serialize_prompt_task_trace,
    stream_prepared_prompt_task,
)


async def stream_question_response_events(
    context: dict[str, Any],
    *,
    actor_user_id: Any,
) -> Any:
    event_meta = build_turn_event_meta(context)
    final_content = ""
    source = context.get("fallback_source") or QUESTION_COMPOSE_FALLBACK_SOURCE
    compose_model = None
    compose_provider = None
    streamed = False
    chunks: list[str] = []
    compose_messages = context.get("compose_messages")
    compose_task = context.get("compose_task") or "question_compose"
    success_source = context.get("success_source") or QUESTION_COMPOSE_SOURCE
    compose_temperature = context.get("compose_temperature")
    compose_response_format = context.get("compose_response_format")
    compose_timeout_ms = context.get("compose_timeout_ms")
    compose_prepared = context.get("compose_prepared")
    latency_spans = context.get("latency_spans")
    compose_started_at: float | None = None

    if compose_messages:
        compose_started_at = time.perf_counter()
        first_compose_chunk = True
        try:
            if not isinstance(compose_prepared, PromptTaskPreparationResult):
                compose_prepared = PromptTaskPreparationResult(
                    task_key=context.get("compose_task_key") or compose_task,
                    provider_task=compose_task,
                    messages=compose_messages,
                    temperature=compose_temperature,
                    response_format=compose_response_format,
                    timeout_ms=compose_timeout_ms,
                    trace=context.get("compose_trace") or {},
                )
            stream_result = await stream_prepared_prompt_task(
                compose_prepared,
                stream_call=call_llm_stream,
            )
            timeout_sec = resolve_question_compose_start_timeout_sec(
                compose_timeout_ms
            )
            if not stream_result.ok:
                if stream_result.failure:
                    context["compose_stream_failure"] = stream_result.failure.reason
                    context["compose_trace"] = serialize_prompt_task_trace(
                        stream_result
                    )
                    raise RuntimeError(stream_result.failure.reason)
                raise RuntimeError("compose stream failed")
            record_latency_span(latency_spans, "compose_start", compose_started_at)
            compose_model = stream_result.model
            compose_provider = stream_result.provider
            stream_iter = stream_result.stream.__aiter__()
            while True:
                try:
                    if not chunks and timeout_sec > 0:
                        chunk = await asyncio.wait_for(
                            stream_iter.__anext__(),
                            timeout_sec,
                        )
                    else:
                        chunk = await stream_iter.__anext__()
                except StopAsyncIteration:
                    break
                if not chunk:
                    continue
                chunks.append(chunk)
                if first_compose_chunk:
                    first_compose_chunk = False
                    record_latency_span(
                        latency_spans,
                        "compose_first_token",
                        compose_started_at,
                    )
                    yield sse_event("assistant_first_token", event_meta)
                streamed = True
                yield sse_event("token", {"delta": chunk, **event_meta})
            raw_content = "".join(chunks)
            sanitized_content = sanitize_composed_question(raw_content)
            if sanitized_content:
                final_content = sanitized_content
                source = success_source
        except asyncio.CancelledError:
            raise
        except Exception:
            if chunks:
                raw_content = "".join(chunks)
                sanitized_content = sanitize_composed_question(raw_content)
                if sanitized_content:
                    final_content = sanitized_content
                    source = success_source
                else:
                    return
        finally:
            record_latency_span(latency_spans, "compose_complete", compose_started_at)

    if not final_content:
        if chunks:
            return
        final_content = context.get("fallback_content") or ""
        async for event in stream_text_events(
            final_content,
            event_meta=event_meta,
            emit_markers=True,
        ):
            yield event
        return

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            await set_system_actor(session)
            await session.execute(
                text("SELECT set_config('app.user_id', :user_id, true)"),
                {"user_id": str(actor_user_id)},
            )
            await session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": context["org_id"]},
            )
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )
            await update_streamed_question_message(
                session,
                context,
                content=final_content,
                source=source,
                compose_model=compose_model,
                compose_provider=compose_provider,
                streamed=streamed,
            )
    yield sse_event("assistant_done", build_turn_event_meta(context))
