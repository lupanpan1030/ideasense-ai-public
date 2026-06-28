import unittest
from unittest.mock import patch

from app.services import qa_digests


class QaDigestTests(unittest.IsolatedAsyncioTestCase):
    def test_derive_answer_summary_prefers_rolling_summary(self) -> None:
        self.assertEqual(
            qa_digests.derive_answer_summary(["first", "second"], "  rolling  "),
            "rolling",
        )

    def test_derive_answer_summary_falls_back_to_key_points(self) -> None:
        self.assertEqual(
            qa_digests.derive_answer_summary(["first", "second", "third"], None),
            "first; second",
        )

    async def test_build_qa_digests_skips_invalid_and_deduplicates_questions(self) -> None:
        rows = [
            {"id": "skip-1", "meta": None, "model_name": "row-model"},
            {
                "id": "msg-1",
                "meta": {
                    "question_id": "S1Q1",
                    "key_points": [" point one ", "", 2, "point two"],
                },
                "model_name": "row-model",
            },
            {
                "id": "msg-2",
                "meta": {"question_id": "S1Q1", "key_points": ["later"]},
                "model_name": "row-model-2",
            },
        ]

        async def _fake_generate(*_args, **_kwargs):
            return "AI summary", "summary-model"

        with patch.object(qa_digests, "generate_answer_summary", new=_fake_generate):
            digests = await qa_digests.build_qa_digests_from_messages(
                object(),
                rows,
                output_locale="en",
                project_settings={"llm": "settings"},
            )

        self.assertEqual(
            digests,
            [
                {
                    "question_id": "S1Q1",
                    "answer_summary": "AI summary",
                    "key_points": ["point one", "point two"],
                    "source_message_id": "msg-1",
                    "model": "summary-model",
                }
            ],
        )

    async def test_build_qa_digests_uses_row_model_when_summary_model_missing(self) -> None:
        rows = [
            {
                "id": "msg-1",
                "meta": {"question_id": "S1Q1", "rolling_summary": "User summary"},
                "model_name": "row-model",
            }
        ]

        async def _fake_generate(*_args, **_kwargs):
            return "User summary", None

        with patch.object(qa_digests, "generate_answer_summary", new=_fake_generate):
            digests = await qa_digests.build_qa_digests_from_messages(
                object(),
                rows,
                output_locale="en",
            )

        self.assertEqual(digests[0]["model"], "row-model")


if __name__ == "__main__":
    unittest.main()
