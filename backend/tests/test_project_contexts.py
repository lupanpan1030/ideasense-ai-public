import unittest
from datetime import datetime, timezone

from app.services.project_contexts import fetch_project_context


class _FakeResult:
    def __init__(self, *, first_row: dict | None = None, rows: list[dict] | None = None) -> None:
        self._first_row = first_row
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._first_row

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    def __init__(self, context_row: dict | None, claim_rows: list[dict] | None = None) -> None:
        self.context_row = context_row
        self.claim_rows = claim_rows or []
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append((sql, params))
        if "FROM project_stage_verification_claims" in sql:
            return _FakeResult(rows=self.claim_rows)
        return _FakeResult(first_row=self.context_row)


class ProjectContextReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_project_context_builds_payload(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            {
                "project_id": "project-1",
                "project_stage": "problem",
                "project_updated_at": updated_at,
                "runtime_stage": "problem",
                "turn_state": "draft",
                "missing_paths": ["problem.one_line"],
                "runtime_updated_at": None,
                "current_question_id": "q-current",
                "next_question_id": None,
                "state_json": {},
                "state_meta": {
                    "user_edited_paths": {" Problem ": ["problem.one_line"]},
                    "answer_meta": {
                        "problem.one_line": {
                            "resolution_status": "answered",
                            "claim_type": "fact",
                            "evidence_level": "E2",
                            "source": "user",
                        }
                    },
                },
                "state_version": None,
                "state_updated_at": None,
            },
            claim_rows=[
                {
                    "stage": "problem",
                    "claim": "Manual reporting is slow.",
                    "verdict": "supported",
                    "confidence": 0.8,
                }
            ],
        )

        payload = await fetch_project_context(session, "project-1")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["project_id"], "project-1")
        self.assertEqual(payload["stage"], "problem")
        self.assertEqual(payload["next_question_id"], "q-current")
        self.assertEqual(payload["context_version"], 0)
        self.assertEqual(payload["updated_at"], updated_at)
        self.assertEqual(payload["missing_fields"], ["problem.one_line"])
        self.assertEqual(payload["user_edited_paths"], {"problem": ["problem.one_line"]})
        self.assertEqual(
            payload["answer_meta"]["problem.one_line"]["source"],
            "user",
        )
        self.assertEqual(
            payload["context_card"]["verification_summary"]["supported_claims"],
            1,
        )
        self.assertEqual(
            session.calls[1][1],
            {"project_id": "project-1", "stage": "problem"},
        )

    async def test_fetch_project_context_returns_none_when_missing(self) -> None:
        payload = await fetch_project_context(_FakeSession(None), "missing")

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
