import unittest
from pathlib import Path

from app.services.prompt_runtime import (
    DEFAULT_PROMPT_OUTPUT_GUARD,
    PromptMutationClass,
)
from app.services.stage_transition import (
    STAGE_STATUS_AWAITING_CONFIRM,
    STAGE_STATUS_IN_PROGRESS,
    STAGE_STATUS_PASSED,
    decide_next_stage_after_confirmation,
    decide_report_confirmation_complete,
    decide_stage_confirmation_advance,
    decide_stage_draft_generation,
    decide_stage_question_answer,
    decide_stage_ready,
    is_report_generation_recovery_stage,
    next_stage_starts_in_review,
)
from app.services.stage_runtime import (
    advance_project_stage_from_decision,
    mark_project_stage_passed_from_decision,
    update_project_runtime_missing_paths_from_decision,
    update_project_stage_status_from_decision,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class _FakeSession:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict]] = []

    async def execute(self, statement, params=None):
        self.executed.append((str(statement), dict(params or {})))
        return type("Result", (), {"rowcount": 1})()


class StageTransitionDecisionTests(unittest.TestCase):
    def test_resolved_blocking_paths_can_enter_awaiting_confirm(self) -> None:
        decision = decide_stage_ready(
            "problem",
            ["problem.one_line"],
            state_json={"problem": {"one_line": "Manual reporting is slow."}},
            state_meta={},
            variant="default",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.next_stage_status, STAGE_STATUS_AWAITING_CONFIRM)
        self.assertEqual(decision.reason, "blocking_paths_resolved")
        self.assertEqual(decision.missing_paths, [])
        self.assertIsNone(decision.current_stage_update)

    def test_pending_confirm_does_not_count_as_confirmed_input(self) -> None:
        decision = decide_stage_ready(
            "problem",
            ["problem.one_line"],
            state_json={},
            state_meta={
                "pending_confirm": {
                    "problem": {"one_line": "Manual reporting is slow."}
                }
            },
            variant="default",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.next_stage_status, STAGE_STATUS_IN_PROGRESS)
        self.assertEqual(decision.reason, "blocking_paths_missing")
        self.assertEqual(decision.missing_paths, ["problem.one_line"])

    def test_router_stage_does_not_auto_enter_awaiting_confirm(self) -> None:
        decision = decide_stage_ready(
            "tech",
            ["tech_execution.product_scope.mvp_definition"],
            state_json={
                "tech_execution": {
                    "product_scope": {
                        "mvp_definition": "Pilot dashboard for finance ops."
                    }
                }
            },
            state_meta={},
            variant="router",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.next_stage_status, STAGE_STATUS_IN_PROGRESS)
        self.assertEqual(decision.reason, "stage_disallows_auto_awaiting_confirm")
        self.assertEqual(decision.missing_paths, [])
        self.assertIsNone(decision.current_stage_update)

    def test_report_stage_is_ready_for_report_confirmation(self) -> None:
        decision = decide_next_stage_after_confirmation(
            "report",
            [],
            state_json={},
            state_meta={},
            variant="default",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.next_stage_status, STAGE_STATUS_AWAITING_CONFIRM)
        self.assertEqual(decision.reason, "report_stage_ready")
        self.assertFalse(
            next_stage_starts_in_review("report", decision.next_stage_status)
        )

    def test_awaiting_confirm_does_not_advance_without_confirmation(self) -> None:
        ready_decision = decide_stage_ready(
            "market",
            [],
            state_json={},
            state_meta={},
            variant="default",
        )
        blocked_confirmation = decide_stage_confirmation_advance(
            requested_stage="market",
            current_stage="market",
            stage_status=STAGE_STATUS_IN_PROGRESS,
            next_stage="tech",
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
        )
        allowed_confirmation = decide_stage_confirmation_advance(
            requested_stage="market",
            current_stage="market",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
            next_stage="tech",
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
        )

        self.assertIsNone(ready_decision.current_stage_update)
        self.assertFalse(blocked_confirmation.allowed)
        self.assertIsNone(blocked_confirmation.current_stage_update)
        self.assertTrue(allowed_confirmation.allowed)
        self.assertEqual(allowed_confirmation.current_stage_update, "tech")

    def test_report_confirmation_marks_report_passed_only_from_awaiting_confirm(self) -> None:
        blocked = decide_report_confirmation_complete(
            current_stage="report",
            stage_status=STAGE_STATUS_IN_PROGRESS,
        )
        allowed = decide_report_confirmation_complete(
            current_stage="report",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )

        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.reason, "stage_not_awaiting_confirm")
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.next_stage_status, STAGE_STATUS_PASSED)
        self.assertIsNone(allowed.current_stage_update)

    def test_report_generation_recovery_allows_already_passed_report_stage(self) -> None:
        self.assertTrue(
            is_report_generation_recovery_stage(
                current_stage="report",
                stage_status=STAGE_STATUS_PASSED,
            )
        )
        self.assertFalse(
            is_report_generation_recovery_stage(
                current_stage="report",
                stage_status=STAGE_STATUS_AWAITING_CONFIRM,
            )
        )
        self.assertFalse(
            is_report_generation_recovery_stage(
                current_stage="tech",
                stage_status=STAGE_STATUS_PASSED,
            )
        )

    def test_question_answering_is_allowed_only_while_stage_in_progress(self) -> None:
        allowed = decide_stage_question_answer(
            current_stage="problem",
            stage_status=STAGE_STATUS_IN_PROGRESS,
        )
        waiting = decide_stage_question_answer(
            current_stage="problem",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )
        report = decide_stage_question_answer(
            current_stage="report",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )
        passed = decide_stage_question_answer(
            current_stage="tech",
            stage_status=STAGE_STATUS_PASSED,
        )

        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.reason, "stage_allows_questions")
        self.assertFalse(waiting.allowed)
        self.assertEqual(waiting.reason, "stage_not_in_progress")
        self.assertFalse(report.allowed)
        self.assertEqual(report.reason, "stage_blocks_questions")
        self.assertFalse(passed.allowed)
        self.assertEqual(passed.reason, "stage_passed")

    def test_stage_draft_generation_requires_matching_awaiting_confirm_stage(self) -> None:
        allowed = decide_stage_draft_generation(
            requested_stage="problem",
            current_stage="problem",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )
        wrong_stage = decide_stage_draft_generation(
            requested_stage="market",
            current_stage="problem",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )
        not_ready = decide_stage_draft_generation(
            requested_stage="problem",
            current_stage="problem",
            stage_status=STAGE_STATUS_IN_PROGRESS,
        )

        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.reason, "stage_allows_draft_generation")
        self.assertFalse(wrong_stage.allowed)
        self.assertEqual(wrong_stage.reason, "stage_mismatch")
        self.assertFalse(not_ready.allowed)
        self.assertEqual(not_ready.reason, "stage_not_awaiting_confirm")


class StageRuntimeWriterTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_status_writer_uses_decision_status(self) -> None:
        session = _FakeSession()
        decision = decide_stage_ready(
            "problem",
            [],
            state_json={},
            state_meta={},
            variant="default",
        )

        await update_project_stage_status_from_decision(
            session,
            project_id="project-1",
            org_id="org-1",
            decision=decision,
            current_stage="problem",
            require_allowed=True,
        )

        sql, params = session.executed[-1]
        self.assertIn("UPDATE projects", sql)
        self.assertEqual(params["stage_status"], STAGE_STATUS_AWAITING_CONFIRM)
        self.assertEqual(params["current_stage"], "problem")

    async def test_runtime_missing_paths_writer_uses_decision_missing_paths(self) -> None:
        session = _FakeSession()
        decision = decide_stage_ready(
            "market",
            ["market_strategy.uvp.one_line"],
            state_json={},
            state_meta={},
            variant="default",
        )

        await update_project_runtime_missing_paths_from_decision(
            session,
            project_id="project-1",
            org_id="org-1",
            decision=decision,
        )

        sql, params = session.executed[-1]
        self.assertIn("UPDATE project_runtime", sql)
        self.assertEqual(params["missing_paths"], ["market_strategy.uvp.one_line"])

    async def test_stage_advance_writer_requires_allowed_confirmation_decision(self) -> None:
        session = _FakeSession()
        blocked = decide_stage_confirmation_advance(
            requested_stage="problem",
            current_stage="problem",
            stage_status=STAGE_STATUS_IN_PROGRESS,
            next_stage="market",
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
        )
        with self.assertRaises(ValueError):
            await advance_project_stage_from_decision(
                session,
                project_id="project-1",
                org_id="org-1",
                decision=blocked,
                next_variant="default",
            )

        allowed = decide_stage_confirmation_advance(
            requested_stage="problem",
            current_stage="problem",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
            next_stage="market",
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
        )
        await advance_project_stage_from_decision(
            session,
            project_id="project-1",
            org_id="org-1",
            decision=allowed,
            next_variant="default",
        )

        sql, params = session.executed[-1]
        self.assertIn("SET current_stage = :next_stage", sql)
        self.assertEqual(params["next_stage"], "market")
        self.assertEqual(params["stage_status"], STAGE_STATUS_IN_PROGRESS)

    async def test_report_passed_writer_requires_report_passed_decision(self) -> None:
        session = _FakeSession()
        decision = decide_report_confirmation_complete(
            current_stage="report",
            stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        )

        await mark_project_stage_passed_from_decision(
            session,
            project_id="project-1",
            org_id="org-1",
            decision=decision,
        )

        sql, params = session.executed[-1]
        self.assertIn("UPDATE projects", sql)
        self.assertEqual(params["stage_status"], STAGE_STATUS_PASSED)
        self.assertEqual(params["current_stage"], "report")


class PromptMutationBoundaryInvariantTests(unittest.TestCase):
    def test_llm_tasks_do_not_escape_registered_mutation_boundaries(self) -> None:
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "answer_gate",
            PromptMutationClass.DECISION_ONLY,
        )
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "extract",
            PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        )
        for task_key in (
            "stage_summary_problem",
            "stage_summary_market",
            "stage_summary_tech",
            "dvf_scoring",
            "final_report",
        ):
            with self.subTest(task_key=task_key):
                DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
                    task_key,
                    PromptMutationClass.REPORT_ARTIFACT,
                )
                with self.assertRaises(PermissionError):
                    DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
                        task_key,
                        PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
                    )


class StageTransitionSourceGuardTests(unittest.TestCase):
    def test_normal_runtime_stage_writes_go_through_stage_runtime(self) -> None:
        normal_runtime_sources = (
            "app/api/routes/assessments.py",
            "app/api/routes/chat.py",
            "app/api/routes/projects.py",
            "app/worker.py",
        )
        forbidden_sql_fragments = (
            "SET current_stage =",
            "SET stage_status =",
            "current_stage = :current_stage",
            "stage_status = :stage_status",
        )

        for relative_path in normal_runtime_sources:
            source = (BACKEND_ROOT / relative_path).read_text()
            for fragment in forbidden_sql_fragments:
                with self.subTest(relative_path=relative_path, fragment=fragment):
                    self.assertNotIn(fragment, source)

        stage_runtime_source = (
            BACKEND_ROOT / "app/services/stage_runtime.py"
        ).read_text()
        self.assertIn("SET current_stage = :next_stage", stage_runtime_source)
        self.assertIn("SET stage_status = :stage_status", stage_runtime_source)

        admin_project_source = (
            BACKEND_ROOT / "app/api/routes/admin_projects.py"
        ).read_text()
        self.assertIn("Admin-only repair override", admin_project_source)


if __name__ == "__main__":
    unittest.main()
