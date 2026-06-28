import unittest
from unittest.mock import AsyncMock, patch

from app.services.report_confirmations import (
    ReportConfirmationConflictError,
    confirm_report_stage_workflow,
    confirm_project_report_stage_workflow,
    fetch_report_confirmation_recovery_report,
    resolve_report_confirmation_prerequisites,
    ReportConfirmationPermissionError,
    ReportConfirmationWorkflowResult,
)


class _FakeResult:
    def __init__(
        self,
        *,
        row: dict | None = None,
        rows: list[dict] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


class ReportConfirmationPrerequisiteTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_report_confirmation_prerequisites_merges_plans(self) -> None:
        session = _FakeSession(
            [
                _FakeResult(row={"state_version": 4}),
                _FakeResult(
                    rows=[
                        {
                            "stage": "problem",
                            "confirmed": True,
                            "validation_plan_json": [
                                {"action": "Interview users"},
                            ],
                        },
                        {
                            "stage": "market",
                            "confirmed": True,
                            "validation_plan_json": [
                                {"action": "Test willingness to pay"},
                            ],
                        },
                        {
                            "stage": "tech",
                            "confirmed": True,
                            "validation_plan_json": [
                                {"action": "Interview users"},
                                {"action": "Build spike"},
                            ],
                        },
                    ]
                ),
            ]
        )

        result = await resolve_report_confirmation_prerequisites(
            session,
            project_id="project-1",
            org_id="org-1",
            client_context_version=4,
        )

        self.assertEqual(result.state_version, 4)
        self.assertEqual(
            [item["action"] for item in result.validation_plan],
            ["Interview users", "Test willingness to pay", "Build spike"],
        )
        self.assertEqual(
            session.calls[0][1],
            {"project_id": "project-1", "org_id": "org-1"},
        )
        self.assertIn("stage IN ('problem','market','tech')", session.calls[1][0])

    async def test_resolve_report_confirmation_prerequisites_rejects_stale_client(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ReportConfirmationConflictError,
            "Context updated while you were away. Refresh and try again.",
        ):
            await resolve_report_confirmation_prerequisites(
                _FakeSession([_FakeResult(row={"state_version": 5})]),
                project_id="project-1",
                org_id="org-1",
                client_context_version=4,
            )

    async def test_resolve_report_confirmation_prerequisites_requires_all_stages(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ReportConfirmationConflictError,
            "All stage summaries must be confirmed before generating report.",
        ):
            await resolve_report_confirmation_prerequisites(
                _FakeSession(
                    [
                        _FakeResult(row={"state_version": 4}),
                        _FakeResult(
                            rows=[
                                {"stage": "problem", "confirmed": True},
                                {"stage": "market", "confirmed": True},
                            ]
                        ),
                    ]
                ),
                project_id="project-1",
                org_id="org-1",
                client_context_version=4,
            )


class ReportConfirmationRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_report_confirmation_recovery_report_filters_context_locale(
        self,
    ) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    row={
                        "id": "report-1",
                        "report_version": 3,
                        "created_at": "2026-06-06T00:00:00Z",
                    }
                )
            ]
        )

        report = await fetch_report_confirmation_recovery_report(
            session,
            project_id="project-1",
            org_id="org-1",
            state_version=4,
            output_locale="zh",
            default_output_locale="en",
        )

        sql, params = session.calls[0]
        self.assertEqual(
            report,
            {
                "id": "report-1",
                "report_version": 3,
                "created_at": "2026-06-06T00:00:00Z",
            },
        )
        self.assertIn("status = 'final'", sql)
        self.assertIn("generated_from_state_version = :state_version", sql)
        self.assertIn("content_json->>'artifact_locale'", sql)
        self.assertEqual(
            params,
            {
                "project_id": "project-1",
                "org_id": "org-1",
                "state_version": 4,
                "output_locale": "zh",
                "default_output_locale": "en",
            },
        )


class ReportConfirmationWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirm_project_report_stage_denies_without_permission(self) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    row={
                        "id": "project-1",
                        "current_stage": "report",
                        "stage_status": "awaiting_confirm",
                    }
                )
            ]
        )

        with (
            patch(
                "app.services.report_confirmations.can_mutate_project",
                new_callable=AsyncMock,
                return_value=False,
            ) as can_mutate,
            patch(
                "app.services.report_confirmations.confirm_report_stage_workflow",
                new_callable=AsyncMock,
            ) as confirm_core,
        ):
            with self.assertRaisesRegex(
                ReportConfirmationPermissionError,
                "Insufficient project permissions.",
            ):
                await confirm_project_report_stage_workflow(
                    session,
                    project_id="project-1",
                    org_id="org-1",
                    user_id="user-1",
                    client_context_version=None,
                    output_locale="en",
                    default_output_locale="en",
                )

        can_mutate.assert_awaited_once()
        confirm_core.assert_not_awaited()

    async def test_confirm_project_report_stage_passes_loaded_status_to_core(
        self,
    ) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    row={
                        "id": "project-1",
                        "current_stage": "report",
                        "stage_status": "awaiting_confirm",
                    }
                )
            ]
        )
        expected = ReportConfirmationWorkflowResult(
            stage_status="awaiting_confirm",
            validation_plan=[],
            report_job_status={"status": "queued"},
        )

        with (
            patch(
                "app.services.report_confirmations.can_mutate_project",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.report_confirmations.confirm_report_stage_workflow",
                new_callable=AsyncMock,
                return_value=expected,
            ) as confirm_core,
        ):
            result = await confirm_project_report_stage_workflow(
                session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
                client_context_version=4,
                output_locale="zh",
                default_output_locale="en",
            )

        self.assertIs(result, expected)
        confirm_core.assert_awaited_once()
        _, kwargs = confirm_core.await_args
        self.assertEqual(kwargs["current_stage"], "report")
        self.assertEqual(kwargs["stage_status"], "awaiting_confirm")
        self.assertEqual(kwargs["client_context_version"], 4)
        self.assertEqual(kwargs["output_locale"], "zh")

    async def test_confirm_report_stage_workflow_returns_recovery_ready_report(
        self,
    ) -> None:
        session = _FakeSession(
            [
                _FakeResult(row={"state_version": 4}),
                _FakeResult(
                    rows=[
                        {"stage": "problem", "confirmed": True},
                        {"stage": "market", "confirmed": True},
                        {
                            "stage": "tech",
                            "confirmed": True,
                            "validation_plan_json": [{"action": "Build spike"}],
                        },
                    ]
                ),
                _FakeResult(row={"current_stage": "report", "stage_status": "passed"}),
                _FakeResult(
                    row={
                        "id": "report-1",
                        "report_version": 2,
                        "created_at": "2026-06-06T00:00:00Z",
                    }
                ),
            ]
        )

        with (
            patch(
                "app.services.report_confirmations.enforce_report_daily_limit",
                new_callable=AsyncMock,
            ) as daily_limit,
            patch(
                "app.services.report_confirmations.enforce_llm_usage_limits",
                new_callable=AsyncMock,
            ) as llm_limit,
            patch(
                "app.services.report_confirmations.enqueue_report_generation_job",
                new_callable=AsyncMock,
            ) as enqueue_job,
        ):
            result = await confirm_report_stage_workflow(
                session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
                client_context_version=4,
                output_locale="zh",
                default_output_locale="en",
                current_stage="report",
                stage_status="passed",
            )

        self.assertEqual(result.stage_status, "passed")
        self.assertEqual(result.validation_plan, [{"action": "Build spike"}])
        self.assertEqual(result.report_job_status["status"], "ready")
        self.assertEqual(result.report_job_status["report_id"], "report-1")
        self.assertEqual(result.report_job_status["context_version"], 4)
        daily_limit.assert_not_awaited()
        llm_limit.assert_not_awaited()
        enqueue_job.assert_not_awaited()
        self.assertIn("FOR UPDATE", session.calls[2][0])

    async def test_confirm_report_stage_workflow_enqueues_report_job(self) -> None:
        session = _FakeSession(
            [
                _FakeResult(row={"state_version": 4}),
                _FakeResult(
                    rows=[
                        {"stage": "problem", "confirmed": True},
                        {"stage": "market", "confirmed": True},
                        {"stage": "tech", "confirmed": True},
                    ]
                ),
                _FakeResult(
                    row={
                        "current_stage": "report",
                        "stage_status": "awaiting_confirm",
                    }
                ),
            ]
        )

        with (
            patch(
                "app.services.report_confirmations.enforce_report_daily_limit",
                new_callable=AsyncMock,
            ) as daily_limit,
            patch(
                "app.services.report_confirmations.enforce_llm_usage_limits",
                new_callable=AsyncMock,
            ) as llm_limit,
            patch(
                "app.services.report_confirmations.enqueue_report_generation_job",
                new_callable=AsyncMock,
                return_value={"status": "queued"},
            ) as enqueue_job,
        ):
            result = await confirm_report_stage_workflow(
                session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
                client_context_version=4,
                output_locale="zh",
                default_output_locale="en",
                current_stage="report",
                stage_status="awaiting_confirm",
            )

        self.assertEqual(result.stage_status, "awaiting_confirm")
        self.assertEqual(result.report_job_status["status"], "queued")
        self.assertEqual(result.report_job_status["context_version"], 4)
        daily_limit.assert_awaited_once_with(session, user_id="user-1")
        llm_limit.assert_awaited_once_with(
            session,
            user_id="user-1",
            is_verified=True,
        )
        enqueue_job.assert_awaited_once_with(
            session,
            org_id="org-1",
            project_id="project-1",
            context_version=4,
            output_locale="zh",
            requested_by_user_id="user-1",
        )


if __name__ == "__main__":
    unittest.main()
