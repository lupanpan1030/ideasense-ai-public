import unittest
from datetime import datetime, timezone

from app.services.project_conversations import (
    ConversationCursorValidationError,
    fetch_project_conversation_list,
    normalize_conversation_cursor,
)


class _FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return _FakeResult(self.rows)


class ConversationCursorTests(unittest.TestCase):
    def test_normalize_conversation_cursor_accepts_z_suffix(self) -> None:
        cursor = normalize_conversation_cursor(
            before="2026-01-02T03:04:05Z",
            before_id=12,
        )

        self.assertEqual(
            cursor.before,
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(cursor.before_id, 12)
        self.assertFalse(cursor.is_first_page)

    def test_normalize_conversation_cursor_defaults_naive_time_to_utc(self) -> None:
        cursor = normalize_conversation_cursor(
            before="2026-01-02T03:04:05",
            before_id=None,
        )

        self.assertEqual(cursor.before.tzinfo, timezone.utc)

    def test_normalize_conversation_cursor_rejects_invalid_timestamp(self) -> None:
        with self.assertRaisesRegex(
            ConversationCursorValidationError,
            "Invalid 'before' timestamp.",
        ):
            normalize_conversation_cursor(before="not-a-date", before_id=None)

    def test_normalize_conversation_cursor_requires_before_for_before_id(self) -> None:
        with self.assertRaisesRegex(
            ConversationCursorValidationError,
            "before_id requires a valid before timestamp.",
        ):
            normalize_conversation_cursor(before=None, before_id=12)


class ConversationListReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_project_conversation_list_parses_meta_and_reverses_rows(
        self,
    ) -> None:
        created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                {
                    "id": 2,
                    "role": "assistant",
                    "content": "Second",
                    "created_at": created_at,
                    "stage": "market",
                    "meta": "{not-json",
                },
                {
                    "id": 1,
                    "role": "user",
                    "content": "First",
                    "created_at": created_at,
                    "stage": "market",
                    "meta": '{"content_locale":"en"}',
                },
            ]
        )
        cursor = normalize_conversation_cursor(
            before="2026-01-02T03:04:05Z",
            before_id=2,
        )

        payload = await fetch_project_conversation_list(
            session,
            project_id="project-1",
            limit=50,
            cursor=cursor,
        )

        self.assertEqual([row["id"] for row in payload["messages"]], [1, 2])
        self.assertEqual(payload["messages"][0]["meta"], {"content_locale": "en"})
        self.assertIsNone(payload["messages"][1]["meta"])
        sql, params = session.calls[0]
        self.assertIn("(cm.created_at, cm.id) < (:before, :before_id)", sql)
        self.assertEqual(params["project_id"], "project-1")
        self.assertEqual(params["limit"], 50)
        self.assertEqual(params["before_id"], 2)

    async def test_fetch_project_conversation_list_omits_cursor_filter_on_first_page(
        self,
    ) -> None:
        cursor = normalize_conversation_cursor(before=None, before_id=None)
        session = _FakeSession([])

        await fetch_project_conversation_list(
            session,
            project_id="project-1",
            limit=20,
            cursor=cursor,
        )

        self.assertNotIn("cm.created_at <", session.calls[0][0])
        self.assertTrue(cursor.is_first_page)


if __name__ == "__main__":
    unittest.main()
