import unittest
from datetime import datetime, timezone

from app.services import (
    answer_extraction_jobs,
    report_jobs,
    stage_finalize_jobs,
    stage_summary_jobs,
    verification_jobs,
)
from app.services.background_jobs import (
    background_job_sort_time,
    enqueue_background_job,
    normalize_background_job_status,
)


class _FakeResult:
    def __init__(self, row, rowcount=None):
        self._row = row
        self.rowcount = 1 if rowcount is None and row is not None else rowcount or 0

    def mappings(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, rows=None, rowcounts=None):
        default_row = {"id": "job-1", "status": "queued", "payload": {}}
        if rows is None:
            self._rows = [default_row]
        elif isinstance(rows, list):
            self._rows = rows
        else:
            self._rows = [rows]
        self._rowcounts = list(rowcounts or [])
        self.calls = []

    async def execute(self, statement, params=None, **_kwargs):
        self.calls.append({"statement": str(statement), "params": params or {}})
        row = self._rows.pop(0) if self._rows else None
        rowcount = self._rowcounts.pop(0) if self._rowcounts else None
        return _FakeResult(row, rowcount=rowcount)


class BackgroundJobEnqueueTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_background_job_status_strips_and_lowercases(self) -> None:
        self.assertEqual(normalize_background_job_status(" Running "), "running")
        self.assertEqual(normalize_background_job_status("FAILED"), "failed")
        self.assertIsNone(normalize_background_job_status(""))
        self.assertIsNone(normalize_background_job_status(None))
        self.assertIsNone(normalize_background_job_status(42))

    async def test_enqueue_background_job_uses_partial_index_conflict_target(self) -> None:
        session = _FakeSession()

        await enqueue_background_job(
            session,
            org_id="org-1",
            project_id="project-1",
            job_type="sample_job",
            payload={"project_id": "project-1"},
            idempotency_key="sample:project-1",
            requeue_statuses=("failed", "cancelled"),
        )

        statement = session.calls[0]["statement"]
        self.assertIn(
            "ON CONFLICT (org_id, job_type, idempotency_key)",
            statement,
        )
        self.assertIn(
            "WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL",
            statement,
        )
        self.assertIn("background_jobs.status IN ('failed', 'cancelled')", statement)
        self.assertEqual(session.calls[0]["params"]["job_type"], "sample_job")

    async def test_report_generation_requeues_terminal_statuses(self) -> None:
        session = _FakeSession()

        await report_jobs.enqueue_report_generation_job(
            session,
            org_id="org-1",
            project_id="project-1",
            context_version=8,
            output_locale="zh",
            requested_by_user_id="user-1",
        )

        statement = session.calls[0]["statement"]
        self.assertIn(
            "background_jobs.status IN ('failed', 'cancelled', 'succeeded')",
            statement,
        )
        self.assertEqual(
            session.calls[0]["params"]["idempotency_key"],
            "report-generation:project-1:8:zh",
        )
        self.assertEqual(session.calls[0]["params"]["job_type"], "report_generation_v0")
        self.assertEqual(session.calls[0]["params"]["payload"]["phase"], "queued")

    async def test_stage_finalize_requeues_failed_cancelled_only(self) -> None:
        session = _FakeSession()

        await stage_finalize_jobs.enqueue_stage_finalize_job(
            session,
            org_id="org-1",
            project_id="project-1",
            stage="Problem",
            context_version=8,
            output_locale="en",
            requested_by_user_id="user-1",
            question_bank_version_id="bank-1",
            variant="lite",
        )

        statement = session.calls[0]["statement"]
        self.assertIn("background_jobs.status IN ('failed', 'cancelled')", statement)
        self.assertNotIn("'succeeded'", statement)
        self.assertEqual(
            session.calls[0]["params"]["idempotency_key"],
            "stage-finalize:project-1:problem:8:en",
        )
        self.assertEqual(session.calls[0]["params"]["job_type"], "stage_finalize_v0")
        self.assertEqual(session.calls[0]["params"]["payload"]["stage"], "problem")

    async def test_stage_summary_inserts_with_do_nothing_conflict(self) -> None:
        session = _FakeSession([None, None, {"id": "job-1", "status": "queued"}])

        await stage_summary_jobs.enqueue_stage_summary_job(
            session,
            project_id="project-1",
            stage="Problem",
            context_version=8,
            output_locale="en",
        )

        self.assertEqual(len(session.calls), 3)
        insert_statement = session.calls[1]["statement"]
        self.assertIn("DO NOTHING", insert_statement)
        self.assertEqual(
            session.calls[1]["params"]["idempotency_key"],
            "stage-summary:project-1:problem:8:en",
        )
        self.assertEqual(session.calls[1]["params"]["job_type"], "stage_summary_v0")
        self.assertEqual(session.calls[1]["params"]["payload"]["stage"], "Problem")

    async def test_stage_summary_retries_terminal_jobs_only_when_requested(self) -> None:
        session = _FakeSession({"id": "job-1", "status": "failed"})

        job = await stage_summary_jobs.enqueue_stage_summary_job(
            session,
            project_id="project-1",
            stage="problem",
            context_version=8,
            output_locale="en",
            retry=False,
        )

        self.assertEqual(job["status"], "failed")
        self.assertEqual(len(session.calls), 1)

        retry_session = _FakeSession(
            [
                {"id": "job-1", "status": "failed"},
                {"id": "job-1", "status": "queued"},
            ]
        )
        await stage_summary_jobs.enqueue_stage_summary_job(
            retry_session,
            project_id="project-1",
            stage="problem",
            context_version=8,
            output_locale="en",
            retry=True,
        )

        self.assertEqual(len(retry_session.calls), 2)
        self.assertIn("UPDATE background_jobs", retry_session.calls[1]["statement"])

    async def test_enqueue_background_job_rejects_unknown_requeue_status(self) -> None:
        with self.assertRaises(ValueError):
            await enqueue_background_job(
                _FakeSession(),
                org_id="org-1",
                project_id="project-1",
                job_type="sample_job",
                payload={},
                idempotency_key="sample:project-1",
                requeue_statuses=("running",),
            )

    def test_background_job_sort_time_prefers_completion_update_create_order(self) -> None:
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        updated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        completed_at = datetime(2026, 1, 3, tzinfo=timezone.utc)

        self.assertEqual(
            background_job_sort_time(
                {
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "completed_at": completed_at,
                }
            ),
            completed_at,
        )
        self.assertEqual(
            background_job_sort_time(
                {"created_at": created_at, "updated_at": updated_at}
            ),
            updated_at,
        )
        self.assertIsNone(background_job_sort_time(None))

    async def test_answer_extraction_enqueue_returns_existing_job_id(self) -> None:
        session = _FakeSession({"id": "job-1"})

        job = await answer_extraction_jobs.enqueue_authoritative_answer_extraction_job(
            session,
            project_id="project-1",
            question_instance_id="qi-1",
            user_message_id="42",
            request_id="request-1",
            client_message_id="client-1",
        )

        statement = session.calls[0]["statement"]
        self.assertIn("WITH inserted AS", statement)
        self.assertIn("DO NOTHING", statement)
        self.assertIn("UNION ALL SELECT id FROM background_jobs", statement)
        self.assertEqual(job["id"], "job-1")
        self.assertEqual(
            session.calls[0]["params"]["idempotency_key"],
            "extract-answer:qi-1:42",
        )
        self.assertEqual(session.calls[0]["params"]["job_type"], "extract_answer_v0")
        self.assertEqual(
            session.calls[0]["params"]["payload"],
            {
                "project_id": "project-1",
                "question_instance_id": "qi-1",
                "message_id": 42,
                "source_message_id": 42,
                "request_id": "request-1",
                "client_message_id": "client-1",
                "trigger": "authoritative_extract",
            },
        )

    async def test_answer_verification_enqueue_preserves_payload_shape(self) -> None:
        session = _FakeSession([], rowcounts=[1])

        inserted = await verification_jobs.enqueue_answer_question_verification_job(
            session,
            project_id="project-1",
            question_instance_id="qi-1",
            question_bank_question_id="qbq-1",
            user_message_id=42,
            priority="high",
        )

        self.assertTrue(inserted)
        statement = session.calls[0]["statement"]
        self.assertIn("DO NOTHING", statement)
        self.assertEqual(
            session.calls[0]["params"]["idempotency_key"],
            "verify-question:qi-1:42",
        )
        self.assertEqual(
            session.calls[0]["params"]["job_type"],
            "verify_question_claims_v0",
        )
        self.assertEqual(
            session.calls[0]["params"]["payload"],
            {
                "project_id": "project-1",
                "question_instance_id": "qi-1",
                "question_bank_question_id": "qbq-1",
                "priority": "high",
                "trigger": "answer",
            },
        )

    async def test_summary_verification_enqueue_uses_answered_at_key(self) -> None:
        session = _FakeSession([], rowcounts=[1])
        answered_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        inserted = await verification_jobs.enqueue_summary_question_verification_job(
            session,
            project_id="project-1",
            question_instance_id="qi-1",
            question_bank_question_id="qbq-1",
            answered_at=answered_at,
            priority="medium",
        )

        self.assertTrue(inserted)
        self.assertEqual(
            session.calls[0]["params"]["idempotency_key"],
            f"verify-question:qi-1:{answered_at}",
        )
        self.assertEqual(session.calls[0]["params"]["payload"]["trigger"], "summary")

    async def test_verification_requeue_resets_failed_cancelled_jobs(self) -> None:
        session = _FakeSession([], rowcounts=[1])

        requeued = await verification_jobs.requeue_question_verification_job(
            session,
            job_id="job-1",
        )

        self.assertTrue(requeued)
        statement = session.calls[0]["statement"]
        self.assertIn("UPDATE background_jobs", statement)
        self.assertIn("status IN ('failed','cancelled')", statement)
        self.assertEqual(session.calls[0]["params"]["job_id"], "job-1")


if __name__ == "__main__":
    unittest.main()
