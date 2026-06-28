import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PlatformSettingsValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def normalize_setting_key(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise PlatformSettingsValidationError("Setting key cannot be empty")
    return cleaned


def row_to_platform_setting_entry_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": row.get("key") or "",
        "value": row.get("value"),
        "updated_by": row.get("updated_by"),
        "updated_by_email": row.get("email"),
        "updated_by_name": row.get("display_name"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def build_platform_settings_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "settings": {row.get("key"): row.get("value") for row in rows},
        "entries": [row_to_platform_setting_entry_payload(row) for row in rows],
    }


async def fetch_platform_settings_payload(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(
        text(
            "SELECT ps.key, ps.value, ps.updated_by, ps.created_at, ps.updated_at, "
            "u.email, u.display_name "
            "FROM platform_settings ps "
            "LEFT JOIN users u ON u.id = ps.updated_by AND u.deleted_at IS NULL "
            "ORDER BY ps.key"
        )
    )
    return build_platform_settings_payload(result.mappings().all())


async def update_platform_settings_payload(
    session: AsyncSession,
    *,
    settings_payload: dict[str, Any] | None,
    remove_payload: list[Any] | None,
) -> dict[str, Any]:
    settings_payload = settings_payload or {}
    remove_payload = remove_payload or []

    if not settings_payload and not remove_payload:
        raise PlatformSettingsValidationError("settings or remove is required")

    normalized_settings: dict[str, Any] = {}
    for key, value in settings_payload.items():
        normalized_key = normalize_setting_key(key)
        normalized_settings[normalized_key] = value

    normalized_remove = []
    for key in remove_payload:
        if not isinstance(key, str):
            raise PlatformSettingsValidationError("remove must contain string keys")
        normalized_remove.append(normalize_setting_key(key))

    remove_set = set(normalized_remove)
    duplicate_keys = [key for key in normalized_settings if key in remove_set]
    if duplicate_keys:
        raise PlatformSettingsValidationError(
            f"remove overlaps settings keys: {', '.join(sorted(duplicate_keys))}"
        )

    if normalized_settings:
        values = [
            {
                "key": key,
                "value": json.dumps(value),
            }
            for key, value in normalized_settings.items()
        ]
        await session.execute(
            text(
                "INSERT INTO platform_settings (key, value, updated_by) "
                "VALUES (:key, CAST(:value AS jsonb), app_user_id()) "
                "ON CONFLICT (key) DO UPDATE "
                "SET value = EXCLUDED.value, "
                "updated_by = app_user_id(), "
                "updated_at = now()"
            ),
            values,
        )

    if normalized_remove:
        await session.execute(
            text(
                "DELETE FROM platform_settings "
                "WHERE key = ANY(:keys)"
            ),
            {"keys": normalized_remove},
        )

    return await fetch_platform_settings_payload(session)
