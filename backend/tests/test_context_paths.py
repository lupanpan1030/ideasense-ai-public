import unittest

from app.services.context_paths import (
    get_context_path_value,
    infer_context_path_stage,
    pop_context_path_value,
    set_context_path_value,
    split_context_path,
)


class ContextPathMutationTests(unittest.TestCase):
    def test_set_path_wraps_terminal_list_scalar(self) -> None:
        target: dict = {}

        set_context_path_value(target, "problem.scenarios[]", "late reporting")

        self.assertEqual(target, {"problem": {"scenarios": ["late reporting"]}})

    def test_set_path_preserves_list_and_none_terminal_list_values(self) -> None:
        target: dict = {}

        set_context_path_value(target, "problem.scenarios[]", ["a", "b"])
        set_context_path_value(target, "problem.empty[]", None)

        self.assertEqual(target["problem"]["scenarios"], ["a", "b"])
        self.assertIsNone(target["problem"]["empty"])

    def test_set_path_replaces_non_dict_intermediate(self) -> None:
        target = {"problem": "old"}

        set_context_path_value(target, "problem.one_line", "new")

        self.assertEqual(target, {"problem": {"one_line": "new"}})

    def test_pop_path_removes_value_and_empty_parents(self) -> None:
        target = {
            "pending": {
                "nested": {"value": "draft"},
                "keep": {"value": "other"},
            }
        }

        value = pop_context_path_value(target, " pending.nested.value ")

        self.assertEqual(value, "draft")
        self.assertEqual(target, {"pending": {"keep": {"value": "other"}}})

    def test_pop_path_returns_none_for_missing_or_empty_path(self) -> None:
        target = {"problem": {"one_line": "x"}}

        self.assertIsNone(pop_context_path_value(target, ""))
        self.assertIsNone(pop_context_path_value(target, "problem.missing"))
        self.assertEqual(target, {"problem": {"one_line": "x"}})


class ContextPathReadTests(unittest.TestCase):
    def test_split_context_path_trims_and_strips_list_markers(self) -> None:
        self.assertEqual(
            split_context_path(" problem.scenarios[].value "),
            ["problem", "scenarios", "value"],
        )

    def test_get_context_path_value_reads_string_or_list_paths(self) -> None:
        state = {"problem": {"scenarios": [{"text": "slow exports"}]}}

        self.assertEqual(
            get_context_path_value(state, "problem.scenarios[]"),
            [{"text": "slow exports"}],
        )
        self.assertEqual(
            get_context_path_value(state, ["problem", "scenarios"]),
            [{"text": "slow exports"}],
        )


class ContextPathStageInferenceTests(unittest.TestCase):
    def test_infer_context_path_stage_uses_only_legacy_exact_prefixes(self) -> None:
        self.assertEqual(infer_context_path_stage("market.foo", "problem"), "market")
        self.assertEqual(infer_context_path_stage("report.foo", "tech"), "report")
        self.assertEqual(
            infer_context_path_stage("market_strategy.uvp.one_line", "problem"),
            "problem",
        )
        self.assertEqual(
            infer_context_path_stage("tech_execution.product_scope.mvp", "market"),
            "market",
        )


if __name__ == "__main__":
    unittest.main()
