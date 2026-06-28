import unittest
from unittest.mock import patch

from app.services.prompt_runtime import (
    DEFAULT_PROMPT_OUTPUT_GUARD,
    DEFAULT_PROMPT_TASK_REGISTRY,
    PromptContextBuilder,
    PromptMutationClass,
    PromptTaskSpec,
    PromptTaskPreparationResult,
    execute_prompt_task,
    prepare_prompt_task,
    render_prompt_messages,
    resolve_prompt_task_timeout_ms,
    serialize_prompt_task_trace,
    stream_prepared_prompt_task,
)
from app.services.prompt_output_parsers import AnswerGateResult, QuestionRewriteResult
from app.services.prompt_task_specs import (
    DEFAULT_PROMPT_TASK_SPECS,
    PromptMutationClass as CanonicalPromptMutationClass,
    PromptTaskSpec as CanonicalPromptTaskSpec,
)


class PromptTaskRegistryTests(unittest.TestCase):
    def test_runtime_registry_uses_canonical_task_specs(self) -> None:
        self.assertIs(PromptMutationClass, CanonicalPromptMutationClass)
        self.assertIs(PromptTaskSpec, CanonicalPromptTaskSpec)
        self.assertEqual(
            tuple(DEFAULT_PROMPT_TASK_REGISTRY.keys()),
            tuple(task.task_key for task in DEFAULT_PROMPT_TASK_SPECS),
        )
        for task in DEFAULT_PROMPT_TASK_SPECS:
            self.assertIs(DEFAULT_PROMPT_TASK_REGISTRY.get(task.task_key), task)

    def test_registry_inventories_chat_and_planned_report_tasks(self) -> None:
        keys = set(DEFAULT_PROMPT_TASK_REGISTRY.keys())

        self.assertIn("answer_gate", keys)
        self.assertIn("question_compose", keys)
        self.assertIn("followup_compose", keys)
        self.assertIn("extract", keys)
        self.assertIn("question_rewrite_chat", keys)
        self.assertIn("question_rewrite_basic", keys)
        self.assertIn("stage_summary_problem", keys)
        self.assertIn("dvf_scoring", keys)
        self.assertIn("final_report", keys)
        self.assertIn("claim_verification", keys)

        answer_gate = DEFAULT_PROMPT_TASK_REGISTRY.get("answer_gate")
        self.assertEqual(answer_gate.provider_task, "answer_gate")
        self.assertEqual(answer_gate.timeout_ms, 3000)
        self.assertEqual(answer_gate.timeout_env, "ANSWER_GATE_TIMEOUT_MS")
        self.assertEqual(answer_gate.response_format, "json_object")
        self.assertEqual(answer_gate.output_contract, "answer_gate_json")
        self.assertEqual(answer_gate.allowed_mutation, PromptMutationClass.DECISION_ONLY)
        self.assertEqual(answer_gate.phase, "chat_migrated")

        final_report = DEFAULT_PROMPT_TASK_REGISTRY.get("final_report")
        self.assertEqual(final_report.provider_task, "report")
        self.assertEqual(final_report.temperature, 0.2)
        self.assertEqual(final_report.timeout_ms, 60000)
        self.assertEqual(final_report.timeout_env, "FINAL_REPORT_TIMEOUT_MS")
        self.assertEqual(final_report.response_format, "json_object")
        self.assertEqual(final_report.output_contract, "final_report_json")
        self.assertEqual(
            final_report.allowed_mutation,
            PromptMutationClass.REPORT_ARTIFACT,
        )

        dvf_scoring = DEFAULT_PROMPT_TASK_REGISTRY.get("dvf_scoring")
        self.assertEqual(dvf_scoring.timeout_ms, 45000)
        self.assertEqual(dvf_scoring.timeout_env, "DVF_SCORING_TIMEOUT_MS")
        self.assertEqual(dvf_scoring.output_contract, "dvf_json")

        stage_summary = DEFAULT_PROMPT_TASK_REGISTRY.get("stage_summary_problem")
        self.assertEqual(stage_summary.timeout_ms, 60000)
        self.assertEqual(stage_summary.timeout_env, "STAGE_SUMMARY_TIMEOUT_MS")

        claim_verification = DEFAULT_PROMPT_TASK_REGISTRY.get("claim_verification")
        self.assertEqual(
            claim_verification.system_template,
            "shared/claim_verification_system",
        )
        self.assertEqual(claim_verification.response_format, "json_object")
        self.assertEqual(claim_verification.output_contract, "claim_verification_json")
        self.assertEqual(claim_verification.allowed_mutation, PromptMutationClass.NONE)

    def test_output_guard_blocks_unauthorized_mutation_class(self) -> None:
        DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
            "question_compose",
            PromptMutationClass.VISIBLE_COPY_ONLY,
        )

        with self.assertRaises(PermissionError):
            DEFAULT_PROMPT_OUTPUT_GUARD.assert_allows(
                "question_compose",
                PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
            )

    def test_timeout_resolution_uses_task_env_override(self) -> None:
        task = DEFAULT_PROMPT_TASK_REGISTRY.get("answer_gate")

        with patch.dict("os.environ", {"ANSWER_GATE_TIMEOUT_MS": "250"}, clear=False):
            self.assertEqual(
                resolve_prompt_task_timeout_ms(task, minimum_ms=500),
                500,
            )

        with patch.dict("os.environ", {"ANSWER_GATE_TIMEOUT_MS": "0"}, clear=False):
            self.assertEqual(resolve_prompt_task_timeout_ms(task), 0)

        with patch.dict("os.environ", {"ANSWER_GATE_TIMEOUT_MS": "bad"}, clear=False):
            self.assertEqual(resolve_prompt_task_timeout_ms(task), 3000)


class PromptContextBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = PromptContextBuilder()

    def test_answer_gate_context_preserves_existing_prompt_variables(self) -> None:
        context = self.builder.answer_gate(
            {
                "question_id": "S1Q1",
                "stage": "problem",
                "variant": "default",
                "type_raw": "open",
                "prompt": "What problem are you solving?",
                "validation_rule": "Must include user and pain.",
                "instruction": "Be concrete.",
                "expected_key_points": ["User", "Pain", ""],
                "schema_paths": ["problem.target_user", "problem.pain"],
            },
            "Students lose track of deadlines.",
            "Project context summary.",
        )

        self.assertEqual(context.task_key, "answer_gate")
        self.assertEqual(
            context.variables["expected_key_points"],
            "- User\n- Pain",
        )
        self.assertEqual(
            context.variables["schema_list"],
            "- problem.target_user\n- problem.pain",
        )
        self.assertEqual(context.variables["context_block"], "Project context summary.\n\n")
        self.assertIn("latest_answer", context.section_names())

    def test_question_compose_context_truncates_bounded_sections(self) -> None:
        context = self.builder.question_compose(
            {
                "question_id": "S1Q2",
                "stage": "problem",
                "variant": "default",
                "instruction": "",
                "validation_rule": "",
                "expected_key_points": ["Buyer", "User"],
                "schema_paths": [],
            },
            base_prompt="Who is the first user?",
            latest_answer="a" * 1005,
            context_summary="b" * 1405,
            output_language="English",
        )

        self.assertEqual(context.variables["instruction"], "None")
        self.assertEqual(context.variables["validation_rule"], "None")
        self.assertEqual(context.variables["schema_list"], "None")
        self.assertEqual(context.variables["latest_answer"], f"{'a' * 1000}...")
        self.assertEqual(context.variables["context_summary"], f"{'b' * 1400}...")
        truncated_sections = {
            section.name: section.truncated for section in context.sections
        }
        self.assertTrue(truncated_sections["latest_answer"])
        self.assertTrue(truncated_sections["project_context"])

    def test_followup_compose_context_formats_decision_lists(self) -> None:
        context = self.builder.followup_compose(
            {
                "question_id": "S1Q3",
                "stage": "problem",
                "variant": "default",
                "prompt": "Pick the MVP priority.",
                "expected_key_points": "priority",
                "schema_paths": ["problem.mvp_priority"],
            },
            {
                "missing_points": ["MVP priority"],
                "critical_issues": [],
                "followup_questions": ["What ships first?"],
                "help_examples": ["The first version should prioritize __."],
            },
            fallback_message="Please clarify the MVP priority.",
            latest_answer=None,
            context_summary=None,
            output_language="English",
        )

        self.assertEqual(context.variables["missing_points"], "- MVP priority")
        self.assertEqual(context.variables["critical_issues"], "None")
        self.assertEqual(context.variables["followup_questions"], "- What ships first?")
        self.assertEqual(
            context.variables["help_examples"],
            "- The first version should prioritize __.",
        )
        self.assertEqual(context.variables["expected_key_points"], "- priority")
        self.assertEqual(context.variables["latest_answer"], "None")
        self.assertEqual(context.variables["context_summary"], "None")

    def test_question_rewrite_context_uses_registered_contract_sections(self) -> None:
        context = self.builder.question_rewrite(
            "question_rewrite_basic",
            {
                "question_id": "S1Q1",
                "stage": "problem",
                "variant": "default",
                "type_raw": "short_text",
                "prompt": "What is the problem?",
                "instruction": "Be specific.",
                "validation_rule": "non_empty",
                "standard_question": "Describe the core problem.",
                "schema_paths": ("problem.one_line",),
            },
            output_language="Simplified Chinese",
        )

        self.assertEqual(context.task_key, "question_rewrite_basic")
        self.assertEqual(context.variables["output_language"], "Simplified Chinese")
        self.assertEqual(context.variables["schema_list"], "- problem.one_line")
        self.assertIn("stage_question_contract", context.section_names())

    def test_ai_assist_context_tracks_visible_copy_boundary(self) -> None:
        context = self.builder.ai_assist(
            {
                "prompt": "Describe the user.",
                "validation_rule": "Must mention segment.",
                "instruction": "One sentence.",
            },
            context_summary="Project context.",
            sentence_hint="Answer in exactly one sentence.",
            output_language="English",
        )

        self.assertEqual(context.task_key, "ai_assist")
        self.assertIn("output_constraints", context.section_names())
        self.assertEqual(
            context.variables["sentence_hint"],
            "Answer in exactly one sentence.",
        )

    def test_qa_digest_context_registers_input_payload(self) -> None:
        context = self.builder.qa_digest(
            question_id="S1Q1",
            key_points=["Problem is manual reporting."],
            rolling_summary=None,
            output_language="English",
        )

        self.assertEqual(context.task_key, "qa_digest")
        self.assertIn("qa_digest_input", context.section_names())
        self.assertIn("Problem is manual reporting.", context.variables["payload_json"])

    def test_trace_metadata_redacts_prompt_variables(self) -> None:
        context = self.builder.question_compose(
            {"question_id": "S1Q2"},
            base_prompt="Who is the first user?",
            latest_answer="Students lose deadlines.",
            context_summary=None,
            output_language="English",
        )
        task = DEFAULT_PROMPT_TASK_REGISTRY.get("question_compose")
        trace = context.trace_metadata(task)

        self.assertTrue(trace["redacted"])
        self.assertEqual(trace["variables"]["latest_answer"]["type"], "str")
        self.assertEqual(
            trace["variables"]["latest_answer"]["chars"],
            len("Students lose deadlines."),
        )
        self.assertNotIn("Students lose deadlines", str(trace["variables"]))

    def test_report_contexts_preserve_payload_json_as_required_section(self) -> None:
        payload = {"project": {"title": "IdeaSense"}}

        stage_context = self.builder.stage_summary(
            "problem",
            payload,
            output_language="English",
        )
        self.assertEqual(stage_context.task_key, "stage_summary_problem")
        self.assertIn('"title": "IdeaSense"', stage_context.variables["payload_json"])
        self.assertIn("report_input", stage_context.section_names())

        dvf_context = self.builder.dvf_scoring(
            payload,
            output_language="English",
        )
        self.assertEqual(dvf_context.task_key, "dvf_scoring")
        self.assertIn("output_constraints", dvf_context.section_names())

        report_context = self.builder.final_report(
            payload,
            output_language="English",
        )
        self.assertEqual(report_context.task_key, "final_report")
        self.assertIn("report_input", report_context.section_names())

    def test_stage_summary_rejects_unsupported_stage(self) -> None:
        with self.assertRaises(ValueError):
            self.builder.stage_summary(
                "sales",
                {"project": {"title": "IdeaSense"}},
                output_language="English",
            )

    def test_claim_verification_context_registers_evidence_payload(self) -> None:
        context = self.builder.claim_verification(
            claim="The market is growing.",
            evidence=[{"title": "Market report", "snippet": "Growth is steady."}],
        )

        self.assertEqual(context.task_key, "claim_verification")
        self.assertIn("verification_input", context.section_names())
        self.assertIn("The market is growing.", context.variables["payload_json"])


class PromptRenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_render_prompt_messages_uses_registry_templates(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")
        calls = []

        async def renderer(session, template_name, **kwargs):
            calls.append((template_name, kwargs))
            return f"rendered:{template_name}:{kwargs.get('schema_list')}"

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            messages = await render_prompt_messages(
                object(),
                context,
                project_settings={"prompt_template_ids": {}},
            )

        self.assertEqual(
            messages,
            [
                {
                    "role": "system",
                    "content": "rendered:shared/extraction_system:- problem.pain",
                },
                {
                    "role": "user",
                    "content": "rendered:shared/extraction_user:- problem.pain",
                },
            ],
        )
        self.assertEqual(calls[0][0], "shared/extraction_system")
        self.assertEqual(calls[1][0], "shared/extraction_user")
        self.assertEqual(calls[0][1]["project_settings"], {"prompt_template_ids": {}})

    async def test_execute_prompt_task_uses_registry_metadata_and_parser(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")
        captured = {}

        class Result:
            content = '{"problem.pain": "Manual reporting is slow."}'
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}:{kwargs.get('schema_list')}"

        async def llm_call(provider_task, messages, **kwargs):
            captured["provider_task"] = provider_task
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
                parser=lambda content: {"parsed": content},
                provider_check=lambda provider_task: provider_task == "extract",
                llm_call=llm_call,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.provider_task, "extract")
        self.assertEqual(result.model, "gpt-test")
        self.assertEqual(
            result.parsed,
            {"parsed": '{"problem.pain": "Manual reporting is slow."}'},
        )
        self.assertEqual(captured["provider_task"], "extract")
        self.assertEqual(captured["kwargs"]["temperature"], 0.0)
        self.assertEqual(captured["kwargs"]["response_format"], "json_object")
        self.assertEqual(result.trace["timeout_ms"], 2500)
        self.assertEqual(result.trace["allowed_mutation"], "validated_context_update")
        self.assertEqual(result.trace["output_contract"], "schema_path_json")
        self.assertEqual(result.trace["parse_status"], "ok")
        self.assertIn("latency_ms", result.trace)

    async def test_execute_prompt_task_uses_registry_output_contract_parser(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")

        class Result:
            content = '{"problem.pain": "Manual reporting is slow."}'
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}"

        async def llm_call(provider_task, messages, **kwargs):
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
                provider_check=lambda _provider_task: True,
                llm_call=llm_call,
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.parsed,
            {"problem.pain": "Manual reporting is slow."},
        )

    async def test_execute_prompt_task_uses_answer_gate_output_contract_parser(self) -> None:
        builder = PromptContextBuilder()
        context = builder.answer_gate(
            {
                "question_id": "S1Q1",
                "prompt": "What problem are you solving?",
                "schema_paths": ["problem.one_line"],
            },
            "Manual reporting wastes hours.",
        )

        class Result:
            content = (
                '{"verdict":"pass","missing_points":[],"critical_issues":[],'
                '"followup_questions":[],"help_examples":[],'
                '"score":{"clarity":1,"completeness":0.8,"evidence":0.7},'
                '"overall":0.85}'
            )
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}"

        async def llm_call(provider_task, messages, **kwargs):
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.DECISION_ONLY,
                provider_check=lambda _provider_task: True,
                llm_call=llm_call,
            )

        self.assertTrue(result.ok)
        self.assertIsInstance(result.parsed, AnswerGateResult)
        self.assertEqual(result.parsed.verdict, "pass")

    async def test_execute_prompt_task_uses_rewrite_output_contract_parser(self) -> None:
        builder = PromptContextBuilder()
        context = builder.question_rewrite(
            "question_rewrite_basic",
            {"prompt": "Distribution?", "schema_paths": ["market.channels"]},
            output_language="English",
        )

        class Result:
            content = '{"prompt":"What is your first distribution channel?"}'
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}"

        async def llm_call(provider_task, messages, **kwargs):
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
                provider_check=lambda _provider_task: True,
                llm_call=llm_call,
            )

        self.assertTrue(result.ok)
        self.assertIsInstance(result.parsed, QuestionRewriteResult)
        self.assertEqual(
            result.parsed.prompt,
            "What is your first distribution channel?",
        )

    async def test_prepare_prompt_task_returns_stream_ready_metadata(self) -> None:
        builder = PromptContextBuilder()
        context = builder.question_compose(
            {"prompt": "Who is the primary user?", "schema_paths": ["problem.user"]},
            base_prompt="Who is the primary user?",
            latest_answer="Students first.",
            context_summary=None,
            output_language="English",
        )

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}:{kwargs.get('prompt')}"

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            prepared = await prepare_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VISIBLE_COPY_ONLY,
                provider_check=lambda provider_task: provider_task == "question_compose",
            )

        self.assertTrue(prepared.ok)
        self.assertEqual(prepared.provider_task, "question_compose")
        self.assertEqual(prepared.temperature, 0.35)
        self.assertEqual(prepared.timeout_ms, 3500)
        self.assertEqual(len(prepared.messages), 2)
        self.assertEqual(prepared.trace["allowed_mutation"], "visible_copy_only")

    async def test_execute_prompt_task_allows_runtime_timeout_override(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")

        class Result:
            content = '{"problem.pain": "Manual reporting is slow."}'
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}"

        async def llm_call(provider_task, messages, **kwargs):
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
                timeout_override_ms=50,
                timeout_minimum_ms=200,
                provider_check=lambda _provider_task: True,
                llm_call=llm_call,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.trace["timeout_ms"], 200)

    async def test_execute_prompt_task_returns_provider_unavailable_fallback(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")

        result = await execute_prompt_task(
            object(),
            context,
            expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
            provider_check=lambda _provider_task: False,
            fallback=lambda failure: {"reason": failure.reason},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.failure.reason, "provider_unavailable")
        self.assertEqual(result.failure_reason, "provider_unavailable")
        self.assertEqual(result.fallback_kind, "skip_sync_extraction")
        self.assertEqual(result.fallback_value, {"reason": "provider_unavailable"})
        trace = serialize_prompt_task_trace(result)
        self.assertEqual(trace["fallback_kind"], "skip_sync_extraction")

    async def test_execute_prompt_task_returns_standard_fallback_value(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")

        result = await execute_prompt_task(
            object(),
            context,
            expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
            provider_check=lambda _provider_task: False,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.fallback_kind, "skip_sync_extraction")
        self.assertEqual(
            result.fallback_value,
            {
                "kind": "skip_sync_extraction",
                "reason": "provider_unavailable",
            },
        )

    async def test_execute_prompt_task_reports_parse_error(self) -> None:
        builder = PromptContextBuilder()
        context = builder.extraction(["problem.pain"], "Manual reporting is slow.")

        class Result:
            content = "not-json"
            provider = "openai"
            model = "gpt-test"

        async def renderer(session, template_name, **kwargs):
            return f"rendered:{template_name}"

        async def llm_call(provider_task, messages, **kwargs):
            return Result()

        with patch("app.services.prompt_runtime.render_prompt_template", renderer):
            result = await execute_prompt_task(
                object(),
                context,
                expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
                parser=lambda _content: (_ for _ in ()).throw(ValueError("bad json")),
                provider_check=lambda _provider_task: True,
                llm_call=llm_call,
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.failure.reason, "parse_error")
        self.assertIn("bad json", result.failure.message)
        trace = serialize_prompt_task_trace(result)
        self.assertEqual(trace["failure_reason"], "parse_error")
        self.assertEqual(trace["model"], "gpt-test")
        self.assertEqual(trace["provider"], "openai")

    async def test_stream_prepared_prompt_task_uses_runtime_timeout_and_trace(self) -> None:
        prepared = PromptTaskPreparationResult(
            task_key="question_compose",
            provider_task="question_compose",
            messages=[{"role": "user", "content": "Compose the next question."}],
            temperature=0.35,
            response_format=None,
            timeout_ms=3500,
            trace={"task_key": "question_compose", "redacted": True},
        )
        captured = {}

        async def fake_stream_call(provider_task, messages, **kwargs):
            captured["provider_task"] = provider_task
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            return type(
                "StreamResult",
                (),
                {
                    "stream": object(),
                    "provider": "openai",
                    "model": "gpt-test",
                },
            )()

        result = await stream_prepared_prompt_task(
            prepared,
            stream_call=fake_stream_call,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.provider_task, "question_compose")
        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.model, "gpt-test")
        self.assertEqual(captured["provider_task"], "question_compose")
        self.assertEqual(captured["kwargs"]["temperature"], 0.35)
        self.assertEqual(result.trace["task_key"], "question_compose")

    async def test_stream_prepared_prompt_task_returns_standard_fallback_value(self) -> None:
        prepared = PromptTaskPreparationResult(
            task_key="question_compose",
            provider_task="question_compose",
            messages=[{"role": "user", "content": "Compose the next question."}],
            temperature=0.35,
            response_format=None,
            timeout_ms=3500,
            trace={"task_key": "question_compose", "redacted": True},
        )

        async def fake_stream_call(provider_task, messages, **kwargs):
            raise RuntimeError("stream failed")

        result = await stream_prepared_prompt_task(
            prepared,
            stream_call=fake_stream_call,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.failure.reason, "llm_error")
        self.assertEqual(result.fallback_kind, "persist_backend_selected_question")
        self.assertEqual(
            result.fallback_value,
            {
                "kind": "persist_backend_selected_question",
                "reason": "llm_error",
                "message": "stream failed",
            },
        )


if __name__ == "__main__":
    unittest.main()
