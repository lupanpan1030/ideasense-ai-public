import types
import unittest
from unittest.mock import patch

from app.services import stage_summary_worker_handler
from app.services.stage_summary_worker_handler import (
    STAGE_SUMMARY_FALLBACK_MODEL,
    generate_stage_summary_v0,
    run_stage_summary_v0,
)


class StageSummaryWorkerHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_stage_summary_uses_prompt_runtime(self) -> None:
        captured: dict[str, object] = {}

        async def fake_execute_prompt_task(session, context, **kwargs):
            captured["session"] = session
            captured["task_key"] = context.task_key
            captured["expected_mutation"] = kwargs["expected_mutation"]
            return types.SimpleNamespace(
                ok=True,
                content="Summary text",
                model="model-a",
                provider="test-provider",
                trace={"task_key": context.task_key},
                failure=None,
            )

        session = object()
        trace_sink: dict[str, object] = {}
        with patch.object(
            stage_summary_worker_handler,
            "execute_prompt_task",
            new=fake_execute_prompt_task,
        ):
            summary, model = await generate_stage_summary_v0(
                session,
                "problem",
                {"data": {"problem": {"one_line": "Manual reporting is slow."}}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertEqual(summary, "Summary text")
        self.assertEqual(model, "model-a")
        self.assertIs(captured["session"], session)
        self.assertEqual(captured["task_key"], "stage_summary_problem")
        self.assertEqual(
            captured["expected_mutation"],
            stage_summary_worker_handler.PromptMutationClass.REPORT_ARTIFACT,
        )
        self.assertIn("stage_summary_problem", trace_sink)

    async def test_generate_stage_summary_uses_fallback_on_executor_error(
        self,
    ) -> None:
        async def fake_execute_prompt_task(_session, _context, **_kwargs):
            raise RuntimeError("provider timeout")

        trace_sink: dict[str, object] = {}
        with patch.object(
            stage_summary_worker_handler,
            "execute_prompt_task",
            new=fake_execute_prompt_task,
        ):
            summary, model = await generate_stage_summary_v0(
                object(),
                "market",
                {"data": {"market_strategy": {"uvp": {"one_line": "Fast setup"}}}},
                output_locale="en",
                trace_sink=trace_sink,
            )

        self.assertIn("Fast setup", summary)
        self.assertEqual(model, STAGE_SUMMARY_FALLBACK_MODEL)
        self.assertEqual(trace_sink["stage_summary_market"]["status"], "fallback")

    async def test_run_stage_summary_requires_identifiers(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Job payload missing stage summary identifiers.",
        ):
            await run_stage_summary_v0(object(), {"project_id": "project-1"})


if __name__ == "__main__":
    unittest.main()
