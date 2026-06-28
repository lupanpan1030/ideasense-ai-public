import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from app.services.assessment_quality_observability import (
    build_assessment_quality_observation,
    build_observation_from_artifact_dir,
    load_canonical_cases,
    write_observation_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export-production-smoke-db.py"


def _load_export_script():
    spec = importlib.util.spec_from_file_location(
        "export_production_smoke_db",
        EXPORT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load export-production-smoke-db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_report() -> dict:
    return {
        "project_id": "bb60d1dc-375f-4c63-b1f8-204a54de4a00",
        "report_id": "fb0e0c53-92ab-482e-bc78-11a3d88f688e",
        "report_version": 1,
        "status": "final",
        "artifact_schema_version": "report_v2",
        "dvf_scoreboard": {
            "desirability": 84,
            "viability": 76,
            "feasibility": 80,
            "total_score": 80,
            "decision_band": "go",
        },
        "decision_snapshot": {
            "verdict": "go",
            "total_score": 80,
            "confidence": "high",
            "rationale": "Strong evidence supports a focused validation tool.",
            "top_findings": ["12 users named the same validation problem."],
            "top_gaps": [],
            "next_action": "Run a pricing pilot.",
        },
        "score_rationales": {
            "desirability": {
                "score": 84,
                "confidence": 0.82,
                "rationale": "A clear segment and repeated pain are present.",
                "evidence_references": [{"path": "evidence.user_interview_count"}],
                "evidence_gaps": [],
            },
            "viability": {
                "score": 76,
                "confidence": 0.72,
                "rationale": "Buyer and pilot channel are named.",
                "evidence_references": [{"path": "market_strategy.business_model.payer_role"}],
                "evidence_gaps": [],
            },
            "feasibility": {
                "score": 80,
                "confidence": 0.78,
                "rationale": "MVP scope and architecture are explicit.",
                "evidence_references": [{"path": "tech_execution.product_scope.mvp_definition"}],
                "evidence_gaps": [],
            },
        },
        "risk_register": [{"risk": "Pilot conversion may be weak."}],
        "experiment_plan": [{"action": "Run a pricing pilot."}],
        "evidence_index": {
            "counts": {
                "user_confirmed_inputs": 6,
                "founder_assumptions": 0,
                "ai_inferences": 0,
                "unknowns": 0,
                "evidence_gaps": 0,
                "verification_summary": 1,
            },
            "items": [
                {
                    "stage": "problem",
                    "layer": "user_confirmed_inputs",
                    "path": "evidence.user_interview_count",
                    "label": "User interview count",
                    "evidence_level": "E3",
                }
            ],
        },
    }


class AssessmentQualityObservabilityTests(unittest.TestCase):
    def test_observation_matches_canonical_strong_case(self) -> None:
        observation = build_assessment_quality_observation(
            _base_report(),
            canonical_fixture=load_canonical_cases(),
        )

        self.assertEqual(
            observation["artifact_schema_version"],
            "assessment_quality_observation_v1",
        )
        self.assertEqual(observation["summary"]["status"], "pass")
        self.assertTrue(
            observation["canonical_boundaries"]["within_any_score_boundary"]
        )
        matched_ids = {
            item["id"]
            for item in observation["canonical_boundaries"]["matched_cases"]
        }
        self.assertIn("strong_founder_validation_tool", matched_ids)
        self.assertEqual(
            observation["dimensions"]["desirability"]["evidence_reference_count"],
            1,
        )

    def test_observation_reports_nearest_case_outside_boundary(self) -> None:
        report = _base_report()
        report["dvf_scoreboard"] = {
            "desirability": 99,
            "viability": 99,
            "feasibility": 99,
            "total_score": 99,
        }
        for rationale in report["score_rationales"].values():
            rationale["score"] = 99
        report["decision_snapshot"]["total_score"] = 99

        observation = build_assessment_quality_observation(
            report,
            canonical_fixture=load_canonical_cases(),
        )

        self.assertEqual(observation["summary"]["status"], "warn")
        self.assertFalse(
            observation["canonical_boundaries"]["within_any_score_boundary"]
        )
        self.assertIsNotNone(
            observation["canonical_boundaries"]["nearest_case"]["id"]
        )

    def test_strict_canonical_match_can_fail(self) -> None:
        report = _base_report()
        report["decision_snapshot"]["total_score"] = 99
        report["dvf_scoreboard"]["total_score"] = 99

        observation = build_assessment_quality_observation(
            report,
            canonical_fixture=load_canonical_cases(),
            require_canonical_match=True,
        )

        self.assertEqual(observation["summary"]["status"], "fail")
        failed = {item["id"] for item in observation["invariants"] if item["status"] == "fail"}
        self.assertIn("canonical_score_boundary", failed)

    def test_source_layer_promotion_is_flagged(self) -> None:
        report = _base_report()
        report["decision_snapshot"]["confidence"] = "low"
        report["decision_snapshot"]["top_gaps"] = ["Buyer still needs validation."]
        report["evidence_index"]["counts"].update(
            {"user_confirmed_inputs": 1, "ai_inferences": 1, "evidence_gaps": 1}
        )
        report["evidence_index"]["items"] = [
            {
                "stage": "market",
                "layer": "ai_inferences",
                "path": "market_strategy.uvp.one_line",
                "label": "AI suggested UVP",
                "pending": True,
            },
            {
                "stage": "market",
                "layer": "user_confirmed_inputs",
                "path": "market_strategy.uvp.one_line",
                "label": "AI suggested UVP",
            },
        ]

        observation = build_assessment_quality_observation(
            report,
            canonical_fixture=load_canonical_cases(),
        )

        self.assertEqual(observation["summary"]["status"], "fail")
        failed = {item["id"] for item in observation["invariants"] if item["status"] == "fail"}
        self.assertIn("source_layers_not_promoted", failed)
        self.assertEqual(
            observation["evidence"]["promoted_paths"],
            ["market_strategy.uvp.one_line"],
        )

    def test_missing_dimension_confidence_is_flagged(self) -> None:
        report = _base_report()
        report["score_rationales"]["viability"].pop("confidence")

        observation = build_assessment_quality_observation(
            report,
            canonical_fixture=load_canonical_cases(),
        )

        self.assertEqual(observation["summary"]["status"], "fail")
        failed = {item["id"] for item in observation["invariants"] if item["status"] == "fail"}
        self.assertIn("score_rationales_complete", failed)

    def test_artifact_dir_can_use_db_report_v2_export(self) -> None:
        report = _base_report()
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_dir = Path(temp_dir)
            (artifact_dir / "db-report-v2.json").write_text(
                json.dumps(
                    {
                        "artifact_schema_version": "production_report_v2_export_v1",
                        "latest_report": report,
                    }
                ),
                encoding="utf-8",
            )

            observation = build_observation_from_artifact_dir(
                artifact_dir,
                canonical_fixture_path=None,
            )
            written = write_observation_artifact(artifact_dir)

            self.assertEqual(observation["source"]["report_source"], "db-report-v2.json")
            self.assertEqual(written["summary"]["status"], "pass")
            self.assertTrue((artifact_dir / "assessment-quality-observation.json").exists())

    def test_artifact_dir_merges_report_api_with_db_report_identity(self) -> None:
        report = _base_report()
        api_payload = dict(report)
        api_payload.pop("report_id")
        api_payload.pop("report_version")
        api_payload.pop("status")
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_dir = Path(temp_dir)
            (artifact_dir / "report-api.json").write_text(
                json.dumps(api_payload),
                encoding="utf-8",
            )
            (artifact_dir / "db-report-v2.json").write_text(
                json.dumps(
                    {
                        "artifact_schema_version": "production_report_v2_export_v1",
                        "latest_report": report,
                    }
                ),
                encoding="utf-8",
            )

            observation = build_observation_from_artifact_dir(artifact_dir)

            self.assertEqual(
                observation["source"]["report_source"],
                "report-api.json+db-report-v2.json",
            )
            self.assertEqual(observation["report"]["report_id"], report["report_id"])
            self.assertEqual(
                observation["report"]["report_version"],
                report["report_version"],
            )

    def test_export_script_writes_safe_report_v2_json(self) -> None:
        export_script = _load_export_script()
        report = _base_report()
        report_row = {
            "id": report["report_id"],
            "project_id": report["project_id"],
            "org_id": "org-1",
            "report_version": report["report_version"],
            "status": report["status"],
            "generated_from_state_version": 6,
            "artifact_schema_version": "report_v2",
            "decision_snapshot_json": report["decision_snapshot"],
            "score_rationales_json": report["score_rationales"],
            "risk_register_json": report["risk_register"],
            "experiment_plan_json": report["experiment_plan"],
            "evidence_index_json": report["evidence_index"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_dir = Path(temp_dir)
            count = export_script._write_report_v2_export(artifact_dir, [report_row])

            self.assertEqual(count, 1)
            observation = build_observation_from_artifact_dir(artifact_dir)

            self.assertEqual(observation["summary"]["status"], "pass")
            self.assertEqual(
                observation["source"]["report_source"],
                "db-report-v2.json",
            )


if __name__ == "__main__":
    unittest.main()
