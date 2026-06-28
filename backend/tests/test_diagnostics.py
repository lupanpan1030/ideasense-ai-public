import unittest

from app.services.diagnostics import (
    build_context_card,
    build_report_diagnosis,
    build_validation_plan,
    summarize_verification_payload,
)


class ContextCardTests(unittest.TestCase):
    def test_build_context_card_layers_confirmed_assumptions_ai_and_unknowns(self) -> None:
        card = build_context_card(
            stage="market",
            state_json={
                "market_strategy": {
                    "channels": ["Campus portal"],
                    "pricing": "Likely $49/month",
                    "buyer": "Unknown",
                }
            },
            state_meta={
                "answer_meta": {
                    "market_strategy.channels": {
                        "resolution_status": "answered",
                        "claim_type": "fact",
                        "evidence_level": "E2",
                        "source": "user",
                        "updated_at": "2026-04-04T12:00:00Z",
                    },
                    "market_strategy.pricing": {
                        "resolution_status": "answered",
                        "claim_type": "estimate",
                        "evidence_level": "E1",
                        "source": "user",
                        "updated_at": "2026-04-04T12:00:00Z",
                    },
                    "market_strategy.buyer": {
                        "resolution_status": "unknown",
                        "claim_type": "hypothesis",
                        "evidence_level": "E0",
                        "source": "user",
                        "updated_at": "2026-04-04T12:00:00Z",
                    },
                },
                "pending_confirm": {
                    "market_strategy": {
                        "positioning": {
                            "value": "Most reliable campus shuttle companion",
                            "source": "ai",
                        }
                    }
                },
            },
            missing_paths=["market_strategy.competition"],
            verification_summary={
                "status": "checked",
                "supported_claims": 1,
                "unsupported_claims": 0,
                "uncertain_claims": 1,
                "items": [],
            },
        )

        self.assertEqual(card["stage"], "market")
        self.assertEqual(card["user_confirmed_inputs"][0]["path"], "market_strategy.channels")
        self.assertEqual(card["founder_assumptions"][0]["path"], "market_strategy.pricing")
        self.assertTrue(
            any(item["path"] == "market_strategy.positioning" for item in card["ai_inferences"])
        )
        self.assertTrue(
            any(item["path"] == "market_strategy.buyer" for item in card["unknowns"])
        )
        self.assertTrue(
            any(item["path"] == "market_strategy.competition" for item in card["unknowns"])
        )
        self.assertGreaterEqual(len(card["evidence_gaps"]), 2)
        self.assertEqual(card["verification_summary"]["supported_claims"], 1)

    def test_build_validation_plan_returns_short_cycle_actions(self) -> None:
        card = build_context_card(
            stage="problem",
            state_json={"problem": {"one_line": "Missed shuttles"}},
            state_meta={},
            missing_paths=["problem.severity"],
        )

        plan = build_validation_plan(stage="problem", context_card=card)

        self.assertGreaterEqual(len(plan), 3)
        self.assertLessEqual(len(plan), 5)
        self.assertTrue(all(item.get("action") for item in plan))
        self.assertTrue(all(item.get("success_signal") for item in plan))

    def test_report_diagnosis_aggregates_stage_cards(self) -> None:
        card = build_context_card(
            stage="tech",
            state_json={"tech_execution": {"mvp": "Live map"}},
            state_meta={},
        )
        plan = build_validation_plan(stage="tech", context_card=card)

        diagnosis = build_report_diagnosis(
            assessments=[
                {
                    "stage": "tech",
                    "context_card": card,
                    "validation_plan": plan,
                }
            ],
            dvf_confidence={"coverage": 70},
            key_risks=[{"risk": "Feed quality", "severity": "High"}],
        )

        self.assertIn("tech", diagnosis["context_cards"])
        self.assertEqual(diagnosis["dvf_confidence"]["coverage"], 70)
        self.assertEqual(diagnosis["risk_register"][0]["risk"], "Feed quality")
        self.assertIn("tech", diagnosis["stage_validation_plans"])

    def test_summarize_verification_payload_handles_disabled(self) -> None:
        summary = summarize_verification_payload(None)

        self.assertEqual(summary["status"], "not_checked")
        self.assertEqual(summary["supported_claims"], 0)


if __name__ == "__main__":
    unittest.main()
