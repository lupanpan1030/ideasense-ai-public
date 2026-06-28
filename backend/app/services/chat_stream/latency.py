from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager


def record_latency_span(
    spans: dict[str, float] | None,
    name: str,
    started_at: float,
) -> None:
    if spans is None:
        return
    spans[name] = round((time.perf_counter() - started_at) * 1000, 1)


@contextmanager
def latency_span(spans: dict[str, float] | None, name: str) -> Iterator[None]:
    started_at = time.perf_counter()
    try:
        yield
    finally:
        record_latency_span(spans, name, started_at)


def log_chat_stream_latency(
    *,
    status_value: str,
    spans: dict[str, float],
    started_at: float,
    project_id: str | None = None,
) -> None:
    logging.getLogger("uvicorn.error").info(
        "chat_stream_latency status=%s project_id=%s total_ms=%.1f spans=%s",
        status_value,
        project_id,
        (time.perf_counter() - started_at) * 1000,
        dict(sorted(spans.items())),
    )
