import json
import unittest
from pathlib import Path
from typing import Any, Mapping

from app.core.report_sections import build_report_v2_sections
from app.services.diagnostics import (
    build_context_card,
    build_report_diagnosis,
    build_validation_plan,
)
from app.services.prompt_output_parsers import parse_final_report_payload


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "assessment_quality_cases.json"
)

EVIDENCE_LAYERS = (
    "user_confirmed_inputs",
    "founder_assumptions",
    "ai_inferences",
    "unknowns",
    "evidence_gaps",
)


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def _case_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).lower()


def _build_case_artifact(
    case: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    assessments: list[dict[str, Any]] = []
    for stage in ("problem", "market", "tech"):
        stage_input = case["stages"][stage]
        card = build_context_card(
            stage=stage,
            state_json=stage_input.get("state_json"),
            state_meta=stage_input.get("state_meta"),
            missing_paths=stage_input.get("missing_paths") or [],
            verification_summary=stage_input.get("verification_summary"),
        )
        plan = build_validation_plan(
            stage=stage,
            context_card=card,
            key_risks=case.get("key_risks") or [],
        )
        assessments.append(
            {
                "stage": stage,
                "summary_text": stage_input.get("summary"),
                "context_card": card,
                "validation_plan": plan,
            }
        )

    diagnosis = build_report_diagnosis(
        assessments=assessments,
        dvf_confidence=case.get("dvf_confidence") or {},
        key_risks=case.get("key_risks") or [],
    )
    report_payload = {
        "project": case.get("project") or {},
        "assessments": assessments,
        "diagnosis": diagnosis,
        "dvf_confidence": case.get("dvf_confidence") or {},
        "dvf_scoreboard": case["dvf"]["scoreboard"],
        "dvf_assessment": case["dvf"]["assessment"],
        "key_risks": case.get("key_risks") or [],
        "validation_plan": case.get("validation_plan") or [],
    }
    return build_report_v2_sections(report_payload), report_payload, assessments


def _expected_evidence_counts(assessments: list[dict[str, Any]]) -> dict[str, int]:
    counts = {layer: 0 for layer in EVIDENCE_LAYERS}
    verification_count = 0
    for assessment in assessments:
        card = assessment["context_card"]
        for layer in EVIDENCE_LAYERS:
            values = card.get(layer)
            if isinstance(values, list):
                counts[layer] += len(values)
        summary = card.get("verification_summary")
        if isinstance(summary, Mapping):
            items = summary.get("items")
            if isinstance(items, list):
                verification_count += len(items)
    if verification_count:
        counts["verification_summary"] = verification_count
    return counts


def _find_evidence_item(
    artifact: Mapping[str, Any],
    *,
    path: str,
    layer: str,
) -> dict[str, Any] | None:
    evidence_index = artifact.get("evidence_index")
    if not isinstance(evidence_index, Mapping):
        return None
    items = evidence_index.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, Mapping):
            continue
        if item.get("path") == path and item.get("layer") == layer:
            return dict(item)
    return None


class AssessmentQualityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = _load_fixture()
        cls.cases = cls.fixture["cases"]

    def test_fixture_set_covers_canonical_quality_cases(self) -> None:
        self.assertEqual(self.fixture["version"], "assessment-quality-regression-v1")
        self.assertGreaterEqual(len(self.cases), 5)
        self.assertLessEqual(len(self.cases), 8)

        covered_categories = {
            category
            for case in self.cases
            for category in case.get("categories", [])
        }
        self.assertTrue(
            {
                "strong",
                "weak",
                "evidence_thin",
                "technically_strong_market_weak",
                "non_technical_founder",
                "complex_dependency",
                "unknown_heavy",
                "contradiction_prone",
                "pending_confirm",
                "externally_contradicted",
            }.issubset(covered_categories)
        )

    def test_fixture_expectations_are_complete(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["id"]):
                expectations = case.get("expectations")
                self.assertIsInstance(expectations, dict)
                for key in (
                    "score_ranges",
                    "decision_confidence",
                    "min_evidence_counts",
                    "forbidden_claims",
                    "required_gap_terms",
                    "required_action_terms",
                ):
                    self.assertIn(key, expectations, f"{case['id']} missing {key}")
                for dimension in (
                    "desirability",
                    "viability",
                    "feasibility",
                    "total_score",
                ):
                    self.assertIn(dimension, expectations["score_ranges"])

    def test_report_v2_quality_invariants_for_canonical_cases(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["id"]):
                artifact, _payload, assessments = _build_case_artifact(case)
                expectations = case["expectations"]

                self.assertEqual(artifact["artifact_schema_version"], "report_v2")
                self.assertEqual(
                    artifact["decision_snapshot"]["confidence"],
                    expectations["decision_confidence"],
                )

                self._assert_scores_in_expected_ranges(artifact, expectations)
                self._assert_evidence_counts_preserved(
                    artifact,
                    assessments,
                    expectations,
                )
                self._assert_report_v2_sections_are_complete(artifact)
                self._assert_required_terms(artifact, expectations)
                self._assert_forbidden_claims_absent(artifact, expectations)
                self._assert_source_layers(artifact, expectations)

    def test_final_report_parser_preserves_report_v2_fields(self) -> None:
        payload = {
            "artifact_schema_version": "report_v2",
            "overall_summary": "Use only the provided evidence.",
            "decision_snapshot": {
                "verdict": "hold",
                "total_score": 52,
                "confidence": "low",
                "top_gaps": ["Buyer is unknown"],
            },
            "score_rationales": {
                "viability": {
                    "score": 40,
                    "confidence": 0.3,
                    "evidence_gaps": ["Buyer is unknown"],
                }
            },
            "risk_register": [{"risk": "Buyer path is unproven."}],
            "experiment_plan": [{"action": "Run buyer interviews."}],
            "evidence_index": {
                "counts": {"unknowns": 1, "evidence_gaps": 1},
                "items": [
                    {
                        "stage": "market",
                        "layer": "unknowns",
                        "path": "market_strategy.business_model.payer_role",
                        "label": "Payer Role",
                    }
                ],
            },
        }

        parsed = parse_final_report_payload(json.dumps(payload))

        self.assertEqual(parsed["artifact_schema_version"], "report_v2")
        self.assertEqual(parsed["decision_snapshot"]["confidence"], "low")
        self.assertEqual(parsed["score_rationales"]["viability"]["score"], 40)
        self.assertEqual(parsed["evidence_index"]["counts"]["unknowns"], 1)
        self.assertEqual(parsed["risk_register"][0]["risk"], "Buyer path is unproven.")
        self.assertEqual(parsed["experiment_plan"][0]["action"], "Run buyer interviews.")

    def test_final_report_parser_rejects_truncated_second_object(self) -> None:
        payload = {
            "overall_summary": "Use only the provided evidence.",
            "decision_snapshot": {"verdict": "hold"},
        }

        with self.assertRaisesRegex(ValueError, "invalid final report payload"):
            parse_final_report_payload(
                f"{json.dumps(payload)} "
                '{"overall_summary": "silently accepted tail"'
            )

    def _assert_scores_in_expected_ranges(
        self,
        artifact: Mapping[str, Any],
        expectations: Mapping[str, Any],
    ) -> None:
        ranges = expectations["score_ranges"]
        snapshot = artifact["decision_snapshot"]
        self._assert_value_in_range(snapshot["total_score"], ranges["total_score"])

        rationales = artifact["score_rationales"]
        max_confidence = expectations.get("max_dimension_confidence")
        for dimension in ("desirability", "viability", "feasibility"):
            rationale = rationales[dimension]
            self._assert_value_in_range(rationale["score"], ranges[dimension])
            self.assertIn("confidence", rationale)
            if max_confidence is not None and rationale["confidence"] is not None:
                self.assertLessEqual(rationale["confidence"], max_confidence)

    def _assert_evidence_counts_preserved(
        self,
        artifact: Mapping[str, Any],
        assessments: list[dict[str, Any]],
        expectations: Mapping[str, Any],
    ) -> None:
        evidence_index = artifact["evidence_index"]
        actual_counts = evidence_index["counts"]
        expected_counts = _expected_evidence_counts(assessments)
        for layer, expected_count in expected_counts.items():
            self.assertEqual(
                actual_counts.get(layer, 0),
                expected_count,
                f"Unexpected evidence count for {layer}",
            )
        for layer, minimum_count in expectations["min_evidence_counts"].items():
            self.assertGreaterEqual(
                actual_counts.get(layer, 0),
                minimum_count,
                f"Expected at least {minimum_count} {layer}",
            )

    def _assert_report_v2_sections_are_complete(self, artifact: Mapping[str, Any]) -> None:
        snapshot = artifact["decision_snapshot"]
        self.assertIn("top_gaps", snapshot)
        self.assertIsInstance(snapshot["top_gaps"], list)

        for dimension in ("desirability", "viability", "feasibility"):
            rationale = artifact["score_rationales"][dimension]
            self.assertIn("score", rationale)
            self.assertIn("confidence", rationale)
            self.assertIn("rationale", rationale)
            self.assertIn("evidence_references", rationale)
            self.assertIn("evidence_gaps", rationale)
            self.assertTrue(
                rationale["evidence_references"] or rationale["evidence_gaps"],
                f"{dimension} lacks both evidence references and gaps",
            )

        self.assertIsInstance(artifact["risk_register"], list)
        self.assertTrue(artifact["risk_register"])
        self.assertIsInstance(artifact["experiment_plan"], list)
        self.assertTrue(artifact["experiment_plan"])

    def _assert_required_terms(
        self,
        artifact: Mapping[str, Any],
        expectations: Mapping[str, Any],
    ) -> None:
        gap_text = _case_text(
            {
                "top_gaps": artifact["decision_snapshot"].get("top_gaps"),
                "score_rationales": artifact["score_rationales"],
                "evidence_index": artifact["evidence_index"],
                "risk_register": artifact["risk_register"],
            }
        )
        for term in expectations.get("required_gap_terms", []):
            self.assertIn(term.lower(), gap_text)

        action_text = _case_text(
            {
                "next_action": artifact["decision_snapshot"].get("next_action"),
                "experiment_plan": artifact["experiment_plan"],
            }
        )
        for term in expectations.get("required_action_terms", []):
            self.assertIn(term.lower(), action_text)

    def _assert_forbidden_claims_absent(
        self,
        artifact: Mapping[str, Any],
        expectations: Mapping[str, Any],
    ) -> None:
        artifact_text = _case_text(artifact)
        for claim in expectations.get("forbidden_claims", []):
            self.assertNotIn(claim.lower(), artifact_text)

    def _assert_source_layers(
        self,
        artifact: Mapping[str, Any],
        expectations: Mapping[str, Any],
    ) -> None:
        for expected in expectations.get("required_source_layers", []):
            item = _find_evidence_item(
                artifact,
                path=expected["path"],
                layer=expected["layer"],
            )
            self.assertIsNotNone(item, f"Missing evidence item {expected}")
            for key in ("resolution_status", "claim_type", "evidence_level"):
                if key in expected:
                    self.assertEqual(item.get(key), expected[key])

        for path in expectations.get("required_pending_paths", []):
            item = _find_evidence_item(artifact, path=path, layer="ai_inferences")
            self.assertIsNotNone(item, f"Missing pending AI inference for {path}")
            self.assertTrue(item.get("pending"))
            self.assertIsNone(
                _find_evidence_item(
                    artifact,
                    path=path,
                    layer="user_confirmed_inputs",
                ),
                f"Pending suggestion {path} was promoted to confirmed input",
            )

        verification_text = _case_text(artifact["evidence_index"])
        for verdict in expectations.get("required_verification_verdicts", []):
            self.assertIn(verdict.lower(), verification_text)

    def _assert_value_in_range(self, value: Any, expected_range: list[int]) -> None:
        self.assertIsInstance(value, (int, float))
        self.assertGreaterEqual(value, expected_range[0])
        self.assertLessEqual(value, expected_range[1])


if __name__ == "__main__":
    unittest.main()
