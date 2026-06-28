import unittest
from unittest.mock import AsyncMock, patch

from app.services.stage_confirmations import (
    ConfirmedStagePersistenceResult,
    StageConfirmationRuntimeError,
    commit_stage_confirmation_workflow,
    initialize_stage_confirmation_runtime,
    persist_confirmed_stage_assessment,
)
from app.services.stage_confirmation_preparation import (
    build_prepared_stage_confirmation_payload,
    extract_stage_prompt_task_traces,
    normalize_stage_state_snapshot,
    resolve_stage_confirmation_defaults,
)
from app.services.stage_confirmation_persistence_payloads import (
    build_confirmed_stage_artifact_payload,
)


class _FakeResult:
    def __init__(self, row: dict | None = None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


class StageConfirmationPreparationHelperTests(unittest.TestCase):
    def test_normalize_stage_state_snapshot_defends_against_bad_values(self) -> None:
        snapshot = normalize_stage_state_snapshot(
            {
                "state_json": None,
                "state_meta": "bad",
                "state_version": None,
            }
        )

        self.assertEqual(snapshot.state_json, {})
        self.assertEqual(snapshot.state_meta, {})
        self.assertEqual(snapshot.state_version, 0)

    def test_resolve_stage_confirmation_defaults_shapes_next_stage(self) -> None:
        defaults = resolve_stage_confirmation_defaults(
            stage="market",
            next_stage_map={"market": "tech"},
        )

        self.assertIsNotNone(defaults)
        self.assertEqual(defaults.next_stage, "tech")
        self.assertEqual(defaults.next_variant, "router")
        self.assertEqual(defaults.next_stage_status, "in_progress")

        report_defaults = resolve_stage_confirmation_defaults(
            stage="tech",
            next_stage_map={"tech": "report"},
        )
        self.assertEqual(report_defaults.next_stage_status, "awaiting_confirm")

        self.assertIsNone(
            resolve_stage_confirmation_defaults(
                stage="unknown",
                next_stage_map={"market": "tech"},
            )
        )

    def test_extract_stage_prompt_task_traces_returns_defensive_copy(self) -> None:
        row = {"scores_json": {"prompt_task_traces": {"stage_summary": {"ok": True}}}}

        traces = extract_stage_prompt_task_traces(row)
        traces["stage_summary"]["ok"] = False

        self.assertEqual(
            row["scores_json"]["prompt_task_traces"]["stage_summary"]["ok"],
            True,
        )
        self.assertEqual(extract_stage_prompt_task_traces({}), {})

    def test_build_prepared_stage_confirmation_payload_preserves_fields(self) -> None:
        state_snapshot = normalize_stage_state_snapshot(
            {"state_json": {}, "state_meta": {}, "state_version": 7}
        )
        defaults = resolve_stage_confirmation_defaults(
            stage="problem",
            next_stage_map={"problem": "market"},
        )

        payload = build_prepared_stage_confirmation_payload(
            org_id="org-1",
            project_id="project-1",
            user_id="user-1",
            stage="problem",
            bank_id="bank-1",
            current_variant="default",
            defaults=defaults,
            next_variant="default",
            next_stage_status="in_progress",
            state_snapshot=state_snapshot,
            current_stage_missing_paths=["problem.one_line"],
            assessment_row={
                "draft_summary_markdown": "Summary",
                "generator_model": "model-a",
            },
            prompt_task_traces={"stage_summary": {"ok": True}},
            output_locale="zh",
            current_question_id="question-1",
            next_question_id="question-2",
            missing_paths=["market.uvp"],
            question_detail={"question_id": "M1"},
        )

        self.assertEqual(payload["next_stage"], "market")
        self.assertEqual(payload["state_version"], 7)
        self.assertEqual(payload["summary_markdown"], "Summary")
        self.assertEqual(payload["summary_model"], "model-a")
        self.assertEqual(payload["prompt_task_traces"], {"stage_summary": {"ok": True}})
        self.assertEqual(payload["question_detail"], {"question_id": "M1"})


class StageConfirmationPersistencePayloadTests(unittest.TestCase):
    def test_build_confirmed_stage_artifact_payload_preserves_prompt_traces(
        self,
    ) -> None:
        payload = build_confirmed_stage_artifact_payload(
            stage="market",
            state_json={"market": {"target_segment": "SMB"}},
            state_meta={},
            missing_paths=[],
            prompt_task_traces={"stage_summary": {"model": "test-model"}},
        )

        self.assertEqual(payload.context_card["stage"], "market")
        self.assertIsInstance(payload.validation_plan, list)
        self.assertEqual(
            payload.scores_json_payload,
            {"prompt_task_traces": {"stage_summary": {"model": "test-model"}}},
        )

    def test_build_confirmed_stage_artifact_payload_omits_empty_prompt_traces(
        self,
    ) -> None:
        payload = build_confirmed_stage_artifact_payload(
            stage="problem",
            state_json={},
            state_meta={},
            missing_paths=["problem.one_line"],
            prompt_task_traces={},
        )

        self.assertEqual(payload.context_card["stage"], "problem")
        self.assertIsNone(payload.scores_json_payload)


class StageConfirmationPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_persist_confirmed_stage_assessment_writes_payloads(self) -> None:
        session = _FakeSession([_FakeResult({"id": "assessment-1"}), _FakeResult()])

        result = await persist_confirmed_stage_assessment(
            session,
            org_id="org-1",
            project_id="project-1",
            stage="market",
            user_id="user-1",
            state_version=7,
            state_json={
                "market_strategy": {
                    "uvp": {"one_line": "Fast setup for student founders."}
                }
            },
            state_meta={"summary_locales": {"market": {"draft": "zh"}}},
            missing_paths=["market_strategy.competition.alternatives"],
            summary_markdown="Market summary",
            summary_model="model-a",
            prompt_task_traces={"stage_summary": {"ok": True}},
            output_locale="zh",
        )

        insert_sql, insert_params = session.calls[0]
        update_sql, update_params = session.calls[1]

        self.assertEqual(result.assessment_id, "assessment-1")
        self.assertEqual(
            result.scores_json_payload,
            {"prompt_task_traces": {"stage_summary": {"ok": True}}},
        )
        self.assertEqual(insert_params["org_id"], "org-1")
        self.assertEqual(insert_params["project_id"], "project-1")
        self.assertEqual(insert_params["stage"], "market")
        self.assertEqual(insert_params["state_version"], 7)
        self.assertEqual(insert_params["summary"], "Market summary")
        self.assertEqual(insert_params["generator_model"], "model-a")
        self.assertEqual(
            insert_params["scores_json"],
            {"prompt_task_traces": {"stage_summary": {"ok": True}}},
        )
        self.assertIn(
            "ON CONFLICT (project_id, stage) WHERE deleted_at IS NULL",
            insert_sql,
        )
        self.assertEqual(update_params["project_id"], "project-1")
        self.assertEqual(update_params["org_id"], "org-1")
        self.assertEqual(
            update_params["state_meta"]["summary_locales"]["market"],
            {"draft": "zh", "final": "zh"},
        )
        self.assertIn("UPDATE project_states", update_sql)
        self.assertEqual(result.context_card["stage"], "market")
        self.assertTrue(result.validation_plan)

    async def test_persist_confirmed_stage_assessment_omits_empty_trace_payload(
        self,
    ) -> None:
        session = _FakeSession([_FakeResult({"id": "assessment-2"}), _FakeResult()])

        result = await persist_confirmed_stage_assessment(
            session,
            org_id="org-1",
            project_id="project-1",
            stage="problem",
            user_id="user-1",
            state_version=1,
            state_json={},
            state_meta={},
            missing_paths=[],
            summary_markdown=None,
            summary_model=None,
            prompt_task_traces={},
            output_locale="en",
        )

        self.assertIsNone(result.scores_json_payload)
        self.assertIsNone(session.calls[0][1]["scores_json"])


class StageConfirmationCommitWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_commit_stage_confirmation_enqueues_report_before_finalize(
        self,
    ) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    {
                        "current_stage": "tech",
                        "stage_status": "awaiting_confirm",
                        "question_bank_version_id": "bank-1",
                    }
                ),
                _FakeResult(
                    {
                        "state_version": 8,
                        "state_json": {"technical_solution": {}},
                        "state_meta": {},
                    }
                ),
            ]
        )
        call_order: list[str] = []

        async def _enqueue_report(*args, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append("report")
            return {"status": "queued"}

        async def _enqueue_finalize(*args, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append("finalize")
            return {"id": "finalize-job-1"}

        with (
            patch(
                "app.services.stage_confirmations.can_mutate_project",
                new_callable=AsyncMock,
                return_value=True,
            ) as can_mutate,
            patch(
                "app.services.stage_confirmations.persist_confirmed_stage_assessment",
                new_callable=AsyncMock,
                return_value=ConfirmedStagePersistenceResult(
                    assessment_id="assessment-1",
                    context_card={"stage": "tech"},
                    validation_plan=[{"action": "Build spike"}],
                    scores_json_payload={"prompt_task_traces": {"ok": True}},
                ),
            ) as persist_stage,
            patch(
                "app.services.stage_confirmations.advance_project_stage_from_decision",
                new_callable=AsyncMock,
            ) as advance_stage,
            patch(
                "app.services.stage_confirmations.enqueue_report_generation_job",
                side_effect=_enqueue_report,
            ) as enqueue_report,
            patch(
                "app.services.stage_confirmations.enqueue_stage_finalize_job",
                side_effect=_enqueue_finalize,
            ) as enqueue_finalize,
            patch(
                "app.services.stage_confirmations.initialize_stage_confirmation_runtime",
                new_callable=AsyncMock,
            ) as initialize_runtime,
        ):
            result = await commit_stage_confirmation_workflow(
                session,
                org_id="org-1",
                project_id="project-1",
                user_id="user-1",
                stage="tech",
                bank_id="bank-1",
                current_variant="router",
                next_stage="report",
                next_variant="default",
                next_stage_status="awaiting_confirm",
                state_version=8,
                current_stage_missing_paths=[],
                summary_markdown="Tech summary",
                summary_model="model-a",
                prompt_task_traces={"stage_summary": {"ok": True}},
                output_locale="zh",
                current_question_id=None,
                next_question_id=None,
                missing_paths=[],
                question_detail=None,
                report_ready_message="Report ready.",
            )

        self.assertEqual(result.assessment_id, "assessment-1")
        self.assertEqual(result.next_stage, "report")
        self.assertEqual(result.report_job_status["status"], "queued")
        self.assertEqual(call_order, ["report", "finalize"])
        self.assertIn("FOR UPDATE", session.calls[0][0])
        can_mutate.assert_awaited_once_with(
            session,
            project_id="project-1",
            org_id="org-1",
            user_id="user-1",
        )
        persist_stage.assert_awaited_once()
        advance_stage.assert_awaited_once()
        enqueue_report.assert_awaited_once()
        enqueue_finalize.assert_awaited_once()
        initialize_runtime.assert_awaited_once()
        self.assertEqual(
            enqueue_finalize.await_args.kwargs["question_bank_version_id"],
            "bank-1",
        )
        self.assertEqual(enqueue_finalize.await_args.kwargs["variant"], "router")

    async def test_commit_stage_confirmation_reuses_state_snapshot_normalization(
        self,
    ) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    {
                        "current_stage": "problem",
                        "stage_status": "awaiting_confirm",
                        "question_bank_version_id": "bank-1",
                    }
                ),
                _FakeResult(
                    {
                        "state_version": 3,
                        "state_json": "bad",
                        "state_meta": ["bad"],
                    }
                ),
            ]
        )

        with (
            patch(
                "app.services.stage_confirmations.can_mutate_project",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.stage_confirmations.persist_confirmed_stage_assessment",
                new_callable=AsyncMock,
                return_value=ConfirmedStagePersistenceResult(
                    assessment_id="assessment-1",
                    context_card={},
                    validation_plan=[],
                    scores_json_payload=None,
                ),
            ) as persist_stage,
            patch(
                "app.services.stage_confirmations.advance_project_stage_from_decision",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.stage_confirmations.enqueue_stage_finalize_job",
                new_callable=AsyncMock,
            ) as enqueue_finalize,
            patch(
                "app.services.stage_confirmations.initialize_stage_confirmation_runtime",
                new_callable=AsyncMock,
            ),
        ):
            await commit_stage_confirmation_workflow(
                session,
                org_id="org-1",
                project_id="project-1",
                user_id="user-1",
                stage="problem",
                bank_id="bank-1",
                current_variant="default",
                next_stage="market",
                next_variant="default",
                next_stage_status="in_progress",
                state_version=3,
                current_stage_missing_paths=[],
                summary_markdown="Problem summary",
                summary_model="model-a",
                prompt_task_traces={},
                output_locale="en",
                current_question_id="question-1",
                next_question_id=None,
                missing_paths=["market.segment"],
                question_detail={"prompt": "Next question", "question_id": "M1"},
                report_ready_message="Report ready.",
            )

        persist_stage.assert_awaited_once()
        self.assertEqual(persist_stage.await_args.kwargs["state_json"], {})
        self.assertEqual(persist_stage.await_args.kwargs["state_meta"], {})
        self.assertEqual(enqueue_finalize.await_args.kwargs["context_version"], 3)


class StageConfirmationRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_next_stage_runtime_inserts_assistant_prompt(self) -> None:
        session = _FakeSession(
            [
                _FakeResult(),
                _FakeResult({"id": "question-instance-1"}),
                _FakeResult(),
            ]
        )

        await initialize_stage_confirmation_runtime(
            session,
            org_id="org-1",
            project_id="project-1",
            next_stage="market",
            next_variant="default",
            next_stage_status="in_progress",
            current_question_id="question-1",
            next_question_id="question-2",
            missing_paths=["market_strategy.uvp.one_line"],
            assistant_prompt="What is your one-line value proposition?",
            question_detail={
                "question_id": "M1",
                "stage": "market",
                "variant": "default",
                "prompt_meta": {"ui": {"placeholder": "One sentence"}},
            },
            report_ready_message="Report ready.",
        )

        runtime_sql, runtime_params = session.calls[0]
        question_sql, question_params = session.calls[1]
        message_sql, message_params = session.calls[2]

        self.assertIn("UPDATE project_runtime", runtime_sql)
        self.assertEqual(runtime_params["current_question_id"], "question-1")
        self.assertEqual(runtime_params["next_question_id"], "question-2")
        self.assertEqual(
            runtime_params["missing_paths"],
            ["market_strategy.uvp.one_line"],
        )
        self.assertIn("INSERT INTO project_question_instances", question_sql)
        self.assertEqual(question_params["question_id"], "question-1")
        self.assertIn("INSERT INTO conversation_messages", message_sql)
        self.assertEqual(message_params["stage"], "market")
        self.assertEqual(
            message_params["content"],
            "What is your one-line value proposition?",
        )
        self.assertEqual(
            message_params["meta"]["question_meta"]["ui"],
            {"placeholder": "One sentence"},
        )

    async def test_initialize_report_runtime_inserts_report_ready_message(self) -> None:
        session = _FakeSession([_FakeResult(), _FakeResult()])

        await initialize_stage_confirmation_runtime(
            session,
            org_id="org-1",
            project_id="project-1",
            next_stage="report",
            next_variant="default",
            next_stage_status="awaiting_confirm",
            current_question_id=None,
            next_question_id=None,
            missing_paths=["ignored"],
            assistant_prompt=None,
            question_detail=None,
            report_ready_message="Report stage ready.",
        )

        runtime_sql, runtime_params = session.calls[0]
        message_sql, message_params = session.calls[1]

        self.assertIn("UPDATE project_runtime", runtime_sql)
        self.assertIsNone(runtime_params["current_question_id"])
        self.assertEqual(runtime_params["missing_paths"], [])
        self.assertIn("INSERT INTO conversation_messages", message_sql)
        self.assertEqual(message_params["stage"], "report")
        self.assertEqual(message_params["content"], "Report stage ready.")

    async def test_initialize_next_stage_runtime_requires_current_question(self) -> None:
        with self.assertRaisesRegex(
            StageConfirmationRuntimeError,
            "Next stage question is missing.",
        ):
            await initialize_stage_confirmation_runtime(
                _FakeSession([]),
                org_id="org-1",
                project_id="project-1",
                next_stage="market",
                next_variant="default",
                next_stage_status="in_progress",
                current_question_id=None,
                next_question_id=None,
                missing_paths=[],
                assistant_prompt="Prompt",
                question_detail={"question_id": "M1"},
                report_ready_message="Report ready.",
            )


if __name__ == "__main__":
    unittest.main()
