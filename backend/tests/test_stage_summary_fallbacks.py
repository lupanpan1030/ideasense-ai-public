import unittest

from app.services.stage_summary_fallbacks import (
    build_stage_summary_fallback,
    collect_stage_summary_items,
    stage_summary_label,
    stage_summary_value,
)


class StageSummaryFallbackTests(unittest.TestCase):
    def test_stage_summary_label_formats_paths(self) -> None:
        self.assertEqual(
            stage_summary_label("problem.customer_segment"),
            "Problem / Customer Segment",
        )

    def test_stage_summary_value_normalizes_and_truncates(self) -> None:
        self.assertEqual(stage_summary_value("  a\n b  "), "a b")
        self.assertEqual(stage_summary_value(["x", "y"]), '["x", "y"]')
        self.assertEqual(stage_summary_value("abcdef", max_len=5), "ab...")
        self.assertIsNone(stage_summary_value(""))

    def test_collect_stage_summary_items_handles_scalar_lists(self) -> None:
        items = collect_stage_summary_items(
            {"problem": {"channels": ["interviews", "surveys", "calls"]}}
        )

        self.assertEqual(
            items,
            [("Problem / Channels", "interviews; surveys; calls")],
        )

    def test_build_stage_summary_fallback_uses_payload_data(self) -> None:
        summary = build_stage_summary_fallback(
            "problem",
            {"data": {"customer_segment": "student founders"}},
            output_locale="en",
        )

        self.assertIn("### Problem summary", summary)
        self.assertIn("- Customer Segment: student founders", summary)

    def test_build_stage_summary_fallback_handles_empty_payload(self) -> None:
        summary = build_stage_summary_fallback("market", {}, output_locale="zh")

        self.assertIn("### Market summary", summary)
        self.assertIn("No confirmed details were available.", summary)


if __name__ == "__main__":
    unittest.main()
