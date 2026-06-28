from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.localization import OutputLocale, output_language_label
from app.services.chat_followup_compose import sanitize_rewritten_prompt
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    render_prompt_messages,
)


PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


class QuestionPromptMissingError(RuntimeError):
    pass


async def fetch_question_detail(
    session: AsyncSession,
    question_id: Any,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            "SELECT id, question_id, prompt, bank_version_id, stage, variant, "
            "order_index, type_raw, validation_rule, instruction, "
            "standard_question, schema_paths, expected_key_points, prompt_meta "
            "FROM question_bank_questions "
            "WHERE id = :question_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"question_id": str(question_id)},
    )
    row = result.mappings().first()
    if not row or not row.get("prompt"):
        raise QuestionPromptMissingError("Question prompt not found.")
    return dict(row)


async def build_question_rewrite_prompt(
    session: AsyncSession,
    question_detail: dict[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    context = PROMPT_CONTEXT_BUILDER.question_rewrite(
        "question_rewrite_basic",
        question_detail,
        output_language=output_language_label(output_locale),
    )
    return await render_prompt_messages(
        session,
        context,
        project_settings=project_settings,
    )


async def run_question_rewrite(
    session: AsyncSession,
    question_detail: dict[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict[str, Any] | None = None,
) -> str | None:
    prompt = question_detail.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    context = PROMPT_CONTEXT_BUILDER.question_rewrite(
        "question_rewrite_basic",
        question_detail,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
    )
    if not result.ok or not result.parsed:
        return None
    rewritten = getattr(result.parsed, "prompt", None)
    if isinstance(rewritten, str):
        cleaned = rewritten.strip()
        if cleaned:
            return cleaned
    return None


async def run_chat_question_rewrite(
    session: AsyncSession,
    question_detail: dict[str, Any],
    latest_answer: str | None,
    *,
    output_locale: OutputLocale,
    project_settings: dict[str, Any] | None = None,
) -> str | None:
    prompt = question_detail.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    context = PROMPT_CONTEXT_BUILDER.question_rewrite(
        "question_rewrite_chat",
        question_detail,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
    )
    if not result.ok or not result.parsed:
        return None
    rewritten = result.parsed.prompt.strip()
    return sanitize_rewritten_prompt(rewritten)


__all__ = [
    "QuestionPromptMissingError",
    "build_question_rewrite_prompt",
    "fetch_question_detail",
    "run_chat_question_rewrite",
    "run_question_rewrite",
]
