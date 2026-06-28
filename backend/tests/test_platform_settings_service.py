import unittest
from datetime import datetime, timezone
from uuid import UUID

from app.services.platform_settings import (
    PlatformSettingsValidationError,
    build_platform_settings_payload,
    normalize_setting_key,
    update_platform_settings_payload,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def _row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "key": "report_quality.enabled",
        "value": True,
        "updated_by": USER_ID,
        "email": "admin@example.com",
        "display_name": "Admin",
        "created_at": now,
        "updated_at": now,
    }


class PlatformSettingsServiceTests(unittest.TestCase):
    def test_normalize_setting_key_rejects_empty_key(self) -> None:
        with self.assertRaises(PlatformSettingsValidationError) as exc:
            normalize_setting_key("  ")

        self.assertEqual(exc.exception.detail, "Setting key cannot be empty")

    def test_build_platform_settings_payload_preserves_entries(self) -> None:
        payload = build_platform_settings_payload([_row()])

        self.assertEqual(payload["settings"], {"report_quality.enabled": True})
        self.assertEqual(payload["entries"][0]["key"], "report_quality.enabled")
        self.assertEqual(payload["entries"][0]["updated_by_email"], "admin@example.com")

    def test_update_platform_settings_rejects_empty_payload(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformSettingsValidationError) as exc:
            _run(
                update_platform_settings_payload(
                    session,
                    settings_payload=None,
                    remove_payload=None,
                )
            )

        self.assertEqual(exc.exception.detail, "settings or remove is required")

    def test_update_platform_settings_rejects_overlapping_keys(self) -> None:
        session = _Session([[]])

        with self.assertRaises(PlatformSettingsValidationError) as exc:
            _run(
                update_platform_settings_payload(
                    session,
                    settings_payload={"flag": True},
                    remove_payload=["flag"],
                )
            )

        self.assertEqual(exc.exception.detail, "remove overlaps settings keys: flag")

    def test_update_platform_settings_upserts_removes_and_returns_payload(self) -> None:
        session = _Session([[], [], [_row()]])

        payload = _run(
            update_platform_settings_payload(
                session,
                settings_payload={" report_quality.enabled ": True},
                remove_payload=["old.flag"],
            )
        )

        self.assertEqual(payload["settings"], {"report_quality.enabled": True})
        self.assertEqual(session.params[0], [{"key": "report_quality.enabled", "value": "true"}])
        self.assertEqual(session.params[1], {"keys": ["old.flag"]})


def _run(awaitable):
    import asyncio

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


if __name__ == "__main__":
    unittest.main()
