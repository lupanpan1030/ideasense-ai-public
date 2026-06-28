from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ActorContext, get_actor_context, get_admin_db_session, get_db_session

router = APIRouter(tags=["user"])


class UserSettingsResponse(BaseModel):
    email_notifications: bool
    weekly_summary: bool
    time_zone: str | None


class UserSettingsUpdate(BaseModel):
    email_notifications: bool | None = None
    weekly_summary: bool | None = None
    time_zone: str | None = None


class UserProfileResponse(BaseModel):
    id: str
    email: str | None
    display_name: str | None


class UserProfileUpdate(BaseModel):
    display_name: str | None = None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _fields_set(payload: BaseModel) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if isinstance(model_fields_set, set):
        return model_fields_set
    return getattr(payload, "__fields_set__", set())


async def _ensure_user_settings(session: AsyncSession) -> None:
    await session.execute(
        text(
            "INSERT INTO user_settings (user_id) "
            "VALUES (app_user_id()) "
            "ON CONFLICT (user_id) DO NOTHING"
        )
    )


@router.get("/user-settings", response_model=UserSettingsResponse)
async def get_user_settings(
    session: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    await _ensure_user_settings(session)
    result = await session.execute(
        text(
            "SELECT email_notifications, weekly_summary, time_zone "
            "FROM user_settings "
            "WHERE user_id = app_user_id()"
        )
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found",
        )
    return UserSettingsResponse(
        email_notifications=bool(row.get("email_notifications")),
        weekly_summary=bool(row.get("weekly_summary")),
        time_zone=row.get("time_zone"),
    )


@router.patch("/user-settings", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    fields_set = _fields_set(payload)
    if not fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No settings provided",
        )

    updates: list[str] = []
    params: dict[str, object] = {}

    if "email_notifications" in fields_set:
        if payload.email_notifications is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="email_notifications is required",
            )
        updates.append("email_notifications = :email_notifications")
        params["email_notifications"] = payload.email_notifications

    if "weekly_summary" in fields_set:
        if payload.weekly_summary is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="weekly_summary is required",
            )
        updates.append("weekly_summary = :weekly_summary")
        params["weekly_summary"] = payload.weekly_summary

    if "time_zone" in fields_set:
        updates.append("time_zone = :time_zone")
        params["time_zone"] = _normalize_optional_string(payload.time_zone)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid settings provided",
        )

    await _ensure_user_settings(session)
    result = await session.execute(
        text(
            "UPDATE user_settings "
            "SET " + ", ".join(updates) + " "
            "WHERE user_id = app_user_id() "
            "RETURNING email_notifications, weekly_summary, time_zone"
        ),
        params,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found",
        )
    return UserSettingsResponse(
        email_notifications=bool(row.get("email_notifications")),
        weekly_summary=bool(row.get("weekly_summary")),
        time_zone=row.get("time_zone"),
    )


@router.patch("/users/me", response_model=UserProfileResponse)
async def update_user_profile(
    payload: UserProfileUpdate,
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_admin_db_session),
) -> UserProfileResponse:
    fields_set = _fields_set(payload)
    if not fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No profile fields provided",
        )

    if "display_name" not in fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="display_name is required",
        )

    display_name = _normalize_optional_string(payload.display_name)

    result = await session.execute(
        text(
            "UPDATE users "
            "SET display_name = :display_name "
            "WHERE id = :user_id AND deleted_at IS NULL "
            "RETURNING id, email, display_name"
        ),
        {"display_name": display_name, "user_id": actor.user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or inactive",
        )

    await session.execute(
        text(
            "INSERT INTO users_public_profiles "
            "(user_id, display_name, created_at, updated_at, deleted_at) "
            "VALUES (:user_id, :display_name, now(), now(), NULL) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "display_name = EXCLUDED.display_name, "
            "updated_at = now(), "
            "deleted_at = NULL"
        ),
        {"user_id": actor.user_id, "display_name": display_name},
    )

    return UserProfileResponse(
        id=str(row.get("id")),
        email=row.get("email"),
        display_name=row.get("display_name"),
    )
