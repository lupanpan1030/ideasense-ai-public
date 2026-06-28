from __future__ import annotations

from typing import Any

from app.services.localization import OutputLocale, output_language_label
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
)


PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


def derive_answer_summary(
    key_points: list[str],
    rolling_summary: str | None,
) -> str | None:
    if isinstance(rolling_summary, str) and rolling_summary.strip():
        return rolling_summary.strip()
    if key_points:
        return "; ".join(key_points[:2])
    return None


async def generate_answer_summary(
    session,
    *,
    question_id: str,
    key_points: list[str],
    rolling_summary: str | None,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> tuple[str | None, str | None]:
    if not key_points and not (rolling_summary and rolling_summary.strip()):
        return None, None
    context = PROMPT_CONTEXT_BUILDER.qa_digest(
        question_id=question_id,
        key_points=key_points,
        rolling_summary=rolling_summary,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.NONE,
    )
    if not result.ok:
        return derive_answer_summary(key_points, rolling_summary), None
    summary = (result.content or "").strip()
    if not summary:
        return derive_answer_summary(key_points, rolling_summary), result.model
    return summary, result.model


async def build_qa_digests_from_messages(
    session,
    rows: list[dict[str, Any]],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> list[dict[str, Any]]:
    digests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        meta = row.get("meta")
        if not isinstance(meta, dict):
            continue
        question_id = meta.get("question_id")
        if not isinstance(question_id, str) or not question_id.strip():
            continue
        if question_id in seen:
            continue
        key_points_raw = meta.get("key_points") or []
        key_points: list[str] = []
        if isinstance(key_points_raw, list):
            for item in key_points_raw:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned:
                        key_points.append(cleaned)
        rolling_summary = meta.get("rolling_summary")
        answer_summary, summary_model = await generate_answer_summary(
            session,
            question_id=question_id,
            key_points=key_points,
            rolling_summary=rolling_summary if isinstance(rolling_summary, str) else None,
            output_locale=output_locale,
            project_settings=project_settings,
        )
        if not key_points and not answer_summary:
            continue
        digests.append(
            {
                "question_id": question_id,
                "answer_summary": answer_summary,
                "key_points": key_points,
                "source_message_id": row.get("id"),
                "model": summary_model or row.get("model_name"),
            }
        )
        seen.add(question_id)
    return digests


__all__ = [
    "build_qa_digests_from_messages",
    "derive_answer_summary",
    "generate_answer_summary",
]
