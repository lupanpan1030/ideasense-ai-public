from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import text

from app.core.database_async import AdminAsyncSessionLocal
from app.services.prompt_output_parsers import AnswerGateResult
from app.services.prompt_runtime import (
    DEFAULT_PROMPT_TASK_REGISTRY,
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    resolve_prompt_task_timeout_ms,
    serialize_prompt_task_trace,
)


PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


async def run_answer_extraction(
    session,
    question_detail: dict,
    answer: str,
    *,
    project_settings: dict | None = None,
) -> tuple[dict[str, Any], bool, dict[str, Any] | None]:
    schema_paths = question_detail.get("schema_paths") or []
    if not schema_paths:
        return {}, False, None
    context = PROMPT_CONTEXT_BUILDER.extraction(schema_paths, answer)
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        timeout_minimum_ms=200,
    )
    trace = serialize_prompt_task_trace(result)
    if not result.ok:
        return {}, False, trace
    if not isinstance(result.parsed, dict):
        return {}, False, trace
    return result.parsed, True, trace


async def run_sync_answer_extraction(
    session,
    question_detail: dict,
    answer: str,
    *,
    project_settings: dict | None = None,
) -> tuple[dict[str, Any], bool, dict[str, Any] | None]:
    timeout_ms = resolve_prompt_task_timeout_ms(
        DEFAULT_PROMPT_TASK_REGISTRY.get("extract"),
        minimum_ms=200,
    )
    timeout_ms = timeout_ms or 0
    if timeout_ms <= 0:
        return {}, False, None
    try:
        return await asyncio.wait_for(
            run_answer_extraction(
                session,
                question_detail,
                answer,
                project_settings=project_settings,
            ),
            timeout=timeout_ms / 1000,
        )
    except TimeoutError:
        return {}, False, None
    except asyncio.TimeoutError:
        return {}, False, None


async def run_answer_gate(
    session,
    question_detail: dict,
    answer: str,
    context_summary: str | None = None,
    *,
    project_settings: dict | None = None,
) -> tuple[AnswerGateResult | None, str | None, dict[str, Any] | None]:
    context = PROMPT_CONTEXT_BUILDER.answer_gate(
        question_detail,
        answer,
        context_summary,
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.DECISION_ONLY,
        timeout_minimum_ms=500,
    )
    trace = serialize_prompt_task_trace(result)
    if not result.ok:
        if result.failure and result.failure.reason == "timeout":
            return None, "answer_gate_timeout", trace
        return None, None, trace
    return result.parsed, result.model, trace


async def run_answer_gate_for_context(
    gate_context: dict[str, Any],
) -> tuple[AnswerGateResult | None, str | None, dict[str, Any] | None]:
    async with AdminAsyncSessionLocal() as prompt_session:
        async with prompt_session.begin():
            await prompt_session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": gate_context.get("org_id")},
            )
            await prompt_session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "user"},
            )
            return await run_answer_gate(
                prompt_session,
                gate_context["question_detail"],
                gate_context["gate_answer_text"],
                gate_context["context_summary"],
                project_settings=gate_context.get("project_settings"),
            )


async def run_sync_answer_extraction_for_context(
    gate_context: dict[str, Any],
) -> tuple[dict[str, Any], bool, dict[str, Any] | None]:
    if AdminAsyncSessionLocal is None:
        return {}, False, None
    async with AdminAsyncSessionLocal() as extraction_session:
        async with extraction_session.begin():
            await extraction_session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": gate_context.get("org_id")},
            )
            await extraction_session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )
            return await run_sync_answer_extraction(
                extraction_session,
                gate_context["question_detail"],
                gate_context["extraction_answer_text"],
                project_settings=gate_context.get("project_settings"),
            )
