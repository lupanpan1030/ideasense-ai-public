"""Prompt task registry and sectioned context assembly."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.core.llm_router import call_llm, call_llm_stream, has_available_provider
from app.services import prompt_runtime_execution
from app.services.prompt_output_parsers import get_prompt_output_parser
from app.services.prompt_task_specs import (
    DEFAULT_PROMPT_TASK_SPECS,
    PromptMutationClass,
    PromptTaskSpec,
)
from app.services.prompt_templates import render_prompt_template

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PromptTaskFailure:
    reason: str
    message: str | None = None


@dataclass(frozen=True)
class PromptTaskExecutionResult:
    task_key: str
    provider_task: str
    content: str | None
    provider: str | None = None
    model: str | None = None
    parsed: Any = None
    failure: PromptTaskFailure | None = None
    fallback_kind: str | None = None
    fallback_value: Any = None
    trace: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failure is None

    @property
    def failure_reason(self) -> str | None:
        return self.failure.reason if self.failure else None


@dataclass(frozen=True)
class PromptTaskPreparationResult:
    task_key: str
    provider_task: str
    messages: list[dict[str, str]] | None
    temperature: float | None
    response_format: str | None
    timeout_ms: int | None
    failure: PromptTaskFailure | None = None
    fallback_kind: str | None = None
    fallback_value: Any = None
    trace: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failure is None

    @property
    def failure_reason(self) -> str | None:
        return self.failure.reason if self.failure else None


@dataclass(frozen=True)
class PromptTaskStreamResult:
    task_key: str
    provider_task: str
    stream: Any = None
    provider: str | None = None
    model: str | None = None
    failure: PromptTaskFailure | None = None
    fallback_kind: str | None = None
    fallback_value: Any = None
    trace: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failure is None

    @property
    def failure_reason(self) -> str | None:
        return self.failure.reason if self.failure else None


@dataclass(frozen=True)
class PromptSection:
    name: str
    content: str
    required: bool
    budget_chars: int | None = None
    truncated: bool = False

    @property
    def size_chars(self) -> int:
        return len(self.content)


@dataclass(frozen=True)
class PromptContext:
    task_key: str
    variables: Mapping[str, Any]
    sections: tuple[PromptSection, ...] = field(default_factory=tuple)

    def section_names(self) -> tuple[str, ...]:
        return tuple(section.name for section in self.sections)

    def trace_metadata(self, task: PromptTaskSpec) -> dict[str, Any]:
        return {
            "task_key": task.task_key,
            "provider_task": task.provider_task,
            "system_template": task.system_template,
            "user_template": task.user_template,
            "allowed_mutation": task.allowed_mutation.value,
            "fallback_policy": task.fallback_policy,
            "sections": [
                {
                    "name": section.name,
                    "required": section.required,
                    "size_chars": section.size_chars,
                    "budget_chars": section.budget_chars,
                    "truncated": section.truncated,
                }
                for section in self.sections
            ],
            "variables": {
                key: _summarize_variable(value)
                for key, value in self.variables.items()
            },
            "redacted": True,
        }


class PromptTaskRegistry:
    def __init__(self, tasks: Iterable[PromptTaskSpec]) -> None:
        self._tasks: dict[str, PromptTaskSpec] = {}
        for task in tasks:
            if task.task_key in self._tasks:
                raise ValueError(f"Duplicate prompt task: {task.task_key}")
            self._tasks[task.task_key] = task

    def get(self, task_key: str) -> PromptTaskSpec:
        try:
            return self._tasks[task_key]
        except KeyError as exc:
            raise KeyError(f"Unknown prompt task: {task_key}") from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(self._tasks)

    def inventory(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "task_key": task.task_key,
                "provider_task": task.provider_task,
                "system_template": task.system_template,
                "user_template": task.user_template,
                "allowed_mutation": task.allowed_mutation.value,
                "timeout_ms": task.timeout_ms,
                "timeout_env": task.timeout_env,
                "response_format": task.response_format,
                "output_contract": task.output_contract,
                "parse_strategy": task.parse_strategy,
                "fallback_policy": task.fallback_policy,
                "phase": task.phase,
                "call_sites": task.call_sites,
            }
            for task in self._tasks.values()
        )


class PromptOutputGuard:
    def __init__(self, registry: PromptTaskRegistry) -> None:
        self._registry = registry

    def mutation_class(self, task_key: str) -> PromptMutationClass:
        return self._registry.get(task_key).allowed_mutation

    def assert_allows(
        self,
        task_key: str,
        mutation_class: PromptMutationClass,
    ) -> None:
        allowed = self.mutation_class(task_key)
        if allowed != mutation_class:
            raise PermissionError(
                f"Prompt task {task_key} allows {allowed.value}, "
                f"not {mutation_class.value}"
            )


serialize_prompt_task_trace = prompt_runtime_execution.serialize_prompt_task_trace
resolve_prompt_task_timeout_ms = (
    prompt_runtime_execution.resolve_prompt_task_timeout_ms
)


def _summarize_variable(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"type": "str", "chars": len(value)}
    if isinstance(value, list):
        return {"type": "list", "items": len(value)}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": len(value)}
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, int | float):
        return {"type": type(value).__name__}
    return {"type": type(value).__name__}


from app.services.prompt_context_builders import PromptContextBuilder


async def render_prompt_messages(
    session,
    context: PromptContext,
    *,
    project_settings: dict[str, Any] | None = None,
    registry: PromptTaskRegistry | None = None,
) -> list[dict[str, str]]:
    resolved_registry = registry or DEFAULT_PROMPT_TASK_REGISTRY
    task = resolved_registry.get(context.task_key)
    missing = set(task.required_sections).difference(context.section_names())
    if missing:
        raise ValueError(
            f"Prompt context for {context.task_key} missing sections: "
            f"{', '.join(sorted(missing))}"
        )
    if not task.system_template or not task.user_template:
        raise ValueError(f"Prompt task has no template pair: {context.task_key}")
    logger.debug(
        "rendering prompt task %s trace=%s",
        context.task_key,
        context.trace_metadata(task),
    )
    system_prompt = (
        await render_prompt_template(
            session,
            task.system_template,
            project_settings=project_settings,
            **context.variables,
        )
    ).strip()
    user_prompt = (
        await render_prompt_template(
            session,
            task.user_template,
            project_settings=project_settings,
            **context.variables,
        )
    ).strip()
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def prepare_prompt_task(
    session,
    context: PromptContext,
    *,
    project_settings: dict[str, Any] | None = None,
    registry: PromptTaskRegistry | None = None,
    expected_mutation: PromptMutationClass | None = None,
    fallback: Callable[[PromptTaskFailure], Any] | None = None,
    timeout_override_ms: int | None = None,
    timeout_minimum_ms: int | None = None,
    temperature_override: float | None = None,
    provider_check: Callable[[str], bool] | None = None,
) -> PromptTaskPreparationResult:
    resolved_registry = registry or DEFAULT_PROMPT_TASK_REGISTRY
    task = resolved_registry.get(context.task_key)
    if timeout_override_ms is None:
        timeout_ms = resolve_prompt_task_timeout_ms(
            task,
            minimum_ms=timeout_minimum_ms,
        )
    else:
        timeout_ms = max(0, timeout_override_ms)
        if timeout_minimum_ms is not None and 0 < timeout_ms < timeout_minimum_ms:
            timeout_ms = timeout_minimum_ms
    temperature = task.temperature if temperature_override is None else temperature_override
    trace = prompt_runtime_execution.execution_trace(
        context,
        task,
        timeout_ms=timeout_ms,
        temperature=temperature,
    )

    guard = (
        DEFAULT_PROMPT_OUTPUT_GUARD
        if registry is None
        else PromptOutputGuard(resolved_registry)
    )
    if expected_mutation is not None:
        guard.assert_allows(context.task_key, expected_mutation)

    check_provider = provider_check or has_available_provider
    if not check_provider(task.provider_task):
        return prompt_runtime_execution.preparation_failure_result(
            task,
            trace=trace,
            timeout_ms=timeout_ms,
            temperature=temperature,
            reason="provider_unavailable",
            fallback=fallback,
        )

    try:
        messages = await render_prompt_messages(
            session,
            context,
            project_settings=project_settings,
            registry=resolved_registry,
        )
    except Exception as exc:
        return prompt_runtime_execution.preparation_failure_result(
            task,
            trace=trace,
            timeout_ms=timeout_ms,
            temperature=temperature,
            reason="render_error",
            message=str(exc),
            fallback=fallback,
        )

    return PromptTaskPreparationResult(
        task_key=task.task_key,
        provider_task=task.provider_task,
        messages=messages,
        temperature=temperature,
        response_format=task.response_format,
        timeout_ms=timeout_ms,
        trace=trace,
    )


async def execute_prompt_task(
    session,
    context: PromptContext,
    *,
    project_settings: dict[str, Any] | None = None,
    registry: PromptTaskRegistry | None = None,
    expected_mutation: PromptMutationClass | None = None,
    parser: Callable[[str], Any] | None = None,
    fallback: Callable[[PromptTaskFailure], Any] | None = None,
    timeout_override_ms: int | None = None,
    timeout_minimum_ms: int | None = None,
    temperature_override: float | None = None,
    provider_check: Callable[[str], bool] | None = None,
    llm_call: Callable[..., Awaitable[Any]] | None = None,
) -> PromptTaskExecutionResult:
    prepared = await prepare_prompt_task(
        session,
        context,
        project_settings=project_settings,
        registry=registry,
        expected_mutation=expected_mutation,
        fallback=fallback,
        timeout_override_ms=timeout_override_ms,
        timeout_minimum_ms=timeout_minimum_ms,
        temperature_override=temperature_override,
        provider_check=provider_check,
    )
    if not prepared.ok:
        return PromptTaskExecutionResult(
            task_key=prepared.task_key,
            provider_task=prepared.provider_task,
            content=None,
            failure=prepared.failure,
            fallback_kind=prepared.fallback_kind,
            fallback_value=prepared.fallback_value,
            trace=prepared.trace,
        )
    prepared_task = (registry or DEFAULT_PROMPT_TASK_REGISTRY).get(prepared.task_key)
    trace = dict(prepared.trace or {})
    started_at = time.perf_counter()

    try:
        run_call = llm_call or call_llm
        call = run_call(
            prepared.provider_task,
            prepared.messages or [],
            temperature=prepared.temperature,
            response_format=prepared.response_format,
        )
        if prepared.timeout_ms and prepared.timeout_ms > 0:
            result = await asyncio.wait_for(call, timeout=prepared.timeout_ms / 1000)
        else:
            result = await call
    except (TimeoutError, asyncio.TimeoutError):
        trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)
        trace["parse_status"] = "not_run"
        return prompt_runtime_execution.failure_result(
            prepared_task,
            trace=trace,
            reason="timeout",
            fallback=fallback,
        )
    except Exception as exc:
        trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)
        trace["parse_status"] = "not_run"
        return prompt_runtime_execution.failure_result(
            prepared_task,
            trace=trace,
            reason="llm_error",
            message=str(exc),
            fallback=fallback,
        )
    trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)

    content = result.content or ""
    parsed = None
    output_parser = parser or get_prompt_output_parser(
        prepared_task.output_contract or prepared_task.parse_strategy
    )
    if output_parser is not None:
        try:
            parsed = output_parser(content)
        except Exception as exc:
            trace["parse_status"] = "error"
            return prompt_runtime_execution.failure_result(
                prepared_task,
                trace=trace,
                reason="parse_error",
                message=str(exc),
                provider=result.provider,
                model=result.model,
                fallback=fallback,
            )
        trace["parse_status"] = "ok"
    else:
        trace["parse_status"] = "not_required"

    return PromptTaskExecutionResult(
        task_key=prepared.task_key,
        provider_task=prepared.provider_task,
        content=content,
        provider=result.provider,
        model=result.model,
        parsed=parsed,
        trace=trace,
    )


async def stream_prepared_prompt_task(
    prepared: PromptTaskPreparationResult,
    *,
    registry: PromptTaskRegistry | None = None,
    fallback: Callable[[PromptTaskFailure], Any] | None = None,
    stream_call: Callable[..., Awaitable[Any]] | None = None,
) -> PromptTaskStreamResult:
    resolved_registry = registry or DEFAULT_PROMPT_TASK_REGISTRY
    task = resolved_registry.get(prepared.task_key)
    if not prepared.ok:
        return PromptTaskStreamResult(
            task_key=prepared.task_key,
            provider_task=prepared.provider_task,
            failure=prepared.failure,
            fallback_kind=prepared.fallback_kind,
            fallback_value=prepared.fallback_value,
            trace=prepared.trace,
        )

    trace = dict(prepared.trace or {})
    started_at = time.perf_counter()
    try:
        run_call = stream_call or call_llm_stream
        call = run_call(
            prepared.provider_task,
            prepared.messages or [],
            temperature=prepared.temperature,
            response_format=prepared.response_format,
        )
        if prepared.timeout_ms and prepared.timeout_ms > 0:
            result = await asyncio.wait_for(call, timeout=prepared.timeout_ms / 1000)
        else:
            result = await call
    except (TimeoutError, asyncio.TimeoutError):
        trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)
        return prompt_runtime_execution.stream_failure_result(
            task,
            trace=trace,
            reason="timeout",
            fallback=fallback,
        )
    except Exception as exc:
        trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)
        return prompt_runtime_execution.stream_failure_result(
            task,
            trace=trace,
            reason="llm_error",
            message=str(exc),
            fallback=fallback,
        )
    trace["latency_ms"] = int((time.perf_counter() - started_at) * 1000)

    return PromptTaskStreamResult(
        task_key=prepared.task_key,
        provider_task=prepared.provider_task,
        stream=result.stream,
        provider=result.provider,
        model=result.model,
        trace=trace,
    )


DEFAULT_PROMPT_TASK_REGISTRY = PromptTaskRegistry(DEFAULT_PROMPT_TASK_SPECS)

DEFAULT_PROMPT_OUTPUT_GUARD = PromptOutputGuard(DEFAULT_PROMPT_TASK_REGISTRY)


__all__ = [
    "DEFAULT_PROMPT_OUTPUT_GUARD",
    "DEFAULT_PROMPT_TASK_REGISTRY",
    "PromptTaskExecutionResult",
    "PromptTaskFailure",
    "PromptTaskPreparationResult",
    "PromptTaskStreamResult",
    "PromptContext",
    "PromptContextBuilder",
    "PromptMutationClass",
    "PromptOutputGuard",
    "PromptSection",
    "PromptTaskRegistry",
    "PromptTaskSpec",
    "execute_prompt_task",
    "prepare_prompt_task",
    "render_prompt_messages",
    "resolve_prompt_task_timeout_ms",
    "serialize_prompt_task_trace",
    "stream_prepared_prompt_task",
]
