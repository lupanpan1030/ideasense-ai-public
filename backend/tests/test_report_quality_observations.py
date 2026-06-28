import unittest
from unittest.mock import AsyncMock, patch

from app.services.report_quality_observations import (
    build_report_quality_observation_record,
    upsert_report_quality_observation,
)
from app.services import report_generation_worker_handler as report_worker


def _base_report() -> dict:
    return {
        "artifact_schema_version": "report_v2",
        "dvf_scoreboard": {
            "desirability": 84,
            "viability": 76,
            "feasibility": 80,
            "total_score": 80,
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
                "evidence_references": [
                    {"path": "market_strategy.business_model.payer_role"}
                ],
                "evidence_gaps": [],
            },
            "feasibility": {
                "score": 80,
                "confidence": 0.78,
                "rationale": "MVP scope and architecture are explicit.",
                "evidence_references": [
                    {"path": "tech_execution.product_scope.mvp_definition"}
                ],
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


class ReportQualityObservationRecordTests(unittest.TestCase):
    def test_build_record_compacts_safe_observation(self) -> None:
        report = _base_report()
        report["raw_prompt"] = "never persist this"
        report["provider_key"] = "never persist this"
        report["content_json"] = {"raw_user_answer": "never persist this"}

        record = build_report_quality_observation_record(
            report,
            org_id="2c59666d-e746-4c1a-863f-2f3d80a4ef3b",
            project_id="bb60d1dc-375f-4c63-b1f8-204a54de4a00",
            project_title="  Validation Tool  ",
            report_id="fb0e0c53-92ab-482e-bc78-11a3d88f688e",
            report_version=1,
            generated_from_state_version=6,
        )

        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["project_title"], "Validation Tool")
        self.assertEqual(record["failed_invariants_json"], [])
        self.assertEqual(record["score_snapshot_json"]["total_score"], 80.0)
        self.assertEqual(
            record["evidence_counts_json"]["user_confirmed_inputs"],
            6,
        )
        self.assertFalse(_contains_key(record["observation_json"], "raw_prompt"))
        self.assertFalse(_contains_key(record["observation_json"], "provider_key"))
        self.assertFalse(_contains_key(record["observation_json"], "content_json"))

    def test_build_record_preserves_failed_invariant_ids(self) -> None:
        report = _base_report()
        report["score_rationales"]["viability"].pop("confidence")

        record = build_report_quality_observation_record(
            report,
            org_id="2c59666d-e746-4c1a-863f-2f3d80a4ef3b",
            project_id="bb60d1dc-375f-4c63-b1f8-204a54de4a00",
            report_id="fb0e0c53-92ab-482e-bc78-11a3d88f688e",
            report_version=1,
            generated_from_state_version=6,
        )

        self.assertEqual(record["status"], "fail")
        self.assertIn("score_rationales_complete", record["failed_invariants_json"])


class ReportQualityObservationSqlTests(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_uses_report_state_conflict_key(self) -> None:
        session = _CaptureSession()
        record = build_report_quality_observation_record(
            _base_report(),
            org_id="2c59666d-e746-4c1a-863f-2f3d80a4ef3b",
            project_id="bb60d1dc-375f-4c63-b1f8-204a54de4a00",
            report_id="fb0e0c53-92ab-482e-bc78-11a3d88f688e",
            report_version=1,
            generated_from_state_version=6,
        )

        row = await upsert_report_quality_observation(session, record)

        self.assertEqual(row["id"], "observation-1")
        self.assertIn(
            "ON CONFLICT (report_id, generated_from_state_version)",
            session.statements[0],
        )
        self.assertEqual(session.params[0]["status"], "pass")
        self.assertEqual(session.params[0]["generated_from_state_version"], 6)


class WorkerReportQualityObservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_helper_swallows_observation_failure(self) -> None:
        session = _CaptureSession()
        context = {
            "org_id": "2c59666d-e746-4c1a-863f-2f3d80a4ef3b",
            "project_id": "bb60d1dc-375f-4c63-b1f8-204a54de4a00",
            "project_title": "Validation Tool",
            "report_id": "fb0e0c53-92ab-482e-bc78-11a3d88f688e",
            "report_version": 1,
            "generated_from_state_version": 6,
            "report_payload": _base_report(),
            "actor_user_id": "50f0e2a1-9a8c-42dc-8c57-16106053fe4a",
            "generator_model": "unit-test-model",
        }

        with patch.object(
            report_worker,
            "persist_report_quality_observation",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            await report_worker._persist_report_quality_observation_safely(
                session,
                context,
            )

        self.assertEqual(session.begin_count, 1)
        self.assertGreaterEqual(len(session.statements), 3)


class _CaptureSession:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.params: list[dict] = []
        self.begin_count = 0

    def begin(self) -> "_AsyncBegin":
        self.begin_count += 1
        return _AsyncBegin()

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.statements.append(str(statement))
        self.params.append(params or {})
        return _Result({"id": "observation-1"})


class _AsyncBegin:
    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False


class _Result:
    def __init__(self, row: dict) -> None:
        self._row = row

    def mappings(self) -> "_Result":
        return self

    def first(self) -> dict:
        return self._row


def _contains_key(value, key: str) -> bool:  # type: ignore[no-untyped-def]
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
