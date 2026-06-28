import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)

admin_projects_path = BACKEND_ROOT / "app" / "api" / "routes" / "admin_projects.py"
spec = importlib.util.spec_from_file_location("admin_projects", admin_projects_path)
admin_projects = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(admin_projects)

from app.services.prompt_trace_debug import normalize_prompt_task_trace_rows


class PromptTraceNormalizationTests(unittest.TestCase):
    def test_ignores_empty_and_invalid_trace_rows(self) -> None:
        records = normalize_prompt_task_trace_rows(
            [
                {"source_type": "answer_evaluation", "prompt_task_traces": None},
                {"source_type": "project_report", "prompt_task_traces": []},
                {
                    "source_type": "unknown",
                    "prompt_task_traces": {"answer_gate": {"task_key": "answer_gate"}},
                },
            ]
        )

        self.assertEqual(records, [])

    def test_merges_sources_into_chronological_schema(self) -> None:
        base_time = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
        answer_id = uuid4()
        stage_id = uuid4()
        report_id = uuid4()

        records = normalize_prompt_task_trace_rows(
            [
                {
                    "source_type": "project_report",
                    "source_id": report_id,
                    "stage": "report",
                    "created_at": base_time + timedelta(minutes=5),
                    "prompt_task_traces": {
                        "final_report": {
                            "task_key": "final_report",
                            "model": "gpt-report",
                            "redacted": True,
                        }
                    },
                },
                {
                    "source_type": "answer_evaluation",
                    "source_id": answer_id,
                    "stage": "problem",
                    "created_at": base_time,
                    "prompt_task_traces": {
                        "extract": {
                            "task_key": "extract",
                            "provider": "openai",
                            "timeout_ms": "500",
                            "latency_ms": 42,
                            "parse_status": "ok",
                            "allowed_mutation": "validated_context_update",
                            "redacted": True,
                        },
                        "answer_gate": {
                            "task_key": "answer_gate",
                            "failure_reason": "timeout",
                            "timeout_ms": 1000,
                            "allowed_mutation": "decision_only",
                            "redacted": True,
                        },
                    },
                },
                {
                    "source_type": "stage_assessment",
                    "source_id": stage_id,
                    "stage": "problem",
                    "created_at": base_time + timedelta(minutes=3),
                    "prompt_task_traces": {
                        "stage_summary_problem": {
                            "model": "gpt-summary",
                            "redacted": True,
                        }
                    },
                },
            ]
        )

        self.assertEqual(
            [record["task_key"] for record in records],
            ["answer_gate", "extract", "stage_summary_problem", "final_report"],
        )
        self.assertEqual(records[0]["source_type"], "answer_evaluation")
        self.assertEqual(records[0]["failure_reason"], "timeout")
        self.assertEqual(records[1]["timeout_ms"], 500)
        self.assertEqual(records[1]["latency_ms"], 42)
        self.assertEqual(records[1]["parse_status"], "ok")
        self.assertEqual(records[1]["allowed_mutation"], "validated_context_update")
        self.assertEqual(records[2]["source_id"], stage_id)
        self.assertEqual(records[3]["stage"], "report")


class ProjectPromptTaskTraceEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_requires_org_admin_before_project_lookup(self) -> None:
        project_id = uuid4()

        async def fake_require(_session, capability):
            self.assertEqual(capability, "is_org_admin")
            raise HTTPException(status_code=403, detail="denied")

        async def fake_ensure_project(_session, _project_id):
            self.fail("_ensure_project should not run when permission fails")

        with (
            patch.object(
                admin_projects,
                "require_org_capability",
                new=fake_require,
            ),
            patch.object(
                admin_projects,
                "_ensure_project",
                new=fake_ensure_project,
            ),
        ):
            with self.assertRaises(HTTPException) as exc:
                await admin_projects.list_project_prompt_task_traces(
                    project_id,
                    object(),
                )

        self.assertEqual(exc.exception.status_code, 403)

    async def test_endpoint_returns_empty_trace_list(self) -> None:
        project_id = uuid4()

        async def fake_require(_session, capability):
            self.assertEqual(capability, "is_org_admin")

        async def fake_ensure_project(_session, checked_project_id):
            self.assertEqual(checked_project_id, project_id)

        async def fake_fetch(_session, checked_project_id):
            self.assertEqual(checked_project_id, project_id)
            return []

        with (
            patch.object(
                admin_projects,
                "require_org_capability",
                new=fake_require,
            ),
            patch.object(
                admin_projects,
                "_ensure_project",
                new=fake_ensure_project,
            ),
            patch.object(
                admin_projects,
                "fetch_project_prompt_task_traces",
                new=fake_fetch,
            ),
        ):
            response = await admin_projects.list_project_prompt_task_traces(
                project_id,
                object(),
            )

        self.assertEqual(response.project_id, project_id)
        self.assertEqual(response.traces, [])


if __name__ == "__main__":
    unittest.main()
