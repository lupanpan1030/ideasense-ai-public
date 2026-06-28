import unittest

from app.services.verification.question_instances import (
    is_verifiable_question_instance,
)


class VerifiableQuestionInstanceTests(unittest.TestCase):
    def test_answered_question_with_final_answer_is_verifiable(self) -> None:
        self.assertTrue(
            is_verifiable_question_instance(
                "answered",
                "Finance teams still close the books manually.",
            )
        )

    def test_skipped_question_is_not_verifiable(self) -> None:
        self.assertFalse(
            is_verifiable_question_instance(
                "skipped",
                "我不确定",
            )
        )

    def test_blank_final_answer_is_not_verifiable(self) -> None:
        self.assertFalse(is_verifiable_question_instance("answered", "   "))


if __name__ == "__main__":
    unittest.main()
