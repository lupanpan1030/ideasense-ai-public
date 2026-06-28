import asyncio
import unittest
from datetime import datetime, timezone
from uuid import UUID

from app.services.platform_admin_users import (
    PlatformAdminUserNotFoundError,
    PlatformAdminUsersValidationError,
    list_platform_admin_payloads,
    row_to_platform_admin_payload,
    upsert_platform_admin_payload,
)


USER_ID = UUID("22222222-2222-4222-8222-222222222222")


def _admin_row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": USER_ID,
        "email": "admin@example.com",
        "display_name": "Admin",
        "role": "superadmin",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


class PlatformAdminUsersServiceTests(unittest.TestCase):
    def test_row_to_platform_admin_payload_defaults_role_and_status(self) -> None:
        payload = row_to_platform_admin_payload({"user_id": USER_ID})

        self.assertEqual(payload["user_id"], USER_ID)
        self.assertEqual(payload["role"], "admin")
        self.assertEqual(payload["status"], "active")

    def test_list_platform_admin_payloads_shapes_rows(self) -> None:
        session = _Session([[_admin_row()]])

        payloads = _run(list_platform_admin_payloads(session))

        self.assertEqual(payloads[0]["email"], "admin@example.com")
        self.assertEqual(payloads[0]["role"], "superadmin")

    def test_upsert_rejects_missing_user_identifier(self) -> None:
        session = _Session([])

        with self.assertRaises(PlatformAdminUsersValidationError) as exc:
            _run(
                upsert_platform_admin_payload(
                    session,
                    user_id=None,
                    email=None,
                    role="admin",
                    status="active",
                )
            )

        self.assertEqual(exc.exception.detail, "user_id or email is required")
        self.assertEqual(session.params, [])

    def test_upsert_raises_not_found_when_email_lookup_misses(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformAdminUserNotFoundError) as exc:
            _run(
                upsert_platform_admin_payload(
                    session,
                    user_id=None,
                    email="missing@example.com",
                    role="admin",
                    status="active",
                )
            )

        self.assertEqual(exc.exception.detail, "User not found")
        self.assertEqual(session.params[0], {"email": "missing@example.com"})

    def test_upsert_preserves_lookup_before_role_validation(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformAdminUserNotFoundError) as exc:
            _run(
                upsert_platform_admin_payload(
                    session,
                    user_id=None,
                    email="missing@example.com",
                    role="invalid",
                    status="active",
                )
            )

        self.assertEqual(exc.exception.detail, "User not found")
        self.assertEqual(len(session.params), 1)

    def test_upsert_rejects_invalid_role(self) -> None:
        session = _Session([])

        with self.assertRaises(PlatformAdminUsersValidationError) as exc:
            _run(
                upsert_platform_admin_payload(
                    session,
                    user_id=USER_ID,
                    email=None,
                    role="invalid",
                    status="active",
                )
            )

        self.assertEqual(exc.exception.detail, "Invalid role")
        self.assertEqual(session.params, [])

    def test_upsert_rejects_missing_membership(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformAdminUsersValidationError) as exc:
            _run(
                upsert_platform_admin_payload(
                    session,
                    user_id=USER_ID,
                    email=None,
                    role="admin",
                    status="active",
                )
            )

        self.assertEqual(
            exc.exception.detail,
            "Platform admins must have an active owner/admin membership",
        )
        self.assertEqual(session.params[0], {"user_id": str(USER_ID)})

    def test_upsert_writes_and_refetches_admin_payload(self) -> None:
        session = _Session([[{"exists": 1}], [], [_admin_row()]])

        payload = _run(
            upsert_platform_admin_payload(
                session,
                user_id=USER_ID,
                email=None,
                role="superadmin",
                status="active",
            )
        )

        self.assertEqual(payload["user_id"], USER_ID)
        self.assertEqual(payload["role"], "superadmin")
        self.assertEqual(
            session.params[1],
            {"user_id": str(USER_ID), "role": "superadmin", "status": "active"},
        )
        self.assertEqual(session.params[2], {"user_id": str(USER_ID)})


def _run(awaitable):
    return asyncio.run(awaitable)


class _Session:
    def __init__(self, results: list[list[dict]]) -> None:
        self.results = list(results)
        self.params: list[object] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.params.append(params or {})
        rows = self.results.pop(0) if self.results else []
        return _Result(rows)


class _Result:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict]:
        return self.rows

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None


if __name__ == "__main__":
    unittest.main()
