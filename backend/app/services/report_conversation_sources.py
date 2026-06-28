from __future__ import annotations

from sqlalchemy import text


async def fetch_report_last_user_message(
    session,
    *,
    org_id: str,
    project_id: str,
) -> str | None:
    result = await session.execute(
        text(
            "SELECT content "
            "FROM conversation_messages "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND role = 'user' "
            "AND is_visible "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    row = result.mappings().first()
    content = row.get("content") if row else None
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None
