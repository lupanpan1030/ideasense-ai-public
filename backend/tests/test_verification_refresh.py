import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services import verification_refresh


class _FakeResult:
    def __init__(self, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []
        self.prepare_write_actor_calls = 0

    async def execute(self, statement, params=None, **_kwargs):
        self.calls.append({"statement": str(statement), "params": params or {}})
        if not self._results:
            raise AssertionError(f"unexpected SQL call: {statement}")
        return self._results.pop(0)


def _answered_question_row(
    *,
    answered_at: datetime,
    question_instance_id: str = "qi-1",
    question_bank_question_id: str = "qbq-1",
    stage: str = "problem",
    priority: str = "high",
):
    return {
        "question_instance_id": question_instance_id,
        "answered_at": answered_at,
        "status": "answered",
        "final_answer_text": "Customer interviews show weekly pain.",
        "question_bank_question_id": question_bank_question_id,
        "question_id": "S1Q1",
        "title": "Customer pain",
        "stage": stage,
        "order_index": 1,
        "prompt_meta": {"verification": {"priority": priority}},
    }


async def _prepare_write_actor(session):
    session.prepare_write_actor_calls += 1


class VerificationRefreshServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_project_returns_not_found_without_extra_queries(self) -> None:
        session = _FakeSession([_FakeResult([])])

        result = await verification_refresh.schedule_project_stage_verification_refresh(
            session,
            project_id="project-1",
            stages=["problem"],
            prepare_write_actor=_prepare_write_actor,
        )

        self.assertFalse(result.project_exists)
        self.assertEqual(result.enqueued, 0)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.prepare_write_actor_calls, 0)

    async def test_enqueues_unclaimed_answered_question(self) -> None:
        answered_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult([{"id": "project-1"}]),
                _FakeResult([_answered_question_row(answered_at=answered_at)]),
                _FakeResult([]),
                _FakeResult([]),
                _FakeResult([], rowcount=1),
            ]
        )

        result = await verification_refresh.schedule_project_stage_verification_refresh(
            session,
            project_id="project-1",
            stages=["problem"],
            prepare_write_actor=_prepare_write_actor,
        )

        self.assertTrue(result.project_exists)
        self.assertEqual(result.enqueued, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(session.prepare_write_actor_calls, 1)
        insert_call = session.calls[-1]
        self.assertIn("INSERT INTO background_jobs", insert_call["statement"])
        self.assertEqual(
            insert_call["params"]["idempotency_key"],
            f"verify-question:qi-1:{answered_at}",
        )
        self.assertEqual(
            insert_call["params"]["payload"],
            {
                "project_id": "project-1",
                "question_instance_id": "qi-1",
                "question_bank_question_id": "qbq-1",
                "priority": "high",
                "trigger": "summary",
            },
        )

    async def test_requeues_latest_failed_job_for_question(self) -> None:
        answered_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        failed_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult([{"id": "project-1"}]),
                _FakeResult([_answered_question_row(answered_at=answered_at)]),
                _FakeResult([]),
                _FakeResult(
                    [
                        {
                            "id": "job-1",
                            "payload": {"question_bank_question_id": "qbq-1"},
                            "status": "failed",
                            "created_at": failed_at,
                            "updated_at": failed_at,
                            "completed_at": None,
                        }
                    ]
                ),
                _FakeResult([], rowcount=1),
            ]
        )

        result = await verification_refresh.schedule_project_stage_verification_refresh(
            session,
            project_id="project-1",
            stages=["problem"],
            prepare_write_actor=_prepare_write_actor,
        )

        self.assertTrue(result.project_exists)
        self.assertEqual(result.enqueued, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(session.prepare_write_actor_calls, 1)
        update_call = session.calls[-1]
        self.assertIn("UPDATE background_jobs", update_call["statement"])
        self.assertEqual(update_call["params"]["job_id"], "job-1")

    async def test_refresh_workflow_disabled_preserves_requested_stage(self) -> None:
        session = _FakeSession([])

        with patch.object(
            verification_refresh,
            "verification_enabled",
            return_value=False,
        ):
            result = await verification_refresh.refresh_project_stage_verification_workflow(
                session,
                project_id="project-1",
                stage=" Problem ",
                prepare_write_actor=_prepare_write_actor,
            )

        self.assertEqual(result.normalized_stage, " Problem ")
        self.assertEqual(result.enqueued, 0)
        self.assertEqual(session.calls, [])

    async def test_refresh_workflow_rejects_unsupported_stage(self) -> None:
        session = _FakeSession([])

        with (
            patch.object(verification_refresh, "verification_enabled", return_value=True),
            patch.object(
                verification_refresh,
                "resolve_verification_provider_unavailable_reason",
                return_value=None,
            ),
        ):
            with self.assertRaisesRegex(
                verification_refresh.VerificationRefreshStageUnsupportedError,
                "Stage not supported.",
            ):
                await verification_refresh.refresh_project_stage_verification_workflow(
                    session,
                    project_id="project-1",
                    stage="sales",
                    prepare_write_actor=_prepare_write_actor,
                )

        self.assertEqual(session.calls, [])

    async def test_refresh_workflow_schedules_normalized_stage(self) -> None:
        session = _FakeSession([])

        with (
            patch.object(verification_refresh, "verification_enabled", return_value=True),
            patch.object(
                verification_refresh,
                "resolve_verification_provider_unavailable_reason",
                return_value=None,
            ),
            patch.object(
                verification_refresh,
                "schedule_project_stage_verification_refresh",
                new_callable=AsyncMock,
                return_value=verification_refresh.VerificationRefreshJobResult(
                    project_exists=True,
                    enqueued=2,
                    skipped=1,
                ),
            ) as schedule,
        ):
            result = await verification_refresh.refresh_project_stage_verification_workflow(
                session,
                project_id="project-1",
                stage=" Problem ",
                prepare_write_actor=_prepare_write_actor,
            )

        self.assertEqual(result.normalized_stage, "problem")
        self.assertEqual(result.enqueued, 2)
        self.assertEqual(result.skipped, 1)
        schedule.assert_awaited_once_with(
            session,
            project_id="project-1",
            stages=["problem"],
            prepare_write_actor=_prepare_write_actor,
        )


if __name__ == "__main__":
    unittest.main()
