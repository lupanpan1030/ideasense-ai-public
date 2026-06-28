import unittest
from datetime import datetime, timezone

from app.services.project_mutations import (
    ProjectMutationValidationError,
    soft_delete_project,
    update_project_summary,
)


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


class ProjectMutationTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_project_summary_normalizes_and_updates_fields(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult(
                    {
                        "id": "project-1",
                        "org_id": "org-1",
                        "owner_user_id": "user-1",
                        "title": "IdeaSense",
                        "description": None,
                        "question_bank_version_id": "bank-1",
                        "current_stage": "market",
                        "current_variant": "default",
                        "stage_status": "in_progress",
                        "is_archived": True,
                        "created_at": updated_at,
                        "updated_at": updated_at,
                    }
                )
            ]
        )

        row = await update_project_summary(
            session,
            project_id="project-1",
            fields_set={"title", "description", "is_archived"},
            title="  IdeaSense  ",
            description="   ",
            is_archived=True,
        )

        self.assertEqual(row["title"], "IdeaSense")
        sql, params = session.calls[0]
        self.assertIn("title = :title", sql)
        self.assertIn("description = :description", sql)
        self.assertIn("is_archived = :is_archived", sql)
        self.assertEqual(
            params,
            {
                "project_id": "project-1",
                "title": "IdeaSense",
                "description": None,
                "is_archived": True,
            },
        )

    async def test_update_project_summary_rejects_empty_payload(self) -> None:
        with self.assertRaisesRegex(
            ProjectMutationValidationError,
            "No project fields provided.",
        ):
            await update_project_summary(
                _FakeSession([]),
                project_id="project-1",
                fields_set=set(),
            )

    async def test_update_project_summary_rejects_blank_title(self) -> None:
        with self.assertRaisesRegex(
            ProjectMutationValidationError,
            "Project title is required.",
        ):
            await update_project_summary(
                _FakeSession([]),
                project_id="project-1",
                fields_set={"title"},
                title="   ",
            )

    async def test_update_project_summary_returns_none_when_missing(self) -> None:
        row = await update_project_summary(
            _FakeSession([_FakeResult(None)]),
            project_id="missing",
            fields_set={"description"},
            description="Updated",
        )

        self.assertIsNone(row)

    async def test_soft_delete_project_reports_result(self) -> None:
        session = _FakeSession([_FakeResult({"id": "project-1"})])

        deleted = await soft_delete_project(session, project_id="project-1")

        self.assertTrue(deleted)
        self.assertIn("SET deleted_at = now()", session.calls[0][0])
        self.assertEqual(session.calls[0][1], {"project_id": "project-1"})

    async def test_soft_delete_project_returns_false_when_missing(self) -> None:
        deleted = await soft_delete_project(
            _FakeSession([_FakeResult(None)]),
            project_id="missing",
        )

        self.assertFalse(deleted)


if __name__ == "__main__":
    unittest.main()
