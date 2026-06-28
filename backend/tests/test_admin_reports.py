import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Stub database_async to avoid requiring DATABASE_URL / asyncpg for unit tests.
stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)

admin_reports_path = BACKEND_ROOT / "app" / "api" / "routes" / "admin_reports.py"
spec = importlib.util.spec_from_file_location("admin_reports", admin_reports_path)
admin_reports = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(admin_reports)


class ResolveConfirmedFilterTests(unittest.TestCase):
    def test_resolve_confirmed_filter(self) -> None:
        self.assertIsNone(admin_reports._resolve_confirmed_filter(None))
        self.assertIsNone(admin_reports._resolve_confirmed_filter("all"))
        self.assertTrue(admin_reports._resolve_confirmed_filter("confirmed"))
        self.assertFalse(admin_reports._resolve_confirmed_filter("unconfirmed"))


class BuildReportSummaryTests(unittest.TestCase):
    def test_build_report_summary_without_cohort(self) -> None:
        now = datetime.now(timezone.utc)
        row = {
            "id": uuid4(),
            "report_version": 3,
            "status": "final",
            "confirmed": True,
            "created_at": now,
            "updated_at": now,
            "project_id": uuid4(),
            "project_title": "Market Insights",
            "current_stage": "report",
            "stage_status": "passed",
            "project_archived": False,
            "owner_id": uuid4(),
            "owner_name": "Ada Lovelace",
            "owner_email": "ada@example.com",
            "cohort_id": None,
            "cohort_name": None,
            "cohort_archived": None,
        }

        summary = admin_reports._build_report_summary(row)
        self.assertEqual(summary.id, row["id"])
        self.assertEqual(summary.report_version, 3)
        self.assertEqual(summary.status, "final")
        self.assertTrue(summary.confirmed)
        self.assertEqual(summary.project.title, "Market Insights")
        self.assertIsNone(summary.project.cohort)
        self.assertEqual(summary.project.owner.email, "ada@example.com")

    def test_build_report_summary_defaults(self) -> None:
        now = datetime.now(timezone.utc)
        row = {
            "id": uuid4(),
            "report_version": None,
            "status": None,
            "confirmed": False,
            "created_at": now,
            "updated_at": now,
            "project_id": uuid4(),
            "project_title": None,
            "current_stage": None,
            "stage_status": None,
            "project_archived": None,
            "owner_id": None,
            "owner_name": None,
            "owner_email": None,
            "cohort_id": uuid4(),
            "cohort_name": "Spring 2026",
            "cohort_archived": True,
        }

        summary = admin_reports._build_report_summary(row)
        self.assertEqual(summary.report_version, 1)
        self.assertEqual(summary.status, "draft")
        self.assertEqual(summary.project.title, "Untitled project")
        self.assertIsNotNone(summary.project.cohort)
        self.assertTrue(summary.project.cohort.is_archived)


if __name__ == "__main__":
    unittest.main()
