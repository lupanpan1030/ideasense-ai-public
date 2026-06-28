import sys
import types
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.api.routes import projects  # noqa: E402
from app.services.project_report_access import (  # noqa: E402
    ProjectReportAccessDeniedError,
    ProjectReportAccessConfigurationError,
    ProjectReportEmailVerificationError,
    ProjectReportAccessNotFoundError,
    ensure_project_report_access,
    ensure_project_report_access_gate,
)


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _ReportSession:
    def __init__(self, rows: list[dict | None]) -> None:
        self.rows = rows
        self.calls: list[str] = []
        self.params: list[dict | None] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append(str(statement))
        self.params.append(params)
        row = self.rows.pop(0) if self.rows else None
        return _FakeResult(row)


class _AsyncContext:
    def __init__(self, value=None) -> None:
        self.value = value

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self.value

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False


class _AdminSession:
    def begin(self) -> _AsyncContext:
        return _AsyncContext()


class ProjectReportAccessServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_access_gate_requires_admin_session_factory(self) -> None:
        with self.assertRaises(ProjectReportAccessConfigurationError) as exc:
            await ensure_project_report_access_gate(
                _ReportSession([]),
                admin_session_factory=None,
                set_system_actor_fn=AsyncMock(),
                is_email_verified_fn=AsyncMock(),
                actor_user_id=uuid4(),
                project_id=uuid4(),
            )

        self.assertEqual(
            exc.exception.detail,
            "DATABASE_URL_ADMIN is required for reports.",
        )

    async def test_access_gate_requires_verified_email(self) -> None:
        set_system_actor = AsyncMock()
        is_email_verified = AsyncMock(return_value=False)

        with self.assertRaises(ProjectReportEmailVerificationError) as exc:
            await ensure_project_report_access_gate(
                _ReportSession([]),
                admin_session_factory=lambda: _AsyncContext(_AdminSession()),
                set_system_actor_fn=set_system_actor,
                is_email_verified_fn=is_email_verified,
                actor_user_id=uuid4(),
                project_id=uuid4(),
            )

        self.assertEqual(
            exc.exception.detail,
            "Verify your email to access reports.",
        )
        set_system_actor.assert_awaited_once()
        is_email_verified.assert_awaited_once()

    async def test_access_gate_verifies_email_then_project_access(self) -> None:
        project_id = uuid4()
        session = _ReportSession([{"id": project_id, "can_view_facts": True}])
        set_system_actor = AsyncMock()
        is_email_verified = AsyncMock(return_value=True)

        await ensure_project_report_access_gate(
            session,
            admin_session_factory=lambda: _AsyncContext(_AdminSession()),
            set_system_actor_fn=set_system_actor,
            is_email_verified_fn=is_email_verified,
            actor_user_id=uuid4(),
            project_id=project_id,
        )

        set_system_actor.assert_awaited_once()
        is_email_verified.assert_awaited_once()
        self.assertEqual(session.params, [{"project_id": str(project_id)}])

    async def test_missing_project_raises_domain_error(self) -> None:
        project_id = uuid4()
        session = _ReportSession([None])

        with self.assertRaises(ProjectReportAccessNotFoundError) as exc:
            await ensure_project_report_access(session, project_id)

        self.assertEqual(str(exc.exception), "Project not found.")
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.params, [{"project_id": str(project_id)}])

    async def test_project_without_fact_access_raises_domain_error(self) -> None:
        session = _ReportSession([{"id": uuid4(), "can_view_facts": False}])

        with self.assertRaises(ProjectReportAccessDeniedError) as exc:
            await ensure_project_report_access(session, uuid4())

        self.assertEqual(str(exc.exception), "Report access denied.")
        self.assertEqual(len(session.calls), 1)

    async def test_project_with_fact_access_returns_none(self) -> None:
        session = _ReportSession([{"id": uuid4(), "can_view_facts": True}])

        result = await ensure_project_report_access(session, uuid4())

        self.assertIsNone(result)
        self.assertEqual(len(session.calls), 1)


class ProjectReportAccessTests(unittest.IsolatedAsyncioTestCase):
    async def _call_report(self, session: _ReportSession):
        with patch.object(
            projects,
            "AdminAsyncSessionLocal",
            lambda: _AsyncContext(_AdminSession()),
        ):
            with patch.object(projects, "set_system_actor", AsyncMock()):
                with patch.object(
                    projects,
                    "is_email_verified",
                    AsyncMock(return_value=True),
                ):
                    return await projects.get_project_report(
                        uuid4(),
                        actor=projects.ActorContext(
                            user_id=str(uuid4()),
                            org_id=None,
                            actor_type="user",
                        ),
                        session=session,
                    )

    async def test_report_returns_project_not_found_before_empty_report_state(self) -> None:
        session = _ReportSession([None])

        with self.assertRaises(HTTPException) as exc:
            await self._call_report(session)

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.detail, "Project not found.")
        self.assertEqual(len(session.calls), 1)

    async def test_report_denies_project_without_fact_access(self) -> None:
        session = _ReportSession([{"id": uuid4(), "can_view_facts": False}])

        with self.assertRaises(HTTPException) as exc:
            await self._call_report(session)

        self.assertEqual(exc.exception.status_code, 403)
        self.assertEqual(exc.exception.detail, "Report access denied.")
        self.assertEqual(len(session.calls), 1)

    async def test_accessible_project_without_report_stays_empty_report_404(self) -> None:
        session = _ReportSession(
            [{"id": uuid4(), "can_view_facts": True}, None]
        )

        with self.assertRaises(HTTPException) as exc:
            await self._call_report(session)

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.detail, "Report not found.")
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
