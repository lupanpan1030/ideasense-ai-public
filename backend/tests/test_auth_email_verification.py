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
from app.core.email_verification import VerificationError  # noqa: E402
from app.services.auth_email_verification import (  # noqa: E402
    AuthEmailVerificationDeliveryError,
    AuthEmailVerificationMissingEmailError,
    AuthEmailVerificationTokenError,
    AuthEmailVerificationUserError,
    resend_email_verification_workflow,
    verify_email_workflow,
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


class AuthEmailVerificationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_email_workflow_maps_invalid_token(self) -> None:
        with patch(
            "app.services.auth_email_verification.verify_email_token",
            AsyncMock(side_effect=VerificationError("Invalid token")),
        ):
            with self.assertRaises(AuthEmailVerificationTokenError) as exc:
                await verify_email_workflow(_FakeSession(), token="bad")

        self.assertEqual(exc.exception.detail, "Invalid token")

    async def test_verify_email_workflow_returns_verified(self) -> None:
        with patch(
            "app.services.auth_email_verification.verify_email_token",
            AsyncMock(),
        ) as verify_token:
            status = await verify_email_workflow(_FakeSession(), token="ok")

        self.assertEqual(status, "verified")
        verify_token.assert_awaited_once()

    async def test_resend_email_verification_requires_active_user(self) -> None:
        session = _FakeSession([None])

        with self.assertRaises(AuthEmailVerificationUserError) as exc:
            await resend_email_verification_workflow(
                session, user_id="user-1"
            )

        self.assertEqual(exc.exception.detail, "User not found or inactive")

    async def test_resend_email_verification_returns_already_verified(self) -> None:
        session = _FakeSession(
            [{"id": "user-1", "email": "a@b.com", "email_verified_at": object()}]
        )

        status = await resend_email_verification_workflow(
            session, user_id="user-1"
        )

        self.assertEqual(status, "already_verified")

    async def test_resend_email_verification_requires_email(self) -> None:
        session = _FakeSession(
            [{"id": "user-1", "email": " ", "email_verified_at": None}]
        )

        with self.assertRaises(AuthEmailVerificationMissingEmailError) as exc:
            await resend_email_verification_workflow(
                session, user_id="user-1"
            )

        self.assertEqual(exc.exception.detail, "User email is missing.")

    async def test_resend_email_verification_sends_token(self) -> None:
        session = _FakeSession(
            [{"id": "user-1", "email": "a@b.com", "email_verified_at": None}]
        )

        with patch(
            "app.services.auth_email_verification.issue_email_verification_token",
            AsyncMock(return_value=SimpleNamespace(token="verify-token")),
        ) as issue_token:
            with patch(
                "app.services.auth_email_verification.send_verification_email"
            ) as send_email:
                status = await resend_email_verification_workflow(
                    session, user_id="user-1"
                )

        self.assertEqual(status, "sent")
        self.assertIn("FROM users", session.calls[0][0])
        issue_token.assert_awaited_once_with(
            session, user_id="user-1", email="a@b.com"
        )
        send_email.assert_called_once_with(
            to_email="a@b.com", token="verify-token"
        )

    async def test_resend_email_verification_maps_delivery_failure(self) -> None:
        session = _FakeSession(
            [{"id": "user-1", "email": "a@b.com", "email_verified_at": None}]
        )

        with patch(
            "app.services.auth_email_verification.issue_email_verification_token",
            AsyncMock(return_value=SimpleNamespace(token="verify-token")),
        ):
            with patch(
                "app.services.auth_email_verification.send_verification_email",
                side_effect=RuntimeError("missing config"),
            ):
                with self.assertRaises(
                    AuthEmailVerificationDeliveryError
                ) as exc:
                    await resend_email_verification_workflow(
                        session, user_id="user-1"
                    )

        self.assertEqual(
            exc.exception.detail,
            "Unable to send verification email.",
        )


class AuthEmailVerificationRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_email_route_maps_invalid_token(self) -> None:
        with patch.object(
            auth,
            "verify_email_workflow",
            AsyncMock(
                side_effect=AuthEmailVerificationTokenError("Invalid token")
            ),
        ):
            with self.assertRaises(HTTPException) as exc:
                await auth.verify_email(
                    auth.VerifyEmailRequest(token="bad"),
                    session=object(),
                )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail, "Invalid token")

    async def test_resend_verification_route_returns_service_status(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        actor = SimpleNamespace(user_id="user-1")
        session = object()

        with patch.object(auth, "_apply_rate_limit", AsyncMock()) as rate_limit:
            with patch.object(auth, "_require_captcha", AsyncMock()) as captcha:
                with patch.object(
                    auth,
                    "resend_email_verification_workflow",
                    AsyncMock(return_value="already_verified"),
                ) as resend:
                    response = await auth.resend_verification(
                        request,
                        payload=auth.ResendVerificationRequest(
                            captcha_token="captcha"
                        ),
                        actor=actor,
                        session=session,
                    )

        self.assertEqual(response.status, "already_verified")
        self.assertEqual(rate_limit.await_count, 2)
        captcha.assert_awaited_once_with("captcha", "127.0.0.1")
        resend.assert_awaited_once_with(session, user_id="user-1")
