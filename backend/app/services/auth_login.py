from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limits import RateLimitSettings, increment_rate_limit


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


class AuthLoginError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthLoginInvalidCredentialsError(AuthLoginError):
    pass


class AuthLoginNoActiveMembershipError(AuthLoginError):
    pass


async def fetch_user_for_login(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT u.id, u.email, u.display_name "
            "FROM user_identities ui "
            "JOIN users u ON u.id = ui.user_id "
            "WHERE ui.provider = 'local' "
            "AND ui.deleted_at IS NULL "
            "AND u.deleted_at IS NULL "
            "AND ui.status = 'active' "
            "AND u.is_active IS TRUE "
            "AND ui.email = :email "
            "AND ui.password_hash = crypt(:password, ui.password_hash) "
            "LIMIT 1"
        ),
        {"email": email, "password": password},
    )
    return result.mappings().first()


async def fetch_user_for_dev_login(
    session: AsyncSession,
    *,
    email: str,
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT u.id, u.email, u.display_name "
            "FROM user_identities ui "
            "JOIN users u ON u.id = ui.user_id "
            "WHERE ui.provider = 'local' "
            "AND ui.deleted_at IS NULL "
            "AND u.deleted_at IS NULL "
            "AND ui.status = 'active' "
            "AND u.is_active IS TRUE "
            "AND ui.email = :email "
            "LIMIT 1"
        ),
        {"email": email},
    )
    return result.mappings().first()


async def require_active_membership(
    session: AsyncSession, *, user_id: str
) -> str:
    result = await session.execute(
        text(
            "SELECT org_id "
            "FROM organization_memberships "
            "WHERE user_id = :user_id "
            "AND status = 'active' "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    org_id = row.get("org_id") if row else None
    if not org_id:
        raise AuthLoginNoActiveMembershipError("No active org membership")
    return str(org_id)


async def record_login_failure(
    session: AsyncSession,
    *,
    client_ip: str | None,
    email: str,
    fail_limit: RateLimitSettings,
) -> None:
    if client_ip:
        await increment_rate_limit(
            session,
            scope="login_fail:ip",
            key=client_ip,
            window_seconds=fail_limit.window_seconds,
        )
    await increment_rate_limit(
        session,
        scope="login_fail:email",
        key=email,
        window_seconds=fail_limit.window_seconds,
    )


def _authenticated_user(row: dict) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(row.get("id")),
        email=row.get("email"),
    )


async def login_local_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    client_ip: str | None,
    fail_limit: RateLimitSettings,
) -> AuthenticatedUser:
    user = await fetch_user_for_login(
        session, email=email, password=password
    )
    if not user:
        await record_login_failure(
            session,
            client_ip=client_ip,
            email=email,
            fail_limit=fail_limit,
        )
        raise AuthLoginInvalidCredentialsError("Invalid credentials")

    authenticated = _authenticated_user(user)
    await require_active_membership(session, user_id=authenticated.user_id)
    return authenticated


async def dev_login_local_user(
    session: AsyncSession,
    *,
    email: str,
) -> AuthenticatedUser:
    user = await fetch_user_for_dev_login(session, email=email)
    if not user:
        raise AuthLoginInvalidCredentialsError("Invalid credentials")

    authenticated = _authenticated_user(user)
    await require_active_membership(session, user_id=authenticated.user_id)
    return authenticated
