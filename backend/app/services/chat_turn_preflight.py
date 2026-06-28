from collections.abc import Mapping
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.chat_ai_assist import build_answer_text_from_history
from app.services.chat_turn_context import (
    build_gate_context_summary,
    select_extraction_answer,
    select_gate_answer,
)
from app.services.localization import OutputLocale


async def insert_chat_user_message(
    session,
    *,
    project_id: Any,
    actor_user_id: str,
    stage: str | None,
    variant: str | None,
    question_instance_id: Any,
    content: str,
    message_meta: dict[str, Any] | None,
    client_message_id: str | None,
    request_id: str,
) -> Any | None:
    result = await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, author_user_id, role, "
            "stage, variant, question_instance_id, content, meta, "
            "client_message_id, request_id"
            ") VALUES ("
            "app_org_id(), :project_id, :author_user_id, 'user', "
            ":stage, :variant, :question_instance_id, :content, :meta, "
            ":client_message_id, :request_id"
            ") RETURNING id"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": project_id,
            "author_user_id": actor_user_id,
            "stage": stage,
            "variant": variant,
            "question_instance_id": question_instance_id,
            "content": content,
            "meta": message_meta,
            "client_message_id": client_message_id,
            "request_id": request_id,
        },
    )
    row = result.mappings().first()
    if not row:
        return None
    return row.get("id")


def build_chat_gate_context(
    *,
    project_row: Mapping[str, Any],
    org_id: str,
    current_question_id: Any,
    current_question_instance_id: Any,
    user_message_id: Any,
    request_id: str,
    client_message_id: str | None,
    question_detail: dict[str, Any],
    state_json: dict[str, Any] | None,
    state_meta: dict[str, Any] | None,
    previous_answer_parts: list[str],
    latest_message: str,
    message_meta: dict[str, Any] | None,
    output_locale: OutputLocale,
) -> dict[str, Any]:
    ai_assisted, cleaned_message, answer_text = build_answer_text_from_history(
        previous_answer_parts,
        latest_message,
    )
    gate_answer_text = select_gate_answer(
        question_detail,
        cleaned_message,
        answer_text,
    )
    extraction_answer_text = select_extraction_answer(
        question_detail,
        cleaned_message,
        answer_text,
    )
    context_summary = build_gate_context_summary(
        state_json,
        project_row.get("runtime_stage"),
        question_detail,
        cleaned_message,
    )
    router_state_json = None
    if (
        project_row.get("runtime_stage") == "tech"
        and project_row.get("runtime_variant") == "router"
    ):
        router_state_json = state_json

    return {
        "project_id": str(project_row.get("project_id")),
        "org_id": str(org_id),
        "project_settings": project_row.get("settings") or {},
        "current_stage": project_row.get("current_stage"),
        "runtime_stage": project_row.get("runtime_stage"),
        "runtime_variant": project_row.get("runtime_variant"),
        "runtime_version": int(project_row.get("runtime_version") or 0),
        "current_question_id": current_question_id,
        "current_question_instance_id": current_question_instance_id,
        "next_question_id": project_row.get("next_question_bank_question_id"),
        "runtime_missing_paths": project_row.get("missing_paths"),
        "bank_version_id": project_row.get("question_bank_version_id"),
        "stage_status": project_row.get("stage_status"),
        "user_message_id": user_message_id,
        "request_id": request_id,
        "client_message_id": client_message_id,
        "question_detail": question_detail,
        "message_meta": message_meta,
        "router_state_json": router_state_json,
        "state_json": state_json,
        "state_meta": state_meta,
        "answer_text": answer_text,
        "gate_answer_text": gate_answer_text,
        "extraction_answer_text": extraction_answer_text,
        "context_summary": context_summary,
        "latest_answer": cleaned_message,
        "ai_assisted": ai_assisted,
        "output_locale": output_locale,
    }
