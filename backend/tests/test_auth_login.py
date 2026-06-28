import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)

from app.api.routes import auth  # noqa: E402
from app.core.rate_limits import RateLimitSettings  # noqa: E402
from app.services.auth_login import (  # noqa: E402
    AuthLoginInvalidCredentialsError,
    AuthLoginNoActiveMembershipError,
    AuthenticatedUser,
    dev_login_local_user,
    login_local_user,
    require_active_membership,
)


class _FakeResult:
    def __init__(self, row: dict | None = None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, rows: list[dict | None] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        row = self.rows.pop(0) if self.rows else None
        return _FakeResult(row)


class AuthLoginServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_local_user_returns_authenticated_user(self) -> None:
        session = _FakeSession(
            [
                {"id": "user-1", "email": "a@b.com"},
                {"org_id": "org-1"},
            ]
        )

        result = await login_local_user(
            session,
            email="a@b.com",
            password="secret-password",
            client_ip="127.0.0.1",
            fail_limit=RateLimitSettings(window_seconds=900, max_count=3),
        )

        self.assertEqual(result, AuthenticatedUser(user_id="user-1", email="a@b.com"))
        self.assertIn("FROM user_identities", session.calls[0][0])
        self.assertEqual(
            session.calls[0][1],
            {"email": "a@b.com", "password": "secret-password"},
        )
        self.assertIn("FROM organization_memberships", session.calls[1][0])
        self.assertEqual(session.calls[1][1], {"user_id": "user-1"})

    async def test_login_local_user_records_failure_counters(self) -> None:
        session = _FakeSession([None])

        with patch(
            "app.services.auth_login.increment_rate_limit",
            AsyncMock(),
        ) as increment:
            with self.assertRaises(AuthLoginInvalidCredentialsError) as exc:
                await login_local_user(
                    session,
                    email="a@b.com",
                    password="bad-password",
                    client_ip="127.0.0.1",
                    fail_limit=RateLimitSettings(window_seconds=900, max_count=3),
                )

        self.assertEqual(exc.exception.detail, "Invalid credentials")
        self.assertEqual(increment.await_count, 2)
        self.assertEqual(
            increment.await_args_list[0].kwargs,
            {
                "scope": "login_fail:ip",
                "key": "127.0.0.1",
                "window_seconds": 900,
            },
        )
        self.assertEqual(
            increment.await_args_list[1].kwargs,
            {
                "scope": "login_fail:email",
                "key": "a@b.com",
                "window_seconds": 900,
            },
        )

    async def test_require_active_membership_raises_domain_error(self) -> None:
        session = _FakeSession([None])

        with self.assertRaises(AuthLoginNoActiveMembershipError) as exc:
            await require_active_membership(session, user_id="user-1")

        self.assertEqual(exc.exception.detail, "No active org membership")

    async def test_dev_login_local_user_enforces_membership(self) -> None:
        session = _FakeSession(
            [
                {"id": "user-1", "email": "a@b.com"},
                {"org_id": "org-1"},
            ]
        )

        result = await dev_login_local_user(session, email="a@b.com")

        self.assertEqual(result.user_id, "user-1")
        self.assertEqual(result.email, "a@b.com")
        self.assertIn("FROM user_identities", session.calls[0][0])
        self.assertIn("FROM organization_memberships", session.calls[1][0])

    async def test_dev_login_local_user_maps_missing_user(self) -> None:
        session = _FakeSession([None])

        with self.assertRaises(AuthLoginInvalidCredentialsError) as exc:
            await dev_login_local_user(session, email="missing@example.com")

        self.assertEqual(exc.exception.detail, "Invalid credentials")


class AuthLoginRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_route_returns_token_from_authenticated_user(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        session = object()

        with patch.object(auth, "_apply_rate_limit", AsyncMock()) as rate_limit:
            with patch.object(
                auth, "_should_require_login_captcha", AsyncMock(return_value=False)
            ) as should_captcha:
                with patch.object(
                    auth,
                    "login_local_user",
                    AsyncMock(
                        return_value=AuthenticatedUser(
                            user_id="user-1",
                            email="a@b.com",
                        )
                    ),
                ) as login:
                    with patch.object(
                        auth,
                        "create_access_token",
                        return_value="access-token",
                    ) as create_token:
                        response = await auth.login_with_email(
                            auth.LoginRequest(
                                email=" A@B.COM ",
                                password=" secret-password ",
                            ),
                            request,
                            session=session,
                        )

        self.assertEqual(response.access_token, "access-token")
        self.assertEqual(rate_limit.await_count, 2)
        should_captcha.assert_awaited_once_with(
            session, client_ip="127.0.0.1", email="a@b.com"
        )
        login.assert_awaited_once_with(
            session,
            email="a@b.com",
            password="secret-password",
            client_ip="127.0.0.1",
            fail_limit=auth.LOGIN_FAIL_LIMIT,
        )
        create_token.assert_called_once_with(
            user_id="user-1",
            actor_type="user",
            email="a@b.com",
        )

    async def test_login_route_maps_invalid_credentials(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

        with patch.object(auth, "_apply_rate_limit", AsyncMock()):
            with patch.object(
                auth, "_should_require_login_captcha", AsyncMock(return_value=False)
            ):
                with patch.object(
                    auth,
                    "login_local_user",
                    AsyncMock(
                        side_effect=AuthLoginInvalidCredentialsError(
                            "Invalid credentials"
                        )
                    ),
                ):
                    with self.assertRaises(HTTPException) as exc:
                        await auth.login_with_email(
                            auth.LoginRequest(
                                email="a@b.com",
                                password="bad-password",
                            ),
                            request,
                            session=object(),
                        )

        self.assertEqual(exc.exception.status_code, 401)
        self.assertEqual(exc.exception.detail, "Invalid credentials")

    async def test_dev_login_route_maps_membership_error(self) -> None:
        with patch.object(auth, "DEV_LOGIN_ENABLED", True):
            with patch.object(
                auth,
                "dev_login_local_user",
                AsyncMock(
                    side_effect=AuthLoginNoActiveMembershipError(
                        "No active org membership"
                    )
                ),
            ):
                with self.assertRaises(HTTPException) as exc:
                    await auth.dev_login_with_email(
                        auth.DevLoginRequest(email="a@b.com"),
                        session=object(),
                    )

        self.assertEqual(exc.exception.status_code, 403)
        self.assertEqual(exc.exception.detail, "No active org membership")
