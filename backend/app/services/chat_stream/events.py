from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.services.localization import normalize_output_locale


STREAM_BREAK_CHARS = set(" \n\t.,!?;:，。！？；：")

CHAT_STATUS_LABELS = {
    "en": {
        "checking_answer": "Checking your answer",
        "preparing_context": "Preparing project context",
        "preparing_next_question": "Preparing the next question",
        "composing_response": "Writing the response",
    },
    "zh": {
        "checking_answer": "正在检查你的回答",
        "preparing_context": "正在准备项目上下文",
        "preparing_next_question": "正在准备下一题",
        "composing_response": "正在组织回复",
    },
}


def sse_event(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def clean_event_meta(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not extra:
        return {}
    payload: dict[str, Any] = {}
    for key, value in extra.items():
        if value is None:
            continue
        if isinstance(value, UUID):
            payload[key] = str(value)
        else:
            payload[key] = value
    return payload


def build_streamed_question_message_meta(
    context: dict[str, Any],
    *,
    source: str,
    compose_model: str | None = None,
    compose_provider: str | None = None,
    streamed: bool = False,
) -> dict[str, Any]:
    meta = dict(context.get("meta") or {})
    meta["source"] = source
    meta["display_format"] = "markdown"
    if streamed:
        meta["streamed"] = True
    if compose_model:
        meta["compose_model"] = compose_model
    if compose_provider:
        meta["compose_provider"] = compose_provider
    trace = context.get("compose_trace")
    if isinstance(trace, dict):
        trace_payload = dict(trace)
        if compose_model:
            trace_payload["model"] = compose_model
        if compose_provider:
            trace_payload["provider"] = compose_provider
        failure_reason = context.get("compose_stream_failure") or context.get(
            "compose_prepare_failure"
        )
        if failure_reason:
            trace_payload["failure_reason"] = failure_reason
        meta["prompt_task_trace"] = trace_payload

    return meta


def build_turn_event_meta(context: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "request_id",
        "client_message_id",
        "user_message_id",
        "source_message_id",
        "assistant_message_id",
        "question_instance_id",
        "project_id",
    )
    return clean_event_meta({key: context.get(key) for key in keys})


def build_stream_error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Chat request failed."
        return {
            "status": "error",
            "code": exc.status_code,
            "detail": detail,
        }
    return {
        "status": "error",
        "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "Chat request failed. Please try again.",
    }


def resolve_stream_settings() -> tuple[int, int, int]:
    min_chars = int(os.getenv("SSE_STREAM_MIN_CHARS", "12") or 12)
    max_chars = int(os.getenv("SSE_STREAM_MAX_CHARS", "28") or 28)
    delay_ms = int(os.getenv("SSE_STREAM_DELAY_MS", "18") or 18)
    if max_chars < 1:
        max_chars = 1
    if min_chars < 1:
        min_chars = 1
    if min_chars > max_chars:
        min_chars = max_chars
    if delay_ms < 0:
        delay_ms = 0
    return min_chars, max_chars, delay_ms


def iter_stream_chunks(text: str, min_chars: int, max_chars: int):
    if not text:
        return
    buffer = ""
    for ch in text:
        buffer += ch
        if len(buffer) >= max_chars:
            yield buffer
            buffer = ""
            continue
        if len(buffer) >= min_chars and ch in STREAM_BREAK_CHARS:
            yield buffer
            buffer = ""
    if buffer:
        yield buffer


async def stream_text_events(
    text: str,
    *,
    event_meta: dict[str, Any] | None = None,
    emit_markers: bool = False,
):
    if not text:
        return
    meta_payload = clean_event_meta(event_meta)
    if emit_markers:
        yield sse_event("assistant_first_token", meta_payload)
    min_chars, max_chars, delay_ms = resolve_stream_settings()
    if delay_ms == 0:
        yield sse_event("token", {"delta": text, **meta_payload})
        if emit_markers:
            yield sse_event("assistant_done", meta_payload)
        return
    for chunk in iter_stream_chunks(text, min_chars, max_chars):
        yield sse_event("token", {"delta": chunk, **meta_payload})
        await asyncio.sleep(delay_ms / 1000)
    if emit_markers:
        yield sse_event("assistant_done", meta_payload)


def build_chat_status_payload(
    phase: str,
    output_locale: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    locale = normalize_output_locale(output_locale)
    labels = CHAT_STATUS_LABELS.get(locale, CHAT_STATUS_LABELS["en"])
    label = labels.get(phase) or CHAT_STATUS_LABELS["en"].get(phase)
    return {"phase": phase, "label": label, "detail": None, **clean_event_meta(extra)}


def sse_status_event(
    phase: str,
    output_locale: str | None,
    extra: dict[str, Any] | None = None,
) -> str:
    return sse_event("status", build_chat_status_payload(phase, output_locale, extra))
