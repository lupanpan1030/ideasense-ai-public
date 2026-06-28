import unittest

from app.core.report_sections import build_report_v2_sections
from app.services.answer_meta import (
    extract_answer_value_and_meta,
    set_answer_meta_entry,
)
from app.services.diagnostics import build_context_card
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths


class ProductionEvidenceMetadataTests(unittest.TestCase):
    def test_explicit_user_fact_metadata_becomes_confirmed_input(self) -> None:
        state_meta: dict = {}
        value, answer_meta = extract_answer_value_and_meta(
            {
                "value": 12,
                "source": "user",
                "resolution_status": "answered",
                "claim_type": "fact",
                "evidence_level": "E3",
                "note": "User supplied interview count.",
            }
        )

        set_answer_meta_entry(state_meta, "evidence.user_interview_count", **answer_meta)
        card = build_context_card(
            stage="problem",
            state_json={"evidence": {"user_interview_count": value}},
            state_meta=state_meta,
        )

        self.assertEqual(card["user_confirmed_inputs"][0]["path"], "evidence.user_interview_count")
        self.assertEqual(card["user_confirmed_inputs"][0]["evidence_level"], "E3")
        self.assertFalse(card["evidence_gaps"])

    def test_legacy_unknown_value_stays_unknown(self) -> None:
        state_meta: dict = {}
        value, answer_meta = extract_answer_value_and_meta(
            {"value": "Unknown", "source": "user"}
        )

        set_answer_meta_entry(
            state_meta,
            "market_strategy.business_model.payer_role",
            **answer_meta,
        )
        card = build_context_card(
            stage="market",
            state_json={
                "market_strategy": {
                    "business_model": {"payer_role": value}
                }
            },
            state_meta=state_meta,
        )

        self.assertEqual(card["unknowns"][0]["path"], "market_strategy.business_model.payer_role")
        self.assertEqual(card["unknowns"][0]["resolution_status"], "unknown")
        self.assertEqual(card["unknowns"][0]["evidence_level"], "E0")
        self.assertTrue(card["evidence_gaps"])

    def test_legacy_scalar_value_remains_low_evidence_hypothesis(self) -> None:
        value, answer_meta = extract_answer_value_and_meta("Campus pilots")

        self.assertEqual(value, "Campus pilots")
        self.assertEqual(answer_meta["resolution_status"], "answered")
        self.assertEqual(answer_meta["claim_type"], "hypothesis")
        self.assertEqual(answer_meta["evidence_level"], "E1")
        self.assertEqual(answer_meta["source"], "user")

    def test_pending_ai_suggestion_is_context_card_inference(self) -> None:
        card = build_context_card(
            stage="market",
            state_json={},
            state_meta={
                "pending_confirm": {
                    "market_strategy": {
                        "uvp": {
                            "one_line": {
                                "value": "AI-drafted UVP",
                                "source": "ai",
                            }
                        }
                    }
                }
            },
        )

        self.assertEqual(card["ai_inferences"][0]["path"], "market_strategy.uvp.one_line")
        self.assertTrue(card["ai_inferences"][0]["pending"])
        self.assertEqual(card["ai_inferences"][0]["evidence_level"], "E0")
        self.assertTrue(card["evidence_gaps"])

    def test_accepted_ai_suggestion_is_not_promoted_to_fact(self) -> None:
        state_meta: dict = {}
        value, answer_meta = extract_answer_value_and_meta(
            {
                "value": "AI-drafted UVP",
                "source": "ai",
            },
            default_source="mixed",
        )

        set_answer_meta_entry(
            state_meta,
            "market_strategy.uvp.one_line",
            **answer_meta,
        )
        card = build_context_card(
            stage="market",
            state_json={
                "market_strategy": {"uvp": {"one_line": value}}
            },
            state_meta=state_meta,
        )

        self.assertEqual(card["ai_inferences"][0]["path"], "market_strategy.uvp.one_line")
        self.assertFalse(card["user_confirmed_inputs"])
        self.assertEqual(card["ai_inferences"][0]["source"], "ai")

    def test_unknown_value_can_progress_but_remains_evidence_layer(self) -> None:
        state_meta: dict = {}
        value, answer_meta = extract_answer_value_and_meta("Unknown")
        set_answer_meta_entry(
            state_meta,
            "market_strategy.business_model.payer_role",
            **answer_meta,
        )
        state_json = {
            "market_strategy": {
                "business_model": {"payer_role": value}
            }
        }

        missing = filter_stage_blocking_missing_paths(
            "market",
            ["market_strategy.business_model.payer_role"],
            state_json=state_json,
            state_meta=state_meta,
        )
        card = build_context_card(
            stage="market",
            state_json=state_json,
            state_meta=state_meta,
        )

        self.assertEqual(missing, [])
        self.assertEqual(card["unknowns"][0]["path"], "market_strategy.business_model.payer_role")

    def test_report_v2_rebuilds_evidence_index_from_context_cards(self) -> None:
        context_card = build_context_card(
            stage="market",
            state_json={
                "market_strategy": {
                    "business_model": {"payer_role": "Unknown"}
                }
            },
            state_meta={
                "answer_meta": {
                    "market_strategy.business_model.payer_role": {
                        "resolution_status": "unknown",
                        "claim_type": "hypothesis",
                        "evidence_level": "E0",
                        "source": "user",
                    }
                }
            },
        )

        artifact = build_report_v2_sections(
            {
                "assessments": [
                    {
                        "stage": "market",
                        "context_card": context_card,
                    }
                ],
                "dvf_scoreboard": {"total_score": 42},
                "dvf_confidence": {"level": "low"},
                "evidence_index": {
                    "counts": {"user_confirmed_inputs": 999},
                    "items": [{"label": "bogus prompt evidence"}],
                },
            }
        )

        self.assertEqual(artifact["evidence_index"]["counts"]["unknowns"], 1)
        self.assertEqual(
            artifact["evidence_index"]["counts"]["user_confirmed_inputs"],
            0,
        )
        evidence_text = str(artifact["evidence_index"]).lower()
        self.assertNotIn("bogus prompt evidence", evidence_text)


if __name__ == "__main__":
    unittest.main()
