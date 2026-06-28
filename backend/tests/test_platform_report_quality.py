import sys
import types
import unittest
from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)

from app.api.routes import platform_admin  # noqa: E402
from app.services import platform_report_quality  # noqa: E402


ORG_ID = UUID("2c59666d-e746-4c1a-863f-2f3d80a4ef3b")
PROJECT_ID = UUID("bb60d1dc-375f-4c63-b1f8-204a54de4a00")
REPORT_ID = UUID("fb0e0c53-92ab-482e-bc78-11a3d88f688e")
OBSERVATION_ID = UUID("9b7e9725-2326-49ec-8b39-a099079a725d")


def _row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": OBSERVATION_ID,
        "org_id": ORG_ID,
        "org_name": "IdeaSense Lab",
        "org_slug": "ideasense-lab",
        "project_id": PROJECT_ID,
        "project_title": "Validation Tool",
        "report_id": REPORT_ID,
        "report_version": 2,
        "generated_from_state_version": 6,
        "observation_schema_version": "assessment_quality_observation_v1",
        "status": "fail",
        "failed_invariants_json": ["score_rationales_complete"],
        "warning_invariants_json": ["canonical_score_boundary"],
        "score_snapshot_json": {"desirability": 80, "total_score": 75},
        "evidence_counts_json": {"unknowns": 2, "evidence_gaps": 3},
        "canonical_boundaries_json": {
            "within_any_score_boundary": False,
            "nearest_case": {"id": "weak_market_case"},
        },
        "observation_json": {"summary": {"status": "fail"}},
        "observed_at": now,
        "created_at": now,
        "updated_at": now,
    }


class PlatformReportQualityFilterTests(unittest.TestCase):
    def test_invalid_status_is_rejected(self) -> None:
        with self.assertRaises(
            platform_report_quality.PlatformReportQualityValidationError
        ) as exc:
            platform_report_quality.build_quality_observation_filters(
                quality_status="broken",
                org_id=None,
                project_id=None,
                report_id=None,
                observed_from=None,
                observed_to=None,
                q=None,
            )

        self.assertEqual(exc.exception.detail, "Invalid report quality status")

    def test_filter_sql_includes_status_and_search(self) -> None:
        where_clause, params = platform_report_quality.build_quality_observation_filters(
            quality_status="fail",
            org_id=ORG_ID,
            project_id=None,
            report_id=None,
            observed_from=None,
            observed_to=None,
            q="Validation",
        )

        self.assertIn("rqo.status = :quality_status", where_clause)
        self.assertIn("rqo.org_id = :org_id", where_clause)
        self.assertIn("rqo.project_title ILIKE :search", where_clause)
        self.assertEqual(params["quality_status"], "fail")
        self.assertEqual(params["org_id"], str(ORG_ID))
        self.assertEqual(params["search"], "%Validation%")


class PlatformReportQualityApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_requires_platform_admin(self) -> None:
        session = _Session([])
        with patch.object(
            platform_admin,
            "require_platform_admin",
            AsyncMock(side_effect=HTTPException(status_code=403, detail="denied")),
        ):
            with self.assertRaises(HTTPException) as exc:
                await platform_admin.list_report_quality_observations(
                    session=session,
                    limit=20,
                    offset=0,
                    status=None,
                    org_id=None,
                    project_id=None,
                    report_id=None,
                    observed_from=None,
                    observed_to=None,
                    q=None,
                )

        self.assertEqual(exc.exception.status_code, 403)
        self.assertEqual(session.calls, [])

    async def test_list_returns_filtered_observations(self) -> None:
        session = _Session([
            [{"total": 1}],
            [_row()],
        ])
        with patch.object(
            platform_admin,
            "require_platform_admin",
            AsyncMock(return_value=None),
        ):
            response = await platform_admin.list_report_quality_observations(
                session=session,
                limit=20,
                offset=0,
                status="fail",
                org_id=ORG_ID,
                project_id=None,
                report_id=None,
                observed_from=None,
                observed_to=None,
                q="Validation",
            )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.observations[0].status, "fail")
        self.assertEqual(
            response.observations[0].failed_invariants,
            ["score_rationales_complete"],
        )
        self.assertEqual(session.params[0]["quality_status"], "fail")
        self.assertEqual(session.params[1]["limit"], 20)

    async def test_summary_returns_status_and_invariant_counts(self) -> None:
        session = _Session([
            [{"status": "fail", "count": 2}, {"status": "warn", "count": 1}],
            [
                {
                    "invariant_id": "score_rationales_complete",
                    "severity": "fail",
                    "count": 2,
                }
            ],
        ])
        with patch.object(
            platform_admin,
            "require_platform_admin",
            AsyncMock(return_value=None),
        ):
            response = await platform_admin.get_report_quality_summary(
                session=session,
                status=None,
                org_id=None,
                project_id=None,
                report_id=None,
                observed_from=None,
                observed_to=None,
                q=None,
            )

        self.assertEqual(response.total, 3)
        self.assertEqual(response.status_counts[0].status, "fail")
        self.assertEqual(response.invariant_counts[0].invariant_id, "score_rationales_complete")

    async def test_detail_404_for_missing_observation(self) -> None:
        session = _Session([[]])
        with patch.object(
            platform_admin,
            "require_platform_admin",
            AsyncMock(return_value=None),
        ):
            with self.assertRaises(HTTPException) as exc:
                await platform_admin.get_report_quality_observation(
                    OBSERVATION_ID,
                    session=session,
                )

        self.assertEqual(exc.exception.status_code, 404)


class _Session:
    def __init__(self, results: list[list[dict]]) -> None:
        self.results = list(results)
        self.calls: list[str] = []
        self.params: list[dict] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append(str(statement))
        self.params.append(params or {})
        rows = self.results.pop(0) if self.results else []
        return _Result(rows)


class _Result:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict]:
        return self.rows

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None


if __name__ == "__main__":
    unittest.main()
