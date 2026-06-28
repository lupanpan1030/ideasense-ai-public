import unittest

from app.services.answer_meta import (
    build_skip_answer_meta_note,
    get_answer_meta_map,
    is_skip_answer_action,
    normalize_answer_meta,
    normalize_answer_action,
    remove_answer_meta_entry,
    resolve_skip_resolution_status,
    set_answer_meta_entry,
)


class NormalizeAnswerMetaTests(unittest.TestCase):
    def test_normalize_answer_meta_filters_invalid_entries(self) -> None:
        normalized = normalize_answer_meta(
            {
                " problem.one_line ": {
                    "resolution_status": "ANSWERED",
                    "claim_type": "unknown-type",
                    "evidence_level": "e9",
                    "source": "USER",
                    "note": "  sample  ",
                    "updated_at": "2026-04-04T10:00:00Z",
                },
                "": {"resolution_status": "answered"},
                "target_user.core": "invalid",
            }
        )

        self.assertEqual(
            normalized,
            {
                "problem.one_line": {
                    "resolution_status": "answered",
                    "claim_type": "hypothesis",
                    "evidence_level": "E1",
                    "source": "user",
                    "note": "sample",
                    "updated_at": "2026-04-04T10:00:00Z",
                }
            },
        )


class AnswerMetaMutationTests(unittest.TestCase):
    def test_set_answer_meta_entry_uses_defaults(self) -> None:
        state_meta: dict = {}

        set_answer_meta_entry(state_meta, "problem.one_line")

        answer_meta = get_answer_meta_map(state_meta)
        self.assertEqual(answer_meta["problem.one_line"]["resolution_status"], "answered")
        self.assertEqual(answer_meta["problem.one_line"]["claim_type"], "hypothesis")
        self.assertEqual(answer_meta["problem.one_line"]["evidence_level"], "E1")
        self.assertEqual(answer_meta["problem.one_line"]["source"], "user")
        self.assertIn("updated_at", answer_meta["problem.one_line"])

    def test_set_answer_meta_entry_allows_explicit_values(self) -> None:
        state_meta: dict = {}

        set_answer_meta_entry(
            state_meta,
            "market_strategy.uvp.one_line",
            resolution_status="partial",
            claim_type="estimate",
            evidence_level="E3",
            source="mixed",
            note="Updated from accepted pending draft",
            updated_at="2026-04-04T11:11:11Z",
        )

        self.assertEqual(
            get_answer_meta_map(state_meta)["market_strategy.uvp.one_line"],
            {
                "resolution_status": "partial",
                "claim_type": "estimate",
                "evidence_level": "E3",
                "source": "mixed",
                "note": "Updated from accepted pending draft",
                "updated_at": "2026-04-04T11:11:11Z",
            },
        )

    def test_remove_answer_meta_entry_cleans_empty_container(self) -> None:
        state_meta: dict = {}
        set_answer_meta_entry(state_meta, "tech_execution.product_scope.mvp_definition")

        remove_answer_meta_entry(
            state_meta, "tech_execution.product_scope.mvp_definition"
        )

        self.assertNotIn("answer_meta", state_meta)

    def test_set_answer_meta_entry_supports_unknown_states(self) -> None:
        state_meta: dict = {}

        set_answer_meta_entry(
            state_meta,
            "market_strategy.business_model.revenue_model",
            resolution_status="not_applicable",
            evidence_level="E0",
            source="user",
            note="User marked this question as not applicable.",
        )

        self.assertEqual(
            get_answer_meta_map(state_meta)[
                "market_strategy.business_model.revenue_model"
            ]["resolution_status"],
            "not_applicable",
        )
        self.assertEqual(
            get_answer_meta_map(state_meta)[
                "market_strategy.business_model.revenue_model"
            ]["evidence_level"],
            "E0",
        )


class AnswerActionTests(unittest.TestCase):
    def test_normalize_answer_action_handles_new_statuses(self) -> None:
        self.assertEqual(normalize_answer_action("unknown"), "unknown")
        self.assertEqual(normalize_answer_action("undecided"), "undecided")
        self.assertEqual(
            normalize_answer_action("not_applicable"), "not_applicable"
        )
        self.assertEqual(normalize_answer_action("ai_draft"), "ai_draft")

    def test_skip_actions_are_detected(self) -> None:
        self.assertTrue(is_skip_answer_action("skip_soft"))
        self.assertTrue(is_skip_answer_action("unknown"))
        self.assertTrue(is_skip_answer_action("undecided"))
        self.assertTrue(is_skip_answer_action("not_applicable"))
        self.assertFalse(is_skip_answer_action("ai_draft"))

    def test_resolve_skip_resolution_status_uses_action_or_reason(self) -> None:
        self.assertEqual(resolve_skip_resolution_status("unknown"), "unknown")
        self.assertEqual(resolve_skip_resolution_status("undecided"), "undecided")
        self.assertEqual(
            resolve_skip_resolution_status("not_applicable"),
            "not_applicable",
        )
        self.assertEqual(
            resolve_skip_resolution_status("skip_soft", "undecided"),
            "undecided",
        )
        self.assertEqual(
            resolve_skip_resolution_status("skip_soft", "not_applicable"),
            "not_applicable",
        )
        self.assertEqual(resolve_skip_resolution_status("skip_soft"), "unknown")

    def test_build_skip_answer_meta_note_suppresses_generic_reasons(self) -> None:
        self.assertEqual(
            build_skip_answer_meta_note("unknown", "cant_answer"),
            "User marked this answer as unknown.",
        )
        self.assertEqual(
            build_skip_answer_meta_note("undecided", "pricing not decided"),
            "User marked this answer as undecided: pricing not decided.",
        )


if __name__ == "__main__":
    unittest.main()
