import logging
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.chat_stream.events import build_streamed_question_message_meta

logger = logging.getLogger("ideasense.chat")


async def persist_fallback_question_message(
    session,
    context: dict[str, Any],
    *,
    fallback_source: str,
) -> int | None:
    meta = build_streamed_question_message_meta(context, source=fallback_source)
    result = await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, role, stage, variant, "
            "question_instance_id, content, meta, request_id"
            ") VALUES ("
            "app_org_id(), :project_id, 'assistant', :stage, "
            ":variant, :question_instance_id, :content, :meta, :request_id"
            ") RETURNING id"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": context["project_id"],
            "stage": context.get("stage"),
            "variant": context.get("variant"),
            "question_instance_id": context["question_instance_id"],
            "content": context.get("fallback_content") or "",
            "meta": meta,
            "request_id": context.get("request_id"),
        },
    )
    row = result.mappings().first()
    message_id = row.get("id") if row else None
    if message_id is None:
        return None
    context["assistant_message_id"] = message_id
    return int(message_id)


async def update_streamed_question_message(
    session,
    context: dict[str, Any],
    *,
    content: str,
    source: str,
    compose_model: str | None = None,
    compose_provider: str | None = None,
    streamed: bool = False,
) -> bool:
    assistant_message_id = context.get("assistant_message_id")
    if not assistant_message_id:
        return False

    meta = build_streamed_question_message_meta(
        context,
        source=source,
        compose_model=compose_model,
        compose_provider=compose_provider,
        streamed=streamed,
    )

    message_result = await session.execute(
        text(
            "UPDATE conversation_messages "
            "SET content = :content, meta = :meta, "
            "request_id = COALESCE(request_id, :request_id) "
            "WHERE id = :message_id "
            "AND project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "message_id": assistant_message_id,
            "project_id": context["project_id"],
            "content": content,
            "meta": meta,
            "request_id": context.get("request_id"),
        },
    )
    if getattr(message_result, "rowcount", None) == 0:
        logger.warning(
            "streamed question message update skipped; message_id=%s project_id=%s",
            assistant_message_id,
            context.get("project_id"),
        )
        return False

    answer_evaluation_request_id = context.get("answer_evaluation_request_id")
    if answer_evaluation_request_id:
        await session.execute(
            text(
                "UPDATE answer_evaluations "
                "SET feedback_markdown = :content "
                "WHERE request_id = :request_id "
                "AND project_id = :project_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL"
            ),
            {
                "content": content,
                "request_id": answer_evaluation_request_id,
                "project_id": context["project_id"],
            },
        )
    return True
