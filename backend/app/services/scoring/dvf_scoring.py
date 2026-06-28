"""DVF scoring service powered by the LLM."""

from __future__ import annotations

import os
from typing import Any, Mapping

from app.services.localization import OutputLocale, output_language_label
from app.services.prompt_runtime import (
    DEFAULT_PROMPT_TASK_REGISTRY,
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    render_prompt_messages,
    serialize_prompt_task_trace,
)


PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


async def _build_prompt(
    session,
    payload: Mapping[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> list[dict[str, str]]:
    context = PROMPT_CONTEXT_BUILDER.dvf_scoring(
        payload,
        output_language=output_language_label(output_locale),
    )
    return await render_prompt_messages(
        session,
        context,
        project_settings=project_settings,
    )


async def generate_dvf_scoring(
    session,
    report_input: Mapping[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
    trace_sink: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    task = DEFAULT_PROMPT_TASK_REGISTRY.get("dvf_scoring")
    context = PROMPT_CONTEXT_BUILDER.dvf_scoring(
        report_input,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.REPORT_ARTIFACT,
        temperature_override=_env_float("IDEASENSE_DVF_TEMPERATURE", task.temperature),
    )
    if trace_sink is not None:
        trace_sink["dvf_scoring"] = serialize_prompt_task_trace(result)
    if not result.ok:
        return None, result.model
    return result.parsed, result.model


__all__ = ["generate_dvf_scoring"]
