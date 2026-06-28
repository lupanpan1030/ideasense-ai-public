import sys
import types
import unittest
from uuid import uuid4


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.api.routes import assessments  # noqa: E402
from app.services import stage_payloads  # noqa: E402
from app.services.stage_transition import next_stage_starts_in_review  # noqa: E402


class _FakeResult:
    def __init__(self, row: dict) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict:
        return self._row


class _FakeSession:
    def __init__(self, row: dict) -> None:
        self._row = row

    async def execute(self, *_args, **_kwargs) -> _FakeResult:
        return _FakeResult(self._row)


class BuildStagePayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_stage_payload_keeps_non_blocking_stage_paths(self) -> None:
        session = _FakeSession(
            {
                "paths": [
                    "market_strategy.uvp.one_line",
                    "market_strategy.unit_economics.cac_hypothesis",
                ]
            }
        )
        state_json = {
            "market_strategy": {
                "uvp": {"one_line": "Cut finance ops time in half."},
                "unit_economics": {"cac_hypothesis": "Acquire via partner channels."},
            }
        }
        state_meta = {
            "ai_assisted_paths": {
                "market": ["market_strategy.uvp.one_line"],
            }
        }

        payload = await stage_payloads.build_stage_payload(
            session,
            uuid4(),
            "market",
            "default",
            state_json,
            state_meta,
        )

        self.assertEqual(
            payload["data"]["market_strategy"]["uvp"]["one_line"],
            "Cut finance ops time in half.",
        )
        self.assertEqual(
            payload["data"]["market_strategy"]["unit_economics"]["cac_hypothesis"],
            "Acquire via partner channels.",
        )
        self.assertEqual(
            payload["ai_assisted_paths"],
            ["market_strategy.uvp.one_line"],
        )

    def test_normalize_stage_path_maps_drops_invalid_entries(self) -> None:
        state_meta = {
            "ai_assisted_paths": {
                " Market ": [" target_user.core ", None, ""],
                "": ["ignored"],
                "problem": "ignored",
            },
            "user_edited_paths": {
                "tech": ["tech_solution.stack", 123],
            },
        }

        self.assertEqual(
            stage_payloads.normalize_ai_assisted_map(state_meta),
            {"market": [" target_user.core "]},
        )
        self.assertEqual(
            stage_payloads.normalize_user_edited_map(state_meta),
            {"tech": ["tech_solution.stack"]},
        )


class NextStageReviewTests(unittest.TestCase):
    def test_next_stage_starts_in_review_only_for_awaiting_confirm_non_report(self) -> None:
        self.assertTrue(
            next_stage_starts_in_review("market", "awaiting_confirm")
        )
        self.assertFalse(next_stage_starts_in_review("market", "in_progress"))
        self.assertFalse(
            next_stage_starts_in_review("report", "awaiting_confirm")
        )


if __name__ == "__main__":
    unittest.main()
