import sys
import time
import types
import unittest
from uuid import uuid4
from unittest.mock import patch


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.api.routes import chat  # noqa: E402
from app.services import chat_ai_assist as ai_assist  # noqa: E402
from app.services import chat_context_reads as context_reads  # noqa: E402
from app.services import chat_followup_compose as followup_compose  # noqa: E402
from app.services import chat_gate_resolution as gate_resolution  # noqa: E402
from app.services import chat_question_filters as question_filters  # noqa: E402
from app.services import chat_question_planning as question_planning  # noqa: E402
from app.services import chat_question_runtime as question_runtime  # noqa: E402
from app.services import chat_router_mode as router_mode  # noqa: E402
from app.services import chat_sync_extraction_preview as extraction_preview  # noqa: E402
from app.services import chat_turn_context as turn_context  # noqa: E402
from app.services import chat_turn_commit as turn_commit  # noqa: E402
from app.services import chat_turn_evaluation as turn_evaluation  # noqa: E402
from app.services import chat_turn_payloads as turn_payloads  # noqa: E402
from app.services import chat_turn_preflight as turn_preflight  # noqa: E402
from app.services import extraction_text_heuristics as text_heuristics  # noqa: E402
from app.services import chat_prompt_tasks  # noqa: E402
from app.services import project_question_prompts  # noqa: E402
from app.services.chat_stream import message_persistence  # noqa: E402
from app.services.chat_stream import question_response  # noqa: E402
from app.services.chat_stage_gate import (  # noqa: E402
    is_stage_gate_ready_for_review,
    should_enter_stage_gate_review,
)
from app.services.prompt_output_parsers import (  # noqa: E402
    AnswerGateResult,
    AnswerGateScore,
)


class _FakeTransaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeResult:
    def __init__(self, row: dict | None = None, rowcount: int | None = None) -> None:
        self.row = row
        self.rowcount = rowcount

    def mappings(self):
        return self

    def first(self):
        return self.row


class _FakeSession:
    def __init__(self, result: _FakeResult | None = None) -> None:
        self.executed: list[tuple[str, dict | None]] = []
        self.result = result or _FakeResult()

    def begin(self) -> _FakeTransaction:
        return _FakeTransaction()

    async def execute(self, statement, params=None):
        self.executed.append((str(statement), params))
        return self.result


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class QuestionComposeTests(unittest.TestCase):
    def test_sanitize_composed_question_accepts_markdown_text(self) -> None:
        result = followup_compose.sanitize_composed_question(
            "Got it.\n\n**Next:** What is the main problem you want to solve?"
        )

        self.assertEqual(
            result,
            "Got it.\n\n**Next:** What is the main problem you want to solve?",
        )

    def test_sanitize_composed_question_unwraps_display_envelope(self) -> None:
        result = followup_compose.sanitize_composed_question(
            "<DISPLAY>Please describe the workflow pain.</DISPLAY>"
        )

        self.assertEqual(result, "Please describe the workflow pain.")

    def test_sanitize_composed_question_strips_markdown_fence(self) -> None:
        result = followup_compose.sanitize_composed_question(
            "```markdown\nPlease list the top three risks.\n```"
        )

        self.assertEqual(result, "Please list the top three risks.")


class FollowupLocalizationTests(unittest.TestCase):
    def test_followup_locale_prefers_latest_chinese_answer(self) -> None:
        self.assertEqual(
            chat._resolve_interview_output_locale(
                "日程管理，AI 拆解任务，AI 分配任务这些",
                "en",
            ),
            "zh",
        )

    def test_followup_locale_prefers_latest_english_answer(self) -> None:
        self.assertEqual(
            chat._resolve_interview_output_locale(
                "Schedule management and AI task breakdown.",
                "zh",
            ),
            "en",
        )

    def test_quick_action_locale_prefers_context_language(self) -> None:
        self.assertEqual(
            chat._resolve_interview_output_locale(
                "I'm not sure",
                "en",
                context_summary="项目围绕日程管理和 AI 拆解任务。",
                message_meta={"answer_mode": "unknown"},
            ),
            "zh",
        )

    def test_regular_english_answer_keeps_english_locale(self) -> None:
        self.assertEqual(
            chat._resolve_interview_output_locale(
                "The target user is a freelancer.",
                "zh",
                context_summary="项目围绕日程管理和 AI 拆解任务。",
            ),
            "en",
        )

    def test_chinese_followup_fallback_ignores_english_gate_message(self) -> None:
        message = followup_compose.build_followup_message(
            {
                "prompt": "List up to three problems and choose the MVP priority.",
                "validation_rule": "Must include MVP priority.",
            },
            {
                "followup_message": "Thanks — please clarify the MVP priority.",
                "missing_points": ["MVP priority"],
                "critical_issues": [],
                "followup_questions": [],
                "help_examples": [],
            },
            "日程管理，AI 拆解任务，AI 分配任务这些",
            output_locale="zh",
        )

        self.assertIn("为了继续往下一步走", message)
        self.assertIn("第一版优先解决", message)
        self.assertNotIn("Thanks", message)

    def test_english_followup_fallback_includes_copyable_pattern(self) -> None:
        message = followup_compose.build_followup_message(
            {"prompt": "List up to three problems and choose the MVP priority."},
            {
                "followup_message": "Thanks — please clarify the MVP priority.",
                "missing_points": ["MVP priority"],
                "critical_issues": [],
                "followup_questions": [],
                "help_examples": [],
            },
            "Schedule management and AI task breakdown.",
            output_locale="en",
        )

        self.assertIn("Please add/clarify: MVP priority", message)
        self.assertIn("The first version should prioritize", message)

    def test_impact_followup_fallback_uses_time_money_pattern(self) -> None:
        message = followup_compose.build_followup_message(
            {
                "prompt": "Approximate impact for one typical user/company.",
                "schema_paths": ["impact.time_impact", "impact.money_impact"],
            },
            {
                "followup_message": "Please add time and money impact.",
                "missing_points": ["Needs time and money impact."],
                "critical_issues": [],
                "followup_questions": [],
                "help_examples": [],
            },
            "Time wasted: 3 hours per week",
            output_locale="en",
        )

        self.assertIn("Time wasted: ___ per week/month", message)
        self.assertIn("Money impact: ___ per month", message)
        self.assertNotIn("The first version should prioritize", message)

    def test_tech_mvp_boundary_followup_uses_scope_pattern(self) -> None:
        message = followup_compose.build_followup_message(
            {
                "question_id": "L3Q1",
                "prompt": "Where is your product today and what is not in MVP?",
                "schema_paths": ["tech_execution.product_scope.core_user_journeys"],
            },
            {
                "followup_message": "Please clarify the MVP scope.",
                "missing_points": ["Needs MVP scope."],
                "critical_issues": [],
                "followup_questions": [],
                "help_examples": [],
            },
            "Working prototype",
            output_locale="en",
        )

        self.assertIn("Current status: ___", message)
        self.assertIn("In-MVP scope: ___", message)
        self.assertNotIn("The first version should prioritize", message)


class AnswerTextFromHistoryTests(unittest.TestCase):
    def test_build_answer_text_appends_current_answer(self) -> None:
        ai_assisted, cleaned_message, answer_text = (
            ai_assist.build_answer_text_from_history(
                ["Earlier context."],
                "Current answer.",
            )
        )

        self.assertFalse(ai_assisted)
        self.assertEqual(cleaned_message, "Current answer.")
        self.assertEqual(answer_text, "Earlier context.\n\nCurrent answer.")

    def test_build_answer_text_strips_ai_draft_prefix(self) -> None:
        ai_assisted, cleaned_message, answer_text = (
            ai_assist.build_answer_text_from_history(
                ["Earlier context."],
                "[AI Draft] Use student teams as the first user.",
            )
        )

        self.assertTrue(ai_assisted)
        self.assertEqual(cleaned_message, "Use student teams as the first user.")
        self.assertEqual(
            answer_text,
            "Earlier context.\n\nUse student teams as the first user.",
        )


class TurnPreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_chat_user_message_persists_turn_metadata(self) -> None:
        fake_session = _FakeSession(_FakeResult({"id": 42}))

        message_id = await turn_preflight.insert_chat_user_message(
            fake_session,
            project_id="project-1",
            actor_user_id="user-1",
            stage="problem",
            variant="default",
            question_instance_id="instance-1",
            content="Latest answer.",
            message_meta={"answer_mode": "draft"},
            client_message_id="client-1",
            request_id="request-1",
        )

        statement, params = fake_session.executed[-1]
        self.assertEqual(message_id, 42)
        self.assertIn("INSERT INTO conversation_messages", statement)
        self.assertEqual(params["author_user_id"], "user-1")
        self.assertEqual(params["meta"], {"answer_mode": "draft"})
        self.assertEqual(params["client_message_id"], "client-1")
        self.assertEqual(params["request_id"], "request-1")

    def test_build_chat_gate_context_shapes_router_and_answer_text(self) -> None:
        context = turn_preflight.build_chat_gate_context(
            project_row={
                "project_id": "project-1",
                "settings": {"tone": "concise"},
                "current_stage": "tech",
                "runtime_stage": "tech",
                "runtime_variant": "router",
                "runtime_version": 3,
                "next_question_bank_question_id": "next-q",
                "missing_paths": ["tech.mode"],
                "question_bank_version_id": "bank-1",
                "stage_status": "in_progress",
            },
            org_id="org-1",
            current_question_id="current-q",
            current_question_instance_id="instance-1",
            user_message_id=42,
            request_id="request-1",
            client_message_id="client-1",
            question_detail={"validation_rule": "Answer in one sentence."},
            state_json={"target_user": {"core": "Student founders"}},
            state_meta={"source": "test"},
            previous_answer_parts=["Earlier answer."],
            latest_message="[AI Draft] Latest answer.",
            message_meta={"answer_mode": "draft"},
            output_locale="en",
        )

        self.assertEqual(context["project_id"], "project-1")
        self.assertEqual(context["runtime_version"], 3)
        self.assertEqual(context["latest_answer"], "Latest answer.")
        self.assertEqual(context["answer_text"], "Earlier answer.\n\nLatest answer.")
        self.assertEqual(context["gate_answer_text"], "Latest answer.")
        self.assertIs(context["router_state_json"], context["state_json"])
        self.assertTrue(context["ai_assisted"])


class AIAssistPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_mark_ai_draft_requested_updates_question_instance_meta(self) -> None:
        fake_session = _FakeSession()
        requested_at = types.SimpleNamespace(
            isoformat=lambda: "2026-06-16T12:00:00+00:00"
        )

        await ai_assist.mark_ai_draft_requested(
            fake_session,
            project_id="project-1",
            question_instance_id="instance-1",
            requested_at=requested_at,
        )

        statement, params = fake_session.executed[-1]
        self.assertIn("UPDATE project_question_instances", statement)
        self.assertEqual(params["project_id"], "project-1")
        self.assertEqual(params["question_instance_id"], "instance-1")
        self.assertIn('"ai_draft_requested": true', params["meta"])
        self.assertIn("2026-06-16T12:00:00+00:00", params["meta"])


class ExtractionTextHeuristicsTests(unittest.TestCase):
    def test_clean_extracted_text_items_strips_prefixes_and_dedupes(self) -> None:
        self.assertEqual(
            text_heuristics._clean_extracted_text_items(
                [
                    "1. Build onboarding",
                    "- Build onboarding",
                    "x",
                    "2) Integrate Slack",
                ]
            ),
            ["Build onboarding", "Integrate Slack"],
        )

    def test_extract_labeled_answer_value_reads_lines_and_inline_labels(self) -> None:
        self.assertEqual(
            text_heuristics._extract_labeled_answer_value(
                "A) Payer: school program leads\nB) End users: students",
                (r"payer", r"who\s*pays"),
            ),
            "school program leads",
        )
        self.assertEqual(
            text_heuristics._extract_labeled_answer_value(
                "We sell to programs. Named competitors: Airtable and Notion.",
                (r"named\s*competitors?",),
            ),
            "Airtable and Notion.",
        )

    def test_clip_value_before_labels_stops_at_next_labeled_field(self) -> None:
        self.assertEqual(
            text_heuristics._clip_value_before_labels(
                "workflow spreadsheets. Named competitors: Airtable",
                (r"named\s*competitors?",),
            ),
            "workflow spreadsheets",
        )

    def test_extract_target_user_value_clips_buyer_context(self) -> None:
        self.assertEqual(
            text_heuristics._extract_target_user_value(
                "Primary user: student founders in incubators. Buyer: university programs."
            ),
            "student founders in incubators",
        )

    def test_market_competition_helpers_extract_labeled_segments(self) -> None:
        answer = (
            "Competitor types: spreadsheets and generic forms. "
            "Named competitors: Airtable, Typeform. "
            "Positioning difference: narrower startup assessment workflow. "
            "Red flags: teams may stay in spreadsheets."
        )

        self.assertEqual(
            text_heuristics._extract_competitor_types_value(answer),
            "spreadsheets and generic forms",
        )
        self.assertEqual(
            text_heuristics._extract_named_competitors_value(answer),
            "Airtable, Typeform",
        )
        self.assertEqual(
            text_heuristics._extract_positioning_summary_value(answer),
            "narrower startup assessment workflow",
        )
        self.assertEqual(
            text_heuristics._extract_competitive_red_flags_value(answer),
            "teams may stay in spreadsheets",
        )

    def test_tech_journey_component_helpers_parse_lists(self) -> None:
        self.assertEqual(
            text_heuristics._extract_core_user_journeys_value(
                "Critical user journeys: 1. Create project; 2. Answer stage questions; 3. Review report. Components: api, worker"
            ),
            ["Create project", "Answer stage questions", "Review report"],
        )
        self.assertEqual(
            text_heuristics._extract_high_level_components_value(
                "High-level components: frontend, api, worker and postgres. Risks: latency"
            ),
            ["frontend", "api", "worker", "postgres"],
        )

    def test_selected_question_classifiers_match_schema_paths(self) -> None:
        self.assertTrue(
            text_heuristics._is_target_user_question(
                ["target_user.core", "target_user.priority_segment"]
            )
        )
        self.assertTrue(
            text_heuristics._is_tech_data_access_question(
                ["tech_execution.data_ai_scalability.data_access_rights"]
            )
        )
        self.assertTrue(
            text_heuristics._is_market_moat_question(
                ["market_strategy.moat.long_term_moat"]
            )
        )


class TurnContextTests(unittest.TestCase):
    def test_collect_key_points_flattens_and_dedupes_values(self) -> None:
        self.assertEqual(
            turn_context.collect_key_points(
                {
                    "problem": "Slow client handoff",
                    "impact": ["Slow client handoff", "3 hours per week", ""],
                    "validated": True,
                }
            ),
            ["Slow client handoff", "3 hours per week", "True"],
        )

    def test_build_assistant_meta_merges_structured_fields(self) -> None:
        meta = turn_context.build_assistant_meta(
            base_meta={"schema_version": "v1"},
            decision={"final_verdict": "pass"},
            rolling_summary="  Founder validated the pain.  ",
            key_points=["Founder validated the pain."],
            question_meta={"question_id": "problem.core"},
            content_locale="ZH",
        )

        self.assertEqual(meta["schema_version"], "v1")
        self.assertEqual(meta["decision"]["final_verdict"], "pass")
        self.assertEqual(meta["rolling_summary"], "  Founder validated the pain.  ")
        self.assertEqual(meta["content_locale"], "zh")

    def test_select_gate_answer_prefers_latest_for_single_sentence_questions(
        self,
    ) -> None:
        self.assertEqual(
            turn_context.select_gate_answer(
                {"validation_rule": "Answer in one sentence."},
                "Latest single sentence.",
                "Older answer.\n\nLatest single sentence.",
            ),
            "Latest single sentence.",
        )

    def test_build_gate_context_summary_includes_market_context(self) -> None:
        summary = turn_context.build_gate_context_summary(
            {
                "target_user": {"core": "Freelance designers"},
                "problem": {"one_line": "Client briefs are vague"},
                "market_strategy": {
                    "uvp": {"one_line": "Structured AI brief intake"},
                    "market_size": {
                        "initial_segment_definition": ["solo designers", "studios"]
                    },
                    "competition": {
                        "positioning_summary": "Narrower than generic form builders"
                    },
                },
            },
            "market",
            {},
            "latest answer",
        )

        self.assertIsNotNone(summary)
        self.assertIn("Priority user: Freelance designers", summary or "")
        self.assertIn("Initial segment: solo designers; studios", summary or "")
        self.assertIn("Competition positioning:", summary or "")


class ChatContextReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_set_chat_session_context_sets_user_and_org(self) -> None:
        fake_session = _FakeSession()

        await context_reads.set_chat_session_context(
            fake_session,
            org_id="org-1",
            actor_type="user",
            user_id="user-1",
        )

        statement, params = fake_session.executed[-1]
        self.assertIn("app.user_id", statement)
        self.assertEqual(params["user_id"], "user-1")
        self.assertEqual(params["org_id"], "org-1")
        self.assertEqual(params["actor_type"], "user")

    async def test_fetch_context_meta_returns_state_version_and_timestamp(self) -> None:
        updated_at = types.SimpleNamespace(isoformat=lambda: "2026-06-16T12:00:00")
        fake_session = _FakeSession(
            _FakeResult({"state_version": 7, "updated_at": updated_at})
        )

        version, updated_at_value = await context_reads.fetch_context_meta(
            fake_session,
            "project-1",
            "org-1",
        )

        self.assertEqual(version, 7)
        self.assertEqual(updated_at_value, "2026-06-16T12:00:00")

    async def test_fetch_chat_question_detail_context_applies_group_override(self) -> None:
        fake_session = _FakeSession()
        question_id = uuid4()
        expected_question_instance_id = uuid4()
        latency_spans: dict[str, float] = {}

        async def fake_fetch_question_detail(session, incoming_question_id):
            self.assertIs(session, fake_session)
            self.assertEqual(incoming_question_id, question_id)
            return {"prompt": "Original prompt", "schema_paths": ["problem.raw"]}

        async def fake_fetch_group_meta(session, *, project_id, question_instance_id):
            self.assertIs(session, fake_session)
            self.assertEqual(project_id, "project-1")
            self.assertEqual(question_instance_id, expected_question_instance_id)
            return {
                "prompt": "Grouped prompt",
                "schema_paths": ["problem.priority"],
            }

        with (
            patch.object(
                context_reads,
                "AdminAsyncSessionLocal",
                lambda: _FakeSessionContext(fake_session),
            ),
            patch.object(
                context_reads,
                "fetch_chat_question_detail",
                fake_fetch_question_detail,
            ),
            patch.object(context_reads, "fetch_group_meta", fake_fetch_group_meta),
        ):
            question_detail = await context_reads.fetch_chat_question_detail_context(
                org_id="org-1",
                user_id="user-1",
                project_id="project-1",
                question_id=question_id,
                question_instance_id=expected_question_instance_id,
                latency_spans=latency_spans,
            )

        self.assertEqual(question_detail["prompt"], "Grouped prompt")
        self.assertEqual(question_detail["schema_paths"], ["problem.priority"])
        self.assertIn("preflight.question_detail", latency_spans)


class StreamMessagePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_persist_fallback_question_message_records_message_id(self) -> None:
        fake_session = _FakeSession(_FakeResult({"id": 42}))
        context = {
            "project_id": "project-1",
            "stage": "problem",
            "variant": "default",
            "question_instance_id": "question-instance-1",
            "fallback_content": "Next question?",
            "request_id": "request-1",
        }

        message_id = await message_persistence.persist_fallback_question_message(
            fake_session,
            context,
            fallback_source="question_compose_fallback",
        )

        self.assertEqual(message_id, 42)
        self.assertEqual(context["assistant_message_id"], 42)
        insert_params = fake_session.executed[-1][1]
        self.assertEqual(insert_params["content"], "Next question?")
        self.assertEqual(insert_params["meta"]["source"], "question_compose_fallback")

    async def test_update_streamed_question_message_updates_feedback(self) -> None:
        fake_session = _FakeSession(_FakeResult(rowcount=1))
        context = {
            "assistant_message_id": 42,
            "project_id": "project-1",
            "request_id": "request-1",
            "answer_evaluation_request_id": "evaluation-request-1",
        }

        updated = await message_persistence.update_streamed_question_message(
            fake_session,
            context,
            content="Composed next question?",
            source="question_compose",
            compose_model="test-model",
            compose_provider="test-provider",
            streamed=True,
        )

        self.assertTrue(updated)
        self.assertEqual(len(fake_session.executed), 2)
        message_update_params = fake_session.executed[0][1]
        self.assertEqual(message_update_params["content"], "Composed next question?")
        self.assertEqual(message_update_params["meta"]["source"], "question_compose")
        feedback_update_params = fake_session.executed[1][1]
        self.assertEqual(feedback_update_params["content"], "Composed next question?")


class ChatTurnEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_chat_turn_applies_s1q5_frequency_heuristic(self) -> None:
        gate_context = {
            "question_detail": {
                "question_id": "S1Q5",
                "schema_paths": [],
            },
            "runtime_stage": "problem",
            "runtime_variant": "default",
            "extraction_answer_text": "It happens every day for the team.",
            "gate_answer_text": "It happens every day for the team.",
            "latest_answer": "It happens every day for the team.",
            "state_json": {"problem": {}},
            "state_meta": {},
            "ai_assisted": False,
            "context_summary": "Summary",
            "output_locale": "en",
        }

        async def fake_resolve_gate_and_sync_extraction(*args, **kwargs):
            return (
                {
                    "final_verdict": "pass",
                    "model_verdict": "pass",
                    "missing_points": [],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                    "risk_notes": [],
                    "score": {},
                    "overall": 1.0,
                },
                "test-model",
                {"frequency": "daily"},
                False,
                {"answer_gate": {"task": "answer_gate"}},
            )

        with patch.object(
            turn_evaluation,
            "resolve_gate_and_sync_extraction",
            fake_resolve_gate_and_sync_extraction,
        ):
            evaluation = await turn_evaluation.evaluate_chat_turn(
                gate_context,
                previous_answer_count=0,
                skip_requested=False,
                skip_reason=None,
                skip_resolution_status=None,
            )

        self.assertEqual(evaluation.gate_model, "test-model")
        self.assertIn("problem.frequency", evaluation.resolved_paths)
        self.assertIn(
            ("state", "problem.frequency", "daily"),
            evaluation.extraction_updates,
        )
        self.assertEqual(
            evaluation.gate_context["state_json"]["problem"]["frequency"],
            "daily",
        )
        self.assertEqual(
            evaluation.gate_context["state_meta"]["answer_meta"]["problem.frequency"][
                "resolution_status"
            ],
            "answered",
        )


class ChatTurnCommitTests(unittest.IsolatedAsyncioTestCase):
    async def test_commit_needs_info_turn_updates_status_and_returns_stream_context(
        self,
    ) -> None:
        fake_session = _FakeSession()
        question_instance_id = uuid4()
        gate_context = {
            "project_id": "project-1",
            "current_question_instance_id": question_instance_id,
            "question_detail": {
                "question_id": "S1Q1",
                "stage": "problem",
                "variant": "default",
                "prompt": "What problem are you solving?",
                "prompt_meta": {"ui": {"input": "textarea"}},
            },
            "output_locale": "en",
            "latest_answer": "Too vague",
            "context_summary": "Summary",
            "message_meta": {},
            "project_settings": {},
        }
        decision = {
            "final_verdict": "needs_info",
            "model_verdict": "needs_info",
            "missing_points": ["Specific problem"],
            "critical_issues": [],
            "followup_questions": [],
            "help_examples": [],
            "risk_notes": [],
            "score": {},
            "overall": 0.2,
        }
        latency_spans: dict[str, float] = {}

        async def fake_build_followup_stream_context(*args, **kwargs):
            return {
                "project_id": kwargs["project_id"],
                "question_instance_id": kwargs["question_instance_id"],
                "fallback_content": kwargs["fallback_content"],
                "meta": kwargs["meta"],
            }

        with patch.object(
            turn_commit,
            "build_followup_stream_context",
            fake_build_followup_stream_context,
        ):
            result = await turn_commit.commit_needs_info_turn(
                fake_session,
                org_id="org-1",
                gate_context=gate_context,
                runtime_row={"stage": "problem", "variant": "default"},
                decision=decision,
                followup_message="Please clarify the specific problem.",
                rolling_summary="Summary",
                key_points=["Too vague"],
                request_id="eval-request-1",
                turn_event_meta={"request_id": "turn-request-1"},
                latency_spans=latency_spans,
            )

        self.assertEqual(len(fake_session.executed), 2)
        self.assertIn("SET status = 'needs_info'", fake_session.executed[0][0])
        self.assertIn("SET turn_state = 'needs_info'", fake_session.executed[1][0])
        self.assertEqual(
            result.assistant_content,
            "Please clarify the specific problem.",
        )
        self.assertEqual(
            result.question_stream_context["request_id"],
            "turn-request-1",
        )
        self.assertEqual(
            result.question_meta_payload["question_id"],
            "S1Q1",
        )
        self.assertIn("db_commit.needs_info_turn", latency_spans)

    async def test_commit_answer_status_marks_skip_with_meta(self) -> None:
        fake_session = _FakeSession()
        latency_spans: dict[str, float] = {}

        await turn_commit.commit_answer_status(
            fake_session,
            org_id="org-1",
            gate_context={
                "project_id": "project-1",
                "current_question_instance_id": uuid4(),
                "extraction_answer_text": "ignored",
            },
            skip_requested=True,
            answer_action="unknown",
            skip_resolution_status="unknown",
            skip_reason="Not enough information yet",
            latency_spans=latency_spans,
        )

        statement, params = fake_session.executed[-1]
        self.assertIn("SET status = 'skipped'", statement)
        self.assertIn('"answer_action": "unknown"', params["meta"])
        self.assertIn('"resolution_status": "unknown"', params["meta"])
        self.assertIn("db_commit.answer_status", latency_spans)

    async def test_apply_chat_state_updates_writes_state_and_event(self) -> None:
        fake_session = _FakeSession(
            _FakeResult(
                {
                    "state_json": {"problem": {}},
                    "state_meta": {},
                    "state_version": 2,
                }
            )
        )
        latency_spans: dict[str, float] = {}

        result = await turn_commit.apply_chat_state_updates(
            fake_session,
            org_id="org-1",
            gate_context={
                "project_id": "project-1",
                "bank_version_id": "bank-version-1",
                "current_question_instance_id": uuid4(),
                "request_id": "request-1",
                "ai_assisted": False,
            },
            runtime_stage="problem",
            runtime_variant="default",
            resolved_paths=["problem.frequency"],
            extraction_updates=[("state", "problem.frequency", "daily")],
            schema_paths=["problem.frequency"],
            skip_requested=False,
            skip_resolution_status=None,
            skip_reason=None,
            partial_unknown_paths=[],
            latency_spans=latency_spans,
        )

        self.assertEqual(result.state_json["problem"]["frequency"], "daily")
        self.assertEqual(
            result.state_meta["answer_meta"]["problem.frequency"][
                "resolution_status"
            ],
            "answered",
        )
        self.assertIn("UPDATE project_states", fake_session.executed[1][0])
        self.assertIn("INSERT INTO project_state_events", fake_session.executed[2][0])
        self.assertIn("db_commit.state_update", latency_spans)

    async def test_update_runtime_metadata_after_answer_updates_missing_paths(
        self,
    ) -> None:
        fake_session = _FakeSession()
        latency_spans: dict[str, float] = {}

        result = await turn_commit.update_runtime_metadata_after_answer(
            fake_session,
            org_id="org-1",
            gate_context={"project_id": "project-1", "state_json": {}, "state_meta": {}},
            runtime_stage="problem",
            runtime_variant="default",
            runtime_missing_paths=["problem.raw", "problem.frequency"],
            resolved_paths=["problem.raw"],
            skip_requested=False,
            state_json=None,
            state_meta=None,
            latency_spans=latency_spans,
        )

        self.assertEqual(result.updated_missing_paths, ["problem.frequency"])
        self.assertIsNone(result.stage_status_ready)
        self.assertIn("UPDATE project_runtime", fake_session.executed[-1][0])
        self.assertEqual(fake_session.executed[-1][1]["missing_paths"], ["problem.frequency"])
        self.assertIn("db_commit.runtime_metadata", latency_spans)

    async def test_build_scores_and_insert_answer_evaluation(self) -> None:
        decision = {
            "final_verdict": "pass",
            "model_verdict": "pass",
            "missing_points": [],
            "critical_issues": [],
            "followup_questions": [],
            "help_examples": [],
            "risk_notes": [],
            "score": {"clarity": 1.0},
            "overall": 1.0,
            "partial_advance": True,
            "partial_resolved_paths": ["problem.raw"],
            "partial_unknown_paths": ["problem.frequency"],
        }
        scores_payload = turn_payloads.build_answer_scores_payload(
            decision,
            skip_requested=True,
            prompt_task_traces={"answer_gate": {"task": "answer_gate"}},
        )

        self.assertEqual(scores_payload["verdict"], "skipped")
        self.assertTrue(scores_payload["partial_advance"])
        self.assertIn("prompt_task_traces", scores_payload)

        fake_session = _FakeSession()
        await turn_commit.insert_answer_evaluation(
            fake_session,
            org_id="org-1",
            gate_context={
                "project_id": "project-1",
                "current_question_instance_id": uuid4(),
            },
            rubric_id="rubric-1",
            scores_payload=scores_payload,
            overall_score=1.0,
            feedback_markdown="Feedback",
            evaluator_model="test-model",
            request_id="eval-request-1",
        )

        statement, params = fake_session.executed[-1]
        self.assertIn("INSERT INTO answer_evaluations", statement)
        self.assertEqual(params["scores_json"], scores_payload)
        self.assertEqual(params["feedback_markdown"], "Feedback")

    async def test_commit_stage_transition_turn_returns_ready_payload(self) -> None:
        fake_session = _FakeSession()

        async def fake_fetch_context_meta(session, project_id, org_id):
            self.assertIs(session, fake_session)
            self.assertEqual(project_id, "project-1")
            self.assertEqual(org_id, "org-1")
            return 5, "2026-06-16T12:00:00"

        with patch.object(turn_commit, "fetch_context_meta", fake_fetch_context_meta):
            result = await turn_commit.commit_stage_transition_turn(
                fake_session,
                org_id="org-1",
                gate_context={
                    "project_id": "project-1",
                    "current_stage": "problem",
                    "runtime_stage": "problem",
                    "output_locale": "en",
                },
                runtime_stage="problem",
                runtime_variant="default",
                decision={
                    "final_verdict": "pass",
                    "model_verdict": "pass",
                    "missing_points": [],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                    "risk_notes": [],
                    "score": {},
                    "overall": 1.0,
                },
                rolling_summary="Summary",
                key_points=["Point"],
                stage_gate_ready_for_review=True,
            )

        self.assertIn("UPDATE project_runtime", fake_session.executed[0][0])
        self.assertIn("INSERT INTO conversation_messages", fake_session.executed[1][0])
        self.assertEqual(result.stage_gate_ready_payload["context_version"], 5)
        self.assertEqual(result.stage_gate_ready_payload["next_stage"], "market")
        self.assertIn("gathered enough information", result.assistant_content)

    async def test_commit_router_mode_next_turn_returns_question_context(self) -> None:
        fake_session = _FakeSession(_FakeResult({"state_version": 8}))
        current_question_id = uuid4()
        next_question_id = uuid4()
        question_instance_id = uuid4()

        async def fake_resolve_initial_questions(*args, **kwargs):
            return current_question_id, next_question_id

        async def fake_resolve_missing_paths(*args, **kwargs):
            return ["tech.scope"]

        async def fake_ensure_question_instance(*args, **kwargs):
            return question_instance_id

        async def fake_fetch_question_detail(*args, **kwargs):
            return {
                "question_id": "T1",
                "prompt": "What technical path will you take?",
            }

        async def fake_build_question_stream_context(*args, **kwargs):
            return {
                "project_id": kwargs["project_id"],
                "question_instance_id": kwargs["question_instance_id"],
                "fallback_content": kwargs["fallback_content"],
            }

        with (
            patch.object(
                turn_commit,
                "resolve_initial_questions",
                fake_resolve_initial_questions,
            ),
            patch.object(
                turn_commit,
                "resolve_missing_paths",
                fake_resolve_missing_paths,
            ),
            patch.object(
                turn_commit,
                "ensure_question_instance",
                fake_ensure_question_instance,
            ),
            patch.object(
                turn_commit,
                "fetch_chat_question_detail",
                fake_fetch_question_detail,
            ),
            patch.object(
                turn_commit,
                "build_question_stream_context",
                fake_build_question_stream_context,
            ),
        ):
            result = await turn_commit.commit_router_mode_next_turn(
                fake_session,
                org_id="org-1",
                gate_context={
                    "project_id": "project-1",
                    "bank_version_id": "bank-version-1",
                    "current_question_instance_id": uuid4(),
                    "request_id": "request-1",
                    "latest_answer": "lite",
                    "output_locale": "en",
                    "project_settings": {},
                },
                decision={
                    "final_verdict": "pass",
                    "model_verdict": "pass",
                    "missing_points": [],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                    "risk_notes": [],
                    "score": {},
                    "overall": 1.0,
                },
                chosen_mode="lite",
                group_enabled=False,
                group_max=1,
                transition_enabled=False,
                planner_settings={"enabled": False},
                planned_question_id=None,
                planned_question_prompt=None,
                rolling_summary="Summary",
                key_points=[],
                request_id="eval-request-1",
                turn_event_meta={"request_id": "turn-request-1"},
            )

        executed_sql = "\n".join(statement for statement, _params in fake_session.executed)
        self.assertIn("UPDATE projects", executed_sql)
        self.assertIn("UPDATE project_runtime", executed_sql)
        self.assertEqual(result.assistant_content, "What technical path will you take?")
        self.assertEqual(result.question_stream_context["request_id"], "turn-request-1")
        self.assertEqual(
            result.question_stream_context["question_instance_id"],
            question_instance_id,
        )

    async def test_commit_standard_next_turn_returns_question_context(self) -> None:
        fake_session = _FakeSession()
        next_question_id = uuid4()
        question_instance_id = uuid4()

        async def fake_resolve_askable_question_id(*args, **kwargs):
            return args[1]

        async def fake_resolve_next_question_id(*args, **kwargs):
            return None

        async def fake_ensure_question_instance(*args, **kwargs):
            return question_instance_id

        async def fake_fetch_question_detail(*args, **kwargs):
            return {
                "question_id": "S2Q1",
                "prompt": "Who is the target user?",
            }

        async def fake_build_question_stream_context(*args, **kwargs):
            return {
                "project_id": kwargs["project_id"],
                "question_instance_id": kwargs["question_instance_id"],
                "fallback_content": kwargs["fallback_content"],
            }

        with (
            patch.object(
                turn_commit,
                "resolve_askable_question_id",
                fake_resolve_askable_question_id,
            ),
            patch.object(
                turn_commit,
                "resolve_next_question_id",
                fake_resolve_next_question_id,
            ),
            patch.object(
                turn_commit,
                "ensure_question_instance",
                fake_ensure_question_instance,
            ),
            patch.object(
                turn_commit,
                "fetch_chat_question_detail",
                fake_fetch_question_detail,
            ),
            patch.object(
                turn_commit,
                "build_question_stream_context",
                fake_build_question_stream_context,
            ),
        ):
            result = await turn_commit.commit_standard_next_turn(
                fake_session,
                org_id="org-1",
                gate_context={
                    "project_id": "project-1",
                    "bank_version_id": "bank-version-1",
                    "stage_status": "in_progress",
                    "state_json": {},
                    "state_meta": {},
                    "latest_answer": "done",
                    "output_locale": "en",
                    "project_settings": {},
                },
                runtime_row={"current_question_bank_question_id": uuid4()},
                runtime_stage="market",
                runtime_variant="default",
                next_question_id=next_question_id,
                updated_missing_paths=["target_user.raw"],
                state_json={},
                stage_status_ready=None,
                schema_paths=[],
                decision={
                    "final_verdict": "pass",
                    "model_verdict": "pass",
                    "missing_points": [],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                    "risk_notes": [],
                    "score": {},
                    "overall": 1.0,
                },
                group_enabled=False,
                group_max=1,
                transition_enabled=False,
                planner_settings={"enabled": False},
                planned_question_id=None,
                planned_question_prompt=None,
                rolling_summary="Summary",
                key_points=[],
                request_id="eval-request-1",
                turn_event_meta={"request_id": "turn-request-1"},
            )

        self.assertEqual(result.assistant_content, "Who is the target user?")
        self.assertIsNone(result.stage_gate_ready_payload)
        self.assertEqual(result.question_stream_context["request_id"], "turn-request-1")
        self.assertIn("UPDATE project_runtime", fake_session.executed[-1][0])


class ChatQuestionRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_question_detail_rejects_missing_prompt(self) -> None:
        fake_session = _FakeSession(_FakeResult({"id": "question-1"}))

        with self.assertRaises(chat.HTTPException) as exc:
            await question_runtime.fetch_chat_question_detail(fake_session, uuid4())

        self.assertEqual(exc.exception.status_code, 500)
        self.assertEqual(exc.exception.detail, "Question prompt not found.")

    async def test_ensure_question_instance_returns_inserted_id(self) -> None:
        question_instance_id = uuid4()
        fake_session = _FakeSession(_FakeResult({"id": question_instance_id}))

        result = await question_runtime.ensure_question_instance(
            fake_session,
            "project-1",
            uuid4(),
        )

        self.assertEqual(result, question_instance_id)
        statement, params = fake_session.executed[-1]
        self.assertIn("INSERT INTO project_question_instances", statement)
        self.assertEqual(params["project_id"], "project-1")


class StreamQuestionResponseEventsTests(unittest.IsolatedAsyncioTestCase):
    async def test_ai_draft_message_localizes_and_avoids_inline_code(self) -> None:
        zh_message = ai_assist.format_ai_draft_message(
            "自由职业者在接到模糊客户需求时，需要先拆解任务。",
            output_locale="zh",
        )

        self.assertIn("下面是 AI 帮你起草的版本", zh_message)
        self.assertIn("[AI Draft]", zh_message)
        self.assertNotIn("`", zh_message)

    async def test_question_rewrite_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "question_rewrite_chat")
            self.assertEqual(
                kwargs["expected_mutation"],
                project_question_prompts.PromptMutationClass.VISIBLE_COPY_ONLY,
            )
            return types.SimpleNamespace(
                ok=True,
                parsed=types.SimpleNamespace(
                    prompt="What is your first distribution channel?"
                ),
            )

        with patch.object(
            project_question_prompts,
            "execute_prompt_task",
            new=fake_executor,
        ):
            rewritten = await project_question_prompts.run_chat_question_rewrite(
                None,
                {
                    "prompt": "Distribution?",
                    "schema_paths": ["market_strategy.channels"],
                },
                latest_answer="Students use Discord.",
                output_locale="en",
            )

        self.assertEqual(rewritten, "What is your first distribution channel?")

    async def test_ai_assist_draft_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "ai_assist")
            self.assertEqual(
                kwargs["expected_mutation"],
                followup_compose.PromptMutationClass.VISIBLE_COPY_ONLY,
            )
            return types.SimpleNamespace(
                ok=True,
                content='"Students lose time clarifying vague client briefs."',
                model="test-model",
            )

        with patch.object(ai_assist, "execute_prompt_task", new=fake_executor):
            draft, model, output_locale = await ai_assist.run_ai_assist_draft(
                None,
                {
                    "prompt": "What problem are you solving?",
                    "validation_rule": "one sentence",
                },
                context_summary="Freelancer workflow tool.",
                latest_answer="",
                output_locale="en",
            )

        self.assertEqual(draft, "Students lose time clarifying vague client briefs.")
        self.assertEqual(model, "test-model")
        self.assertEqual(output_locale, "en")

    async def test_ai_assist_stream_uses_prompt_runtime_boundary(self) -> None:
        stream = object()
        prepared_result = types.SimpleNamespace(task_key="ai_assist", ok=True)

        async def fake_prepare(_session, context, **kwargs):
            self.assertEqual(context.task_key, "ai_assist")
            self.assertEqual(
                kwargs["expected_mutation"],
                ai_assist.PromptMutationClass.VISIBLE_COPY_ONLY,
            )
            self.assertIs(
                kwargs["provider_check"],
                ai_assist.has_available_provider,
            )
            return prepared_result

        async def fake_stream(prepared, **kwargs):
            self.assertIs(prepared, prepared_result)
            self.assertIs(kwargs["stream_call"], ai_assist.call_llm_stream)
            return types.SimpleNamespace(
                ok=True,
                stream=stream,
                model="test-stream-model",
                provider="openai",
            )

        with (
            patch.object(ai_assist, "prepare_prompt_task", new=fake_prepare),
            patch.object(ai_assist, "stream_prepared_prompt_task", new=fake_stream),
        ):
            stream_result, model, output_locale, draft = (
                await ai_assist.run_ai_assist_draft_stream(
                    None,
                    {
                        "prompt": "What problem are you solving?",
                        "validation_rule": "one sentence",
                    },
                    context_summary="Freelancer workflow tool.",
                    latest_answer="",
                    output_locale="en",
                )
            )

        self.assertIs(stream_result.stream, stream)
        self.assertEqual(model, "test-stream-model")
        self.assertEqual(output_locale, "en")
        self.assertIsNone(draft)

    async def test_persist_ai_draft_message_sets_system_actor(self) -> None:
        fake_session = _FakeSession()
        question_instance_id = uuid4()

        await ai_assist.persist_ai_draft_message(
            fake_session,
            project_id=str(uuid4()),
            org_id=str(uuid4()),
            stage="problem",
            variant="default",
            question_instance_id=question_instance_id,
            assistant_content="下面是 AI 帮你起草的版本。",
            draft="自由职业者在接到模糊客户需求时，需要先拆解任务。",
            draft_model="test-model",
            content_locale="zh",
        )

        actor_types = [
            (params or {}).get("actor_type")
            for statement, params in fake_session.executed
            if "app.actor_type" in statement
        ]
        self.assertEqual(actor_types[-1], "system")
        insert_params = [
            params
            for statement, params in fake_session.executed
            if "INSERT INTO conversation_messages" in statement
        ][0]
        self.assertEqual(insert_params["meta"]["content_locale"], "zh")
        self.assertEqual(insert_params["meta"]["source"], "ai_assist_draft")

    async def test_question_stream_context_tracks_user_answer_locale(self) -> None:
        with patch.object(
            followup_compose,
            "has_available_provider",
            return_value=False,
        ):
            context = await followup_compose.build_question_stream_context(
                None,
                project_id=str(uuid4()),
                org_id=str(uuid4()),
                stage="problem",
                variant="default",
                question_instance_id=uuid4(),
                question_detail={"question_id": "problem.target_user"},
                fallback_content="Who is the primary user/customer?",
                meta={"content_locale": "en"},
                output_locale="en",
                latest_answer="第一版优先 AI 拆解任务，因为任务经常不明确。",
                context_summary=None,
            )

        self.assertEqual(context["output_locale"], "zh")
        self.assertEqual(context["requested_output_locale"], "en")
        self.assertEqual(context["meta"]["content_locale"], "zh")
        self.assertEqual(context["meta"]["locale_source"], "latest_user_answer")

    async def test_question_stream_context_uses_context_language_for_quick_action(
        self,
    ) -> None:
        with patch.object(followup_compose, "has_available_provider", return_value=False):
            context = await followup_compose.build_question_stream_context(
                None,
                project_id=str(uuid4()),
                org_id=str(uuid4()),
                stage="problem",
                variant="default",
                question_instance_id=uuid4(),
                question_detail={"question_id": "problem.buyer_user"},
                fallback_content="Who uses and who pays?",
                meta={"content_locale": "en"},
                output_locale="en",
                latest_answer="I'm not sure",
                context_summary="这个项目关注日程管理和 AI 拆解任务。",
                message_meta={"answer_mode": "unknown"},
            )

        self.assertEqual(context["output_locale"], "zh")
        self.assertEqual(context["requested_output_locale"], "en")
        self.assertEqual(context["meta"]["content_locale"], "zh")
        self.assertEqual(context["meta"]["locale_source"], "latest_user_answer")

    async def test_question_stream_context_prepares_compose_runtime(self) -> None:
        async def fake_prepare(_session, context, **kwargs):
            self.assertEqual(context.task_key, "question_compose")
            self.assertEqual(
                kwargs["expected_mutation"],
                followup_compose.PromptMutationClass.VISIBLE_COPY_ONLY,
            )
            self.assertIs(
                kwargs["provider_check"],
                followup_compose.has_available_provider,
            )
            return types.SimpleNamespace(
                ok=True,
                messages=[{"role": "user", "content": "Compose the next question."}],
                timeout_ms=3210,
                trace={"task_key": "question_compose"},
                failure=None,
            )

        with patch.object(followup_compose, "prepare_prompt_task", new=fake_prepare):
            context = await followup_compose.build_question_stream_context(
                None,
                project_id=str(uuid4()),
                org_id=str(uuid4()),
                stage="problem",
                variant="default",
                question_instance_id=uuid4(),
                question_detail={
                    "question_id": "problem.buyer_user",
                    "prompt": "Who uses and who pays?",
                },
                fallback_content="Who uses and who pays?",
                meta={"content_locale": "en"},
                output_locale="en",
                latest_answer="Students first.",
                context_summary=None,
            )

        self.assertEqual(
            context["compose_messages"],
            [{"role": "user", "content": "Compose the next question."}],
        )
        self.assertEqual(context["compose_timeout_ms"], 3210)
        self.assertEqual(context["compose_trace"], {"task_key": "question_compose"})
        self.assertIsNone(context["compose_prepare_failure"])

    async def test_followup_stream_context_tracks_user_answer_locale(self) -> None:
        with patch.object(followup_compose, "has_available_provider", return_value=False):
            context = await followup_compose.build_followup_stream_context(
                None,
                project_id=str(uuid4()),
                org_id=str(uuid4()),
                stage="problem",
                variant="default",
                question_instance_id=uuid4(),
                question_detail={"question_id": "problem.priority"},
                decision={
                    "missing_points": ["MVP priority"],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                },
                fallback_content="请补充第一版优先级。",
                meta={"content_locale": "en"},
                output_locale="en",
                latest_answer="日程管理，AI 拆解任务，AI 分配任务这些",
                context_summary=None,
            )

        self.assertEqual(context["output_locale"], "zh")
        self.assertEqual(context["requested_output_locale"], "en")
        self.assertEqual(context["meta"]["content_locale"], "zh")
        self.assertEqual(context["meta"]["locale_source"], "latest_user_answer")

    async def test_followup_stream_context_prepares_compose_runtime(self) -> None:
        async def fake_prepare(_session, context, **kwargs):
            self.assertEqual(context.task_key, "followup_compose")
            self.assertEqual(
                kwargs["expected_mutation"],
                followup_compose.PromptMutationClass.VISIBLE_COPY_ONLY,
            )
            return types.SimpleNamespace(
                ok=True,
                messages=[{"role": "user", "content": "Compose the follow-up."}],
                timeout_ms=4321,
                trace={"task_key": "followup_compose"},
                failure=None,
            )

        with patch.object(followup_compose, "prepare_prompt_task", new=fake_prepare):
            context = await followup_compose.build_followup_stream_context(
                None,
                project_id=str(uuid4()),
                org_id=str(uuid4()),
                stage="problem",
                variant="default",
                question_instance_id=uuid4(),
                question_detail={
                    "question_id": "problem.priority",
                    "prompt": "What comes first?",
                },
                decision={
                    "missing_points": ["MVP priority"],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                },
                fallback_content="Please clarify the MVP priority.",
                meta={"content_locale": "en"},
                output_locale="en",
                latest_answer="Maybe scheduling.",
                context_summary=None,
            )

        self.assertEqual(
            context["compose_messages"],
            [{"role": "user", "content": "Compose the follow-up."}],
        )
        self.assertEqual(context["compose_timeout_ms"], 4321)
        self.assertEqual(context["compose_trace"], {"task_key": "followup_compose"})
        self.assertIsNone(context["compose_prepare_failure"])

    async def test_persist_fallback_question_message_sets_source_and_id(self) -> None:
        fake_session = _FakeSession(_FakeResult({"id": 77}))
        context = {
            "project_id": str(uuid4()),
            "stage": "problem",
            "variant": "default",
            "question_instance_id": uuid4(),
            "fallback_content": "Please clarify the MVP priority.",
            "meta": {"schema_version": "v1"},
            "fallback_source": followup_compose.FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
            "compose_trace": {
                "task_key": "followup_compose",
                "redacted": True,
            },
            "compose_prepare_failure": "provider_unavailable",
        }

        message_id = await message_persistence.persist_fallback_question_message(
            fake_session,
            context,
            fallback_source=context["fallback_source"],
        )

        self.assertEqual(message_id, 77)
        self.assertEqual(context["assistant_message_id"], 77)
        insert_params = [
            params
            for statement, params in fake_session.executed
            if "INSERT INTO conversation_messages" in statement
        ][0]
        self.assertEqual(insert_params["content"], "Please clarify the MVP priority.")
        self.assertEqual(
            insert_params["meta"]["source"],
            followup_compose.FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
        )
        self.assertEqual(insert_params["meta"]["display_format"], "markdown")
        self.assertEqual(
            insert_params["meta"]["prompt_task_trace"]["task_key"],
            "followup_compose",
        )
        self.assertEqual(
            insert_params["meta"]["prompt_task_trace"]["failure_reason"],
            "provider_unavailable",
        )

    async def test_stream_updates_existing_assistant_message_with_sanitized_content(
        self,
    ) -> None:
        fake_session = _FakeSession()
        context = {
            "project_id": str(uuid4()),
            "org_id": str(uuid4()),
            "stage": "problem",
            "variant": "default",
            "question_instance_id": uuid4(),
            "fallback_content": "Please clarify the MVP priority.",
            "meta": {},
            "assistant_message_id": 77,
            "compose_messages": [{"role": "user", "content": "Compose a follow-up."}],
            "compose_task": "followup_compose",
            "compose_timeout_ms": 3210,
            "compose_trace": {
                "task_key": "followup_compose",
                "redacted": True,
            },
            "success_source": followup_compose.FOLLOWUP_COMPOSE_SOURCE,
            "fallback_source": followup_compose.FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
            "answer_evaluation_request_id": str(uuid4()),
            "latency_spans": {},
        }

        async def fake_stream():
            yield "<DISPLAY>"
            yield "Please name the MVP priority problem."
            yield "</DISPLAY>"

        async def fake_call_llm_stream(*args, **kwargs):
            return types.SimpleNamespace(
                model="test-model",
                provider="openai",
                stream=fake_stream(),
            )

        timeout_inputs = []

        def fake_start_timeout(timeout_ms=None):
            timeout_inputs.append(timeout_ms)
            return 0

        with (
            patch.object(
                question_response,
                "AdminAsyncSessionLocal",
                lambda: _FakeSessionContext(fake_session),
            ),
            patch.object(question_response, "call_llm_stream", fake_call_llm_stream),
            patch.object(
                question_response,
                "resolve_question_compose_start_timeout_sec",
                side_effect=fake_start_timeout,
            ),
        ):
            events = [
                event
                async for event in question_response.stream_question_response_events(
                    context,
                    actor_user_id=uuid4(),
                )
            ]

        self.assertTrue(
            any("Please name the MVP priority problem." in event for event in events)
        )
        self.assertFalse(
            any(
                "INSERT INTO conversation_messages" in statement
                for statement, _ in fake_session.executed
            )
        )
        actor_types = [
            (params or {}).get("actor_type")
            for statement, params in fake_session.executed
            if "app.actor_type" in statement
        ]
        self.assertEqual(actor_types[-1], "system")
        message_updates = [
            params
            for statement, params in fake_session.executed
            if "UPDATE conversation_messages" in statement
        ]
        self.assertEqual(message_updates[0]["message_id"], 77)
        self.assertEqual(
            message_updates[0]["content"],
            "Please name the MVP priority problem.",
        )
        self.assertEqual(
            message_updates[0]["meta"]["source"],
            followup_compose.FOLLOWUP_COMPOSE_SOURCE,
        )
        self.assertTrue(message_updates[0]["meta"]["streamed"])
        self.assertEqual(
            message_updates[0]["meta"]["prompt_task_trace"]["task_key"],
            "followup_compose",
        )
        self.assertEqual(
            message_updates[0]["meta"]["prompt_task_trace"]["model"],
            "test-model",
        )
        self.assertEqual(
            message_updates[0]["meta"]["prompt_task_trace"]["provider"],
            "openai",
        )

        evaluation_updates = [
            params
            for statement, params in fake_session.executed
            if "UPDATE answer_evaluations" in statement
        ]
        self.assertEqual(
            evaluation_updates[0]["content"],
            "Please name the MVP priority problem.",
        )
        self.assertIn("compose_start", context["latency_spans"])
        self.assertIn("compose_first_token", context["latency_spans"])
        self.assertIn("compose_complete", context["latency_spans"])
        self.assertEqual(timeout_inputs, [3210])

    async def test_stream_persists_partial_composed_content_after_stream_error(
        self,
    ) -> None:
        fake_session = _FakeSession()
        context = {
            "project_id": str(uuid4()),
            "org_id": str(uuid4()),
            "stage": "problem",
            "variant": "default",
            "question_instance_id": uuid4(),
            "fallback_content": "Please clarify the MVP priority.",
            "meta": {},
            "assistant_message_id": 77,
            "compose_messages": [{"role": "user", "content": "Compose a follow-up."}],
            "compose_task": "followup_compose",
            "success_source": followup_compose.FOLLOWUP_COMPOSE_SOURCE,
            "fallback_source": followup_compose.FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
        }

        async def fake_stream():
            yield "Please name "
            yield "the MVP priority problem."
            raise RuntimeError("stream ended abruptly")

        async def fake_call_llm_stream(*args, **kwargs):
            return types.SimpleNamespace(
                model="test-model",
                provider="openai",
                stream=fake_stream(),
            )

        with (
            patch.object(
                question_response,
                "AdminAsyncSessionLocal",
                lambda: _FakeSessionContext(fake_session),
            ),
            patch.object(question_response, "call_llm_stream", fake_call_llm_stream),
            patch.object(
                question_response,
                "resolve_question_compose_start_timeout_sec",
                return_value=0,
            ),
        ):
            events = [
                event
                async for event in question_response.stream_question_response_events(
                    context,
                    actor_user_id=uuid4(),
                )
            ]

        self.assertIn("Please name", "".join(events))
        message_updates = [
            params
            for statement, params in fake_session.executed
            if "UPDATE conversation_messages" in statement
        ]
        self.assertEqual(
            message_updates[0]["content"],
            "Please name the MVP priority problem.",
        )
        self.assertEqual(
            message_updates[0]["meta"]["source"],
            followup_compose.FOLLOWUP_COMPOSE_SOURCE,
        )

    async def test_update_streamed_question_message_reports_skipped_update(
        self,
    ) -> None:
        fake_session = _FakeSession(_FakeResult(rowcount=0))
        context = {
            "project_id": str(uuid4()),
            "org_id": str(uuid4()),
            "stage": "problem",
            "variant": "default",
            "question_instance_id": uuid4(),
            "meta": {},
            "assistant_message_id": 77,
            "answer_evaluation_request_id": str(uuid4()),
        }

        updated = await message_persistence.update_streamed_question_message(
            fake_session,
            context,
            content="Please name the MVP priority problem.",
            source=followup_compose.FOLLOWUP_COMPOSE_SOURCE,
            compose_model="test-model",
            compose_provider="openai",
            streamed=True,
        )

        self.assertFalse(updated)
        self.assertTrue(
            any(
                "UPDATE conversation_messages" in statement
                for statement, _ in fake_session.executed
            )
        )
        self.assertFalse(
            any(
                "UPDATE answer_evaluations" in statement
                for statement, _ in fake_session.executed
            )
        )

    async def test_stream_falls_back_when_first_compose_chunk_times_out(self) -> None:
        fake_session = _FakeSession()
        context = {
            "project_id": str(uuid4()),
            "org_id": str(uuid4()),
            "stage": "problem",
            "variant": "default",
            "question_instance_id": uuid4(),
            "fallback_content": "Please clarify the MVP priority.",
            "meta": {},
            "assistant_message_id": 77,
            "compose_messages": [{"role": "user", "content": "Compose a follow-up."}],
            "compose_task": "followup_compose",
            "success_source": followup_compose.FOLLOWUP_COMPOSE_SOURCE,
            "fallback_source": followup_compose.FOLLOWUP_COMPOSE_FALLBACK_SOURCE,
        }

        async def fake_stream():
            await question_response.asyncio.sleep(0.05)
            yield "Please name the MVP priority problem."

        async def fake_call_llm_stream(*args, **kwargs):
            return types.SimpleNamespace(
                model="test-model",
                provider="openai",
                stream=fake_stream(),
            )

        with (
            patch.object(
                question_response,
                "AdminAsyncSessionLocal",
                lambda: _FakeSessionContext(fake_session),
            ),
            patch.object(question_response, "call_llm_stream", fake_call_llm_stream),
            patch.object(
                question_response,
                "resolve_question_compose_start_timeout_sec",
                return_value=0.01,
            ),
        ):
            events = [
                event
                async for event in question_response.stream_question_response_events(
                    context,
                    actor_user_id=uuid4(),
                )
            ]

        self.assertIn("Please clarify", "".join(events))
        self.assertIn("the MVP priority.", "".join(events))
        self.assertFalse(
            any(
                "UPDATE conversation_messages" in statement
                for statement, _ in fake_session.executed
            )
        )


class BuildSyncExtractionPreviewTests(unittest.TestCase):
    def test_build_sync_extraction_preview_updates_current_stage_and_pending_state(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "problem.one_line",
                        "market.uvp.one_line",
                    ]
                },
                {
                    "problem": {
                        "one_line": "Manual monthly close is still done in spreadsheets."
                    },
                    "market": {
                        "uvp": {"one_line": "Close faster with audit-ready workflows."}
                    },
                },
                current_stage="problem",
                answer="Manual monthly close is still done in spreadsheets.",
                state_json={"target_user": {"core": "Finance leads at SMBs"}},
                state_meta={},
                ai_assisted=True,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "problem.one_line",
                "market.uvp.one_line",
            ],
        )
        self.assertIn(
            (
                "state",
                "problem.one_line",
                "Manual monthly close is still done in spreadsheets.",
            ),
            extraction_updates,
        )
        self.assertIn(
            (
                "pending",
                "market.uvp.one_line",
                "Close faster with audit-ready workflows.",
            ),
            extraction_updates,
        )
        self.assertEqual(
            state_json["problem"]["one_line"],
            "Manual monthly close is still done in spreadsheets.",
        )
        self.assertEqual(
            state_json["target_user"]["core"],
            "Finance leads at SMBs",
        )
        pending_value = state_meta["pending_confirm"]["market"]["uvp"]["one_line"]
        self.assertEqual(
            pending_value["value"],
            "Close faster with audit-ready workflows.",
        )
        self.assertEqual(pending_value["source"], "ai")
        self.assertEqual(pending_value["evidence_level"], "E0")
        self.assertEqual(
            state_meta["answer_meta"]["problem.one_line"]["source"],
            "ai",
        )
        self.assertEqual(
            state_meta["ai_assisted_paths"]["problem"],
            ["problem.one_line"],
        )
        self.assertEqual(
            state_meta["ai_assisted_paths"]["market"],
            ["market.uvp.one_line"],
        )

    def test_build_sync_extraction_preview_leaves_state_untouched_when_nothing_resolves(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["problem.one_line"]},
                {},
                current_stage="problem",
                answer="",
                state_json={"problem": {"one_line": "Existing value"}},
                state_meta={"answer_meta": {}},
                ai_assisted=False,
            )
        )

        self.assertEqual(resolved_paths, [])
        self.assertEqual(extraction_updates, [])
        self.assertEqual(state_json, {"problem": {"one_line": "Existing value"}})
        self.assertEqual(
            state_meta,
            {
                "answer_meta": {},
                "pending_confirm": {},
            },
        )

    def test_build_sync_extraction_preview_falls_back_for_single_schema_path(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["market_strategy.uvp.one_line"]},
                {},
                current_stage="market",
                answer="The clearest validation brief for early-stage teams.",
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(resolved_paths, ["market_strategy.uvp.one_line"])
        self.assertIn(
            (
                "state",
                "market_strategy.uvp.one_line",
                "The clearest validation brief for early-stage teams.",
            ),
            extraction_updates,
        )
        self.assertEqual(
            state_json["market_strategy"]["uvp"]["one_line"],
            "The clearest validation brief for early-stage teams.",
        )
        self.assertEqual(
            state_meta["answer_meta"]["market_strategy.uvp.one_line"][
                "resolution_status"
            ],
            "answered",
        )

    def test_target_user_question_falls_back_when_extract_times_out(self) -> None:
        answer = (
            "P0 segment: university incubator and accelerator program managers "
            "in the US, UK, Australia, and New Zealand who support 5-30 "
            "early-stage software founder teams per cohort. The day-to-day user "
            "is the program manager or mentor; the startup teams provide the raw "
            "idea inputs. Market type: B2B, because the institution pays."
        )

        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "S1Q3",
                    "schema_paths": [
                        "target_user.core",
                        "target_user.priority_segment",
                        "target_user.market_type_inferred",
                    ],
                },
                {},
                current_stage="problem",
                answer=answer,
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertIn("target_user.core", resolved_paths)
        self.assertIn("target_user.priority_segment", resolved_paths)
        self.assertIn(
            (
                "state",
                "target_user.core",
                "university incubator and accelerator program managers in the US, UK, Australia, and New Zealand who support 5-30 early-stage software founder teams per cohort",
            ),
            extraction_updates,
        )
        self.assertEqual(
            state_json["target_user"]["priority_segment"],
            state_json["target_user"]["core"],
        )
        self.assertEqual(state_json["target_user"]["market_type_inferred"], "B2B")
        self.assertEqual(
            state_meta["answer_meta"]["target_user.core"]["resolution_status"],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_time_money_impact(self) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["impact.time_impact", "impact.money_impact"]},
                {},
                current_stage="problem",
                answer=(
                    "Time wasted: 3 hours per week\n"
                    "Money impact: $500 lost revenue per month"
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(resolved_paths, ["impact.time_impact", "impact.money_impact"])
        self.assertIn(
            ("state", "impact.time_impact", "3 hours per week"), extraction_updates
        )
        self.assertIn(
            ("state", "impact.money_impact", "$500 lost revenue per month"),
            extraction_updates,
        )
        self.assertEqual(state_json["impact"]["time_impact"], "3 hours per week")
        self.assertEqual(
            state_json["impact"]["money_impact"],
            "$500 lost revenue per month",
        )
        self.assertEqual(
            state_meta["answer_meta"]["impact.time_impact"]["resolution_status"],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_severity_fields(self) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["problem.severity_score", "problem.severity_reason"]},
                {},
                current_stage="problem",
                answer=(
                    "Severity score: 8 out of 10. "
                    "Reason 1: weak framing wastes mentor time. "
                    "Reason 2: teams build before validating the MVP."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths, ["problem.severity_score", "problem.severity_reason"]
        )
        self.assertIn(("state", "problem.severity_score", 8), extraction_updates)
        self.assertEqual(state_json["problem"]["severity_score"], 8)
        self.assertIn("weak framing", state_json["problem"]["severity_reason"])
        self.assertEqual(
            state_meta["answer_meta"]["problem.severity_score"]["resolution_status"],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_alternatives_fields(self) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "alternatives.current_solutions[]",
                        "alternatives.satisfaction_score",
                        "alternatives.main_complaints[]",
                    ]
                },
                {},
                current_stage="problem",
                answer=(
                    "Current solutions: Google Docs, Notion templates, and ChatGPT. "
                    "Satisfaction score: 5 out of 10. "
                    "Main complaints: scattered context, repeated questions, weak reports."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "alternatives.current_solutions[]",
                "alternatives.satisfaction_score",
                "alternatives.main_complaints[]",
            ],
        )
        self.assertIn(
            ("state", "alternatives.satisfaction_score", 5), extraction_updates
        )
        self.assertEqual(state_json["alternatives"]["satisfaction_score"], 5)
        self.assertIn("Google Docs", state_json["alternatives"]["current_solutions"][0])
        self.assertIn(
            "scattered context", state_json["alternatives"]["main_complaints"][0]
        )
        self.assertEqual(
            state_meta["answer_meta"]["alternatives.satisfaction_score"][
                "resolution_status"
            ],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_validation_evidence_fields(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "evidence.user_interview_count",
                        "evidence.key_learnings[]",
                        "evidence.data_evidence",
                        "evidence.key_unknowns[]",
                    ]
                },
                {},
                current_stage="problem",
                answer="\n".join(
                    [
                        "User conversations: 6 informal conversations with student founders.",
                        "Key learnings: founders want sharper framing and mentors want comparable summaries.",
                        "Quant evidence/proxies: no paid pilots yet; 3-5 hours/week preparing review notes.",
                        "Key unknowns: willingness to pay and whether teams complete the interview.",
                    ]
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "evidence.user_interview_count",
                "evidence.key_learnings[]",
                "evidence.data_evidence",
                "evidence.key_unknowns[]",
            ],
        )
        self.assertIn(
            (
                "state",
                "evidence.user_interview_count",
                "6 informal conversations with student founders.",
            ),
            extraction_updates,
        )
        self.assertIn(
            "founders want sharper", state_json["evidence"]["key_learnings"][0]
        )
        self.assertIn("3-5 hours/week", state_json["evidence"]["data_evidence"])
        self.assertIn("willingness to pay", state_json["evidence"]["key_unknowns"][0])
        self.assertEqual(
            state_meta["answer_meta"]["evidence.key_unknowns[]"]["resolution_status"],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_market_business_model_fields(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "market_strategy.business_model.payer_role",
                        "market_strategy.business_model.revenue_model",
                    ]
                },
                {},
                current_stage="market",
                answer=(
                    "Type: B2B. Payer: university incubator director. "
                    "Revenue model: annual SaaS license per program."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "market_strategy.business_model.payer_role",
                "market_strategy.business_model.revenue_model",
            ],
        )
        self.assertIn(
            (
                "state",
                "market_strategy.business_model.payer_role",
                "university incubator director",
            ),
            extraction_updates,
        )
        self.assertEqual(
            state_json["market_strategy"]["business_model"]["revenue_model"],
            "annual SaaS license per program.",
        )

    def test_build_sync_extraction_preview_extracts_market_competition_and_gtm_fields(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "market_strategy.competition.competitor_types[]",
                    "market_strategy.go_to_market.primary_channels[]",
                ]
            },
            {},
            current_stage="market",
            answer=(
                "Competitor types: generic AI chat tools, survey builders, "
                "mentor management tools, and Notion/Airtable templates.\n"
                "Primary channels: direct university incubator outreach and mentor referrals."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertEqual(
            resolved_paths,
            [
                "market_strategy.competition.competitor_types[]",
                "market_strategy.go_to_market.primary_channels[]",
            ],
        )
        self.assertIn(
            "generic AI chat tools",
            state_json["market_strategy"]["competition"]["competitor_types"][0],
        )
        self.assertIn(
            "direct university incubator outreach",
            state_json["market_strategy"]["go_to_market"]["primary_channels"][0],
        )

    def test_build_sync_extraction_preview_extracts_tech_data_access_rights(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.data_ai_scalability.data_access_rights"
                    ]
                },
                {},
                current_stage="tech",
                answer=(
                    "Required data: founder project text and mentor comments. "
                    "Access plan: users enter or approve the data inside the workspace, "
                    "with org-scoped permissions. Refresh cadence: real-time during review."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            ["tech_execution.data_ai_scalability.data_access_rights"],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.data_ai_scalability.data_access_rights",
                "users enter or approve the data inside the workspace, with org-scoped permissions",
            ),
            extraction_updates,
        )
        self.assertIn(
            "org-scoped permissions",
            state_json["tech_execution"]["data_ai_scalability"]["data_access_rights"],
        )

    def test_build_sync_extraction_preview_extracts_rights_access_label(
        self,
    ) -> None:
        answer = (
            "A) Required data: founder-entered project context, staged answers, "
            "mentor edits, generated summaries/reports, and organization membership. "
            "Rights/access: user-generated and organization-approved data entered "
            "into the workspace.\n"
            "B) Collection/refresh: collected during chat and review screens, "
            "refreshed immediately after answers or context edits.\n"
            "C) Quality gaps: vague founder answers and inconsistent terminology."
        )

        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.data_ai_scalability.data_access_rights"
                    ]
                },
                {},
                current_stage="tech",
                answer=answer,
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            ["tech_execution.data_ai_scalability.data_access_rights"],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.data_ai_scalability.data_access_rights",
                "user-generated and organization-approved data entered into the workspace",
            ),
            extraction_updates,
        )
        self.assertNotIn(
            "Collection",
            state_json["tech_execution"]["data_ai_scalability"][
                "data_access_rights"
            ],
        )

    def test_build_sync_extraction_preview_extracts_dependencies_and_risks(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.dependencies.key_integrations",
                        "tech_execution.roadmap_risks.top_technical_risks",
                    ]
                },
                {},
                current_stage="tech",
                answer=(
                    "Key integrations/APIs: OpenAI-compatible LLM provider, "
                    "managed Postgres, email delivery provider, web/app hosting, "
                    "and later Stripe for billing. Top technical risks: LLM "
                    "latency/cost, email delivery reliability, and report "
                    "traceability. Mitigation: provider abstraction and "
                    "regression tests."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertIn("tech_execution.dependencies.key_integrations", resolved_paths)
        self.assertIn(
            "tech_execution.roadmap_risks.top_technical_risks", resolved_paths
        )
        self.assertIn(
            "managed Postgres",
            state_json["tech_execution"]["dependencies"]["key_integrations"],
        )
        self.assertIn(
            "email delivery reliability",
            state_json["tech_execution"]["roadmap_risks"]["top_technical_risks"],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.dependencies.key_integrations",
                [
                    "OpenAI-compatible LLM provider",
                    "managed Postgres",
                    "email delivery provider",
                    "web/app hosting",
                    "later Stripe for billing",
                ],
            ),
            extraction_updates,
        )

    def test_build_sync_extraction_preview_extracts_top_risks_and_experiments_label(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "tech_execution.roadmap_risks.top_technical_risks",
                ]
            },
            {},
            current_stage="tech",
            answer=(
                "A) Team: one technical founder/full-stack engineer. "
                "B) Process: lightweight Kanban and regression tests. "
                "C) 6-12 month roadmap: stabilize core interview/report flow. "
                "D) Top risks and experiments: LLM consistency risk tested "
                "with fixture suites; Stage Gate transition risk tested with "
                "full-path recordings; university privacy/procurement risk "
                "tested with one lightweight DPA/security review."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertIn(
            "tech_execution.roadmap_risks.top_technical_risks",
            resolved_paths,
        )
        self.assertTrue(
            any(
                "Stage Gate transition risk" in risk
                for risk in state_json["tech_execution"]["roadmap_risks"][
                    "top_technical_risks"
                ]
            ),
        )

    def test_build_sync_extraction_preview_extracts_top_tech_worries_label(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "tech_execution.roadmap_risks.top_technical_risks",
                ]
            },
            {},
            current_stage="tech",
            answer=(
                "Top tech worries: LLM summaries may miss or invent details, "
                "Stage Gate may advance with incomplete context, reports may "
                "lose traceability to confirmed answers, university users may "
                "expect stronger privacy controls, and chat latency may feel "
                "too slow. Mitigation: confirmed context review, deterministic "
                "stage-transition tests, prompt traces, provider fallbacks, "
                "and visible progress/retry states."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertIn(
            "tech_execution.roadmap_risks.top_technical_risks",
            resolved_paths,
        )
        self.assertTrue(
            any(
                "Stage Gate" in risk
                for risk in state_json["tech_execution"]["roadmap_risks"][
                    "top_technical_risks"
                ]
            ),
        )

    def test_build_sync_extraction_preview_extracts_risk_mitigation_plan_label(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "tech_execution.roadmap_risks.top_technical_risks",
                    "tech_execution.roadmap_risks.risk_mitigation_plan",
                ]
            },
            {},
            current_stage="tech",
            answer=(
                "Top technical risks: LLM consistency, stage transition bugs, "
                "and privacy review delays. Risk mitigation plan: fixture-based "
                "regression tests, stage-gate smoke recordings, and a lightweight "
                "DPA/security checklist before pilots."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertIn(
            "tech_execution.roadmap_risks.risk_mitigation_plan",
            resolved_paths,
        )
        self.assertIn(
            "stage-gate smoke recordings",
            state_json["tech_execution"]["roadmap_risks"][
                "risk_mitigation_plan"
            ],
        )

    def test_build_sync_extraction_preview_extracts_tech_data_scalability(
        self,
    ) -> None:
        answer = (
            "A) Data sources and ownership: user-generated project answers, mentor "
            "comments, stage summaries, and generated reports owned by the workspace.\n"
            "B) Year-1 data volume: 20-50 pilot programs, 10-50 teams each, "
            "roughly tens of thousands of messages and hundreds of reports; "
            "growth could be 5-10x if cohort pilots convert.\n"
            "C) AI usage: core for extraction, summaries, and reports.\n"
            "D) Performance expectations: most chat turns under 10 seconds and "
            "pilot uptime target around 99%.\n"
            "E) 10x scaling strategy: queue report tasks, cache report artifacts, "
            "index runtime tables, and scale API/worker processes separately."
        )

        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.data_ai_scalability.data_sources",
                        "tech_execution.data_ai_scalability.data_volume_year1",
                        "tech_execution.data_ai_scalability.growth_expectations",
                        "tech_execution.data_ai_scalability.ai_usage",
                        "tech_execution.data_ai_scalability.performance_expectations",
                        "tech_execution.data_ai_scalability.scalability_strategy",
                    ]
                },
                {},
                current_stage="tech",
                answer=answer,
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "tech_execution.data_ai_scalability.data_sources",
                "tech_execution.data_ai_scalability.data_volume_year1",
                "tech_execution.data_ai_scalability.growth_expectations",
                "tech_execution.data_ai_scalability.ai_usage",
                "tech_execution.data_ai_scalability.performance_expectations",
                "tech_execution.data_ai_scalability.scalability_strategy",
            ],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.data_ai_scalability.ai_usage",
                "core for extraction, summaries, and reports.",
            ),
            extraction_updates,
        )
        data_ai = state_json["tech_execution"]["data_ai_scalability"]
        self.assertIn("workspace", data_ai["data_sources"])
        self.assertIn("20-50 pilot programs", data_ai["data_volume_year1"])
        self.assertIn("5-10x", data_ai["growth_expectations"])
        self.assertIn("under 10 seconds", data_ai["performance_expectations"])
        self.assertIn("queue report tasks", data_ai["scalability_strategy"])

    def test_build_sync_extraction_preview_extracts_tech_mvp_boundary(
        self,
    ) -> None:
        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.product_scope.current_status",
                        "tech_execution.product_scope.mvp_definition",
                    ]
                },
                {},
                current_stage="tech",
                answer=(
                    "Current status: working prototype with staged interview and "
                    "report generation. MVP must include project workspace, "
                    "problem/market/tech interview stages, summary confirmation, "
                    "DVF report, and exportable report view. Not in MVP: CRM "
                    "features, autonomous outreach, billing automation, and "
                    "multi-program analytics."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "tech_execution.product_scope.current_status",
                "tech_execution.product_scope.mvp_definition",
            ],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.product_scope.mvp_definition",
                (
                    "MVP must include project workspace, problem/market/tech "
                    "interview stages, summary confirmation, DVF report, and "
                    "exportable report view"
                ),
            ),
            extraction_updates,
        )
        self.assertIn(
            "working prototype",
            state_json["tech_execution"]["product_scope"]["current_status"],
        )

    def test_build_sync_extraction_preview_extracts_tech_compliance_plan(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "tech_execution.security_compliance.compliance_requirements",
                    "tech_execution.security_compliance.compliance_milestones",
                    "tech_execution.security_compliance.data_retention_policy",
                ]
            },
            {},
            current_stage="tech",
            answer=(
                "A) Regulations: GDPR-style privacy obligations for EU users and "
                "university data processing agreements. B) First compliance "
                "milestone: complete DPA/security checklist before paid pilots in "
                "Q3. C) Data retention/deletion plan: keep project data while the "
                "workspace is active, support export/delete on request, and purge "
                "inactive pilot data after 12 months."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertEqual(
            resolved_paths,
            [
                "tech_execution.security_compliance.compliance_requirements",
                "tech_execution.security_compliance.compliance_milestones",
                "tech_execution.security_compliance.data_retention_policy",
            ],
        )
        self.assertIn(
            "GDPR-style",
            state_json["tech_execution"]["security_compliance"][
                "compliance_requirements"
            ],
        )
        self.assertIn(
            "Q3",
            state_json["tech_execution"]["security_compliance"][
                "compliance_milestones"
            ],
        )

    def test_build_sync_extraction_preview_extracts_tech_compliance_natural_labels(
        self,
    ) -> None:
        resolved_paths, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "schema_paths": [
                    "tech_execution.security_compliance.audit_requirements",
                    "tech_execution.security_compliance.compliance_milestones",
                    "tech_execution.security_compliance.data_retention_policy",
                ]
            },
            {},
            current_stage="tech",
            answer=(
                "A) Required audits/certs: no formal certification for first "
                "design pilots, but GDPR-style DPA/security checklist first; "
                "SOC2 readiness becomes a 12-24 month milestone if "
                "universities demand it. B) Retention/deletion: keep workspace "
                "data while active, support export/delete on request, delete "
                "inactive pilot projects after 12 months unless renewed, and "
                "retain only minimal audit metadata. C) First milestone: "
                "technical founder owns a DPA/security checklist and "
                "deletion/export workflow before paid pilots in Q3."
            ),
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertEqual(
            resolved_paths,
            [
                "tech_execution.security_compliance.audit_requirements",
                "tech_execution.security_compliance.compliance_milestones",
                "tech_execution.security_compliance.data_retention_policy",
            ],
        )
        security = state_json["tech_execution"]["security_compliance"]
        self.assertIn("GDPR-style", security["audit_requirements"])
        self.assertIn("Q3", security["compliance_milestones"])
        self.assertIn("12 months", security["data_retention_policy"])

    def test_build_sync_extraction_preview_uses_optional_meta_wrapper(self) -> None:
        _, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["market_strategy.business_model.price"]},
                {
                    "market_strategy": {
                        "business_model": {
                            "price": {
                                "value": "$49/month",
                                "claim_type": "estimate",
                                "evidence_level": "E2",
                                "resolution_status": "partial",
                            }
                        }
                    }
                },
                current_stage="market",
                answer="$49/month",
                state_json={},
                state_meta={},
                ai_assisted=True,
            )
        )

        self.assertEqual(extraction_updates[0][0], "state")
        self.assertEqual(
            extraction_updates[0][1], "market_strategy.business_model.price"
        )
        self.assertEqual(extraction_updates[0][2]["value"], "$49/month")
        self.assertEqual(
            state_json["market_strategy"]["business_model"]["price"],
            "$49/month",
        )
        meta = state_meta["answer_meta"]["market_strategy.business_model.price"]
        self.assertEqual(meta["source"], "ai")
        self.assertEqual(meta["claim_type"], "estimate")
        self.assertEqual(meta["evidence_level"], "E2")
        self.assertEqual(meta["resolution_status"], "partial")

    def test_market_type_extraction_is_canonicalized_to_contract_enum(self) -> None:
        _, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"schema_paths": ["target_user.market_type_inferred"]},
                {"target_user.market_type_inferred": "B2B SaaS"},
                current_stage="problem",
                answer="We sell to 20-200 person B2B SaaS companies.",
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertIn(
            ("state", "target_user.market_type_inferred", "B2B"),
            extraction_updates,
        )
        self.assertEqual(state_json["target_user"]["market_type_inferred"], "B2B")
        self.assertEqual(
            state_meta["answer_meta"]["target_user.market_type_inferred"][
                "resolution_status"
            ],
            "answered",
        )

    def test_market_type_value_wrapper_is_unwrapped_and_canonicalized(self) -> None:
        _, extraction_updates, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {"schema_paths": ["target_user.market_type_inferred"]},
            {"target_user": {"market_type_inferred": {"value": "B2B SaaS"}}},
            current_stage="problem",
            answer="We sell to B2B SaaS teams.",
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertIn(
            ("state", "target_user.market_type_inferred", "B2B"),
            extraction_updates,
        )
        self.assertEqual(state_json["target_user"]["market_type_inferred"], "B2B")

    def test_market_type_is_inferred_from_target_user_text(self) -> None:
        _, _, state_json, _ = extraction_preview.build_sync_extraction_preview(
            {"schema_paths": ["target_user.core"]},
            {
                "target_user": {
                    "core": "Heads of Product at 20-200 person B2B SaaS companies"
                }
            },
            current_stage="problem",
            answer="We sell to product leaders at B2B SaaS companies.",
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        self.assertEqual(state_json["target_user"]["market_type_inferred"], "B2B")

    def test_scenario_answer_with_frequency_populates_frequency_path(self) -> None:
        resolved_paths, extraction_updates, state_json, state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {"question_id": "S1Q5", "schema_paths": ["problem.scenarios[]"]},
                {"problem": {"scenarios": ["Friday roadmap review"]}},
                current_stage="problem",
                answer=(
                    "Every Friday the product lead spends 4-6 hours clustering "
                    "interview notes before a monthly planning review."
                ),
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertIn("problem.frequency", resolved_paths)
        self.assertIn(
            ("state", "problem.frequency", "weekly, with monthly"), extraction_updates
        )
        self.assertEqual(state_json["problem"]["frequency"], "weekly, with monthly")
        self.assertEqual(
            state_meta["answer_meta"]["problem.frequency"]["resolution_status"],
            "answered",
        )

    def test_required_question_is_not_skipped_when_not_stage_blocking(self) -> None:
        should_skip = question_filters.should_skip_non_required_question(
            {
                "type_raw": "Required",
                "schema_paths": ["problem.severity_score", "problem.severity_reason"],
            },
            {"problem": {"frequency": "weekly"}},
            missing_paths=["alternatives.current_solutions[]"],
        )

        self.assertFalse(should_skip)

    def test_required_question_is_skipped_when_already_resolved(self) -> None:
        should_skip = question_filters.should_skip_non_required_question(
            {
                "type_raw": "Required",
                "schema_paths": ["problem.severity_score", "problem.severity_reason"],
            },
            {"problem": {"severity_score": 8, "severity_reason": "urgent"}},
            missing_paths=["alternatives.current_solutions[]"],
        )

        self.assertTrue(should_skip)

    def test_unknown_idea_raw_is_backfilled_from_later_problem_context(self) -> None:
        resolved_paths, extraction_updates, next_state_json, next_state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "S1Q2",
                    "schema_paths": ["problem.main_problems[]", "problem.one_line"],
                },
                {
                    "problem.main_problems": [
                        "Product teams cannot turn scattered interview notes into an evidence-backed MVP priority problem."
                    ],
                    "problem.one_line": "Product teams cannot turn scattered interview notes into an evidence-backed MVP priority problem.",
                },
                current_stage="problem",
                answer="The MVP priority problem is turning scattered interview notes into an evidence-backed priority problem.",
                state_json={"problem_user": {"idea": {"raw": "unknown"}}},
                state_meta={
                    "answer_meta": {
                        "problem_user.idea.raw": {
                            "resolution_status": "unknown",
                            "claim_type": "hypothesis",
                            "evidence_level": "E0",
                            "source": "user",
                            "updated_at": "2026-04-04T12:00:00Z",
                        }
                    }
                },
            )
        )

        self.assertIn("problem.one_line", resolved_paths)
        self.assertTrue(extraction_updates)
        self.assertEqual(
            next_state_json["problem_user"]["idea"]["raw"],
            "Product teams cannot turn scattered interview notes into an evidence-backed MVP priority problem.",
        )
        self.assertEqual(
            next_state_meta["answer_meta"]["problem_user.idea.raw"][
                "resolution_status"
            ],
            "answered",
        )

    def test_build_sync_extraction_preview_extracts_tech_product_scope_nfrs(
        self,
    ) -> None:
        answer = (
            "A) Current status: working prototype with staged interview and reports.\n"
            "B) MVP boundaries: in MVP are project workspace, staged interview, "
            "summary confirmation, and DVF report. Not in MVP are CRM and billing.\n"
            "C) Core journeys: 1) manager creates project; 2) mentor reviews "
            "context; 3) team generates report.\n"
            "D) NFR priorities: security because universities handle cohort data; "
            "latency because chat should feel responsive."
        )

        resolved_paths, extraction_updates, state_json, _ = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "schema_paths": [
                        "tech_execution.product_scope.current_status",
                        "tech_execution.product_scope.mvp_definition",
                        "tech_execution.product_scope.core_user_journeys",
                        "tech_execution.product_scope.non_functional_priorities",
                    ]
                },
                {},
                current_stage="tech",
                answer=answer,
                state_json={},
                state_meta={},
                ai_assisted=False,
            )
        )

        self.assertEqual(
            resolved_paths,
            [
                "tech_execution.product_scope.current_status",
                "tech_execution.product_scope.mvp_definition",
                "tech_execution.product_scope.non_functional_priorities",
                "tech_execution.product_scope.core_user_journeys",
            ],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.product_scope.non_functional_priorities",
                "security because universities handle cohort data; latency because chat should feel responsive.",
            ),
            extraction_updates,
        )
        product_scope = state_json["tech_execution"]["product_scope"]
        self.assertIn("working prototype", product_scope["current_status"])
        self.assertIn("staged interview", product_scope["mvp_definition"])
        self.assertEqual(len(product_scope["core_user_journeys"]), 3)
        self.assertIn("security", product_scope["non_functional_priorities"])

    def test_existing_idea_raw_is_not_overwritten_by_problem_context(self) -> None:
        _, _, next_state_json, _ = extraction_preview.build_sync_extraction_preview(
            {
                "question_id": "S1Q2",
                "schema_paths": ["problem.main_problems[]", "problem.one_line"],
            },
            {"problem.one_line": "Product discovery notes are hard to prioritize."},
            current_stage="problem",
            answer="The priority problem is discovery-note prioritization.",
            state_json={
                "problem_user": {
                    "idea": {
                        "raw": "An AI assistant that turns discovery notes into structured validation decisions."
                    }
                }
            },
            state_meta={},
        )

        self.assertEqual(
            next_state_json["problem_user"]["idea"]["raw"],
            "An AI assistant that turns discovery notes into structured validation decisions.",
        )


class StreamErrorPayloadTests(unittest.TestCase):
    def test_stream_error_payload_keeps_http_exception_detail(self) -> None:
        payload = chat._build_stream_error_payload(
            chat.HTTPException(status_code=403, detail="Verify your email.")
        )

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["code"], 403)
        self.assertEqual(payload["detail"], "Verify your email.")

    def test_stream_error_payload_hides_unexpected_exception_detail(self) -> None:
        payload = chat._build_stream_error_payload(RuntimeError("db password leaked"))

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["code"], 500)
        self.assertNotIn("db password", payload["detail"])


class SyncAnswerExtractionTests(unittest.IsolatedAsyncioTestCase):
    def test_answer_gate_timeout_uses_registry_clamps(self) -> None:
        task = chat_prompt_tasks.DEFAULT_PROMPT_TASK_REGISTRY.get("answer_gate")
        with patch.dict("os.environ", {"ANSWER_GATE_TIMEOUT_MS": "-1"}, clear=False):
            self.assertEqual(
                chat_prompt_tasks.resolve_prompt_task_timeout_ms(
                    task,
                    minimum_ms=500,
                ),
                0,
            )
        with patch.dict("os.environ", {"ANSWER_GATE_TIMEOUT_MS": "50"}, clear=False):
            self.assertEqual(
                chat_prompt_tasks.resolve_prompt_task_timeout_ms(
                    task,
                    minimum_ms=500,
                ),
                500,
            )

    def test_sync_extract_timeout_uses_registry_clamps(self) -> None:
        task = chat_prompt_tasks.DEFAULT_PROMPT_TASK_REGISTRY.get("extract")
        with patch.dict(
            "os.environ", {"SYNC_EXTRACT_TIMEOUT_MS": "-1"}, clear=False
        ):
            self.assertEqual(
                chat_prompt_tasks.resolve_prompt_task_timeout_ms(
                    task,
                    minimum_ms=200,
                ),
                0,
            )
        with patch.dict(
            "os.environ", {"SYNC_EXTRACT_TIMEOUT_MS": "50"}, clear=False
        ):
            self.assertEqual(
                chat_prompt_tasks.resolve_prompt_task_timeout_ms(
                    task,
                    minimum_ms=200,
                ),
                200,
            )

    async def test_run_sync_answer_extraction_times_out_cleanly(self) -> None:
        async def _slow_extract(*_args, **_kwargs):
            await chat.asyncio.sleep(0.05)
            return {"problem": {"one_line": "late"}}, True, {"task_key": "extract"}

        with patch.object(
            chat_prompt_tasks,
            "resolve_prompt_task_timeout_ms",
            return_value=10,
        ):
            with patch.object(
                chat_prompt_tasks,
                "run_answer_extraction",
                new=_slow_extract,
            ):
                extracted, did_sync_extract, trace = (
                    await chat_prompt_tasks.run_sync_answer_extraction(
                        None,
                        {"schema_paths": ["problem.one_line"]},
                        "Manual reporting is slow.",
                    )
                )

        self.assertEqual(extracted, {})
        self.assertFalse(did_sync_extract)
        self.assertIsNone(trace)

    async def test_run_answer_gate_times_out_cleanly(self) -> None:
        async def _timed_out_executor(*_args, **_kwargs):
            return types.SimpleNamespace(
                ok=False,
                failure=types.SimpleNamespace(reason="timeout"),
                parsed=None,
                model=None,
                provider=None,
                trace={"task_key": "answer_gate"},
            )

        with patch.object(
            chat_prompt_tasks,
            "execute_prompt_task",
            new=_timed_out_executor,
        ):
            gate_result, gate_model, trace = await chat_prompt_tasks.run_answer_gate(
                None,
                {"schema_paths": ["problem.one_line"]},
                "Manual reporting is slow.",
            )

        self.assertIsNone(gate_result)
        self.assertEqual(gate_model, "answer_gate_timeout")
        self.assertEqual(trace["task_key"], "answer_gate")
        self.assertEqual(trace["failure_reason"], "timeout")

    async def test_gate_pass_does_not_wait_for_sync_extraction(self) -> None:
        async def _fast_gate(_context):
            await chat.asyncio.sleep(0.01)
            return None, "gate-model", {"task_key": "answer_gate"}

        with (
            patch.object(chat, "AdminAsyncSessionLocal", object()),
            patch.object(gate_resolution, "run_answer_gate_for_context", _fast_gate),
            patch.object(
                gate_resolution,
                "build_gate_decision",
                return_value={"final_verdict": "pass"},
            ),
        ):
            latency_spans: dict[str, float] = {}
            started = time.perf_counter()
            decision, gate_model, extracted, did_extract, traces = (
                await gate_resolution.resolve_gate_and_sync_extraction(
                    {
                        "question_detail": {},
                        "gate_answer_text": "Manual reporting is slow.",
                        "latest_answer": "Manual reporting is slow.",
                    },
                    schema_paths=["problem.one_line"],
                    skip_requested=False,
                    skip_reason=None,
                    skip_resolution_status=None,
                    latency_spans=latency_spans,
                )
            )
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.09)
        self.assertEqual(decision["final_verdict"], "pass")
        self.assertEqual(gate_model, "gate-model")
        self.assertFalse(did_extract)
        self.assertEqual(extracted, {})
        self.assertEqual(traces["answer_gate"]["task_key"], "answer_gate")
        self.assertNotIn("extract", traces)
        self.assertIn("answer_gate", latency_spans)
        self.assertNotIn("sync_extract", latency_spans)

    async def test_needs_info_does_not_wait_for_sync_extraction(self) -> None:
        async def _fast_gate(_context):
            await chat.asyncio.sleep(0.01)
            return None, "gate-model", {"task_key": "answer_gate"}

        with (
            patch.object(chat, "AdminAsyncSessionLocal", object()),
            patch.object(gate_resolution, "run_answer_gate_for_context", _fast_gate),
            patch.object(
                gate_resolution,
                "build_gate_decision",
                return_value={"final_verdict": "needs_info"},
            ),
        ):
            latency_spans: dict[str, float] = {}
            started = time.perf_counter()
            decision, _gate_model, extracted, did_extract, traces = (
                await gate_resolution.resolve_gate_and_sync_extraction(
                    {
                        "question_detail": {},
                        "gate_answer_text": "Too vague.",
                        "latest_answer": "Too vague.",
                    },
                    schema_paths=["problem.one_line"],
                    skip_requested=False,
                    skip_reason=None,
                    skip_resolution_status=None,
                    latency_spans=latency_spans,
                )
            )
            elapsed = time.perf_counter() - started
            await chat.asyncio.sleep(0.01)

        self.assertLess(elapsed, 0.08)
        self.assertEqual(decision["final_verdict"], "needs_info")
        self.assertFalse(did_extract)
        self.assertEqual(extracted, {})
        self.assertEqual(traces["answer_gate"]["task_key"], "answer_gate")
        self.assertNotIn("extract", traces)
        self.assertIn("answer_gate", latency_spans)
        self.assertNotIn("sync_extract", latency_spans)


class QuestionPlannerTests(unittest.IsolatedAsyncioTestCase):
    def test_question_planner_defaults_to_short_bounded_budget(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "QUESTION_PLANNER_TIMEOUT_MS": "",
                "QUESTION_PLANNER_MIN_MISSING_PATHS": "",
                "QUESTION_PLANNER_MIN_CANDIDATES": "",
            },
            clear=False,
        ):
            settings = chat._resolve_question_planner_settings()

        self.assertEqual(settings["timeout_ms"], 1000)
        self.assertEqual(settings["min_missing_paths"], 2)
        self.assertEqual(settings["min_candidates"], 2)

    def test_question_planner_skips_low_value_single_missing_path(self) -> None:
        settings = {
            "enabled": True,
            "max_questions": 3,
            "min_missing_paths": 2,
            "stages": {"problem"},
        }

        should_attempt = question_planning.should_attempt_question_planner(
            planner_settings=settings,
            stage="problem",
            question_detail={"prompt": "What problem are you solving?"},
            missing_paths=["problem.one_line"],
        )

        self.assertFalse(should_attempt)

    async def test_question_plan_skips_when_candidate_count_is_too_low(self) -> None:
        candidate = {
            "id": uuid4(),
            "question_id": "S1Q1",
            "prompt": "What problem are you solving?",
            "order_index": 1,
            "schema_paths": ["problem.one_line"],
            "prompt_meta": {},
        }

        async def fake_fetch(*_args, **_kwargs):
            return [candidate]

        async def fail_executor(*_args, **_kwargs):
            raise AssertionError("planner runtime should not be called")

        async def fake_next_id(*_args, **_kwargs):
            return None

        with patch.object(
            question_planning, "fetch_question_planner_candidates", new=fake_fetch
        ):
            with patch.object(
                question_planning, "execute_prompt_task", new=fail_executor
            ):
                result = await question_planning.resolve_question_group_plan(
                    None,
                    candidate,
                    candidate["prompt"],
                    ["problem.one_line", "problem.severity"],
                    "latest answer",
                    output_locale="en",
                    max_questions=3,
                    max_schema=2,
                    timeout_ms=100,
                    candidate_limit=3,
                    min_candidates=2,
                    resolve_next_question_id=fake_next_id,
                )

        self.assertIsNone(result)

    async def test_single_question_plan_uses_canonical_prompt(self) -> None:
        question_id = uuid4()
        candidate = {
            "id": question_id,
            "question_id": "S2Q5",
            "prompt": "List competitor types, 3-5 named alternatives, your positioning vs them, and competitive red flags.",
            "order_index": 5,
            "schema_paths": ["market_strategy.competition.competitor_types[]"],
            "prompt_meta": {},
        }

        async def fake_fetch(*_args, **_kwargs):
            return [candidate]

        async def fake_executor(*_args, **kwargs):
            self.assertEqual(
                kwargs["expected_mutation"],
                question_planning.PromptMutationClass.DECISION_ONLY,
            )
            self.assertEqual(kwargs["timeout_override_ms"], 100)
            self.assertEqual(kwargs["timeout_minimum_ms"], 200)
            return types.SimpleNamespace(
                ok=True,
                parsed={
                    "question_indices": [1],
                    "prompt": (
                        "Ask about generic pain points, market trends, "
                        "and technology stack."
                    ),
                },
                model="test-model",
                provider="test-provider",
            )

        async def fake_next_id(*_args, **_kwargs):
            return None

        with patch.object(
            question_planning, "fetch_question_planner_candidates", new=fake_fetch
        ):
            with patch.object(
                question_planning, "execute_prompt_task", new=fake_executor
            ):
                result = await question_planning.resolve_question_group_plan(
                    None,
                    candidate,
                    candidate["prompt"],
                    ["market_strategy.competition.competitor_types[]"],
                    "latest answer",
                    output_locale="en",
                    max_questions=1,
                    max_schema=1,
                    timeout_ms=100,
                    candidate_limit=1,
                    resolve_next_question_id=fake_next_id,
                )

        self.assertIsNotNone(result)
        detail, question_ids, next_id, plan_meta = result
        self.assertIn("List competitor types", detail["prompt"])
        self.assertNotIn("generic pain points", detail["prompt"])
        self.assertEqual(question_ids, [str(question_id)])
        self.assertIsNone(next_id)
        self.assertEqual(plan_meta["selected_count"], 1)


class ConditionalQuestionRoutingTests(unittest.TestCase):
    def test_stage_gate_ready_for_review_short_circuits_next_question(self) -> None:
        self.assertTrue(
            is_stage_gate_ready_for_review("awaiting_confirm", "in_progress")
        )
        self.assertTrue(is_stage_gate_ready_for_review(None, "awaiting_confirm"))
        self.assertFalse(is_stage_gate_ready_for_review(None, "in_progress"))
        self.assertTrue(
            should_enter_stage_gate_review(
                stage_status_ready=None,
                current_stage_status="in_progress",
                stage="problem",
                variant="default",
                missing_paths=[],
            )
        )
        self.assertFalse(
            should_enter_stage_gate_review(
                stage_status_ready=None,
                current_stage_status="in_progress",
                stage="problem",
                variant="default",
                missing_paths=["evidence.key_unknowns[]"],
            )
        )
        self.assertFalse(
            should_enter_stage_gate_review(
                stage_status_ready=None,
                current_stage_status="in_progress",
                stage="tech",
                variant="router",
                missing_paths=[],
            )
        )

    def test_active_conditional_question_is_not_skipped_when_path_is_not_blocking(
        self,
    ) -> None:
        should_skip = question_filters.should_skip_non_required_question(
            {
                "type_raw": "Conditional (B2B Only)",
                "schema_paths": ["target_user.decision_vs_end_user"],
                "title": "Decision Maker (B2B Only)",
                "prompt": "Who uses the product day-to-day, and who makes the purchase decision?",
            },
            {"target_user": {"market_type_inferred": "B2B"}},
            missing_paths=["problem.scenarios[]"],
        )

        self.assertFalse(should_skip)

    def test_inactive_conditional_question_is_skipped_for_b2c_market_lock(self) -> None:
        should_skip = question_filters.should_skip_non_required_question(
            {
                "type_raw": "Conditional (B2B Only)",
                "schema_paths": ["target_user.decision_vs_end_user"],
                "title": "Decision Maker (B2B Only)",
                "prompt": "Who uses the product day-to-day, and who makes the purchase decision?",
            },
            {"target_user": {"market_type_inferred": "B2C"}},
            missing_paths=["problem.scenarios[]"],
        )

        self.assertTrue(should_skip)

    def test_inactive_conditional_question_uses_target_user_text_market_lock(
        self,
    ) -> None:
        should_skip = question_filters.should_skip_non_required_question(
            {
                "type_raw": "Conditional (B2C Only)",
                "schema_paths": ["impact.emotional_impact[]"],
                "title": "Emotional Impact (B2C Only)",
                "prompt": "How does this personally affect the user?",
            },
            {
                "target_user": {
                    "core": "Heads of Product at 20-200 person B2B SaaS companies"
                }
            },
            missing_paths=["alternatives.current_solutions[]"],
        )

        self.assertTrue(should_skip)


class RouterModeSelectionTests(unittest.TestCase):
    def test_question_overlap_defer_skips_current_schema_only_questions(self) -> None:
        self.assertTrue(
            question_planning.question_overlaps_only_deferred_paths(
                {"schema_paths": ["market_strategy.business_model.revenue_model"]},
                [
                    "market_strategy.business_model.revenue_model",
                    "market_strategy.competition.competitor_types[]",
                ],
                ["market_strategy.business_model.revenue_model"],
            )
        )
        self.assertFalse(
            question_planning.question_overlaps_only_deferred_paths(
                {"schema_paths": ["market_strategy.competition.competitor_types[]"]},
                [
                    "market_strategy.business_model.revenue_model",
                    "market_strategy.competition.competitor_types[]",
                ],
                ["market_strategy.business_model.revenue_model"],
            )
        )

    def test_single_schema_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs a clearer one-line UVP."],
            critical_issues=[],
            followup_questions=["Why should the target customer choose you?"],
            help_examples=[],
            followup_message="Please answer the UVP in one sentence.",
            score=AnswerGateScore(clarity=0.6, completeness=0.4, evidence=0.2),
            overall=0.4,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["market_strategy.uvp.one_line"],
                "type_raw": "required",
            },
            "The clearest validation brief for early-stage teams deciding what to test next.",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_single_schema_answer_does_not_soft_pass_explicit_none(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs a concrete answer."],
            critical_issues=[],
            followup_questions=["What is the UVP?"],
            help_examples=[],
            followup_message="Please answer the UVP.",
            score=AnswerGateScore(clarity=0.6, completeness=0.4, evidence=0.2),
            overall=0.4,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["market_strategy.uvp.one_line"],
                "type_raw": "required",
            },
            "None yet",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "needs_info")

    def test_idea_snapshot_soft_passes_failed_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs a problem statement."],
            critical_issues=[],
            followup_questions=["What is the problem?"],
            help_examples=[],
            followup_message="Please describe the startup idea.",
            score=AnswerGateScore(clarity=0.5, completeness=0.3, evidence=0.1),
            overall=0.3,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S1Q1",
                "schema_paths": ["problem_user.idea.raw"],
                "type_raw": "required",
            },
            "IdeaSense AI turns messy startup idea notes into a staged assessment, extracts live context, gates summaries for confirmation, scores DVF, and produces a founder-ready report.",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_idea_snapshot_soft_pass_rejects_empty_answer(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs a real idea snapshot."],
            critical_issues=[],
            followup_questions=["What is your idea?"],
            help_examples=[],
            followup_message="Please describe the startup idea.",
            score=AnswerGateScore(clarity=0.2, completeness=0.1, evidence=0.1),
            overall=0.1,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S1Q1",
                "schema_paths": ["problem_user.idea.raw"],
                "type_raw": "required",
            },
            "None yet",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "needs_info")

    def test_single_schema_answer_soft_passes_when_gate_missing(self) -> None:
        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["market_strategy.uvp.one_line"],
                "type_raw": "required",
            },
            "The clearest validation brief for early-stage teams deciding what to test next.",
            None,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_time_money_impact_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs impact estimates."],
            critical_issues=[],
            followup_questions=["What is the time and money impact?"],
            help_examples=[],
            followup_message="Please add time and money impact.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["impact.time_impact", "impact.money_impact"],
                "type_raw": "required",
            },
            "Time wasted: 3 hours per week\nMoney impact: $500 lost revenue per month",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_severity_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs severity."],
            critical_issues=[],
            followup_questions=["What is the severity score?"],
            help_examples=[],
            followup_message="Please add a severity score.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["problem.severity_score", "problem.severity_reason"],
                "type_raw": "required",
            },
            "Severity score: 8 out of 10. Reason: weak framing wastes mentor time.",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_data_scalability_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs data volume and scaling plan."],
            critical_issues=[],
            followup_questions=["Please provide A-E."],
            help_examples=[],
            followup_message="Please clarify data and scaling.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.3),
            overall=0.4,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q5",
                "schema_paths": [
                    "tech_execution.data_ai_scalability.data_sources",
                    "tech_execution.data_ai_scalability.data_volume_year1",
                    "tech_execution.data_ai_scalability.growth_expectations",
                    "tech_execution.data_ai_scalability.ai_usage",
                    "tech_execution.data_ai_scalability.performance_expectations",
                    "tech_execution.data_ai_scalability.scalability_strategy",
                ],
                "type_raw": "required",
            },
            (
                "A) Data sources and ownership: user answers and mentor comments owned by the workspace.\n"
                "B) Year-1 data volume: tens of thousands of messages; growth could be 5-10x.\n"
                "C) AI usage: core for extraction and reports.\n"
                "D) Performance expectations: chat under 10 seconds and 99% uptime target.\n"
                "E) 10x scaling strategy: queue reports, cache artifacts, index tables, and scale workers."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_product_scope_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs MVP boundaries and NFRs."],
            critical_issues=[],
            followup_questions=["Please provide A-D."],
            help_examples=[],
            followup_message="Please clarify product scope.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.3),
            overall=0.4,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q1",
                "schema_paths": [
                    "tech_execution.product_scope.current_status",
                    "tech_execution.product_scope.mvp_definition",
                    "tech_execution.product_scope.core_user_journeys",
                    "tech_execution.product_scope.non_functional_priorities",
                ],
                "type_raw": "required",
            },
            (
                "A) Current status: working prototype.\n"
                "B) MVP boundaries: in MVP are project workspace and DVF report. "
                "Not in MVP are CRM and billing.\n"
                "C) Core journeys: 1) manager creates project; 2) mentor reviews context; "
                "3) team generates report.\n"
                "D) NFR priorities: security because of cohort data; latency because chat "
                "should feel responsive."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_structured_answer_soft_passes_failed_model_verdict(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs severity."],
            critical_issues=["Model missed the explicit score."],
            followup_questions=["What is the severity score?"],
            help_examples=[],
            followup_message="Please add a severity score.",
            score=AnswerGateScore(clarity=0.4, completeness=0.2, evidence=0.2),
            overall=0.2,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["problem.severity_score", "problem.severity_reason"],
                "type_raw": "required",
            },
            "Severity score: 8/10. Reasons: weekly mentor time is wasted.",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_alternatives_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs alternatives."],
            critical_issues=[],
            followup_questions=["How do they solve it today?"],
            help_examples=[],
            followup_message="Please add alternatives.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "alternatives.current_solutions[]",
                    "alternatives.satisfaction_score",
                    "alternatives.main_complaints[]",
                ],
                "type_raw": "required",
            },
            (
                "Current solutions: Google Docs, Notion templates, and ChatGPT. "
                "Satisfaction score: 5 out of 10. "
                "Main complaints: scattered context and repeated questions."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_alternatives_answer_soft_passes_current_solutions_schema_only(
        self,
    ) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs clearer alternatives."],
            critical_issues=[],
            followup_questions=["How do they solve it today?"],
            help_examples=[],
            followup_message="Please add alternatives.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.2),
            overall=0.35,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S1Q10",
                "schema_paths": ["alternatives.current_solutions[]"],
                "type_raw": "required",
            },
            (
                "Current solutions: Google Docs, Notion templates, pitch-deck comments, spreadsheets, and ChatGPT brainstorming.\n"
                "Satisfaction: 5/10.\n"
                "Main complaints: context is scattered, clarification questions repeat, and outputs are hard to compare."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_scenarios_answer_soft_passes_failed_model_verdict(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs real scenarios."],
            critical_issues=["Model missed structured scenario details."],
            followup_questions=["Where does this happen?"],
            help_examples=[],
            followup_message="Please add a scenario.",
            score=AnswerGateScore(clarity=0.4, completeness=0.2, evidence=0.2),
            overall=0.2,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S1Q5",
                "schema_paths": ["problem.scenarios[]"],
                "type_raw": "required",
            },
            (
                "Scenario 1: before weekly mentor office hours, a program "
                "manager reviews 15 founder submissions and spends 2-5 hours "
                "rewriting vague problem statements. Scenario 2: after "
                "customer interviews, teams update assumptions in scattered "
                "docs, leading to unclear mentor feedback."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_scenarios_answer_does_not_soft_pass_unknown(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs real scenarios."],
            critical_issues=[],
            followup_questions=["Where does this happen?"],
            help_examples=[],
            followup_message="Please add a scenario.",
            score=AnswerGateScore(clarity=0.4, completeness=0.2, evidence=0.2),
            overall=0.2,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S1Q5",
                "schema_paths": ["problem.scenarios[]"],
                "type_raw": "required",
            },
            "I am not sure yet and do not know the real scenario.",
            gate,
        )

        self.assertEqual(decision["final_verdict"], "needs_info")

    def test_validation_evidence_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs validation evidence."],
            critical_issues=[],
            followup_questions=["What validation do you have so far?"],
            help_examples=[],
            followup_message="Please add validation evidence.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "evidence.user_interview_count",
                    "evidence.key_learnings[]",
                    "evidence.data_evidence",
                    "evidence.key_unknowns[]",
                ],
                "type_raw": "required",
            },
            (
                "User conversations: 6 informal conversations. "
                "Key learnings: founders want sharper framing. "
                "Quant evidence/proxies: 3-5 hours/week preparing review notes. "
                "Key unknowns: willingness to pay and summary trust."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_market_business_model_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs payer and revenue model."],
            critical_issues=[],
            followup_questions=["Who pays and how do you charge?"],
            help_examples=[],
            followup_message="Please add payer and revenue model.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "market_strategy.business_model.payer_role",
                    "market_strategy.business_model.revenue_model",
                ],
                "type_raw": "required",
            },
            (
                "Type: B2B. Payer: university incubator director. "
                "Revenue model: annual SaaS license per program."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_market_competition_and_gtm_answers_soft_pass_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs market detail."],
            critical_issues=[],
            followup_questions=["What channels or competitors?"],
            help_examples=[],
            followup_message="Please add the missing market detail.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        competition_decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["market_strategy.competition.competitor_types[]"],
                "type_raw": "required",
            },
            "Competitor types: generic AI chat tools, survey builders, and mentor management tools.",
            gate,
        )
        gtm_decision = followup_compose.build_gate_decision(
            {
                "schema_paths": ["market_strategy.go_to_market.primary_channels[]"],
                "type_raw": "required",
            },
            "Primary channels: direct university incubator outreach and mentor referrals.",
            gate,
        )

        self.assertEqual(competition_decision["final_verdict"], "pass")
        self.assertEqual(gtm_decision["final_verdict"], "pass")

    def test_market_launch_segment_answer_soft_passes_failed_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs clearer market sizing."],
            critical_issues=[],
            followup_questions=["What is the initial launch segment?"],
            help_examples=[],
            followup_message="Please add launch segment detail.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.2),
            overall=0.35,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q4",
                "schema_paths": ["market_strategy.segment.initial_launch"],
                "type_raw": "required",
            },
            (
                "Initial launch segment: English-speaking university incubators with 2-6 cohorts per year. "
                "Estimated customers: about 1,000 relevant programs. "
                "Estimated annual revenue per customer: $12,000. "
                "Why now: AI acceptance is rising, but programs need auditable outputs."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_market_unit_economics_and_validation_answers_soft_pass_failed_gate(
        self,
    ) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs more market detail."],
            critical_issues=[],
            followup_questions=["Please clarify the market plan."],
            help_examples=[],
            followup_message="Please add detail.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.2),
            overall=0.35,
        )

        unit_decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q7",
                "schema_paths": ["market_strategy.unit_economics.cac_hypothesis"],
                "type_raw": "required",
            },
            (
                "Cost drivers: LLM usage, onboarding, support, and founder-led sales. "
                "CAC hypothesis: $1,000-$3,000. LTV hypothesis: $24,000-$60,000. "
                "Gross margin expectation: 75-85%. Expected payback period: under 6 months."
            ),
            gate,
        )
        validation_decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q8",
                "schema_paths": ["market_strategy.validation.signals[]"],
                "type_raw": "required",
            },
            (
                "Must-be-true assumptions: programs have enough pain to pay and teams complete the interview. "
                "Top risks: low willingness to pay and outputs seen as generic. "
                "Early validation plan: run 3 cohort pilots and test paid renewal intent. "
                "Validation signals: completion rate, mentor NPS, hours saved, and signed paid LOI."
            ),
            gate,
        )

        self.assertEqual(unit_decision["final_verdict"], "pass")
        self.assertEqual(validation_decision["final_verdict"], "pass")

    def test_tech_data_access_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs data access."],
            critical_issues=[],
            followup_questions=["How will you access the data?"],
            help_examples=[],
            followup_message="Please add the data access plan.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "tech_execution.data_ai_scalability.data_access_rights"
                ],
                "type_raw": "required",
            },
            (
                "Required data: founder project text. Access plan: users enter "
                "or approve the data inside the workspace with org-scoped permissions."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_data_access_rights_label_soft_passes_needs_info_gate(
        self,
    ) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs data access."],
            critical_issues=[],
            followup_questions=["How will you access the data?"],
            help_examples=[],
            followup_message="Please add the data access plan.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q10",
                "schema_paths": [
                    "tech_execution.data_ai_scalability.data_access_rights"
                ],
                "type_raw": "required",
            },
            (
                "A) Required data: founder-entered project context and staged "
                "answers. Rights/access: user-generated and organization-approved "
                "data entered into the workspace. B) Collection/refresh: refreshed "
                "after answers or context edits."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_complexity_debt_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs complexity details."],
            critical_issues=[],
            followup_questions=["What are the hotspots?"],
            help_examples=[],
            followup_message="Please add complexity details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q4",
                "schema_paths": [
                    "tech_execution.architecture.complexity_hotspots",
                    "tech_execution.architecture.tech_debt_strategy",
                ],
                "type_raw": "required",
            },
            (
                "Complexity hotspots: LLM output reliability, multi-tenant "
                "permissions, and stage transition correctness. Acceptable early "
                "debt: admin polish. Strict from day one: org isolation and "
                "report data integrity."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_infra_devops_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs infra details."],
            critical_issues=[],
            followup_questions=["What is the infra plan?"],
            help_examples=[],
            followup_message="Please add infra details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q6",
                "schema_paths": [
                    "tech_execution.infra_devops.hosting_choice",
                    "tech_execution.infra_devops.backup_dr_plan",
                ],
                "type_raw": "required",
            },
            (
                "Hosting: managed web/API hosting plus managed Postgres. "
                "Environments: local, staging, and production. CI/CD: tests on "
                "PR and deploy staging after merge. Monitoring/alerts: API logs "
                "and worker failures. Backup/DR: daily backups, RPO 24 hours, "
                "RTO one business day."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_reliability_testing_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs reliability details."],
            critical_issues=[],
            followup_questions=["What is the reliability plan?"],
            help_examples=[],
            followup_message="Please add reliability details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q12",
                "schema_paths": [
                    "tech_execution.reliability_testing.reliability_target"
                ],
                "type_raw": "required",
            },
            (
                "Reliability target: 99% pilot availability. Testing strategy: "
                "unit, integration, and Playwright E2E tests. Release/rollback: "
                "deploy staging first and keep previous deploy rollback available."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_slo_incident_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs incident details."],
            critical_issues=[],
            followup_questions=["What is the incident plan?"],
            help_examples=[],
            followup_message="Please add incident details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q14",
                "schema_paths": ["tech_execution.slo_incident.targets"],
                "type_raw": "required",
            },
            (
                "SLO/SLA targets: internal pilot target is 99% availability. "
                "Failover: managed backups and retryable provider calls. "
                "Incident response: owner alerting, runbook, and regression tests."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_mvp_boundary_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs MVP boundary."],
            critical_issues=[],
            followup_questions=["What is in and out of the MVP?"],
            help_examples=[],
            followup_message="Please clarify the MVP scope.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "tech_execution.product_scope.current_status",
                    "tech_execution.product_scope.mvp_definition",
                ],
                "type_raw": "required",
            },
            (
                "Current status: working prototype. MVP must include project "
                "workspace, staged interview, summary confirmation, and report "
                "generation. Not in MVP: CRM, billing automation, and analytics."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_mvp_boundary_prompt_soft_passes_even_when_schema_is_adjacent(
        self,
    ) -> None:
        gate = AnswerGateResult(
            verdict="fail",
            missing_points=["Needs MVP boundary."],
            critical_issues=[],
            followup_questions=["What is in and out of the MVP?"],
            help_examples=[],
            followup_message="Please clarify the MVP scope.",
            score=AnswerGateScore(clarity=0.6, completeness=0.3, evidence=0.2),
            overall=0.35,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "L3Q1",
                "prompt": "Where is your product today and what is explicitly not in MVP?",
                "schema_paths": ["tech_execution.product_scope.core_user_journeys"],
                "type_raw": "required",
            },
            (
                "Current status: working prototype. In-MVP scope: project workspace, "
                "staged interview, summary confirmation, and report generation. "
                "Out-of-MVP boundary: CRM, billing automation, and analytics."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_mvp_boundary_soft_pass_uses_latest_answer(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs MVP boundary."],
            critical_issues=[],
            followup_questions=["What is in and out of the MVP?"],
            help_examples=[],
            followup_message="Please clarify the MVP scope.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "tech_execution.product_scope.current_status",
                    "tech_execution.product_scope.mvp_definition",
                ],
                "type_raw": "required",
            },
            "I am non-technical / I prefer plain language.",
            gate,
            latest_answer=(
                "Current status: working prototype. In-MVP scope: project "
                "workspace, staged interview, summary confirmation, and report "
                "generation. Out-of-MVP boundary: CRM, billing automation, and "
                "analytics."
            ),
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_sync_extraction_preview_falls_back_to_latest_answer(self) -> None:
        question_detail = {
            "question_id": "L3Q1",
            "schema_paths": [
                "tech_execution.product_scope.current_status",
                "tech_execution.product_scope.mvp_definition",
            ],
        }

        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                question_detail,
                {},
                current_stage="tech",
                answer="I am non-technical / I prefer plain language.",
                latest_answer=(
                    "Current status: working prototype. In-MVP scope: project "
                    "workspace, staged interview, summary confirmation, and "
                    "report generation. Out-of-MVP boundary: CRM, billing "
                    "automation, and analytics."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn("tech_execution.product_scope.current_status", resolved_paths)
        self.assertIn("tech_execution.product_scope.mvp_definition", resolved_paths)
        self.assertIn(
            (
                "state",
                "tech_execution.product_scope.current_status",
                "working prototype",
            ),
            updates,
        )
        self.assertEqual(
            state_json["tech_execution"]["product_scope"]["mvp_definition"],
            "project workspace, staged interview, summary confirmation, and report generation",
        )

    def test_sync_extraction_preview_adds_l3q1_boundary_paths_from_adjacent_schema(
        self,
    ) -> None:
        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "L3Q1",
                    "schema_paths": ["tech_execution.product_scope.core_user_journeys"],
                },
                {},
                current_stage="tech",
                answer=(
                    "Current status: working prototype. In-MVP scope: project "
                    "workspace, staged interview, summary confirmation, and "
                    "report generation. Out-of-MVP boundary: CRM, billing "
                    "automation, and analytics."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn("tech_execution.product_scope.current_status", resolved_paths)
        self.assertIn("tech_execution.product_scope.mvp_definition", resolved_paths)
        self.assertIn(
            (
                "state",
                "tech_execution.product_scope.current_status",
                "working prototype",
            ),
            updates,
        )
        self.assertEqual(
            state_json["tech_execution"]["product_scope"]["mvp_definition"],
            "project workspace, staged interview, summary confirmation, and report generation",
        )

    def test_tech_journey_components_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs top 2 journeys."],
            critical_issues=[],
            followup_questions=["What are the top 2 critical user journeys?"],
            help_examples=[],
            followup_message="Please choose exactly two journeys.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "L3Q2",
                "schema_paths": [
                    "tech_execution.product_scope.core_user_journeys",
                    "tech_execution.architecture.high_level_components",
                ],
                "type_raw": "required",
            },
            (
                "First version form factor: responsive web app. Critical "
                "journeys: 1) program manager creates a project and founder "
                "answers staged questions; 2) mentor reviews context, confirms "
                "summaries, and generates a report. High-level components: "
                "Next.js frontend, FastAPI backend, Postgres database."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_tech_architecture_components_soft_passes_without_journeys(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs architecture components."],
            critical_issues=[],
            followup_questions=["What are the main system components?"],
            help_examples=[],
            followup_message="Please describe the main components.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S3Q2",
                "schema_paths": [
                    "tech_execution.architecture.high_level_components",
                ],
                "type_raw": "required",
            },
            (
                "Architecture style: modular monolith for the MVP. Components: "
                "Next.js web client, FastAPI API, Postgres database, prompt "
                "runtime, background report worker, and email/auth service. "
                "Reason: the team can ship faster while keeping clear module "
                "boundaries."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_sync_extraction_preview_fills_tech_journeys_and_components(self) -> None:
        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "L3Q2",
                    "schema_paths": [
                        "tech_execution.product_scope.core_user_journeys",
                        "tech_execution.architecture.high_level_components",
                    ],
                },
                {},
                current_stage="tech",
                answer=(
                    "First version form factor: responsive web app. Critical "
                    "journeys: 1) program manager creates a project and founder "
                    "answers staged questions; 2) mentor reviews context, confirms "
                    "summaries, and generates a report. High-level components: "
                    "Next.js frontend, FastAPI backend, Postgres database."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn("tech_execution.product_scope.core_user_journeys", resolved_paths)
        self.assertIn(
            "tech_execution.architecture.high_level_components", resolved_paths
        )
        self.assertIn(
            "program manager creates a project and founder answers staged questions",
            state_json["tech_execution"]["product_scope"]["core_user_journeys"],
        )
        self.assertIn(
            "FastAPI backend",
            state_json["tech_execution"]["architecture"]["high_level_components"],
        )
        self.assertIn(
            (
                "state",
                "tech_execution.architecture.high_level_components",
                ["Next.js frontend", "FastAPI backend", "Postgres database"],
            ),
            updates,
        )

    def test_sync_extraction_preview_fills_architecture_components_only(
        self,
    ) -> None:
        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "S3Q2",
                    "schema_paths": [
                        "tech_execution.architecture.high_level_components",
                    ],
                },
                {},
                current_stage="tech",
                answer=(
                    "Architecture style: modular monolith for the MVP. "
                    "Components: Next.js web client, FastAPI API, Postgres "
                    "database, prompt runtime, background report worker, and "
                    "email/auth service. Reason: the team can ship faster while "
                    "keeping clear module boundaries."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn(
            "tech_execution.architecture.high_level_components", resolved_paths
        )
        self.assertIn(
            "FastAPI API",
            state_json["tech_execution"]["architecture"]["high_level_components"],
        )
        self.assertNotIn(
            "Reason",
            " ".join(
                state_json["tech_execution"]["architecture"][
                    "high_level_components"
                ]
            ),
        )
        self.assertIn(
            (
                "state",
                "tech_execution.architecture.high_level_components",
                [
                    "Next.js web client",
                    "FastAPI API",
                    "Postgres database",
                    "prompt runtime",
                    "background report worker",
                    "email/auth service",
                ],
            ),
            updates,
        )

    def test_market_moat_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs moat details."],
            critical_issues=[],
            followup_questions=["What is your unfair advantage and moat?"],
            help_examples=[],
            followup_message="Please add moat details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q2",
                "schema_paths": [
                    "market_strategy.unfair_advantage",
                    "market_strategy.moat.long_term_moat",
                    "market_strategy.moat.switching_costs",
                    "market_strategy.moat.big_tech_response_risk",
                ],
                "type_raw": "required",
            },
            (
                "A) Unfair advantage today: stage-specific validation flow. "
                "B) 12-18 month differentiation: cohort workflows and traceable reports. "
                "C) Long-term moat: accumulated rubric quality. "
                "D) Switching costs: moving workspace history is costly. "
                "E) Incumbent risk: generic tools could copy pieces."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_sync_extraction_preview_fills_market_moat_paths(self) -> None:
        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "S2Q2",
                    "schema_paths": [
                        "market_strategy.unfair_advantage",
                        "market_strategy.moat.long_term_moat",
                        "market_strategy.moat.switching_costs",
                        "market_strategy.moat.big_tech_response_risk",
                    ],
                },
                {},
                current_stage="market",
                answer=(
                    "A) Unfair advantage today: stage-specific validation flow. "
                    "B) 12-18 month differentiation: cohort workflows and traceable reports. "
                    "C) Long-term moat: accumulated rubric quality. "
                    "D) Switching costs: moving workspace history is costly. "
                    "E) Incumbent risk: generic tools could copy pieces."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn("market_strategy.unfair_advantage", resolved_paths)
        self.assertIn("market_strategy.moat.long_term_moat", resolved_paths)
        self.assertEqual(
            state_json["market_strategy"]["moat"]["long_term_moat"],
            "accumulated rubric quality",
        )
        self.assertIn(
            (
                "state",
                "market_strategy.moat.switching_costs",
                "moving workspace history is costly",
            ),
            updates,
        )

    def test_market_competition_soft_passes_full_competition_answer(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs competition detail."],
            critical_issues=[],
            followup_questions=["List competitor types and named alternatives."],
            help_examples=[],
            followup_message="Please add competition detail.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q5",
                "schema_paths": [
                    "market_strategy.competition.competitor_types[]",
                    "market_strategy.competition.named_competitors[]",
                    "market_strategy.competition.positioning_summary",
                    "market_strategy.competition.competitive_red_flags[]",
                ],
                "type_raw": "required",
            },
            (
                "Competitor types: generic AI chat tools and templates. "
                "Named competitors: ChatGPT, Notion AI, Airtable, Typeform. "
                "Positioning difference: staged interview plus traceable reports. "
                "Red flags: generic tools may be cheaper."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_market_competition_prompt_wins_over_incumbent_moat_keyword(self) -> None:
        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q5",
                "prompt": "List competitor types, named alternatives, positioning, and red flags such as dominant incumbents.",
                "schema_paths": [
                    "market_strategy.competition.competitor_types[]",
                    "market_strategy.competition.named_competitors[]",
                    "market_strategy.competition.positioning_summary",
                    "market_strategy.competition.competitive_red_flags[]",
                ],
                "type_raw": "required",
            },
            (
                "Competitor types: generic AI chat tools and templates. "
                "Named competitors: ChatGPT, Notion AI, Airtable, Typeform. "
                "Positioning difference: staged interview plus traceable reports. "
                "Red flags: generic tools may be cheaper."
            ),
            None,
        )

        self.assertEqual(decision["final_verdict"], "pass")

    def test_market_gtm_prompt_wins_over_switching_costs_moat_keyword(self) -> None:
        decision = followup_compose.build_gate_decision(
            {
                "question_id": "S2Q6",
                "prompt": (
                    "Plan your path to the first 10-50 paying customers. "
                    "Include primary go-to-market channels, first steps, "
                    "sales motion, adoption barriers such as switching costs, "
                    "and expected sales cycle."
                ),
                "schema_paths": [
                    "market_strategy.go_to_market.primary_channels[]",
                    "market_strategy.go_to_market.first_steps[]",
                    "market_strategy.go_to_market.sales_motion",
                    "market_strategy.go_to_market.adoption_barriers[]",
                    "market_strategy.go_to_market.expected_sales_cycle_length",
                ],
                "type_raw": "required",
            },
            (
                "Primary channels: direct university incubator outreach and mentor referrals. "
                "First 3 steps: run 3 design pilots, convert 1 into a paid cohort license, "
                "then publish anonymized examples. Sales motion: founder-led consultative sales. "
                "Adoption barriers: data trust and switching costs. "
                "Sales cycle: 30-60 days with program manager and director approval."
            ),
            None,
        )

        self.assertEqual(decision["final_verdict"], "pass")

    def test_sync_extraction_preview_fills_market_competition_paths(self) -> None:
        resolved_paths, updates, state_json, _state_meta = (
            extraction_preview.build_sync_extraction_preview(
                {
                    "question_id": "S2Q5",
                    "schema_paths": [
                        "market_strategy.competition.competitor_types[]",
                        "market_strategy.competition.named_competitors[]",
                        "market_strategy.competition.positioning_summary",
                        "market_strategy.competition.competitive_red_flags[]",
                    ],
                },
                {},
                current_stage="market",
                answer=(
                    "Competitor types: generic AI chat tools and templates. "
                    "Named competitors: ChatGPT, Notion AI, Airtable, Typeform. "
                    "Positioning difference: staged interview plus traceable reports. "
                    "Red flags: generic tools may be cheaper."
                ),
                state_json={},
                state_meta={},
            )
        )

        self.assertIn("market_strategy.competition.competitor_types[]", resolved_paths)
        self.assertIn("market_strategy.competition.named_competitors[]", resolved_paths)
        self.assertEqual(
            state_json["market_strategy"]["competition"]["positioning_summary"],
            "staged interview plus traceable reports",
        )
        self.assertIn(
            (
                "state",
                "market_strategy.competition.competitive_red_flags[]",
                "generic tools may be cheaper",
            ),
            updates,
        )

    def test_tech_compliance_plan_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs compliance plan."],
            critical_issues=[],
            followup_questions=["What is the first compliance milestone?"],
            help_examples=[],
            followup_message="Please add the compliance milestone.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "tech_execution.security_compliance.audit_requirements",
                    "tech_execution.security_compliance.compliance_milestones",
                    "tech_execution.security_compliance.data_retention_policy",
                ],
                "type_raw": "Conditional (Trigger: Compliance/Sensitive data)",
            },
            (
                "A) Regulations: GDPR-style privacy obligations. B) First "
                "compliance milestone: complete DPA/security checklist before "
                "paid pilots in Q3. C) Data retention/deletion plan: support "
                "export/delete on request and purge inactive pilot data after "
                "12 months."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")

    def test_tech_compliance_plan_natural_labels_soft_pass_needs_info_gate(
        self,
    ) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs compliance plan."],
            critical_issues=[],
            followup_questions=["What is the first compliance milestone?"],
            help_examples=[],
            followup_message="Please add the compliance milestone.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "schema_paths": [
                    "tech_execution.security_compliance.audit_requirements",
                    "tech_execution.security_compliance.compliance_milestones",
                    "tech_execution.security_compliance.data_retention_policy",
                ],
                "type_raw": "Conditional (Trigger: Compliance/Sensitive data)",
            },
            (
                "A) Required audits/certs: no formal certification for first "
                "design pilots, but GDPR-style DPA/security checklist first. "
                "B) Retention/deletion: keep workspace data while active, "
                "support export/delete on request, and delete inactive pilot "
                "projects after 12 months unless renewed. C) First milestone: "
                "technical founder owns a DPA/security checklist and "
                "deletion/export workflow before paid pilots in Q3."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")

    def test_tech_sensitive_data_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs sensitive data selection."],
            critical_issues=[],
            followup_questions=["Will you handle personal/money/health/children/EU data?"],
            help_examples=[],
            followup_message="Please select sensitive data types.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "L3Q3",
                "schema_paths": [
                    "tech_execution.security_compliance.data_types",
                    "tech_execution.security_compliance.compliance_requirements",
                ],
                "type_raw": "required",
            },
            (
                "Data handled: personal info such as user email/name and project text. "
                "No money, health, children data, or payment data in MVP. "
                "EU users are possible, so GDPR-style deletion/export matters."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")

    def test_tech_ai_quality_answer_soft_passes_needs_info_gate(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs AI quality plan."],
            critical_issues=[],
            followup_questions=["Define quality, monitoring, and guardrails."],
            help_examples=[],
            followup_message="Please add AI quality details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.4, evidence=0.3),
            overall=0.45,
        )

        decision = followup_compose.build_gate_decision(
            {
                "question_id": "L3Q11",
                "schema_paths": [
                    "tech_execution.data_ai_scalability.model_quality_metrics",
                    "tech_execution.data_ai_scalability.monitoring_feedback_loop",
                    "tech_execution.data_ai_scalability.fallback_guardrails",
                ],
                "type_raw": "conditional",
            },
            (
                "A) Good output: summaries match confirmed facts and flag unknowns. "
                "B) Quality review: compare extracted fields to user answers weekly. "
                "C) Fallbacks/guardrails: deterministic extraction, timeouts, "
                "and manual review before reports."
            ),
            gate,
        )

        self.assertEqual(decision["final_verdict"], "pass")
        self.assertIn("Soft pass", " ".join(decision["risk_notes"]))

    def test_resolve_explicit_router_mode_prefers_explicit_message_meta(self) -> None:
        mode = chat._resolve_explicit_router_mode(
            {"tech_execution": {"meta": {"mode": "lite"}}},
            {"selected_option_key": "pro"},
        )

        self.assertEqual(mode, "pro")

    def test_resolve_explicit_router_mode_accepts_developer_text(self) -> None:
        mode = chat._resolve_explicit_router_mode(
            {},
            {},
            "I'm a developer",
        )

        self.assertEqual(mode, "pro")

    def test_apply_router_mode_selection_guard_requires_explicit_selection(
        self,
    ) -> None:
        decision, chosen_mode, followup_message = (
            router_mode.apply_router_mode_selection_guard(
                {
                    "prompt": "Choose your technical depth.",
                },
                {
                    "final_verdict": "pass",
                    "model_verdict": "pass",
                    "missing_points": [],
                    "critical_issues": [],
                    "followup_questions": [],
                    "help_examples": [],
                    "followup_message": None,
                    "risk_notes": [],
                    "score": {"clarity": 1.0, "completeness": 1.0, "evidence": 1.0},
                    "overall": 1.0,
                    "unknown": False,
                    "threshold": 0.7,
                },
                state_json={},
                message_meta={},
                latest_answer="I can answer this.",
            )
        )

        self.assertIsNone(chosen_mode)
        self.assertEqual(decision["final_verdict"], "needs_info")
        self.assertIn("explicitly", followup_message or "")

    def test_repeated_followup_cap_marks_unresolved_paths_unknown(self) -> None:
        gate = AnswerGateResult(
            verdict="needs_info",
            missing_points=["Needs the rest of the compliance plan."],
            critical_issues=[],
            followup_questions=["What is the milestone and retention plan?"],
            help_examples=[],
            followup_message="Please add the missing details.",
            score=AnswerGateScore(clarity=0.7, completeness=0.3, evidence=0.2),
            overall=0.35,
        )
        question_detail = {
            "schema_paths": [
                "tech_execution.security_compliance.audit_requirements",
                "tech_execution.security_compliance.compliance_milestones",
                "tech_execution.security_compliance.data_retention_policy",
            ],
            "type_raw": "required",
        }
        answer = "Required certifications: no SOC 2 for MVP pilots yet."
        decision = followup_compose.build_gate_decision(question_detail, answer, gate)
        resolved_paths, _, _, _ = extraction_preview.build_sync_extraction_preview(
            question_detail,
            {},
            current_stage="tech",
            answer=answer,
            state_json={},
            state_meta={},
            ai_assisted=False,
        )

        capped_decision, unknown_paths = followup_compose.apply_repeated_followup_cap(
            decision,
            question_detail,
            answer,
            schema_paths=question_detail["schema_paths"],
            resolved_paths=resolved_paths,
            previous_answer_count=1,
        )

        self.assertEqual(capped_decision["final_verdict"], "pass")
        self.assertTrue(capped_decision["partial_advance"])
        self.assertIn(
            "tech_execution.security_compliance.data_retention_policy",
            unknown_paths,
        )

    def test_partial_fill_followup_focuses_unresolved_paths(self) -> None:
        decision = {
            "final_verdict": "needs_info",
            "model_verdict": "needs_info",
            "missing_points": ["Needs the full compliance plan."],
            "critical_issues": [],
            "followup_questions": ["Please answer the compliance plan."],
            "help_examples": [],
            "followup_message": None,
            "risk_notes": ["Answer lacks required specificity."],
            "score": {"clarity": 0.6, "completeness": 0.4, "evidence": 0.2},
            "overall": 0.4,
            "unknown": False,
            "threshold": 0.7,
        }

        focused = followup_compose.focus_followup_on_unresolved_paths(
            decision,
            schema_paths=[
                "tech_execution.security_compliance.audit_requirements",
                "tech_execution.security_compliance.compliance_milestones",
                "tech_execution.security_compliance.data_retention_policy",
            ],
            resolved_paths=[
                "tech_execution.security_compliance.audit_requirements",
            ],
        )

        self.assertIn("compliance milestones", focused["missing_points"][0])
        self.assertIn("data retention policy", focused["followup_questions"][0])
        self.assertNotIn("audit requirements", focused["followup_questions"][0])

    def test_require_router_mode_rejects_missing_mode(self) -> None:
        with self.assertRaises(RuntimeError):
            router_mode.require_router_mode(None)


if __name__ == "__main__":
    unittest.main()
