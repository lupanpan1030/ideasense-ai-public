from __future__ import annotations

import unittest
from pathlib import Path
import sys
import types
from unittest.mock import patch

stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.services import answer_extraction_worker_handler
from app.services import report_generation_worker_handler
from app.services import stage_finalize_worker_handler
from app.services import stage_summary_worker_handler
from app.services import verification_job_handler


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    REPO_ROOT
    / "database"
    / "migrations"
    / "060_force_rls_on_projects_20260627120000.sql"
)
RUNTIME_TRIGGER_MIGRATION_PATH = (
    REPO_ROOT
    / "database"
    / "migrations"
    / "061_fix_runtime_trigger_under_projects_force_rls_20260627123000.sql"
)
SCHEMA_PATH = REPO_ROOT / "database" / "schema" / "schema.sql"


class _StopAfterProjectRead(RuntimeError):
    pass


class _FakeResult:
    def __init__(self, row: dict | None = None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row

    def all(self) -> list[dict]:
        return []


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ForceRlsSession:
    def __init__(self, *, project_org_id: str = "org-1") -> None:
        self.project_org_id = project_org_id
        self.context_org_id: str | None = None
        self.calls: list[tuple[str, object]] = []
        self.project_was_read = False

    def begin(self) -> _Tx:
        return _Tx()

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append(("sql", sql))
        if "FROM projects" in sql:
            self.project_was_read = True
            if self.context_org_id != self.project_org_id:
                return _FakeResult(None)
            return _FakeResult(
                {
                    "id": "project-1",
                    "org_id": self.project_org_id,
                    "owner_user_id": "user-1",
                    "current_stage": "problem",
                    "current_variant": "default",
                    "stage_status": "awaiting_confirm",
                    "question_bank_version_id": "bank-1",
                    "settings": {},
                    "title": "IdeaSense",
                    "description": "Startup assessment",
                    "updated_at": None,
                }
            )
        if self.project_was_read and "set_config(" not in sql:
            raise _StopAfterProjectRead()
        return _FakeResult(None)


async def _set_fake_worker_context(
    session: _ForceRlsSession,
    org_id: str | None,
) -> None:
    session.calls.append(("context", org_id))
    session.context_org_id = org_id


class ProjectsForceRlsTests(unittest.IsolatedAsyncioTestCase):
    def test_migration_adds_org_scoped_system_select_and_force_rls(self) -> None:
        migration_sql = MIGRATION_PATH.read_text()
        schema_sql = SCHEMA_PATH.read_text()

        self.assertIn("CREATE POLICY projects_system_select ON projects", migration_sql)
        self.assertIn("app_actor_type() = 'system'", migration_sql)
        self.assertIn("AND org_id = app_org_id()", migration_sql)
        self.assertIn("DROP POLICY IF EXISTS projects_select ON projects", migration_sql)
        self.assertIn("CREATE POLICY projects_select ON projects", migration_sql)
        self.assertIn("owner_user_id = app_user_id()", migration_sql)
        self.assertIn("mentor_student_assignments msa", migration_sql)
        self.assertNotIn("can_view_project(id, org_id)", migration_sql)
        self.assertIn("ALTER TABLE projects FORCE ROW LEVEL SECURITY;", migration_sql)
        self.assertNotIn("question_bank_", migration_sql)
        self.assertNotIn("email_verification_tokens", migration_sql)
        self.assertNotIn("password_reset_tokens", migration_sql)

        self.assertIn(
            "-- Source: 060_force_rls_on_projects_20260627120000.sql",
            schema_sql,
        )
        latest_source = schema_sql.split(
            "-- Source: 060_force_rls_on_projects_20260627120000.sql",
            maxsplit=1,
        )[1]
        self.assertIn("DROP POLICY IF EXISTS projects_select ON projects", latest_source)
        self.assertIn("CREATE POLICY projects_select ON projects", latest_source)
        self.assertIn("CREATE POLICY projects_system_select ON projects", latest_source)
        self.assertIn("ALTER TABLE projects FORCE ROW LEVEL SECURITY;", latest_source)

    def test_runtime_trigger_runs_with_rls_enabled_after_projects_force_rls(self) -> None:
        migration_sql = RUNTIME_TRIGGER_MIGRATION_PATH.read_text()
        schema_sql = SCHEMA_PATH.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()", migration_sql)
        self.assertIn("SECURITY DEFINER", migration_sql)
        self.assertIn("SET row_security = on", migration_sql)
        self.assertIn("SET search_path = public, pg_temp", migration_sql)
        self.assertIn("FROM projects p", migration_sql)
        self.assertNotIn("SET row_security = off", migration_sql)
        self.assertNotIn("set_config('row_security'", migration_sql)

        self.assertIn(
            "-- Source: 061_fix_runtime_trigger_under_projects_force_rls_20260627123000.sql",
            schema_sql,
        )
        latest_source = schema_sql.split(
            "-- Source: 061_fix_runtime_trigger_under_projects_force_rls_20260627123000.sql",
            maxsplit=1,
        )[1]
        self.assertIn("CREATE OR REPLACE FUNCTION enforce_project_runtime_questions()", latest_source)
        self.assertIn("SET row_security = on", latest_source)
        self.assertNotIn("SET row_security = off", latest_source)
        self.assertNotIn("set_config('row_security'", latest_source)

    async def test_worker_handlers_read_projects_after_job_org_context(self) -> None:
        cases = [
            (
                answer_extraction_worker_handler.run_extract_answer_v0,
                {
                    "project_id": "project-1",
                    "question_instance_id": "question-instance-1",
                    "message_id": "message-1",
                },
                None,
            ),
            (
                stage_summary_worker_handler.run_stage_summary_v0,
                {
                    "project_id": "project-1",
                    "stage": "problem",
                    "context_version": 1,
                },
                None,
            ),
            (
                stage_finalize_worker_handler.run_stage_finalize_v0,
                {
                    "project_id": "project-1",
                    "stage": "problem",
                    "context_version": 1,
                },
                None,
            ),
            (
                report_generation_worker_handler.run_report_generation_v0,
                {
                    "project_id": "project-1",
                    "context_version": 1,
                    "requested_by_user_id": "user-1",
                },
                {"job_id": 42},
            ),
            (
                verification_job_handler.run_verify_question_claims_v0,
                {
                    "project_id": "project-1",
                    "question_instance_id": "question-instance-1",
                },
                None,
            ),
        ]

        for handler, payload, extra_kwargs in cases:
            session = _ForceRlsSession()
            kwargs = dict(extra_kwargs or {})
            kwargs.update(
                {
                    "job_org_id": "org-1",
                    "set_worker_context_fn": _set_fake_worker_context,
                }
            )
            with patch.object(
                verification_job_handler,
                "verification_enabled",
                lambda: True,
            ):
                try:
                    await handler(session, payload, **kwargs)
                except _StopAfterProjectRead:
                    pass

            context_index = next(
                index for index, (kind, _value) in enumerate(session.calls) if kind == "context"
            )
            project_index = next(
                index
                for index, (kind, value) in enumerate(session.calls)
                if kind == "sql" and "FROM projects" in str(value)
            )
            self.assertLess(context_index, project_index)

    async def test_worker_handlers_fail_closed_when_job_org_mismatches_project(self) -> None:
        cases = [
            (
                answer_extraction_worker_handler.run_extract_answer_v0,
                {
                    "project_id": "project-1",
                    "question_instance_id": "question-instance-1",
                    "message_id": "message-1",
                },
                None,
            ),
            (
                stage_summary_worker_handler.run_stage_summary_v0,
                {
                    "project_id": "project-1",
                    "stage": "problem",
                    "context_version": 1,
                },
                None,
            ),
            (
                stage_finalize_worker_handler.run_stage_finalize_v0,
                {
                    "project_id": "project-1",
                    "stage": "problem",
                    "context_version": 1,
                },
                None,
            ),
            (
                report_generation_worker_handler.run_report_generation_v0,
                {
                    "project_id": "project-1",
                    "context_version": 1,
                    "requested_by_user_id": "user-1",
                },
                {"job_id": 42},
            ),
            (
                verification_job_handler.run_verify_question_claims_v0,
                {
                    "project_id": "project-1",
                    "question_instance_id": "question-instance-1",
                },
                None,
            ),
        ]

        for handler, payload, extra_kwargs in cases:
            session = _ForceRlsSession(project_org_id="org-1")
            kwargs = dict(extra_kwargs or {})
            kwargs.update(
                {
                    "job_org_id": "wrong-org",
                    "set_worker_context_fn": _set_fake_worker_context,
                }
            )
            with (
                patch.object(verification_job_handler, "verification_enabled", lambda: True),
                self.assertRaisesRegex(ValueError, "Project not found"),
            ):
                await handler(session, payload, **kwargs)


if __name__ == "__main__":
    unittest.main()
