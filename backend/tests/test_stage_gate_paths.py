import unittest

from app.services.stage_gate_paths import (
    filter_stage_blocking_missing_paths,
    resolve_stage_blocking_paths,
    stage_allows_awaiting_confirm,
)


class ResolveStageBlockingPathsTests(unittest.TestCase):
    def test_resolve_stage_blocking_paths_keeps_only_anchor_paths(self) -> None:
        available_paths = [
            "problem_user.idea.raw",
            "problem.one_line",
            "target_user.core",
            "problem.scenarios[]",
            "problem.severity_score",
            "alternatives.current_solutions[]",
            "evidence.key_unknowns[]",
        ]

        self.assertEqual(
            resolve_stage_blocking_paths("problem", available_paths),
            [
                "problem.one_line",
                "target_user.core",
                "problem.scenarios[]",
                "alternatives.current_solutions[]",
                "evidence.key_unknowns[]",
            ],
        )

    def test_resolve_stage_blocking_paths_falls_back_when_no_anchor_matches(self) -> None:
        self.assertEqual(
            resolve_stage_blocking_paths(
                "tech",
                ["tech_execution.meta.mode"],
            ),
            ["tech_execution.meta.mode"],
        )


class FilterStageBlockingMissingPathsTests(unittest.TestCase):
    def test_filter_stage_blocking_missing_paths_drops_supporting_paths(self) -> None:
        missing_paths = [
            "market_strategy.uvp.one_line",
            "market_strategy.business_model.revenue_model",
            "market_strategy.unit_economics.cac_hypothesis",
        ]

        self.assertEqual(
            filter_stage_blocking_missing_paths(
                "market",
                missing_paths,
                state_json={},
                state_meta={},
            ),
            [
                "market_strategy.uvp.one_line",
                "market_strategy.business_model.revenue_model",
            ],
        )

    def test_filter_stage_blocking_missing_paths_resolves_by_state_value(self) -> None:
        missing_paths = [
            "problem.one_line",
            "target_user.core",
            "problem.scenarios[]",
        ]
        state_json = {
            "problem": {"one_line": "Manual reporting is slow."},
            "target_user": {"core": "Finance managers in SMBs"},
        }

        self.assertEqual(
            filter_stage_blocking_missing_paths(
                "problem",
                missing_paths,
                state_json=state_json,
                state_meta={},
            ),
            ["problem.scenarios[]"],
        )

    def test_filter_stage_blocking_missing_paths_resolves_not_applicable_only(self) -> None:
        missing_paths = [
            "market_strategy.business_model.payer_role",
            "market_strategy.business_model.revenue_model",
        ]
        state_meta = {
            "answer_meta": {
                "market_strategy.business_model.payer_role": {
                    "resolution_status": "not_applicable",
                    "claim_type": "fact",
                    "evidence_level": "E0",
                    "source": "user",
                    "updated_at": "2026-04-04T12:00:00Z",
                },
                "market_strategy.business_model.revenue_model": {
                    "resolution_status": "unknown",
                    "claim_type": "hypothesis",
                    "evidence_level": "E0",
                    "source": "user",
                    "updated_at": "2026-04-04T12:00:00Z",
                },
            }
        }

        self.assertEqual(
            filter_stage_blocking_missing_paths(
                "market",
                missing_paths,
                state_json={},
                state_meta=state_meta,
            ),
            ["market_strategy.business_model.revenue_model"],
        )


class StageAllowsAwaitingConfirmTests(unittest.TestCase):
    def test_stage_allows_awaiting_confirm_blocks_router_only(self) -> None:
        self.assertFalse(stage_allows_awaiting_confirm("tech", "router"))
        self.assertTrue(stage_allows_awaiting_confirm("tech", "lite"))
        self.assertTrue(stage_allows_awaiting_confirm("problem", "default"))


if __name__ == "__main__":
    unittest.main()
