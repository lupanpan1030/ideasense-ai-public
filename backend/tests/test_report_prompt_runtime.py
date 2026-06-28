import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.core import report_builder  # noqa: E402
from app.core import report_recovery_sections  # noqa: E402
from app.core.report_sections import build_report_v2_sections  # noqa: E402
from app.services import report_generation_worker_handler as report_worker  # noqa: E402
from app.services import report_prompt_tasks  # noqa: E402
from app.services import stage_summary_worker_handler  # noqa: E402
from app.services.localization import output_language_label  # noqa: E402
from app.services.prompt_runtime import (  # noqa: E402
    DEFAULT_PROMPT_TASK_REGISTRY,
    PromptContextBuilder,
    render_prompt_messages,
)
from app.services.scoring import dvf_scoring  # noqa: E402


class ReportPromptRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_summary_prompt_uses_only_payload_json(self) -> None:
        payload = {
            "project": {"title": "Manual Report Helper"},
            "state_json": {"problem": {"pain": "Manual reports take hours"}},
        }
        expected_json = json.dumps(payload, indent=2, ensure_ascii=True)
        context = PromptContextBuilder().stage_summary(
            "problem",
            payload,
            output_language=output_language_label("en"),
        )

        with patch.dict(os.environ, {"IDEASENSE_PROMPT_SOURCE": "file"}):
            messages = await render_prompt_messages(None, context)

        self.assertIn("Use only the provided data", messages[0]["content"])
        self.assertIn(expected_json, messages[1]["content"])
        self.assertIn("Manual reports take hours", messages[1]["content"])
        self.assertNotIn("enterprise compliance buyer", messages[1]["content"])

    async def test_project_description_prompt_uses_provided_title_summary_and_payload(
        self,
    ) -> None:
        payload = {"problem": {"target_user": "student founders"}}
        expected_json = json.dumps(payload, indent=2, ensure_ascii=True)
        context = PromptContextBuilder().project_description(
            title="IdeaSense",
            payload=payload,
            summary="Students need clearer startup assessment.",
            output_language=output_language_label("en"),
        )

        with patch.dict(os.environ, {"IDEASENSE_PROMPT_SOURCE": "file"}):
            messages = await render_prompt_messages(None, context)

        self.assertIn("Use only the provided input", messages[0]["content"])
        self.assertIn("IdeaSense", messages[1]["content"])
        self.assertIn(
            "Students need clearer startup assessment.",
            messages[1]["content"],
        )
        self.assertIn(expected_json, messages[1]["content"])
        self.assertNotIn("enterprise compliance buyer", messages[1]["content"])

    async def test_dvf_prompt_preserves_report_input_json_and_grounding_rule(
        self,
    ) -> None:
        report_input = {
            "project": {"title": "Validation Coach"},
            "context_cards": {
                "problem": {"confirmed_inputs": ["Founders skip interviews"]}
            },
        }
        expected_json = json.dumps(report_input, indent=2, ensure_ascii=True)

        with patch.dict(os.environ, {"IDEASENSE_PROMPT_SOURCE": "file"}):
            messages = await dvf_scoring._build_prompt(
                None,
                report_input,
                output_locale="en",
            )

        self.assertIn("Use only the provided input JSON", messages[0]["content"])
        self.assertIn("Do not invent facts", messages[0]["content"])
        self.assertIn(expected_json, messages[1]["content"])
        self.assertNotIn("enterprise compliance buyer", messages[1]["content"])

    async def test_final_report_prompt_preserves_report_input_json_and_grounding_rule(
        self,
    ) -> None:
        report_input = {
            "project": {"title": "Validation Coach"},
            "stage_summaries": {"problem": "Founders skip interviews."},
            "key_risks": [{"risk": "Unvalidated willingness to pay"}],
        }
        expected_json = json.dumps(report_input, indent=2, ensure_ascii=True)

        with patch.dict(os.environ, {"IDEASENSE_PROMPT_SOURCE": "file"}):
            messages = await report_prompt_tasks.build_report_prompt(
                None,
                report_input,
                output_locale="en",
            )

        self.assertIn("using only the provided input", messages[0]["content"])
        self.assertIn("Do not invent facts", messages[0]["content"])
        self.assertIn(expected_json, messages[1]["content"])
        self.assertNotIn("enterprise compliance buyer", messages[1]["content"])

    async def test_stage_summary_generation_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "stage_summary_problem")
            self.assertEqual(
                kwargs["expected_mutation"],
                stage_summary_worker_handler.PromptMutationClass.REPORT_ARTIFACT,
            )
            return types.SimpleNamespace(
                ok=True,
                content="Founders need faster validation.",
                model="test-model",
                provider="test-provider",
                failure=None,
                trace={"task_key": "stage_summary_problem"},
            )

        trace_sink: dict[str, object] = {}
        with patch.object(
            stage_summary_worker_handler,
            "execute_prompt_task",
            new=fake_executor,
        ):
            summary, model = await stage_summary_worker_handler.generate_stage_summary_v0(
                None,
                "problem",
                {"problem": {"pain": "Slow validation"}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(summary, "Founders need faster validation.")
        self.assertEqual(model, "test-model")
        self.assertEqual(
            trace_sink["stage_summary_problem"]["task_key"],
            "stage_summary_problem",
        )
        self.assertEqual(trace_sink["stage_summary_problem"]["model"], "test-model")
        self.assertEqual(
            trace_sink["stage_summary_problem"]["provider"],
            "test-provider",
        )

    async def test_stage_summary_timeout_uses_context_fallback(self) -> None:
        async def fake_executor(_session, _context, **_kwargs):
            return types.SimpleNamespace(
                ok=False,
                content=None,
                model="slow-model",
                provider="slow-provider",
                failure=types.SimpleNamespace(reason="timeout"),
                trace={"task_key": "stage_summary_problem"},
            )

        trace_sink: dict[str, object] = {}
        with patch.object(
            stage_summary_worker_handler,
            "execute_prompt_task",
            new=fake_executor,
        ):
            summary, model = await stage_summary_worker_handler.generate_stage_summary_v0(
                None,
                "problem",
                {
                    "data": {
                        "problem": {"one_line": "Teams waste mentor reviews."},
                        "target_user": {"core": "student founders"},
                    }
                },
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(model, stage_summary_worker_handler.STAGE_SUMMARY_FALLBACK_MODEL)
        self.assertIn("Generated from the confirmed live context.", summary)
        self.assertIn("Teams waste mentor reviews.", summary)
        self.assertIn("Target User / Core", summary)
        self.assertTrue(trace_sink["stage_summary_problem"]["fallback_used"])

    async def test_stage_summary_executor_exception_uses_context_fallback(self) -> None:
        async def fake_executor(_session, _context, **_kwargs):
            raise TimeoutError("provider timed out")

        trace_sink: dict[str, object] = {}
        with patch.object(
            stage_summary_worker_handler,
            "execute_prompt_task",
            new=fake_executor,
        ):
            summary, model = await stage_summary_worker_handler.generate_stage_summary_v0(
                None,
                "market",
                {"data": {"market": {"segment": "university incubators"}}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(model, stage_summary_worker_handler.STAGE_SUMMARY_FALLBACK_MODEL)
        self.assertIn("university incubators", summary)
        self.assertEqual(
            trace_sink["stage_summary_market"]["status"],
            "fallback",
        )
        self.assertEqual(
            trace_sink["stage_summary_market"]["provider"],
            "deterministic",
        )

    async def test_dvf_scoring_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "dvf_scoring")
            self.assertEqual(
                kwargs["expected_mutation"],
                dvf_scoring.PromptMutationClass.REPORT_ARTIFACT,
            )
            self.assertEqual(kwargs["temperature_override"], 0.4)
            return types.SimpleNamespace(
                ok=True,
                parsed={"dvf_scoreboard": {"total_score": 72}},
                model="test-model",
                provider="test-provider",
                failure=None,
                trace={"task_key": "dvf_scoring"},
            )

        trace_sink: dict[str, object] = {}
        with (
            patch.dict(os.environ, {"IDEASENSE_DVF_TEMPERATURE": "0.4"}),
            patch.object(dvf_scoring, "execute_prompt_task", new=fake_executor),
        ):
            payload, model = await dvf_scoring.generate_dvf_scoring(
                None,
                {"project": {"title": "Validation Coach"}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(payload, {"dvf_scoreboard": {"total_score": 72}})
        self.assertEqual(model, "test-model")
        self.assertEqual(trace_sink["dvf_scoring"]["task_key"], "dvf_scoring")
        self.assertEqual(trace_sink["dvf_scoring"]["model"], "test-model")
        self.assertEqual(trace_sink["dvf_scoring"]["provider"], "test-provider")

    async def test_structured_report_generation_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "final_report")
            self.assertEqual(
                kwargs["expected_mutation"],
                report_worker.PromptMutationClass.REPORT_ARTIFACT,
            )
            self.assertNotIn("parser", kwargs)
            return types.SimpleNamespace(
                ok=True,
                parsed={"executive_summary": "Validation is promising."},
                model="test-model",
                provider="test-provider",
                failure=None,
                trace={"task_key": "final_report"},
            )

        trace_sink: dict[str, object] = {}
        with patch.object(report_worker, "execute_prompt_task", new=fake_executor):
            payload, model = await report_worker._generate_structured_report_v0(
                None,
                {"project": {"title": "Validation Coach"}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(payload, {"executive_summary": "Validation is promising."})
        self.assertEqual(model, "test-model")
        self.assertEqual(trace_sink["final_report"]["task_key"], "final_report")
        self.assertEqual(trace_sink["final_report"]["model"], "test-model")
        self.assertEqual(trace_sink["final_report"]["provider"], "test-provider")

    def test_report_tasks_have_real_path_timeouts(self) -> None:
        registry = DEFAULT_PROMPT_TASK_REGISTRY

        self.assertGreaterEqual(
            registry.get("stage_summary_market").timeout_ms or 0,
            60000,
        )
        self.assertGreaterEqual(
            registry.get("stage_summary_tech").timeout_ms or 0,
            60000,
        )
        self.assertGreaterEqual(
            registry.get("dvf_scoring").timeout_ms or 0,
            45000,
        )
        self.assertGreaterEqual(
            registry.get("final_report").timeout_ms or 0,
            60000,
        )

    def test_report_recovery_sections_fill_blank_report_payload(self) -> None:
        payload = report_builder.build_report_payload(
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "title": "Validation Coach",
                "description": "Helps founders validate before building.",
                "current_stage": "report",
            },
            {
                "problem": {
                    "main_problems": ["Teams build before validating demand."],
                    "one_line": "Founders need faster validation.",
                },
                "target_user": {"priority_segment": "student founders"},
                "market_strategy": {
                    "uvp": {"one_line": "Turns notes into validation reports."},
                    "business_model": {"revenue_model": "annual SaaS license"},
                },
                "tech_execution": {
                    "product_scope": {"mvp_definition": "guided interview and report"},
                },
            },
            [
                {
                    "id": "stage-problem",
                    "stage": "problem",
                    "summary_text": "Student founders need sharper validation.",
                },
                {
                    "id": "stage-market",
                    "stage": "market",
                    "summary_text": "Programs can pilot this with mentor cohorts.",
                },
                {
                    "id": "stage-tech",
                    "stage": "tech",
                    "summary_text": "The first MVP is a staged interview and report.",
                },
            ],
        )

        recovery = report_recovery_sections.build_report_recovery_sections(payload)

        self.assertIn("overall_summary", recovery)
        self.assertIn("Student founders", recovery["overall_summary"])
        self.assertGreater(
            recovery["dvf_scoreboard"]["total_score"],
            0,
        )
        self.assertEqual(
            recovery["dvf_assessment"]["total_score"],
            recovery["dvf_scoreboard"]["total_score"],
        )
        self.assertTrue(recovery["key_risks"])

    def test_report_builder_does_not_recreate_recovery_section_owner(self) -> None:
        builder_source = Path(report_builder.__file__).read_text()
        self.assertNotIn("def _build_fallback_overall_summary", builder_source)
        self.assertNotIn("def _build_fallback_key_risks", builder_source)

    def test_report_v2_sections_fill_from_legacy_report_payload(self) -> None:
        payload = {
            "overall_summary": "Proceed after validating buyer urgency.",
            "dvf_confidence": {"level": "medium", "coverage": 72},
            "dvf_scoreboard": {
                "desirability": 76,
                "viability": 68,
                "feasibility": 73,
                "total_score": 72,
                "decision_band": "Validate first",
            },
            "dvf_assessment": {
                "desirability": {
                    "score": 76,
                    "comment": "Students report a frequent, painful workflow gap.",
                },
                "viability": {
                    "score": 68,
                    "comment": "Buyer urgency needs more proof.",
                },
                "feasibility": {
                    "score": 73,
                    "comment": "MVP scope is manageable.",
                },
            },
            "key_risks": [
                {
                    "risk": "Buyer willingness to pay is unproven.",
                    "severity": "High",
                    "likelihood": "Medium",
                    "category": "Market",
                    "mitigation_suggestion": "Run two pricing interviews.",
                }
            ],
            "validation_plan": [
                {
                    "action": "Interview two program directors about budget.",
                    "target": "Buyer",
                    "success_signal": "Both confirm a budget owner and pilot path.",
                    "linked_risk": "Buyer willingness to pay is unproven.",
                    "priority": "high",
                }
            ],
            "diagnosis": {
                "summary": "Founder should validate buyer urgency before scaling."
            },
        }

        v2_sections = build_report_v2_sections(payload)

        self.assertEqual(v2_sections["artifact_schema_version"], "report_v2")
        self.assertEqual(
            v2_sections["decision_snapshot"]["verdict"],
            "Validate first",
        )
        self.assertEqual(
            v2_sections["decision_snapshot"]["next_action"],
            "Interview two program directors about budget.",
        )
        self.assertEqual(
            v2_sections["score_rationales"]["desirability"]["score"],
            76.0,
        )
        self.assertEqual(
            v2_sections["risk_register"][0]["risk"],
            "Buyer willingness to pay is unproven.",
        )
        self.assertEqual(
            v2_sections["experiment_plan"][0]["time_horizon"],
            "14 days",
        )


if __name__ == "__main__":
    unittest.main()
