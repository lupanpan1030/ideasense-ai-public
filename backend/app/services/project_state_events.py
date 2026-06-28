from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


async def record_project_state_event(
    session: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    event_type: str,
    patch_json: dict[str, Any] | None = None,
    actor_type: str = "system",
    actor_user_id: str | None = None,
    question_instance_id: str | None = None,
    model_name: str | None = None,
    prompt_template_id: str | None = None,
    prev_state_version: int | None = None,
    next_state_version: int | None = None,
    request_id: str | None = None,
) -> None:
    await session.execute(
        text(
            "INSERT INTO project_state_events ("
            "org_id, project_id, question_instance_id, event_type, patch_json, "
            "actor_type, actor_user_id, model_name, prompt_template_id, "
            "prev_state_version, next_state_version, request_id"
            ") VALUES ("
            ":org_id, :project_id, :question_instance_id, :event_type, :patch_json, "
            ":actor_type, :actor_user_id, :model_name, :prompt_template_id, "
            ":prev_state_version, :next_state_version, :request_id"
            ")"
        ).bindparams(bindparam("patch_json", type_=JSONB)),
        {
            "org_id": org_id,
            "project_id": project_id,
            "question_instance_id": question_instance_id,
            "event_type": event_type,
            "patch_json": patch_json,
            "actor_type": actor_type,
            "actor_user_id": actor_user_id,
            "model_name": model_name,
            "prompt_template_id": prompt_template_id,
            "prev_state_version": prev_state_version,
            "next_state_version": next_state_version,
            "request_id": request_id,
        },
    )
