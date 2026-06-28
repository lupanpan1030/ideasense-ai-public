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
from app.services.auth_registration import (  # noqa: E402
    AuthRegistrationDuplicateEmailError,
    AuthRegistrationEmailDeliveryError,
    AuthRegistrationResult,
    AuthRegistrationSlugError,
    generate_unique_registration_slug,
    register_local_user,
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


class AuthRegistrationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_register_local_user_creates_org_user_membership_and_sends_email(
        self,
    ) -> None:
        session = _FakeSession()

        with patch(
            "app.services.auth_registration.issue_email_verification_token",
            AsyncMock(return_value=SimpleNamespace(token="verify-token")),
        ) as issue_token:
            with patch(
                "app.services.auth_registration.send_verification_email"
            ) as send_email:
                result = await register_local_user(
                    session,
                    email="founder@example.com",
                    password="secret-password",
                    full_name=" Founder ",
                )

        self.assertIsInstance(result, AuthRegistrationResult)
        self.assertEqual(result.email, "founder@example.com")
        statements = [sql for sql, _ in session.calls]
        self.assertIn("FROM users", statements[0])
        self.assertIn("FROM organizations", statements[1])
        self.assertIn("INSERT INTO organizations", statements[2])
        self.assertIn("INSERT INTO users", statements[3])
        self.assertIn("INSERT INTO users_public_profiles", statements[4])
        self.assertIn("INSERT INTO user_identities", statements[5])
        self.assertIn("set_config('app.org_id'", statements[6])
        self.assertIn("INSERT INTO organization_memberships", statements[7])
        self.assertEqual(session.calls[2][1]["name"], "Founder's Workspace")
        self.assertEqual(session.calls[2][1]["slug"], "founder")
        self.assertEqual(session.calls[3][1]["display_name"], "Founder")
        issue_token.assert_awaited_once_with(
            session, user_id=result.user_id, email="founder@example.com"
        )
        send_email.assert_called_once_with(
            to_email="founder@example.com", token="verify-token"
        )

    async def test_register_local_user_rejects_duplicate_email(self) -> None:
        session = _FakeSession([{"id": "user-1"}])

        with self.assertRaises(AuthRegistrationDuplicateEmailError) as exc:
            await register_local_user(
                session,
                email="founder@example.com",
                password="secret-password",
                full_name=None,
            )

        self.assertEqual(exc.exception.detail, "Email is already registered")
        self.assertEqual(len(session.calls), 1)

    async def test_generate_unique_registration_slug_retries_collisions(
        self,
    ) -> None:
        session = _FakeSession([{"exists": 1}, None])

        with patch(
            "app.services.auth_registration.secrets.token_hex",
            return_value="abc123",
        ):
            slug = await generate_unique_registration_slug(session, "founder")

        self.assertEqual(slug, "founder-abc123")
        self.assertEqual(
            [params["slug"] for _, params in session.calls],
            ["founder", "founder-abc123"],
        )

    async def test_generate_unique_registration_slug_reports_exhaustion(
        self,
    ) -> None:
        session = _FakeSession([{"exists": 1}] * 8)

        with patch(
            "app.services.auth_registration.secrets.token_hex",
            return_value="abc123",
        ):
            with self.assertRaises(AuthRegistrationSlugError) as exc:
                await generate_unique_registration_slug(session, "founder")

        self.assertEqual(
            exc.exception.detail,
            "Unable to generate a unique organization slug.",
        )

    async def test_register_local_user_maps_verification_email_failure(
        self,
    ) -> None:
        session = _FakeSession()

        with patch(
            "app.services.auth_registration.issue_email_verification_token",
            AsyncMock(return_value=SimpleNamespace(token="verify-token")),
        ):
            with patch(
                "app.services.auth_registration.send_verification_email",
                side_effect=RuntimeError("missing config"),
            ):
                with self.assertRaises(
                    AuthRegistrationEmailDeliveryError
                ) as exc:
                    await register_local_user(
                        session,
                        email="founder@example.com",
                        password="secret-password",
                        full_name=None,
                    )

        self.assertEqual(
            exc.exception.detail,
            "Unable to send verification email.",
        )


class AuthRegistrationRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_register_route_returns_token_from_registration_result(
        self,
    ) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        session = object()
        registration = AuthRegistrationResult(
            user_id="user-1",
            email="founder@example.com",
        )

        with patch.object(auth, "_apply_rate_limit", AsyncMock()) as rate_limit:
            with patch.object(auth, "_require_captcha", AsyncMock()) as captcha:
                with patch.object(
                    auth,
                    "register_local_user",
                    AsyncMock(return_value=registration),
                ) as register:
                    with patch.object(
                        auth,
                        "create_access_token",
                        return_value="access-token",
                    ) as create_token:
                        response = await auth.register_with_email(
                            auth.RegisterRequest(
                                email=" Founder@Example.COM ",
                                password="  secret-password  ",
                                full_name=" Founder ",
                            ),
                            request,
                            session=session,
                        )

        self.assertEqual(response.access_token, "access-token")
        self.assertEqual(rate_limit.await_count, 2)
        captcha.assert_awaited_once()
        register.assert_awaited_once_with(
            session,
            email="founder@example.com",
            password="secret-password",
            full_name=" Founder ",
        )
        create_token.assert_called_once_with(
            user_id="user-1",
            actor_type="user",
            email="founder@example.com",
        )

    async def test_register_route_maps_duplicate_email(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

        with patch.object(auth, "_apply_rate_limit", AsyncMock()):
            with patch.object(auth, "_require_captcha", AsyncMock()):
                with patch.object(
                    auth,
                    "register_local_user",
                    AsyncMock(
                        side_effect=AuthRegistrationDuplicateEmailError(
                            "Email is already registered"
                        )
                    ),
                ):
                    with self.assertRaises(HTTPException) as exc:
                        await auth.register_with_email(
                            auth.RegisterRequest(
                                email="founder@example.com",
                                password="secret-password",
                                full_name=None,
                            ),
                            request,
                            session=object(),
                        )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(
            exc.exception.detail,
            auth.GENERIC_REGISTRATION_FAILURE_DETAIL,
        )

    async def test_register_route_duplicate_email_matches_generic_failure(
        self,
    ) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

        with patch.object(auth, "_apply_rate_limit", AsyncMock()):
            with patch.object(auth, "_require_captcha", AsyncMock()):
                with patch.object(
                    auth,
                    "register_local_user",
                    AsyncMock(
                        side_effect=AuthRegistrationDuplicateEmailError(
                            "Email is already registered"
                        )
                    ),
                ):
                    with self.assertRaises(HTTPException) as exc:
                        await auth.register_with_email(
                            auth.RegisterRequest(
                                email="founder@example.com",
                                password="secret-password",
                                full_name=None,
                            ),
                            request,
                            session=object(),
                        )

        duplicate_body = {
            "detail": exc.exception.detail,
        }
        generic_failure_body = {
            "detail": auth.GENERIC_REGISTRATION_FAILURE_DETAIL,
        }
        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(duplicate_body, generic_failure_body)
