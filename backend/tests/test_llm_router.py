import os
import unittest

from app.core.llm_router import (
    _deepseek_model,
    _gemini_model,
    _qwen_model,
    _resolve_provider_chain,
)


class LLMRouterCostTierTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = (
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_MODEL",
            "DEEPSEEK_PRO_MODEL",
            "DEEPSEEK_REPORT_MODEL",
            "QWEN_API_KEY",
            "QWEN_MODEL",
            "QWEN_PRO_MODEL",
            "QWEN_REPORT_MODEL",
            "QWEN_BASE_URL",
            "GEMINI_API_KEY",
            "GEMINI_MODEL",
            "GEMINI_PRO_MODEL",
            "GEMINI_REPORT_MODEL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
            "BEDROCK_MODEL_ID",
            "BEDROCK_MODEL_ID_CHAT",
            "BEDROCK_MODEL_ID_STAGE_EVAL",
            "BEDROCK_MODEL_ID_REPORT",
            "BEDROCK_MODEL_ID_DEFAULT",
            "LLM_PROVIDER_DEFAULT",
            "LLM_PROVIDER_AI_ASSIST",
            "LLM_PROVIDER_EXTRACT",
            "LLM_PROVIDER_FOLLOWUP_COMPOSE",
            "LLM_PROVIDER_QUESTION_COMPOSE",
            "LLM_PROVIDER_QUESTION_REWRITE",
            "LLM_PROVIDER_ROUTER",
            "LLM_PROVIDER_QA_DIGEST",
            "LLM_PROVIDER_ANSWER_GATE",
            "LLM_PROVIDER_STAGE_SUMMARY",
            "LLM_PROVIDER_DVF_SCORING",
            "LLM_PROVIDER_REPORT",
        )
        self._original = {key: os.environ.get(key) for key in self._keys}
        for key in self._keys:
            os.environ.pop(key, None)
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
        os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-flash"
        os.environ["DEEPSEEK_PRO_MODEL"] = "deepseek-v4-pro"
        os.environ["QWEN_API_KEY"] = "test-qwen-key"
        os.environ["QWEN_MODEL"] = "qwen3.5-plus"
        os.environ["QWEN_PRO_MODEL"] = "qwen3-max"

    def tearDown(self) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_high_volume_tasks_default_to_deepseek_first(self) -> None:
        for task in (
            "ai_assist",
            "extract",
            "router",
            "qa_digest",
        ):
            with self.subTest(task=task):
                self.assertEqual(
                    _resolve_provider_chain(task),
                    ["deepseek", "qwen", "openai"],
                )

    def test_visible_rewrite_defaults_to_qwen_first(self) -> None:
        self.assertEqual(
            _resolve_provider_chain("question_rewrite"),
            ["qwen", "deepseek", "openai"],
        )

    def test_demo_facing_compose_tasks_default_to_qwen_first(self) -> None:
        for task in ("followup_compose", "question_compose"):
            with self.subTest(task=task):
                self.assertEqual(
                    _resolve_provider_chain(task),
                    ["qwen", "deepseek", "openai"],
                )

    def test_demo_facing_compose_tasks_ignore_global_default_chain(self) -> None:
        os.environ["LLM_PROVIDER_DEFAULT"] = "deepseek,openai"

        for task in ("followup_compose", "question_compose"):
            with self.subTest(task=task):
                self.assertEqual(
                    _resolve_provider_chain(task),
                    ["qwen", "deepseek", "openai"],
                )

    def test_assessment_tasks_default_to_cost_conscious_chain(self) -> None:
        expected = {
            "answer_gate": ["deepseek", "qwen", "openai"],
            "stage_summary": ["deepseek", "qwen", "openai"],
            "dvf_scoring": ["deepseek", "qwen", "openai"],
            "report": ["qwen", "deepseek", "openai"],
        }
        for task, chain in expected.items():
            with self.subTest(task=task):
                self.assertEqual(_resolve_provider_chain(task), chain)

    def test_explicit_task_chain_overrides_default_cost_tier(self) -> None:
        os.environ["LLM_PROVIDER_REPORT"] = "deepseek,openai"

        self.assertEqual(_resolve_provider_chain("report"), ["deepseek", "openai"])

    def test_deepseek_uses_flash_for_high_volume_tasks(self) -> None:
        for task in (
            "ai_assist",
            "extract",
            "followup_compose",
            "question_compose",
            "question_rewrite",
            "router",
            "qa_digest",
        ):
            with self.subTest(task=task):
                self.assertEqual(_deepseek_model(task), "deepseek-v4-flash")

    def test_deepseek_uses_pro_for_heavy_assessment_tasks(self) -> None:
        for task in ("stage_summary", "dvf_scoring", "report"):
            with self.subTest(task=task):
                self.assertEqual(_deepseek_model(task), "deepseek-v4-pro")

    def test_task_specific_deepseek_model_overrides_pro_tier(self) -> None:
        os.environ["DEEPSEEK_REPORT_MODEL"] = "deepseek-report-special"

        self.assertEqual(_deepseek_model("report"), "deepseek-report-special")

    def test_qwen_uses_default_for_high_volume_tasks(self) -> None:
        for task in (
            "ai_assist",
            "extract",
            "followup_compose",
            "question_compose",
            "question_rewrite",
            "router",
            "qa_digest",
        ):
            with self.subTest(task=task):
                self.assertEqual(_qwen_model(task), "qwen3.5-plus")

    def test_qwen_uses_pro_for_heavy_assessment_tasks(self) -> None:
        for task in ("stage_summary", "dvf_scoring", "report"):
            with self.subTest(task=task):
                self.assertEqual(_qwen_model(task), "qwen3-max")

    def test_task_specific_qwen_model_overrides_pro_tier(self) -> None:
        os.environ["QWEN_REPORT_MODEL"] = "qwen-report-special"

        self.assertEqual(_qwen_model("report"), "qwen-report-special")

    def test_gemini_uses_default_for_chat_tasks(self) -> None:
        os.environ["GEMINI_MODEL"] = "gemini-3.1-flash-lite"
        os.environ["GEMINI_PRO_MODEL"] = "gemini-3.5-flash"

        for task in ("followup_compose", "question_compose"):
            with self.subTest(task=task):
                self.assertEqual(_gemini_model(task), "gemini-3.1-flash-lite")

    def test_gemini_uses_pro_for_heavy_assessment_tasks(self) -> None:
        os.environ["GEMINI_MODEL"] = "gemini-3.1-flash-lite"
        os.environ["GEMINI_PRO_MODEL"] = "gemini-3.5-flash"

        for task in ("stage_summary", "dvf_scoring", "report"):
            with self.subTest(task=task):
                self.assertEqual(_gemini_model(task), "gemini-3.5-flash")

    def test_task_specific_gemini_model_overrides_pro_tier(self) -> None:
        os.environ["GEMINI_MODEL"] = "gemini-3.1-flash-lite"
        os.environ["GEMINI_PRO_MODEL"] = "gemini-3.5-flash"
        os.environ["GEMINI_REPORT_MODEL"] = "gemini-report-special"

        self.assertEqual(_gemini_model("report"), "gemini-report-special")


if __name__ == "__main__":
    unittest.main()
