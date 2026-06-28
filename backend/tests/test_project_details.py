import unittest
from datetime import datetime, timezone

from app.services.project_details import (
    ProjectRuntimeMissingError,
    fetch_project_detail,
)


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, row: dict | None) -> None:
        self.row = row
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return _FakeResult(self.row)


class ProjectDetailReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_project_detail_builds_nested_payload(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
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
                "settings": None,
                "is_archived": False,
                "archived_at": None,
                "created_at": updated_at,
                "updated_at": updated_at,
                "runtime_project_id": "project-1",
                "runtime_org_id": "org-1",
                "runtime_stage": "market",
                "runtime_variant": "default",
                "current_question_bank_question_id": "question-1",
                "next_question_bank_question_id": None,
                "missing_paths": None,
                "turn_state": "draft",
                "runtime_version": 2,
                "runtime_created_at": updated_at,
                "runtime_updated_at": updated_at,
                "current_question_instance_id": "instance-1",
            }
        )

        payload = await fetch_project_detail(session, "project-1")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["project"]["id"], "project-1")
        self.assertEqual(payload["project"]["settings"], {})
        self.assertEqual(payload["runtime"]["project_id"], "project-1")
        self.assertEqual(payload["runtime"]["missing_paths"], [])
        self.assertEqual(payload["current_question_instance_id"], "instance-1")
        self.assertEqual(session.calls[0][1], {"project_id": "project-1"})

    async def test_fetch_project_detail_returns_none_when_missing(self) -> None:
        payload = await fetch_project_detail(_FakeSession(None), "missing")

        self.assertIsNone(payload)

    async def test_fetch_project_detail_rejects_missing_runtime(self) -> None:
        with self.assertRaises(ProjectRuntimeMissingError):
            await fetch_project_detail(
                _FakeSession({"id": "project-1", "runtime_project_id": None}),
                "project-1",
            )


if __name__ == "__main__":
    unittest.main()
