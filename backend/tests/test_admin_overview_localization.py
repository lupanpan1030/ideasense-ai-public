from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
overview_path = BACKEND_ROOT / "app" / "services" / "admin_overview.py"
stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
spec = importlib.util.spec_from_file_location("admin_overview", overview_path)
admin_overview = importlib.util.module_from_spec(spec)
sys.modules["admin_overview"] = admin_overview
assert spec.loader is not None
spec.loader.exec_module(admin_overview)
from app.services import admin_overview_formatters  # noqa: E402


class AdminOverviewLocalizationTests(unittest.TestCase):
    def test_role_label_localizes(self) -> None:
        self.assertEqual(
            admin_overview_formatters._role_label("mentor", "en"), "Mentor"
        )
        self.assertEqual(
            admin_overview_formatters._role_label("mentor", "zh"), "导师"
        )

    def test_stage_label_localizes(self) -> None:
        self.assertEqual(
            admin_overview._stage_label("problem", "en"), "Problem Statement"
        )
        self.assertEqual(admin_overview._stage_label("problem", "zh"), "问题定义")

    def test_period_label_localizes(self) -> None:
        self.assertEqual(admin_overview._period_label(7, "en"), "previous 7 days")
        self.assertEqual(admin_overview._period_label(7, "zh"), "前 7 天")

    def test_delta_counts_localizes(self) -> None:
        label_en = admin_overview._period_label(7, "en")
        label_zh = admin_overview._period_label(7, "zh")

        self.assertEqual(
            admin_overview._format_delta_counts(0, 0, label_en, "en"),
            ("No change vs previous 7 days", "primary"),
        )
        self.assertEqual(
            admin_overview._format_delta_counts(0, 0, label_zh, "zh"),
            ("较前 7 天无变化", "primary"),
        )

    def test_delta_rate_localizes(self) -> None:
        label_en = admin_overview._period_label(30, "en")
        label_zh = admin_overview._period_label(30, "zh")

        self.assertEqual(
            admin_overview._format_delta_rate(2.5, 0.0, label_en, "en"),
            ("+2.5 pts vs previous 30 days", "success"),
        )
        self.assertEqual(
            admin_overview._format_delta_rate(2.5, 0.0, label_zh, "zh"),
            ("较前 30 天 +2.5 分", "success"),
        )

    def test_period_change_localizes(self) -> None:
        label_en = admin_overview._period_label(30, "en")
        label_zh = admin_overview._period_label(30, "zh")

        self.assertEqual(
            admin_overview._format_period_change(10, 0, label_en, "en"),
            ("+10 vs previous 30 days", "success"),
        )
        self.assertEqual(
            admin_overview._format_period_change(10, 0, label_zh, "zh"),
            ("较前 30 天 +10", "success"),
        )


if __name__ == "__main__":
    unittest.main()
