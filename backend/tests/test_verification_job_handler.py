import unittest
from unittest.mock import patch

from app.services import verification_job_handler
from app.services.verification_job_handler import run_verify_question_claims_v0


class _FakeResult:
    def __init__(
        self,
        *,
        row: dict | None = None,
        rows: list[dict] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row

    def all(self) -> list[dict]:
        return self._rows


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def begin(self) -> _Tx:
        return _Tx()

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append((sql, params))
        if "FROM projects" in sql:
            return _FakeResult(row={"org_id": "org-1", "owner_user_id": "user-1"})
        if "FROM project_question_instances" in sql:
            return _FakeResult(
                row={
                    "status": "answered",
                    "final_answer_text": "Students spend hours on manual reporting.",
                    "id": "question-bank-1",
                    "question_id": "P1",
                    "stage": "problem",
                    "title": "Problem",
                    "prompt_meta": {
                        "verification": {"priority": "high"},
                    },
                }
            )
        if "role = 'user'" in sql:
            return _FakeResult(
                rows=[
                    {
                        "id": 11,
                        "content": "Students spend hours on manual reporting.",
                    }
                ]
            )
        if "role = 'assistant'" in sql:
            return _FakeResult(
                row={
                    "id": 10,
                    "meta": {
                        "key_points": [
                            "Students spend hours on manual reporting.",
                            "Students spend hours on manual reporting.",
                        ]
                    },
                }
            )
        return _FakeResult()


class VerificationJobHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_verify_question_claims_persists_claim_rows(self) -> None:
        captured: dict[str, object] = {}

        async def fake_verify_report_inputs(**kwargs):
            captured["qa_digest_by_stage"] = kwargs["qa_digest_by_stage"]
            captured["last_user_message"] = kwargs["last_user_message"]
            return {
                "enabled": True,
                "evidence_mode": "search",
                "verified_facts": [
                    {
                        "claim": "Students spend hours on manual reporting.",
                        "section": "problem",
                        "verdict": "supported",
                        "confidence": "High",
                        "rationale": "Evidence matched.",
                        "sources": [{"url": "https://example.com"}],
                    }
                ],
                "unsupported_claims": [],
            }

        session = _FakeSession()
        with patch.object(
            verification_job_handler,
            "verify_report_inputs",
            new=fake_verify_report_inputs,
        ):
            await run_verify_question_claims_v0(
                session,
                {
                    "project_id": "project-1",
                    "question_instance_id": "question-instance-1",
                },
            )

        insert_call = next(
            (
                params
                for sql, params in session.calls
                if "INSERT INTO project_stage_verification_claims" in sql
            ),
            None,
        )
        self.assertIsNotNone(insert_call)
        self.assertEqual(insert_call[0]["org_id"], "org-1")
        self.assertEqual(insert_call[0]["project_id"], "project-1")
        self.assertEqual(insert_call[0]["question_bank_question_id"], "question-bank-1")
        self.assertEqual(insert_call[0]["source_message_id"], 11)
        self.assertEqual(insert_call[0]["priority"], "high")
        self.assertEqual(insert_call[0]["evidence_mode"], "search")
        self.assertEqual(
            captured["qa_digest_by_stage"]["problem"][0]["key_points"],
            ["Students spend hours on manual reporting."],
        )

    async def test_run_verify_question_claims_requires_identifiers(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Job payload missing required identifiers.",
        ):
            await run_verify_question_claims_v0(_FakeSession(), {"project_id": "p1"})


if __name__ == "__main__":
    unittest.main()
