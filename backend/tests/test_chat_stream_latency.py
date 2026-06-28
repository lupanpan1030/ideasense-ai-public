import pytest
from unittest.mock import Mock, patch

from app.services.chat_stream.latency import (
    latency_span,
    log_chat_stream_latency,
    record_latency_span,
)


def test_record_latency_span_records_elapsed_milliseconds() -> None:
    spans: dict[str, float] = {}

    with patch("app.services.chat_stream.latency.time.perf_counter", return_value=1.23456):
        record_latency_span(spans, "preflight", 1.0)

    assert spans == {"preflight": 234.6}


def test_record_latency_span_ignores_disabled_span_map() -> None:
    with patch("app.services.chat_stream.latency.time.perf_counter", return_value=2.0):
        record_latency_span(None, "preflight", 1.0)


def test_latency_span_records_elapsed_milliseconds_on_exit() -> None:
    spans: dict[str, float] = {}

    with patch(
        "app.services.chat_stream.latency.time.perf_counter",
        side_effect=[10.0, 10.045],
    ):
        with latency_span(spans, "db_commit"):
            pass

    assert spans == {"db_commit": 45.0}


def test_latency_span_allows_disabled_span_map() -> None:
    with patch(
        "app.services.chat_stream.latency.time.perf_counter",
        side_effect=[10.0, 10.2],
    ):
        with latency_span(None, "db_commit"):
            pass


def test_log_chat_stream_latency_uses_existing_log_payload_shape() -> None:
    logger = Mock()

    with (
        patch("app.services.chat_stream.latency.logging.getLogger", return_value=logger) as get_logger,
        patch("app.services.chat_stream.latency.time.perf_counter", return_value=12.345),
    ):
        log_chat_stream_latency(
            status_value="complete",
            project_id="project-1",
            started_at=12.0,
            spans={"z": 2.0, "a": 1.0},
        )

    get_logger.assert_called_once_with("uvicorn.error")
    logger.info.assert_called_once()
    args = logger.info.call_args.args
    assert args[0] == "chat_stream_latency status=%s project_id=%s total_ms=%.1f spans=%s"
    assert args[1:3] == ("complete", "project-1")
    assert args[3] == pytest.approx(345.0)
    assert args[4] == {"a": 1.0, "z": 2.0}
