from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.localization import OutputLocale, optional_output_locale
from app.services.project_question_prompts import (
    fetch_question_detail,
    run_question_rewrite,
)
from app.services.prompt_templates import fetch_active_prompt_template_ids


class ConversationCursorValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationCursor:
    before: datetime | None = None
    before_id: int | None = None

    @property
    def is_first_page(self) -> bool:
        return self.before is None and self.before_id is None


def normalize_conversation_cursor(
    *,
    before: str | None,
    before_id: int | None,
) -> ConversationCursor:
    before_value = before.strip() if before else None
    before_dt: datetime | None = None
    if before_value:
        cleaned = before_value
        if cleaned.endswith("Z"):
            cleaned = f"{cleaned[:-1]}+00:00"
        try:
            before_dt = datetime.fromisoformat(cleaned)
        except ValueError as exc:
            raise ConversationCursorValidationError(
                "Invalid 'before' timestamp."
            ) from exc
        if before_dt.tzinfo is None:
            before_dt = before_dt.replace(tzinfo=timezone.utc)

    if before_id is not None and before_dt is None:
        raise ConversationCursorValidationError(
            "before_id requires a valid before timestamp."
        )

    return ConversationCursor(before=before_dt, before_id=before_id)


async def fetch_project_conversation_list(
    session: AsyncSession,
    *,
    project_id: Any,
    limit: int,
    cursor: ConversationCursor,
) -> dict[str, Any]:
    before_filter = ""
    if cursor.before and cursor.before_id is not None:
        before_filter = "AND (cm.created_at, cm.id) < (:before, :before_id) "
    elif cursor.before:
        before_filter = "AND cm.created_at < :before "

    result = await session.execute(
        text(
            "SELECT cm.id, cm.role, cm.content, cm.created_at, cm.stage, cm.meta "
            "FROM conversation_messages cm "
            "WHERE cm.project_id = :project_id "
            "AND cm.org_id = app_org_id() "
            "AND cm.deleted_at IS NULL "
            "AND cm.is_visible "
            f"{before_filter}"
            "ORDER BY cm.created_at DESC, cm.id DESC "
            "LIMIT :limit"
        ),
        {
            "project_id": str(project_id),
            "limit": limit,
            "before": cursor.before,
            "before_id": cursor.before_id,
        },
    )
    rows: list[dict[str, Any]] = []
    for row in result.mappings().all():
        payload = dict(row)
        meta = payload.get("meta")
        if isinstance(meta, str):
            try:
                payload["meta"] = json.loads(meta)
            except json.JSONDecodeError:
                payload["meta"] = None
        rows.append(payload)
    rows.reverse()
    return {"messages": rows}


async def maybe_localize_latest_question_prompt(
    session: AsyncSession,
    *,
    project_id: Any,
    output_locale: OutputLocale,
    set_system_actor_fn: Callable[[AsyncSession], Awaitable[None]],
) -> None:
    latest_message_result = await session.execute(
        text(
            "SELECT cm.id, cm.created_at, cm.meta, p.settings, "
            "pqi.question_bank_question_id "
            "FROM conversation_messages cm "
            "JOIN project_question_instances pqi "
            "  ON pqi.id = cm.question_instance_id "
            "JOIN projects p "
            "  ON p.id = cm.project_id "
            " AND p.org_id = cm.org_id "
            " AND p.deleted_at IS NULL "
            "WHERE cm.project_id = :project_id "
            "AND cm.org_id = app_org_id() "
            "AND cm.deleted_at IS NULL "
            "AND cm.is_visible "
            "AND cm.role = 'assistant' "
            "AND cm.question_instance_id IS NOT NULL "
            "ORDER BY cm.created_at DESC, cm.id DESC "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    latest_message = latest_message_result.mappings().first()
    if not latest_message:
        return

    meta = latest_message.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    if meta.get("locale_source") == "latest_user_answer":
        return
    if optional_output_locale(meta.get("content_locale")) == output_locale:
        return

    question_bank_question_id = latest_message.get("question_bank_question_id")
    if not question_bank_question_id:
        return

    answered_result = await session.execute(
        text(
            "SELECT 1 AS found "
            "FROM conversation_messages cm "
            "WHERE cm.project_id = :project_id "
            "AND cm.org_id = app_org_id() "
            "AND cm.deleted_at IS NULL "
            "AND cm.is_visible "
            "AND cm.role = 'user' "
            "AND (cm.created_at, cm.id) > (:created_at, :message_id) "
            "LIMIT 1"
        ),
        {
            "project_id": str(project_id),
            "created_at": latest_message.get("created_at"),
            "message_id": latest_message.get("id"),
        },
    )
    if answered_result.mappings().first():
        return

    question_detail = await fetch_question_detail(session, question_bank_question_id)
    project_settings = latest_message.get("settings")
    if not isinstance(project_settings, dict):
        prompt_template_ids = await fetch_active_prompt_template_ids(session)
        project_settings = {"prompt_template_ids": prompt_template_ids}

    rewritten_prompt = await run_question_rewrite(
        session,
        question_detail,
        output_locale=output_locale,
        project_settings=project_settings,
    )
    if not rewritten_prompt:
        return

    next_meta = dict(meta)
    next_meta["content_locale"] = output_locale
    await set_system_actor_fn(session)
    await session.execute(
        text(
            "UPDATE conversation_messages "
            "SET content = :content, meta = :meta "
            "WHERE id = :message_id "
            "AND project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "content": rewritten_prompt,
            "meta": next_meta,
            "message_id": latest_message.get("id"),
            "project_id": str(project_id),
        },
    )


__all__ = [
    "ConversationCursor",
    "ConversationCursorValidationError",
    "fetch_project_conversation_list",
    "maybe_localize_latest_question_prompt",
    "normalize_conversation_cursor",
]
