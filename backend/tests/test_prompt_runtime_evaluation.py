import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.services import chat_answer_actions as answer_actions  # noqa: E402
from app.services import chat_ai_assist as ai_assist  # noqa: E402
from app.services import chat_followup_compose as followup_compose  # noqa: E402
from app.services import chat_sync_extraction_preview as extraction_preview  # noqa: E402
from app.services.chat_stream import events as stream_events  # noqa: E402
from app.services.prompt_runtime import (  # noqa: E402
    DEFAULT_PROMPT_OUTPUT_GUARD,
    PromptMutationClass,
)
from app.services.prompt_output_parsers import (  # noqa: E402
    AnswerGateResult,
    AnswerGateScore,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "prompt_runtime_evaluation.json"
)
REQUIRED_KINDS = {
    "chinese_complete",
    "english_complete",
    "too_short",
    "skipped",
    "unknown",
    "history_reference",
    "off_topic",
    "complete_unstructured",
}


def _load_scenarios() -> list[dict]:
    payload = json.loads(FIXTURE_PATH.read_text())
    return payload["scenarios"]


def _gate_result(payload: dict | None) -> AnswerGateResult | None:
    if not payload:
        return None
    return AnswerGateResult(
        verdict=payload["verdict"],
        missing_points=payload.get("missing_points", []),
        critical_issues=payload.get("critical_issues", []),
        followup_questions=payload.get("followup_questions", []),
        help_examples=payload.get("help_examples", []),
        followup_message=payload.get("followup_message", ""),
        score=AnswerGateScore(**payload["score"]),
        overall=payload["overall"],
    )


def _decision_for(scenario: dict) -> dict:
    if scenario.get("skip"):
        return answer_actions.build_skip_decision(
            scenario["skip"].get("reason"),
            resolution_status=scenario["skip"].get(
                "resolution_status",
                "unknown",
            ),
        )
    return followup_compose.build_gate_decision(
        scenario["question_detail"],
        scenario["answer"],
        _gate_result(scenario.get("gate_result")),
        scenario["answer"],
    )


def _value_at_path(payload: dict, path: str):
    cursor = payload
    for raw_part in path.split("."):
        part = raw_part[:-2] if raw_part.endswith("[]") else raw_part
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


class PromptRuntimeEvaluationFixtureTests(unittest.TestCase):
    def test_fixture_set_covers_required_answer_shapes(self) -> None:
        scenarios = _load_scenarios()
        kinds = {scenario["kind"] for scenario in scenarios}

        self.assertEqual(kinds, REQUIRED_KINDS)
        self.assertEqual(len(scenarios), len(REQUIRED_KINDS))

    def test_answer_text_and_history_reference_expectations(self) -> None:
        for scenario in _load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                _ai_assisted, _cleaned_message, answer_text = (
                    ai_assist.build_answer_text_from_history(
                        scenario.get("previous_answers", []),
                        scenario["answer"],
                    )
                )

                for expected_text in scenario["expected"]["answer_text_contains"]:
                    self.assertIn(expected_text, answer_text)
                self.assertEqual(
                    extraction_preview.looks_like_history_reference(scenario["answer"]),
                    scenario["expected"]["history_reference"],
                )

    def test_gate_and_skip_decision_expectations(self) -> None:
        for scenario in _load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                decision = _decision_for(scenario)

                self.assertEqual(
                    decision["final_verdict"],
                    scenario["expected"]["gate_verdict"],
                )
                if scenario["expected"].get("skipped"):
                    self.assertTrue(decision["skipped"])
                    self.assertEqual(decision["model_verdict"], "skipped")

    def test_extraction_updates_remain_limited_to_allowed_schema_paths(self) -> None:
        for scenario in _load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                expected = scenario["expected"]
                decision = _decision_for(scenario)
                if decision["final_verdict"] != "pass" or scenario.get("skip"):
                    self.assertEqual(expected["resolved_paths"], [])
                    self.assertEqual(expected["state_paths"], [])
                    self.assertEqual(expected["pending_paths"], [])
                    continue

                resolved_paths, updates = extraction_preview.prepare_extraction_updates(
                    scenario["question_detail"],
                    scenario.get("extracted", {}),
                    scenario["stage"],
                    scenario["answer"],
                )

                self.assertEqual(resolved_paths, expected["resolved_paths"])
                self.assertTrue(
                    set(resolved_paths).issubset(
                        set(scenario["question_detail"].get("schema_paths", []))
                    )
                )
                self.assertEqual(
                    [path for target, path, _value in updates if target == "state"],
                    expected["state_paths"],
                )
                self.assertEqual(
                    [path for target, path, _value in updates if target == "pending"],
                    expected["pending_paths"],
                )

                state_json, state_meta = extraction_preview.apply_extraction_updates_to_state(
                    {},
                    {},
                    updates,
                    current_stage=scenario["stage"],
                    resolved_paths=resolved_paths,
                    ai_assisted=False,
                )

                self.assertNotIn("stage_status", state_json)
                self.assertNotIn("stage_status", state_meta)
                for path in expected["state_paths"]:
                    self.assertIsNotNone(_value_at_path(state_json, path))
                pending_confirm = state_meta.get("pending_confirm", {})
                for path in expected["pending_paths"]:
                    self.assertIsNotNone(_value_at_path(pending_confirm, path))

    def test_prompt_runtime_mutation_boundaries(self) -> None:
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "question_compose",
            PromptMutationClass.VISIBLE_COPY_ONLY,
        )
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "followup_compose",
            PromptMutationClass.VISIBLE_COPY_ONLY,
        )
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "answer_gate",
            PromptMutationClass.DECISION_ONLY,
        )
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "extract",
            PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        )

        with self.assertRaises(PermissionError):
            DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
                "question_compose",
                PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
            )


class PromptRuntimeEvaluationStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_contexts_preserve_locale_and_fallback_metadata(self) -> None:
        for scenario in _load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                decision = _decision_for(scenario)

                with patch.object(
                    followup_compose,
                    "has_available_provider",
                    return_value=False,
                ):
                    if scenario["stream_kind"] == "followup":
                        context = await followup_compose.build_followup_stream_context(
                            None,
                            project_id=str(uuid4()),
                            org_id=str(uuid4()),
                            stage=scenario["stage"],
                            variant=scenario["variant"],
                            question_instance_id=uuid4(),
                            question_detail=scenario["question_detail"],
                            decision=decision,
                            fallback_content=scenario["fallback_content"],
                            meta={"schema_version": "v1"},
                            output_locale=scenario["requested_locale"],
                            latest_answer=scenario["answer"],
                            context_summary=scenario.get("context_summary"),
                            message_meta=scenario.get("message_meta"),
                        )
                    else:
                        context = await followup_compose.build_question_stream_context(
                            None,
                            project_id=str(uuid4()),
                            org_id=str(uuid4()),
                            stage=scenario["stage"],
                            variant=scenario["variant"],
                            question_instance_id=uuid4(),
                            question_detail=scenario["question_detail"],
                            fallback_content=scenario["fallback_content"],
                            meta={"schema_version": "v1"},
                            output_locale=scenario["requested_locale"],
                            latest_answer=scenario["answer"],
                            context_summary=scenario.get("context_summary"),
                            message_meta=scenario.get("message_meta"),
                        )

                expected = scenario["expected"]
                self.assertEqual(context["output_locale"], expected["output_locale"])
                self.assertEqual(
                    context["question_detail"]["question_id"],
                    scenario["question_detail"]["question_id"],
                )
                self.assertIsNone(context["compose_messages"])
                self.assertEqual(context["fallback_source"], expected["fallback_source"])
                self.assertEqual(
                    context["meta"]["content_locale"],
                    expected["output_locale"],
                )
                if expected.get("locale_source"):
                    self.assertEqual(
                        context["meta"]["locale_source"],
                        expected["locale_source"],
                    )
                    self.assertEqual(
                        context["meta"]["requested_output_locale"],
                        scenario["requested_locale"],
                    )
                else:
                    self.assertNotIn("locale_source", context["meta"])

                fallback_meta = stream_events.build_streamed_question_message_meta(
                    context,
                    source=context["fallback_source"],
                )
                self.assertEqual(fallback_meta["source"], expected["fallback_source"])
                self.assertEqual(
                    fallback_meta["display_format"],
                    expected["display_format"],
                )


if __name__ == "__main__":
    unittest.main()
