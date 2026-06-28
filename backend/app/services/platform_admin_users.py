from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PlatformAdminUsersValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PlatformAdminUserNotFoundError(LookupError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def row_to_platform_admin_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": row.get("user_id"),
        "email": row.get("email"),
        "display_name": row.get("display_name"),
        "role": row.get("role") or "admin",
        "status": row.get("status") or "active",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


async def list_platform_admin_payloads(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT pa.user_id, pa.role, pa.status, pa.created_at, pa.updated_at, "
            "u.email, u.display_name "
            "FROM platform_admins pa "
            "JOIN users u ON u.id = pa.user_id AND u.deleted_at IS NULL "
            "WHERE pa.deleted_at IS NULL "
            "ORDER BY pa.created_at DESC"
        )
    )
    return [row_to_platform_admin_payload(row) for row in result.mappings().all()]


async def upsert_platform_admin_payload(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    email: str | None,
    role: str,
    status: str,
) -> dict[str, Any]:
    if not user_id and not email:
        raise PlatformAdminUsersValidationError("user_id or email is required")

    resolved_user_id = user_id
    if not resolved_user_id:
        result = await session.execute(
            text(
                "SELECT id "
                "FROM users "
                "WHERE email = :email "
                "AND deleted_at IS NULL"
            ),
            {"email": email},
        )
        row = result.mappings().first()
        if not row:
            raise PlatformAdminUserNotFoundError("User not found")
        resolved_user_id = row.get("id")

    if role not in {"admin", "superadmin"}:
        raise PlatformAdminUsersValidationError("Invalid role")
    if status not in {"active", "disabled"}:
        raise PlatformAdminUsersValidationError("Invalid status")

    membership_check = await session.execute(
        text(
            "SELECT 1 "
            "FROM organization_memberships "
            "WHERE user_id = :user_id "
            "AND org_role IN ('owner', 'admin') "
            "AND status = 'active' "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"user_id": str(resolved_user_id)},
    )
    if not membership_check.first():
        raise PlatformAdminUsersValidationError(
            "Platform admins must have an active owner/admin membership"
        )

    await session.execute(
        text(
            "INSERT INTO platform_admins (user_id, role, status, created_by) "
            "VALUES (:user_id, :role, :status, app_user_id()) "
            "ON CONFLICT (user_id) WHERE deleted_at IS NULL "
            "DO UPDATE SET role = EXCLUDED.role, status = EXCLUDED.status, "
            "updated_at = now()"
        ),
        {"user_id": str(resolved_user_id), "role": role, "status": status},
    )

    result = await session.execute(
        text(
            "SELECT pa.user_id, pa.role, pa.status, pa.created_at, pa.updated_at, "
            "u.email, u.display_name "
            "FROM platform_admins pa "
            "JOIN users u ON u.id = pa.user_id AND u.deleted_at IS NULL "
            "WHERE pa.user_id = :user_id AND pa.deleted_at IS NULL"
        ),
        {"user_id": str(resolved_user_id)},
    )
    row = result.mappings().first()
    if not row:
        raise PlatformAdminUserNotFoundError("Platform admin not found")
    return row_to_platform_admin_payload(row)
