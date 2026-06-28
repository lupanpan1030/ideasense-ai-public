import unittest
from uuid import uuid4

from app.services.stage_question_setup import (
    StageQuestionPromptMissingError,
    StageStarterQuestionMissingError,
    build_stage_question_meta_payload,
    fetch_stage_question_detail,
    resolve_stage_initial_questions,
    resolve_stage_missing_paths,
)


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


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


class StageQuestionSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_stage_initial_questions_preserves_order(self) -> None:
        current_question_id = uuid4()
        next_question_id = uuid4()
        session = _FakeSession(
            [
                _FakeResult(
                    rows=[
                        {"id": current_question_id},
                        {"id": next_question_id},
                    ]
                )
            ]
        )

        current, next_question = await resolve_stage_initial_questions(
            session,
            bank_id="bank-1",
            stage="market",
            variant="default",
        )

        self.assertEqual(current, current_question_id)
        self.assertEqual(next_question, next_question_id)
        self.assertEqual(
            session.calls[0][1],
            {"bank_id": "bank-1", "stage": "market", "variant": "default"},
        )

    async def test_resolve_stage_initial_questions_rejects_empty_bank(self) -> None:
        with self.assertRaisesRegex(
            StageStarterQuestionMissingError,
            "Question bank has no starter questions for this stage.",
        ):
            await resolve_stage_initial_questions(
                _FakeSession([_FakeResult(rows=[])]),
                bank_id="bank-1",
                stage="market",
                variant="default",
            )

    async def test_resolve_stage_missing_paths_returns_required_paths(self) -> None:
        session = _FakeSession(
            [_FakeResult(row={"paths": ["market_strategy.uvp.one_line"]})]
        )

        paths = await resolve_stage_missing_paths(
            session,
            bank_id="bank-1",
            stage="market",
            variant="default",
        )

        self.assertEqual(paths, ["market_strategy.uvp.one_line"])
        self.assertIn("type_raw ILIKE 'Required%'", session.calls[0][0])

    async def test_fetch_stage_question_detail_requires_prompt(self) -> None:
        with self.assertRaisesRegex(
            StageQuestionPromptMissingError,
            "Question prompt not found.",
        ):
            await fetch_stage_question_detail(
                _FakeSession([_FakeResult(row={"id": "question-1"})]),
                "question-1",
            )

    async def test_build_stage_question_meta_payload_extracts_ui_metadata(self) -> None:
        payload = build_stage_question_meta_payload(
            {
                "question_id": "S2Q1",
                "stage": "market",
                "variant": "default",
                "prompt_meta": {"ui": {"placeholder": "One sentence"}},
            }
        )

        self.assertEqual(
            payload,
            {
                "question_id": "S2Q1",
                "stage": "market",
                "variant": "default",
                "ui": {"placeholder": "One sentence"},
            },
        )


if __name__ == "__main__":
    unittest.main()
