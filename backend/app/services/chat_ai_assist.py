import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.llm_router import call_llm_stream, has_available_provider
from app.services.localization import OutputLocale, output_language_label
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    prepare_prompt_task,
    stream_prepared_prompt_task,
)

AI_DRAFT_PREFIX = "[AI Draft]"
AI_ASSIST_REQUEST_PATTERNS = [
    re.compile(r"\bai (?:draft|assist|help|fill)\b", re.IGNORECASE),
    re.compile(r"\b(auto[-\s]?fill|draft)(?: this| for me)?\b", re.IGNORECASE),
    re.compile(r"^(?:draft|help me draft|auto fill|autofill|assume)$", re.IGNORECASE),
    re.compile("帮我补全"),
    re.compile("帮忙补全"),
    re.compile("生成草稿"),
    re.compile("给个草稿"),
    re.compile("ai补全"),
    re.compile("自动补全"),
]
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


def has_substantive_answer(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    non_space = re.sub(r"\s+", "", cleaned)
    if len(non_space) >= 40:
        return True
    if len(re.findall(r"[A-Za-z0-9]+", cleaned)) >= 8:
        return True
    if len(re.findall(r"[\u4e00-\u9fff]", cleaned)) >= 20:
        return True
    if len([line for line in cleaned.splitlines() if line.strip()]) >= 2:
        return True
    if re.search(r"(?m)^(?:[-*]|\d+[\).、]|[#＃]?\d+[\).、])\s+\S", cleaned):
        return True
    return False


def is_ai_draft_tagged(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    return lowered.startswith(AI_DRAFT_PREFIX.lower())


def strip_ai_draft_prefix(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    lowered = cleaned.lower()
    prefix = AI_DRAFT_PREFIX.lower()
    if lowered.startswith(prefix):
        return cleaned[len(AI_DRAFT_PREFIX) :].lstrip(" :\n\t")
    return cleaned


def is_ai_assist_request(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if is_ai_draft_tagged(cleaned):
        return False
    return any(pattern.search(cleaned) for pattern in AI_ASSIST_REQUEST_PATTERNS)


def build_answer_text_from_history(
    previous_answer_parts: list[str],
    message: str,
) -> tuple[bool, str, str]:
    ai_assisted = is_ai_draft_tagged(message)
    cleaned_message = strip_ai_draft_prefix(message) if ai_assisted else message
    answer_parts = list(previous_answer_parts)
    if cleaned_message.strip():
        answer_parts.append(cleaned_message.strip())
    answer_text = "\n\n".join(answer_parts).strip() or cleaned_message
    return ai_assisted, cleaned_message, answer_text


def requires_single_sentence(question_detail: dict) -> bool:
    for key in ("validation_rule", "prompt", "standard_question"):
        value = question_detail.get(key)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if "one sentence" in lowered or "single sentence" in lowered:
            return True
    return False


def build_ai_assist_context(
    question_detail: dict,
    context_summary: str | None,
    output_locale: OutputLocale,
) -> Any:
    sentence_hint = (
        "Answer in exactly one sentence."
        if requires_single_sentence(question_detail)
        else "Answer concisely and follow the prompt structure."
    )
    return PROMPT_CONTEXT_BUILDER.ai_assist(
        question_detail,
        context_summary=context_summary,
        sentence_hint=sentence_hint,
        output_language=output_language_label(output_locale),
    )


async def run_ai_assist_draft(
    session,
    question_detail: dict,
    context_summary: str | None,
    latest_answer: str,
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> tuple[str | None, str | None, OutputLocale]:
    context = build_ai_assist_context(
        question_detail,
        context_summary,
        output_locale,
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
    )
    if not result.ok:
        return None, None, output_locale
    draft = (result.content or "").strip().strip('"').strip("'").strip()
    if not draft:
        return None, result.model, output_locale
    return draft, result.model, output_locale


async def run_ai_assist_draft_stream(
    session,
    question_detail: dict,
    context_summary: str | None,
    latest_answer: str,
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> tuple[Any | None, str | None, OutputLocale, str | None]:
    context = build_ai_assist_context(
        question_detail,
        context_summary,
        output_locale,
    )
    prepared = await prepare_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
        provider_check=has_available_provider,
    )
    stream_result = await stream_prepared_prompt_task(
        prepared,
        stream_call=call_llm_stream,
    )
    if stream_result.ok:
        return stream_result, stream_result.model, output_locale, None
    draft, model, fallback_locale = await run_ai_assist_draft(
        session,
        question_detail,
        context_summary,
        latest_answer,
        output_locale=output_locale,
        project_settings=project_settings,
    )
    if draft:
        return None, model, fallback_locale, draft
    return None, None, output_locale, None


def ai_draft_message_parts(output_locale: OutputLocale) -> tuple[str, str, str]:
    if output_locale == "zh":
        return (
            "下面是 AI 帮你起草的版本，你可以修改后再发送。",
            f"{AI_DRAFT_PREFIX} ",
            f"保留 {AI_DRAFT_PREFIX} 前缀，表示这是 AI 辅助草稿。",
        )
    return (
        "Here is an AI draft you can edit. Send it back to use it.",
        f"{AI_DRAFT_PREFIX} ",
        f"Keep the {AI_DRAFT_PREFIX} prefix to mark this as AI-assisted.",
    )


def format_ai_draft_message(
    draft: str,
    *,
    output_locale: OutputLocale = "en",
) -> str:
    intro, prefix, guidance = ai_draft_message_parts(output_locale)
    return f"{intro}\n\n{prefix}{draft}\n\n{guidance}"


def ai_draft_unavailable_message(output_locale: OutputLocale) -> str:
    if output_locale == "zh":
        return "现在暂时无法生成 AI 草稿。请先用你的假设和验证计划回答。"
    return (
        "AI draft is unavailable right now. "
        "Please answer with assumptions and a validation plan."
    )


async def persist_ai_draft_message(
    session,
    *,
    project_id: str,
    org_id: str,
    stage: str | None,
    variant: str | None,
    question_instance_id: UUID,
    assistant_content: str,
    draft: str | None,
    draft_model: str | None,
    content_locale: OutputLocale,
) -> None:
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )
    if draft:
        state_result = await session.execute(
            text(
                "SELECT state_meta "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "project_id": project_id,
                "org_id": org_id,
            },
        )
        state_row = state_result.mappings().first()
        state_meta = state_row.get("state_meta") if state_row else {}
        if not isinstance(state_meta, dict):
            state_meta = {}
        ai_drafts = state_meta.get("ai_drafts")
        if not isinstance(ai_drafts, dict):
            ai_drafts = {}
        ai_drafts[str(question_instance_id)] = {
            "draft": draft,
            "model": draft_model,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        state_meta["ai_drafts"] = ai_drafts
        await session.execute(
            text(
                "UPDATE project_states "
                "SET state_meta = :state_meta "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ).bindparams(bindparam("state_meta", type_=JSONB)),
            {
                "project_id": project_id,
                "org_id": org_id,
                "state_meta": state_meta,
            },
        )

    await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, role, stage, variant, "
            "question_instance_id, content, meta"
            ") VALUES ("
            "app_org_id(), :project_id, 'assistant', :stage, "
            ":variant, :question_instance_id, :content, :meta"
            ")"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": project_id,
            "stage": stage,
            "variant": variant,
            "question_instance_id": question_instance_id,
            "content": assistant_content,
            "meta": {
                "schema_version": "v1",
                "ai_draft": True,
                "draft_model": draft_model,
                "content_locale": content_locale,
                "source": "ai_assist_draft",
            },
        },
    )


async def mark_ai_draft_requested(
    session,
    *,
    project_id: str,
    question_instance_id: UUID,
    requested_at: datetime | None = None,
) -> None:
    timestamp = requested_at or datetime.now(timezone.utc)
    await session.execute(
        text(
            "UPDATE project_question_instances "
            "SET meta = COALESCE(meta, '{}'::jsonb) || CAST(:meta AS jsonb), "
            "updated_at = now() "
            "WHERE id = :question_instance_id "
            "AND project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ),
        {
            "question_instance_id": question_instance_id,
            "project_id": project_id,
            "meta": json.dumps(
                {
                    "ai_draft_requested": True,
                    "ai_draft_requested_at": timestamp.isoformat(),
                }
            ),
        },
    )
