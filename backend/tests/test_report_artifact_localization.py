import unittest

from app.core.report_builder import build_assessment_snapshots, build_report_payload


class ReportArtifactLocalizationTests(unittest.TestCase):
    def test_build_assessment_snapshots_includes_stage_locale_metadata(self) -> None:
        rows = [
            {
                "id": "assessment-problem",
                "stage": "problem",
                "draft_summary_markdown": "Draft summary",
                "final_summary_markdown": "Final summary",
                "confirmed": True,
                "total_score": 4.2,
                "confirmed_at": None,
                "created_at": None,
                "updated_at": None,
            }
        ]

        snapshots = build_assessment_snapshots(
            rows,
            summary_locales={"problem": {"draft": "en", "final": "zh"}},
        )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["draft_output_locale"], "en")
        self.assertEqual(snapshots[0]["final_output_locale"], "zh")

    def test_build_report_payload_preserves_artifact_locale(self) -> None:
        payload = build_report_payload(
            {
                "id": "project-1",
                "title": "IdeaSense",
                "description": "Localization",
                "current_stage": "report",
                "updated_at": None,
            },
            {},
            [],
            generated_at="2026-04-06T00:00:00Z",
            artifact_locale="zh",
        )

        self.assertEqual(payload["artifact_locale"], "zh")


if __name__ == "__main__":
    unittest.main()
