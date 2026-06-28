from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session

router = APIRouter()


@router.get("/admin/health")
async def admin_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    result = await session.execute(
        text(
            "SELECT "
            "current_setting('app.user_id', true) AS app_user_id, "
            "current_setting('app.org_id', true) AS app_org_id, "
            "current_setting('app.actor_type', true) AS app_actor_type"
        )
    )
    row = result.mappings().one()
    return {
        "status": "ok",
        "app": {
            "user_id": row.get("app_user_id"),
            "org_id": row.get("app_org_id"),
            "actor_type": row.get("app_actor_type"),
        },
    }
