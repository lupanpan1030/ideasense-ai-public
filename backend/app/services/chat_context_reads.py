from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.database_async import AdminAsyncSessionLocal
from app.services.chat_question_planning import apply_group_override, fetch_group_meta
from app.services.chat_question_runtime import fetch_chat_question_detail
from app.services.chat_stream.latency import latency_span


async def set_chat_session_context(
    session,
    *,
    org_id: str,
    actor_type: str,
    user_id: str | None = None,
) -> None:
    if user_id is not None:
        await session.execute(
            text(
                "SELECT "
                "set_config('app.user_id', :user_id, true), "
                "set_config('app.org_id', :org_id, true), "
                "set_config('app.actor_type', :actor_type, true)"
            ),
            {
                "user_id": user_id,
                "org_id": org_id,
                "actor_type": actor_type,
            },
        )
        return
    await session.execute(
        text(
            "SELECT "
            "set_config('app.org_id', :org_id, true), "
            "set_config('app.actor_type', :actor_type, true)"
        ),
        {
            "org_id": org_id,
            "actor_type": actor_type,
        },
    )


async def fetch_chat_state_context(
    *,
    org_id: str,
    user_id: str,
    project_id: str,
    latency_spans: dict[str, float] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    with latency_span(latency_spans, "preflight.state_context"):
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                await set_chat_session_context(
                    session,
                    org_id=org_id,
                    actor_type="user",
                    user_id=user_id,
                )
                state_result = await session.execute(
                    text(
                        "SELECT state_json, state_meta "
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
                if not state_row:
                    return None, None
                return state_row.get("state_json"), state_row.get("state_meta")


async def fetch_chat_answer_history(
    *,
    org_id: str,
    user_id: str,
    project_id: str,
    question_instance_id,
    latency_spans: dict[str, float] | None = None,
) -> list[str]:
    with latency_span(latency_spans, "preflight.answer_history"):
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                await set_chat_session_context(
                    session,
                    org_id=org_id,
                    actor_type="user",
                    user_id=user_id,
                )
                answer_result = await session.execute(
                    text(
                        "SELECT content "
                        "FROM conversation_messages "
                        "WHERE project_id = :project_id "
                        "AND question_instance_id = :question_instance_id "
                        "AND role = 'user' "
                        "AND deleted_at IS NULL "
                        "ORDER BY id ASC"
                    ),
                    {
                        "project_id": project_id,
                        "question_instance_id": question_instance_id,
                    },
                )
                answer_parts: list[str] = []
                for answer_row in answer_result.mappings().all():
                    content = answer_row.get("content")
                    if isinstance(content, str):
                        cleaned = content.strip()
                        if cleaned:
                            answer_parts.append(cleaned)
                return answer_parts


async def fetch_chat_question_detail_context(
    *,
    org_id: str,
    user_id: str,
    project_id: str,
    question_id: UUID,
    question_instance_id: UUID,
    latency_spans: dict[str, float] | None = None,
) -> dict:
    with latency_span(latency_spans, "preflight.question_detail"):
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                await set_chat_session_context(
                    session,
                    org_id=org_id,
                    actor_type="user",
                    user_id=user_id,
                )
                question_detail = await fetch_chat_question_detail(session, question_id)
                group_meta = await fetch_group_meta(
                    session,
                    project_id=project_id,
                    question_instance_id=question_instance_id,
                )
                if group_meta:
                    question_detail = apply_group_override(
                        question_detail,
                        group_meta,
                    )
                return question_detail


async def fetch_context_meta(
    session,
    project_id: str,
    org_id: str,
) -> tuple[int | None, str | None]:
    result = await session.execute(
        text(
            "SELECT state_version, updated_at "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    row = result.mappings().first()
    if not row:
        return None, None
    version = row.get("state_version")
    updated_at = row.get("updated_at")
    updated_at_value = updated_at.isoformat() if updated_at else None
    return version, updated_at_value
