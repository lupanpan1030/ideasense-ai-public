import asyncio
import json
import uuid
from unittest.mock import patch

from app.services.chat_stream.events import (
    build_chat_status_payload,
    build_streamed_question_message_meta,
    build_turn_event_meta,
    clean_event_meta,
    sse_event,
    stream_text_events,
)


def test_sse_event_serializes_unicode_payload() -> None:
    event = sse_event("status", {"label": "正在检查"})

    assert event.startswith("event: status\n")
    payload = json.loads(event.split("data: ", 1)[1])
    assert payload == {"label": "正在检查"}


def test_clean_event_meta_drops_none_and_stringifies_uuid() -> None:
    value = uuid.UUID("11111111-1111-1111-1111-111111111111")

    assert clean_event_meta({"project_id": value, "empty": None}) == {
        "project_id": str(value)
    }


def test_build_chat_status_payload_uses_localized_label() -> None:
    payload = build_chat_status_payload(
        "checking_answer",
        "zh",
        {"project_id": "project-1"},
    )

    assert payload == {
        "phase": "checking_answer",
        "label": "正在检查你的回答",
        "detail": None,
        "project_id": "project-1",
    }


def test_build_streamed_question_message_meta_enriches_trace_payload() -> None:
    context = {
        "meta": {"content_locale": "en"},
        "compose_trace": {"task_key": "question_compose"},
        "compose_stream_failure": "first token timeout",
    }

    payload = build_streamed_question_message_meta(
        context,
        source="question_compose_v0",
        compose_model="gpt-test",
        compose_provider="openai",
        streamed=True,
    )

    assert payload == {
        "content_locale": "en",
        "source": "question_compose_v0",
        "display_format": "markdown",
        "streamed": True,
        "compose_model": "gpt-test",
        "compose_provider": "openai",
        "prompt_task_trace": {
            "task_key": "question_compose",
            "model": "gpt-test",
            "provider": "openai",
            "failure_reason": "first token timeout",
        },
    }
    assert context["compose_trace"] == {"task_key": "question_compose"}


def test_build_streamed_question_message_meta_uses_prepare_failure_fallback() -> None:
    payload = build_streamed_question_message_meta(
        {
            "compose_trace": {"task_key": "followup_compose"},
            "compose_prepare_failure": "provider unavailable",
        },
        source="question_compose_fallback",
    )

    assert payload == {
        "source": "question_compose_fallback",
        "display_format": "markdown",
        "prompt_task_trace": {
            "task_key": "followup_compose",
            "failure_reason": "provider unavailable",
        },
    }


def test_build_turn_event_meta_filters_none_and_stringifies_uuid() -> None:
    question_instance_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    payload = build_turn_event_meta(
        {
            "request_id": "request-1",
            "client_message_id": None,
            "user_message_id": 10,
            "source_message_id": 10,
            "assistant_message_id": None,
            "question_instance_id": question_instance_id,
            "project_id": "project-1",
            "ignored": "value",
        }
    )

    assert payload == {
        "request_id": "request-1",
        "user_message_id": 10,
        "source_message_id": 10,
        "question_instance_id": str(question_instance_id),
        "project_id": "project-1",
    }


def test_stream_text_events_can_emit_single_token_without_delay() -> None:
    async def collect() -> list[str]:
        with patch.dict(
            "os.environ",
            {"SSE_STREAM_DELAY_MS": "0"},
            clear=False,
        ):
            return [
                item
                async for item in stream_text_events(
                    "hello",
                    event_meta={"project_id": "project-1"},
                    emit_markers=True,
                )
            ]

    events = asyncio.run(collect())

    assert [item.split("\n", 1)[0] for item in events] == [
        "event: assistant_first_token",
        "event: token",
        "event: assistant_done",
    ]
    token_payload = json.loads(events[1].split("data: ", 1)[1])
    assert token_payload == {"delta": "hello", "project_id": "project-1"}
