"""Prompt runtime execution trace and failure-result helpers."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.prompt_runtime import (
        PromptContext,
        PromptTaskExecutionResult,
        PromptTaskFailure,
        PromptTaskPreparationResult,
        PromptTaskSpec,
        PromptTaskStreamResult,
    )

logger = logging.getLogger(__name__)


def serialize_prompt_task_trace(
    result: Any,
    *,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    trace = dict(result.trace or {})
    resolved_model = model if model is not None else getattr(result, "model", None)
    resolved_provider = (
        provider if provider is not None else getattr(result, "provider", None)
    )
    if resolved_model:
        trace["model"] = resolved_model
    if resolved_provider:
        trace["provider"] = resolved_provider
    fallback_kind = getattr(result, "fallback_kind", None)
    if fallback_kind:
        trace["fallback_kind"] = fallback_kind
    if result.failure:
        trace["failure_reason"] = result.failure.reason
    return trace


def resolve_prompt_task_timeout_ms(
    task: "PromptTaskSpec",
    *,
    minimum_ms: int | None = None,
) -> int | None:
    timeout_ms = task.timeout_ms
    if task.timeout_env:
        raw_value = os.getenv(task.timeout_env)
        if raw_value is not None and raw_value.strip():
            try:
                timeout_ms = int(raw_value)
            except ValueError:
                timeout_ms = task.timeout_ms
    if timeout_ms is None:
        return None
    if timeout_ms < 0:
        timeout_ms = 0
    if minimum_ms is not None and 0 < timeout_ms < minimum_ms:
        timeout_ms = minimum_ms
    return timeout_ms


def execution_trace(
    context: "PromptContext",
    task: "PromptTaskSpec",
    *,
    timeout_ms: int | None,
    temperature: float | None = None,
) -> dict[str, Any]:
    trace = dict(context.trace_metadata(task))
    trace["timeout_ms"] = timeout_ms
    trace["temperature"] = task.temperature if temperature is None else temperature
    trace["response_format"] = task.response_format
    trace["output_contract"] = task.output_contract
    trace["parse_strategy"] = task.parse_strategy
    return trace


def fallback_kind(task: "PromptTaskSpec") -> str | None:
    policy = (task.fallback_policy or "").strip()
    if not policy or policy == "none":
        return None
    return policy


def fallback_value(
    resolved_fallback_kind: str | None,
    failure: "PromptTaskFailure",
    fallback: Callable[["PromptTaskFailure"], Any] | None,
) -> Any:
    explicit_value = fallback(failure) if fallback else None
    if explicit_value is not None:
        return explicit_value
    if not resolved_fallback_kind:
        return None
    value: dict[str, Any] = {
        "kind": resolved_fallback_kind,
        "reason": failure.reason,
    }
    if failure.message:
        value["message"] = failure.message
    return value


def failure_result(
    task: "PromptTaskSpec",
    *,
    trace: Mapping[str, Any],
    reason: str,
    message: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    fallback: Callable[["PromptTaskFailure"], Any] | None = None,
) -> "PromptTaskExecutionResult":
    from app.services.prompt_runtime import PromptTaskExecutionResult, PromptTaskFailure

    failure = PromptTaskFailure(reason=reason, message=message)
    resolved_fallback_kind = fallback_kind(task)
    resolved_fallback_value = fallback_value(
        resolved_fallback_kind,
        failure,
        fallback,
    )
    logger.debug(
        "prompt task %s failed reason=%s trace=%s",
        task.task_key,
        reason,
        trace,
    )
    return PromptTaskExecutionResult(
        task_key=task.task_key,
        provider_task=task.provider_task,
        content=None,
        provider=provider,
        model=model,
        failure=failure,
        fallback_kind=resolved_fallback_kind,
        fallback_value=resolved_fallback_value,
        trace=trace,
    )


def preparation_failure_result(
    task: "PromptTaskSpec",
    *,
    trace: Mapping[str, Any],
    timeout_ms: int | None,
    temperature: float | None,
    reason: str,
    message: str | None = None,
    fallback: Callable[["PromptTaskFailure"], Any] | None = None,
) -> "PromptTaskPreparationResult":
    from app.services.prompt_runtime import PromptTaskFailure, PromptTaskPreparationResult

    failure = PromptTaskFailure(reason=reason, message=message)
    resolved_fallback_kind = fallback_kind(task)
    resolved_fallback_value = fallback_value(
        resolved_fallback_kind,
        failure,
        fallback,
    )
    logger.debug(
        "prompt task %s preparation failed reason=%s trace=%s",
        task.task_key,
        reason,
        trace,
    )
    return PromptTaskPreparationResult(
        task_key=task.task_key,
        provider_task=task.provider_task,
        messages=None,
        temperature=temperature,
        response_format=task.response_format,
        timeout_ms=timeout_ms,
        failure=failure,
        fallback_kind=resolved_fallback_kind,
        fallback_value=resolved_fallback_value,
        trace=trace,
    )


def stream_failure_result(
    task: "PromptTaskSpec",
    *,
    trace: Mapping[str, Any],
    reason: str,
    message: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    fallback: Callable[["PromptTaskFailure"], Any] | None = None,
) -> "PromptTaskStreamResult":
    from app.services.prompt_runtime import PromptTaskFailure, PromptTaskStreamResult

    failure = PromptTaskFailure(reason=reason, message=message)
    resolved_fallback_kind = fallback_kind(task)
    resolved_fallback_value = fallback_value(
        resolved_fallback_kind,
        failure,
        fallback,
    )
    logger.debug(
        "prompt task %s stream failed reason=%s trace=%s",
        task.task_key,
        reason,
        trace,
    )
    return PromptTaskStreamResult(
        task_key=task.task_key,
        provider_task=task.provider_task,
        provider=provider,
        model=model,
        failure=failure,
        fallback_kind=resolved_fallback_kind,
        fallback_value=resolved_fallback_value,
        trace=trace,
    )
