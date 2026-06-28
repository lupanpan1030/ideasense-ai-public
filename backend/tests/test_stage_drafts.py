import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services import stage_drafts


class _FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    async def execute(self, statement, params=None, **_kwargs):
        self.calls.append({"statement": str(statement), "params": params or {}})
        if not self._results:
            raise AssertionError(f"unexpected SQL call: {statement}")
        return self._results.pop(0)


def _project_row(**overrides):
    row = {
        "current_stage": "problem",
        "stage_status": "awaiting_confirm",
        "question_bank_version_id": "bank-1",
    }
    row.update(overrides)
    return row


class StageDraftWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_project_stage_draft_missing_project_raises_not_found(self) -> None:
        session = _FakeSession([_FakeResult([])])

        with self.assertRaisesRegex(
            stage_drafts.StageDraftNotFoundError,
            "Project not found.",
        ):
            await stage_drafts.prepare_project_stage_draft_workflow(
                session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
                stage="problem",
                client_context_version=None,
                output_locale="en",
            )

        self.assertEqual(len(session.calls), 1)

    async def test_project_stage_draft_permission_denied_before_prepare(self) -> None:
        session = _FakeSession([_FakeResult([_project_row(id="project-1")])])

        with (
            patch.object(
                stage_drafts,
                "can_mutate_project",
                new_callable=AsyncMock,
                return_value=False,
            ) as can_mutate,
            patch.object(
                stage_drafts,
                "prepare_stage_draft_workflow",
                new_callable=AsyncMock,
            ) as prepare,
        ):
            with self.assertRaisesRegex(
                stage_drafts.StageDraftPermissionError,
                "Insufficient project permissions.",
            ):
                await stage_drafts.prepare_project_stage_draft_workflow(
                    session,
                    project_id="project-1",
                    org_id="org-1",
                    user_id="user-1",
                    stage="problem",
                    client_context_version=None,
                    output_locale="en",
                )

        can_mutate.assert_awaited_once()
        prepare.assert_not_awaited()

    async def test_stage_mismatch_returns_conflict_code_without_queries(self) -> None:
        session = _FakeSession([])

        result = await stage_drafts.prepare_stage_draft_workflow(
            session,
            project_id="project-1",
            org_id="org-1",
            user_id="user-1",
            stage="market",
            project_row=_project_row(current_stage="problem"),
            client_context_version=None,
            output_locale="en",
        )

        self.assertEqual(result.error, stage_drafts.STAGE_DRAFT_STAGE_CHANGED)
        self.assertEqual(session.calls, [])

    async def test_reuses_ready_cache_without_enqueueing_job(self) -> None:
        updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session = _FakeSession(
            [
                _FakeResult(
                    [
                        {
                            "state_meta": {"summary_locales": {"problem": {"draft": "en"}}},
                            "state_version": 7,
                            "updated_at": updated_at,
                        }
                    ]
                ),
                _FakeResult(
                    [
                        {
                            "id": "assessment-1",
                            "draft_summary_markdown": "Cached summary",
                            "generated_from_state_version": 7,
                        }
                    ]
                ),
            ]
        )

        result = await stage_drafts.prepare_stage_draft_workflow(
            session,
            project_id="project-1",
            org_id="org-1",
            user_id="user-1",
            stage="problem",
            project_row=_project_row(),
            client_context_version=7,
            output_locale="en",
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.generation_status, "ready")
        self.assertEqual(result.draft_summary_text, "Cached summary")
        self.assertEqual(result.assessment_id, "assessment-1")
        self.assertEqual(result.context_updated_at, updated_at)
        self.assertEqual(len(session.calls), 2)

    async def test_context_version_mismatch_returns_conflict_code(self) -> None:
        session = _FakeSession(
            [
                _FakeResult(
                    [
                        {
                            "state_meta": {},
                            "state_version": 8,
                            "updated_at": None,
                        }
                    ]
                )
            ]
        )

        result = await stage_drafts.prepare_stage_draft_workflow(
            session,
            project_id="project-1",
            org_id="org-1",
            user_id="user-1",
            stage="problem",
            project_row=_project_row(),
            client_context_version=7,
            output_locale="en",
        )

        self.assertEqual(result.error, stage_drafts.STAGE_DRAFT_CONTEXT_CONFLICT)
        self.assertEqual(result.context_version, 8)

    async def test_enqueues_stage_summary_job_when_cache_is_not_reusable(self) -> None:
        session = _FakeSession(
            [
                _FakeResult([{"state_meta": {}, "state_version": 7, "updated_at": None}]),
                _FakeResult([]),
            ]
        )

        async def _fake_enforce(*_args, **_kwargs):
            return None

        async def _fake_enqueue(*_args, **_kwargs):
            return {"status": "queued", "last_error": None}

        with (
            patch.object(stage_drafts, "enforce_llm_usage_limits", new=_fake_enforce),
            patch.object(stage_drafts, "enqueue_stage_summary_job", new=_fake_enqueue),
        ):
            result = await stage_drafts.prepare_stage_draft_workflow(
                session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
                stage="problem",
                project_row=_project_row(),
                client_context_version=None,
                output_locale="zh",
                retry=True,
            )

        self.assertIsNone(result.error)
        self.assertEqual(result.generation_status, "queued")
        self.assertEqual(result.draft_output_locale, "zh")
        self.assertFalse(result.retryable)


if __name__ == "__main__":
    unittest.main()
