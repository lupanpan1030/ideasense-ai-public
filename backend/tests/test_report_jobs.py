import unittest

from app.services import report_jobs


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, rows):
        self._rows = list(rows)
        self.calls = []

    async def execute(self, statement, params=None, **_kwargs):
        self.calls.append({"statement": str(statement), "params": params or {}})
        if not self._rows:
            raise AssertionError("Unexpected query")
        return _FakeResult(self._rows.pop(0))


class ReportGenerationStatusTests(unittest.IsolatedAsyncioTestCase):
    def test_build_ready_report_job_status_normalizes_report_id_and_timestamp(self) -> None:
        status = report_jobs.build_ready_report_job_status(
            project_id="project-1",
            current_stage="report",
            stage_status="passed",
            report_id=123,
            report_version=2,
            generated_at="2026-06-02T12:00:00Z",
            context_version=8,
        )

        self.assertEqual(status["status"], "ready")
        self.assertFalse(status["retryable"])
        self.assertEqual(status["report_id"], "123")
        self.assertEqual(status["generated_at"], "2026-06-02T12:00:00Z")
        self.assertEqual(status["next_poll_ms"], 0)

    def test_build_queued_report_job_status_uses_default_polling(self) -> None:
        status = report_jobs.build_queued_report_job_status(
            project_id="project-1",
            current_stage="report",
            stage_status="awaiting_confirm",
            status=None,
            context_version=8,
        )

        self.assertEqual(status["status"], "queued")
        self.assertFalse(status["retryable"])
        self.assertIsNone(status["report_id"])
        self.assertEqual(status["next_poll_ms"], report_jobs.REPORT_DEFAULT_NEXT_POLL_MS)

    async def test_missing_project_reports_not_started_without_retry(self) -> None:
        status = await report_jobs.resolve_report_generation_status(
            _FakeSession([None]),
            project_id="project-1",
        )

        self.assertEqual(status["status"], "not_started")
        self.assertFalse(status["retryable"])
        self.assertIsNone(status["job_type"])

    async def test_current_report_reports_ready(self) -> None:
        session = _FakeSession(
            [
                {
                    "current_stage": "report",
                    "stage_status": "awaiting_confirm",
                    "state_version": 8,
                },
                {
                    "id": "report-1",
                    "report_version": 1,
                    "generated_from_state_version": 8,
                    "created_at": "2026-06-02T12:00:00Z",
                },
            ]
        )
        status = await report_jobs.resolve_report_generation_status(
            session,
            project_id="project-1",
            output_locale="zh",
        )

        self.assertEqual(status["status"], "ready")
        self.assertFalse(status["retryable"])
        self.assertEqual(status["report_id"], "report-1")
        self.assertEqual(status["next_poll_ms"], 0)
        self.assertIn("content_json->>'artifact_locale'", session.calls[1]["statement"])
        self.assertEqual(session.calls[1]["params"]["output_locale"], "zh")

    async def test_failed_job_is_retryable(self) -> None:
        session = _FakeSession(
            [
                {
                    "current_stage": "report",
                    "stage_status": "awaiting_confirm",
                    "state_version": 8,
                },
                None,
                {
                    "id": "job-1",
                    "status": "failed",
                    "payload": {"context_version": 8},
                    "last_error": "timeout",
                },
            ]
        )
        status = await report_jobs.resolve_report_generation_status(
            session,
            project_id="project-1",
            output_locale="zh",
        )

        self.assertEqual(status["status"], "failed")
        self.assertTrue(status["retryable"])
        self.assertIn("payload->>'output_locale'", session.calls[2]["statement"])
        self.assertEqual(session.calls[2]["params"]["output_locale"], "zh")

    async def test_running_finalizing_job_normalizes_status(self) -> None:
        session = _FakeSession(
            [
                {
                    "current_stage": "report",
                    "stage_status": "awaiting_confirm",
                    "state_version": 8,
                },
                None,
                {
                    "id": "job-1",
                    "status": " Running ",
                    "payload": {"context_version": 8, "phase": "finalizing"},
                    "last_error": None,
                },
            ]
        )

        status = await report_jobs.resolve_report_generation_status(
            session,
            project_id="project-1",
            output_locale="zh",
        )

        self.assertEqual(status["status"], "finalizing")
        self.assertFalse(status["retryable"])
        self.assertEqual(status["next_poll_ms"], 1500)

    async def test_passed_report_stage_without_report_is_retryable(self) -> None:
        session = _FakeSession(
            [
                {
                    "current_stage": "report",
                    "stage_status": "passed",
                    "state_version": 8,
                },
                None,
                None,
            ]
        )

        status = await report_jobs.resolve_report_generation_status(
            session,
            project_id="project-1",
            output_locale="en",
        )

        self.assertEqual(status["status"], "not_started")
        self.assertTrue(status["retryable"])
        self.assertEqual(status["current_stage"], "report")
        self.assertEqual(status["stage_status"], "passed")

    async def test_context_mismatch_reports_stale(self) -> None:
        status = await report_jobs.resolve_report_generation_status(
            _FakeSession(
                [
                    {
                        "current_stage": "report",
                        "stage_status": "awaiting_confirm",
                        "state_version": 9,
                    },
                    None,
                    {
                        "id": "job-1",
                        "status": "running",
                        "payload": {"context_version": 8},
                    },
                ]
            ),
            project_id="project-1",
        )

        self.assertEqual(status["status"], "stale")
        self.assertTrue(status["retryable"])

    def test_report_generation_idempotency_key_includes_locale(self) -> None:
        self.assertEqual(
            report_jobs.report_generation_idempotency_key(
                "project-1",
                8,
                "zh",
            ),
            "report-generation:project-1:8:zh",
        )


if __name__ == "__main__":
    unittest.main()
