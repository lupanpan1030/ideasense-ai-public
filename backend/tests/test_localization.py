import unittest

from app.services.localization import (
    apply_summary_locale_update,
    normalize_output_locale,
    normalize_summary_locale_map,
    output_language_label,
)


class LocalizationTests(unittest.TestCase):
    def test_normalize_output_locale_defaults_to_english(self) -> None:
        self.assertEqual(normalize_output_locale(None), "en")
        self.assertEqual(normalize_output_locale(""), "en")
        self.assertEqual(normalize_output_locale("es"), "en")

    def test_normalize_output_locale_accepts_supported_values(self) -> None:
        self.assertEqual(normalize_output_locale("en"), "en")
        self.assertEqual(normalize_output_locale("zh"), "zh")
        self.assertEqual(normalize_output_locale("ZH"), "zh")

    def test_output_language_label_matches_locale(self) -> None:
        self.assertEqual(output_language_label("en"), "English")
        self.assertEqual(output_language_label("zh"), "Simplified Chinese")

    def test_normalize_summary_locale_map_filters_invalid_entries(self) -> None:
        self.assertEqual(
            normalize_summary_locale_map(
                {
                    "summary_locales": {
                        "Problem": {"draft": "en", "final": "ZH"},
                        "market": {"draft": "es"},
                        "": {"final": "zh"},
                    }
                }
            ),
            {"problem": {"draft": "en", "final": "zh"}},
        )

    def test_apply_summary_locale_update_merges_existing_state_meta(self) -> None:
        updated = apply_summary_locale_update(
            {
                "other": {"keep": True},
                "summary_locales": {"problem": {"draft": "en"}},
            },
            stage="problem",
            final_output_locale="zh",
        )
        self.assertEqual(updated["other"], {"keep": True})
        self.assertEqual(
            updated["summary_locales"]["problem"],
            {"draft": "en", "final": "zh"},
        )


if __name__ == "__main__":
    unittest.main()
