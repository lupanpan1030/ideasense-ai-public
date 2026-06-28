import unittest

from app.services.answer_extraction_worker_handler import _apply_extraction_fallbacks
from app.services.report_generation_worker_handler import _commit_if_transaction_open


class CommitIfTransactionOpenTests(unittest.IsolatedAsyncioTestCase):
    async def test_commits_when_transaction_is_open(self) -> None:
        session = _FakeSession(in_transaction=True)

        await _commit_if_transaction_open(session)

        self.assertEqual(session.commit_count, 1)

    async def test_skips_commit_when_transaction_is_not_open(self) -> None:
        session = _FakeSession(in_transaction=False)

        await _commit_if_transaction_open(session)

        self.assertEqual(session.commit_count, 0)


class ExtractionFallbackTests(unittest.TestCase):
    def test_single_schema_path_falls_back_to_answer(self) -> None:
        result = _apply_extraction_fallbacks(
            ["market_strategy.uvp.one_line"],
            {},
            "This is the clearest validation brief for early-stage teams.",
        )

        self.assertEqual(
            result,
            {
                "market_strategy.uvp.one_line": (
                    "This is the clearest validation brief for early-stage teams."
                )
            },
        )

    def test_single_schema_path_does_not_fallback_for_explicit_none(self) -> None:
        result = _apply_extraction_fallbacks(
            ["evidence.data_evidence"],
            {},
            "None yet",
        )

        self.assertEqual(result, {})


class _FakeSession:
    def __init__(self, *, in_transaction: bool) -> None:
        self._in_transaction = in_transaction
        self.commit_count = 0

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def commit(self) -> None:
        self.commit_count += 1


if __name__ == "__main__":
    unittest.main()
