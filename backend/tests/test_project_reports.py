import unittest
from datetime import datetime, timezone

from app.services.project_reports import fetch_project_report_payload


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


class ProjectReportPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_project_report_payload_merges_stored_content(self) -> None:
        generated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult(
                    first_row={
                        "id": "project-1",
                        "title": "IdeaSense",
                        "description": "Startup assessment",
                        "current_stage": "report",
                        "question_bank_version_id": "bank-1",
                        "updated_at": generated_at,
                        "content_json": {
                            "artifact_locale": "en",
                            "overall_summary": "Stored summary",
                        },
                        "diagnosis_json": {"summary": "Stored diagnosis"},
                        "validation_plan_json": [{"action": "Interview users"}],
                        "artifact_schema_version": "report.v2",
                        "decision_snapshot_json": {"decision": "continue"},
                        "score_rationales_json": {"desirability": "Strong pain"},
                        "risk_register_json": [{"risk": "Low evidence"}],
                        "experiment_plan_json": [{"experiment": "Pilot"}],
                        "evidence_index_json": {"items": []},
                        "report_created_at": generated_at,
                    }
                ),
                _FakeResult(
                    first_row={
                        "state_json": {},
                        "state_meta": {
                            "ai_assisted_paths": {"problem": ["problem.one_line"]},
                            "user_edited_paths": {"problem": ["problem.one_line"]},
                        },
                    }
                ),
                _FakeResult(first_row={"missing_paths": ["problem.one_line"]}),
                _FakeResult(first_row={"skipped_count": 2}),
                _FakeResult(
                    rows=[
                        {
                            "question_id": "problem-1",
                            "title": "Problem one-liner",
                        }
                    ]
                ),
                _FakeResult(rows=[]),
            ]
        )

        payload = await fetch_project_report_payload(
            session,
            "project-1",
            output_locale="en",
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["project_id"], "project-1")
        self.assertEqual(payload["overall_summary"], "Stored summary")
        self.assertEqual(payload["artifact_schema_version"], "report.v2")
        self.assertEqual(payload["decision_snapshot"], {"decision": "continue"})
        self.assertEqual(payload["risk_register"], [{"risk": "Low evidence"}])
        self.assertEqual(payload["data_quality"]["missing_count"], 1)
        self.assertEqual(payload["data_quality"]["skipped_questions"]["count"], 2)
        self.assertEqual(
            payload["data_quality"]["missing_questions"],
            [{"question_id": "problem-1", "title": "Problem one-liner"}],
        )
        self.assertEqual(
            session.calls[0][1],
            {
                "project_id": "project-1",
                "output_locale": "en",
                "default_output_locale": "en",
            },
        )

    async def test_fetch_project_report_payload_returns_none_when_missing(self) -> None:
        payload = await fetch_project_report_payload(
            _FakeSession([_FakeResult(first_row=None)]),
            "missing",
            output_locale="en",
        )

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
