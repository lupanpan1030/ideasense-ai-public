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
from app.core.password_reset import (  # noqa: E402
    PasswordResetError,
    PasswordResetRecord,
)
from app.services.auth_password_reset import (  # noqa: E402
    AuthPasswordResetInvalidTokenError,
    AuthPasswordResetUserNotFoundError,
    confirm_password_reset_workflow,
    request_password_reset_workflow,
)


class _FakeResult:
    def __init__(self, row: dict | None = None, rowcount: int = 0) -> None:
        self._row = row
        self.rowcount = rowcount

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(
        self,
        results: list[_FakeResult] | None = None,
    ) -> None:
        self.results = results or []
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        if self.results:
            return self.results.pop(0)
        return _FakeResult()


class AuthPasswordResetServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_password_reset_issues_token_and_sends_email(self) -> None:
        session = _FakeSession([_FakeResult({"id": "user-1", "email": "a@b.com"})])

        with patch(
            "app.services.auth_password_reset.issue_password_reset_token",
            AsyncMock(return_value=SimpleNamespace(token="reset-token")),
        ) as issue_token:
            with patch(
                "app.services.auth_password_reset.send_password_reset_email"
            ) as send_email:
                status = await request_password_reset_workflow(
                    session, email="a@b.com"
                )

        self.assertEqual(status, "sent")
        self.assertIn("FROM user_identities", session.calls[0][0])
        issue_token.assert_awaited_once_with(
            session, user_id="user-1", email="a@b.com"
        )
        send_email.assert_called_once_with(
            to_email="a@b.com", token="reset-token"
        )

    async def test_request_password_reset_hides_missing_user(self) -> None:
        session = _FakeSession([_FakeResult(None)])

        with patch(
            "app.services.auth_password_reset.issue_password_reset_token",
            AsyncMock(),
        ) as issue_token:
            with patch(
                "app.services.auth_password_reset.send_password_reset_email"
            ) as send_email:
                status = await request_password_reset_workflow(
                    session, email="missing@example.com"
                )

        self.assertEqual(status, "sent")
        issue_token.assert_not_awaited()
        send_email.assert_not_called()

    async def test_request_password_reset_hides_email_delivery_failure(
        self,
    ) -> None:
        session = _FakeSession([_FakeResult({"id": "user-1", "email": "a@b.com"})])

        with patch(
            "app.services.auth_password_reset.issue_password_reset_token",
            AsyncMock(return_value=SimpleNamespace(token="reset-token")),
        ):
            with patch(
                "app.services.auth_password_reset.send_password_reset_email",
                side_effect=RuntimeError("missing config"),
            ):
                status = await request_password_reset_workflow(
                    session, email="a@b.com"
                )

        self.assertEqual(status, "sent")

    async def test_confirm_password_reset_maps_invalid_token(self) -> None:
        with patch(
            "app.services.auth_password_reset.verify_password_reset_token",
            AsyncMock(side_effect=PasswordResetError("Reset token is invalid.")),
        ):
            with self.assertRaises(AuthPasswordResetInvalidTokenError) as exc:
                await confirm_password_reset_workflow(
                    _FakeSession(), token="bad", password="secret-password"
                )

        self.assertEqual(exc.exception.detail, "Reset token is invalid.")

    async def test_confirm_password_reset_maps_inactive_user(self) -> None:
        session = _FakeSession([_FakeResult(rowcount=0)])

        with patch(
            "app.services.auth_password_reset.verify_password_reset_token",
            AsyncMock(
                return_value=PasswordResetRecord(
                    token_id="token-1",
                    user_id="user-1",
                    email="a@b.com",
                )
            ),
        ):
            with self.assertRaises(AuthPasswordResetUserNotFoundError) as exc:
                await confirm_password_reset_workflow(
                    session, token="token", password="secret-password"
                )

        self.assertEqual(exc.exception.detail, "User not found or inactive")
        self.assertEqual(len(session.calls), 1)

    async def test_confirm_password_reset_updates_password_and_consumes_token(
        self,
    ) -> None:
        session = _FakeSession([_FakeResult(rowcount=1), _FakeResult()])

        with patch(
            "app.services.auth_password_reset.verify_password_reset_token",
            AsyncMock(
                return_value=PasswordResetRecord(
                    token_id="token-1",
                    user_id="user-1",
                    email="a@b.com",
                )
            ),
        ) as verify_token:
            status = await confirm_password_reset_workflow(
                session, token="token", password="secret-password"
            )

        self.assertEqual(status, "reset")
        verify_token.assert_awaited_once_with(session, token="token")
        self.assertIn("UPDATE user_identities", session.calls[0][0])
        self.assertEqual(
            session.calls[0][1],
            {"password": "secret-password", "user_id": "user-1"},
        )
        self.assertIn("UPDATE password_reset_tokens", session.calls[1][0])
        self.assertEqual(session.calls[1][1], {"token_id": "token-1"})


class AuthPasswordResetRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_password_reset_request_route_calls_service(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        session = object()

        with patch.object(auth, "_apply_rate_limit", AsyncMock()) as rate_limit:
            with patch.object(auth, "_require_captcha", AsyncMock()) as captcha:
                with patch.object(
                    auth,
                    "request_password_reset_workflow",
                    AsyncMock(return_value="sent"),
                ) as request_reset:
                    response = await auth.request_password_reset(
                        auth.PasswordResetRequest(
                            email=" Founder@Example.COM ",
                            captcha_token="captcha",
                        ),
                        request,
                        session=session,
                    )

        self.assertEqual(response.status, "sent")
        self.assertEqual(rate_limit.await_count, 2)
        captcha.assert_awaited_once_with("captcha", "127.0.0.1")
        request_reset.assert_awaited_once_with(
            session, email="founder@example.com"
        )

    async def test_password_reset_confirm_route_maps_invalid_token(self) -> None:
        with patch.object(
            auth,
            "confirm_password_reset_workflow",
            AsyncMock(
                side_effect=AuthPasswordResetInvalidTokenError(
                    "Reset token is invalid."
                )
            ),
        ):
            with self.assertRaises(HTTPException) as exc:
                await auth.confirm_password_reset(
                    auth.PasswordResetConfirmRequest(
                        token="bad",
                        password="secret-password",
                    ),
                    session=object(),
                )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail, "Reset token is invalid.")
