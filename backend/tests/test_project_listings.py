import unittest
from datetime import datetime, timezone

from app.services.project_listings import (
    fetch_project_list,
    normalize_project_list_filters,
)


class _FakeResult:
    def __init__(
        self,
        *,
        first_row: dict | None = None,
        rows: list[dict] | None = None,
    ) -> None:
        self._first_row = first_row
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._first_row

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


class ProjectListingFilterTests(unittest.TestCase):
    def test_normalize_project_list_filters_applies_defaults(self) -> None:
        filters = normalize_project_list_filters(
            stage="all",
            archived=None,
            sort=None,
            order=None,
        )

        self.assertIsNone(filters.stage)
        self.assertEqual(filters.archived, "active")
        self.assertEqual(filters.sort, "updated_at")
        self.assertEqual(filters.order, "desc")

    def test_normalize_project_list_filters_rejects_unknown_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid stage filter"):
            normalize_project_list_filters(
                stage="unknown",
                archived=None,
                sort=None,
                order=None,
            )

        with self.assertRaisesRegex(ValueError, "Invalid sort order"):
            normalize_project_list_filters(
                stage=None,
                archived=None,
                sort=None,
                order="sideways",
            )


class ProjectListingReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_project_list_builds_filtered_payload(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult(first_row={"total": 1}),
                _FakeResult(
                    rows=[
                        {
                            "id": "project-1",
                            "org_id": "org-1",
                            "owner_user_id": "user-1",
                            "title": "IdeaSense",
                            "description": "Startup assessment",
                            "question_bank_version_id": "bank-1",
                            "current_stage": "market",
                            "current_variant": "default",
                            "stage_status": "in_progress",
                            "is_archived": False,
                            "created_at": updated_at,
                            "updated_at": updated_at,
                        }
                    ]
                ),
            ]
        )

        payload = await fetch_project_list(
            session,
            owner_user_id="user-1",
            limit=20,
            offset=0,
            stage=" Market ",
            archived="all",
            sort="title",
            order="asc",
        )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["limit"], 20)
        self.assertEqual(payload["projects"][0]["title"], "IdeaSense")
        self.assertIn("p.current_stage = :stage", session.calls[0][0])
        self.assertNotIn("p.is_archived =", session.calls[0][0])
        self.assertIn("LOWER(p.title) ASC", session.calls[1][0])
        self.assertEqual(
            session.calls[1][1],
            {"limit": 20, "offset": 0, "owner_user_id": "user-1", "stage": "market"},
        )


if __name__ == "__main__":
    unittest.main()
