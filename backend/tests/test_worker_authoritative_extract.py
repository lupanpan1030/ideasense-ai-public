import sys
import types
import unittest
from unittest.mock import patch


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app import worker  # noqa: E402
from app.services import answer_extraction_worker_handler as extraction_worker  # noqa: E402
from app.services import chat_sync_extraction_preview as sync_extraction  # noqa: E402
from app.services import report_generation_worker_handler as report_worker  # noqa: E402


class WorkerPromptRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_worker_job_handlers_include_known_job_types(self) -> None:
        handlers = worker._worker_job_handlers()

        self.assertIs(
            handlers["extract_answer_v0"],
            worker._process_extract_answer_job,
        )
        self.assertIs(
            handlers[worker.STAGE_SUMMARY_JOB_TYPE],
            worker._process_stage_summary_job,
        )
        self.assertIs(
            handlers["stage_summary_v0"],
            worker._process_stage_summary_job,
        )
        self.assertIs(
            handlers[worker.STAGE_FINALIZE_JOB_TYPE],
            worker._process_stage_finalize_job,
        )
        self.assertIs(
            handlers["verify_question_claims_v0"],
            worker._process_verify_question_claims_job,
        )
        self.assertIs(
            handlers[worker.REPORT_GENERATION_JOB_TYPE],
            worker._process_report_generation_job,
        )

    async def test_extract_with_openai_uses_prompt_runtime_executor(self) -> None:
        captured: dict[str, object] = {}

        async def fake_executor(session, context, **kwargs):
            captured["session"] = session
            captured["task_key"] = context.task_key
            captured["schema_list"] = context.variables["schema_list"]
            captured["expected_mutation"] = kwargs["expected_mutation"]
            return types.SimpleNamespace(
                ok=True,
                parsed={"problem.one_line": "Manual reporting is slow."},
                failure=None,
            )

        session = object()
        with patch.object(extraction_worker, "execute_prompt_task", new=fake_executor):
            result = await extraction_worker._extract_with_openai(
                session,
                ["problem.one_line"],
                "Manual reporting is slow.",
            )

        self.assertEqual(result, {"problem.one_line": "Manual reporting is slow."})
        self.assertIs(captured["session"], session)
        self.assertEqual(captured["task_key"], "extract")
        self.assertEqual(captured["schema_list"], "- problem.one_line")
        self.assertEqual(
            captured["expected_mutation"],
            extraction_worker.PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        )

    async def test_process_job_dispatches_extract_answer_v0(self) -> None:
        captured: dict[str, object] = {}

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_extract_answer(
            session,
            payload,
            *,
            job_org_id=None,
            set_worker_context_fn=None,
        ):
            captured["session"] = session
            captured["payload"] = payload
            captured["job_org_id"] = job_org_id
            captured["set_worker_context_fn"] = set_worker_context_fn

        payload = {
            "project_id": "project-1",
            "question_instance_id": "question-instance-1",
            "message_id": "message-1",
        }
        with (
            patch.object(worker, "AdminAsyncSessionLocal", lambda: _Session()),
            patch.object(
                worker,
                "run_extract_answer_v0",
                new=fake_extract_answer,
            ),
        ):
            await worker._process_job(
                {"org_id": "org-1", "job_type": "extract_answer_v0", "payload": payload}
            )

        self.assertIsInstance(captured["session"], _Session)
        self.assertEqual(captured["payload"], payload)
        self.assertEqual(captured["job_org_id"], "org-1")
        self.assertIs(captured["set_worker_context_fn"], worker._set_worker_context)

    async def test_process_job_dispatches_stage_summary_v0(self) -> None:
        captured: dict[str, object] = {}

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_stage_summary(
            session,
            payload,
            *,
            job_org_id=None,
            set_worker_context_fn=None,
        ):
            captured["session"] = session
            captured["payload"] = payload
            captured["job_org_id"] = job_org_id
            captured["set_worker_context_fn"] = set_worker_context_fn

        payload = {
            "project_id": "project-1",
            "stage": "problem",
            "context_version": 4,
        }
        with (
            patch.object(worker, "AdminAsyncSessionLocal", lambda: _Session()),
            patch.object(
                worker,
                "run_stage_summary_v0",
                new=fake_stage_summary,
            ),
        ):
            await worker._process_job(
                {
                    "org_id": "org-1",
                    "job_type": worker.STAGE_SUMMARY_JOB_TYPE,
                    "payload": payload,
                }
            )

        self.assertIsInstance(captured["session"], _Session)
        self.assertEqual(captured["payload"], payload)
        self.assertEqual(captured["job_org_id"], "org-1")
        self.assertIs(captured["set_worker_context_fn"], worker._set_worker_context)

    async def test_process_job_dispatches_stage_finalize_v0(self) -> None:
        captured: dict[str, object] = {}

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_stage_finalize(
            session,
            payload,
            *,
            job_org_id=None,
            set_worker_context_fn=None,
        ):
            captured["session"] = session
            captured["payload"] = payload
            captured["job_org_id"] = job_org_id
            captured["set_worker_context_fn"] = set_worker_context_fn

        payload = {
            "project_id": "project-1",
            "stage": "market",
            "context_version": 8,
        }
        with (
            patch.object(worker, "AdminAsyncSessionLocal", lambda: _Session()),
            patch.object(
                worker,
                "run_stage_finalize_v0",
                new=fake_stage_finalize,
            ),
        ):
            await worker._process_job(
                {
                    "org_id": "org-1",
                    "job_type": worker.STAGE_FINALIZE_JOB_TYPE,
                    "payload": payload,
                }
            )

        self.assertIsInstance(captured["session"], _Session)
        self.assertEqual(captured["payload"], payload)
        self.assertEqual(captured["job_org_id"], "org-1")
        self.assertIs(captured["set_worker_context_fn"], worker._set_worker_context)

    async def test_process_job_dispatches_verify_question_claims_v0(self) -> None:
        captured: dict[str, object] = {}

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_verify_question_claims(
            session,
            payload,
            *,
            job_org_id=None,
            set_worker_context_fn=None,
        ):
            captured["session"] = session
            captured["payload"] = payload
            captured["job_org_id"] = job_org_id
            captured["set_worker_context_fn"] = set_worker_context_fn

        payload = {
            "project_id": "project-1",
            "question_instance_id": "question-instance-1",
        }
        with (
            patch.object(worker, "AdminAsyncSessionLocal", lambda: _Session()),
            patch.object(
                worker,
                "run_verify_question_claims_v0",
                new=fake_verify_question_claims,
            ),
        ):
            await worker._process_job(
                {
                    "org_id": "org-1",
                    "job_type": "verify_question_claims_v0",
                    "payload": payload,
                }
            )

        self.assertIsInstance(captured["session"], _Session)
        self.assertEqual(captured["payload"], payload)
        self.assertEqual(captured["job_org_id"], "org-1")
        self.assertIs(captured["set_worker_context_fn"], worker._set_worker_context)

    async def test_process_job_dispatches_report_generation_v0(self) -> None:
        captured: dict[str, object] = {}

        class _Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def fake_report_generation(
            session,
            payload,
            *,
            job_id=None,
            job_org_id=None,
            set_worker_context_fn=None,
        ):
            captured["session"] = session
            captured["payload"] = payload
            captured["job_id"] = job_id
            captured["job_org_id"] = job_org_id
            captured["set_worker_context_fn"] = set_worker_context_fn

        payload = {
            "project_id": "project-1",
            "context_version": 8,
            "requested_by_user_id": "user-1",
        }
        with (
            patch.object(worker, "AdminAsyncSessionLocal", lambda: _Session()),
            patch.object(
                worker,
                "run_report_generation_v0",
                new=fake_report_generation,
            ),
        ):
            await worker._process_job(
                {
                    "id": 42,
                    "org_id": "org-1",
                    "job_type": worker.REPORT_GENERATION_JOB_TYPE,
                    "payload": payload,
                }
            )

        self.assertIsInstance(captured["session"], _Session)
        self.assertEqual(captured["payload"], payload)
        self.assertEqual(captured["job_id"], 42)
        self.assertEqual(captured["job_org_id"], "org-1")
        self.assertIs(captured["set_worker_context_fn"], worker._set_worker_context)

    async def test_process_job_requires_org_id_for_force_rls_context(self) -> None:
        with (
            patch.object(worker, "AdminAsyncSessionLocal", object()),
            self.assertRaisesRegex(ValueError, "missing org_id"),
        ):
            await worker._process_job({"job_type": "extract_answer_v0", "payload": {}})

    async def test_touch_report_job_sets_org_context_and_extends_lock(self) -> None:
        class _Tx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _Session:
            def __init__(self):
                self.calls: list[tuple[str, dict[str, object]]] = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def begin(self):
                return _Tx()

            async def execute(self, statement, params=None):
                self.calls.append((str(statement), params or {}))
                return None

        session = _Session()
        with patch.object(report_worker, "AdminAsyncSessionLocal", lambda: session):
            await report_worker._touch_report_job(42, "org-1", phase="finalizing")

        update_statement, update_params = session.calls[-1]
        self.assertIn("AND org_id = :org_id", update_statement)
        self.assertIn("lock_expires_at", update_statement)
        self.assertIn("CAST(:phase AS text)", update_statement)
        self.assertEqual(update_params["job_id"], 42)
        self.assertEqual(update_params["org_id"], "org-1")
        self.assertEqual(update_params["phase"], "finalizing")
        self.assertEqual(update_params["lock_ttl"], report_worker.REPORT_LOCK_TTL_SEC)
        self.assertTrue(
            any(params.get("org_id") == "org-1" for _, params in session.calls)
        )

    async def test_claim_report_job_uses_report_lock_ttl(self) -> None:
        await self._assert_claim_job_uses_report_lock_ttl(
            worker.REPORT_GENERATION_JOB_TYPE
        )

    async def test_claim_stage_finalize_job_uses_report_lock_ttl(self) -> None:
        await self._assert_claim_job_uses_report_lock_ttl(
            worker.STAGE_FINALIZE_JOB_TYPE
        )

    async def _assert_claim_job_uses_report_lock_ttl(self, job_type: str) -> None:
        class _Result:
            def __init__(self, row):
                self._row = row

            def mappings(self):
                return self

            def first(self):
                return self._row

        class _Session:
            def __init__(self):
                self.calls: list[tuple[str, dict[str, object]]] = []

            async def execute(self, statement, params=None):
                text_value = str(statement)
                self.calls.append((text_value, params or {}))
                if (
                    "FROM background_jobs" in text_value
                    and "WHERE status = 'queued'" in text_value
                ):
                    return _Result(
                        {
                            "id": 7,
                            "org_id": "org-1",
                            "project_id": "project-1",
                            "job_type": job_type,
                            "payload": {},
                            "attempts": 0,
                            "max_attempts": 3,
                        }
                    )
                return _Result(None)

        session = _Session()
        job = await worker._claim_job(session)

        self.assertEqual(job["id"], 7)
        update_call = next(
            (params for statement, params in session.calls if "SET status = 'running'" in statement),
            None,
        )
        self.assertIsNotNone(update_call)
        self.assertEqual(update_call["lock_ttl"], worker.REPORT_LOCK_TTL_SEC)


class AuthoritativeExtractMutationGuardTests(unittest.TestCase):
    def test_skips_main_context_mutation_after_stage_enters_confirmation(self) -> None:
        self.assertTrue(
            extraction_worker._should_skip_authoritative_extract_mutation("awaiting_confirm")
        )
        self.assertFalse(
            extraction_worker._should_skip_authoritative_extract_mutation("in_progress")
        )


class ApplyAuthoritativeExtractionUpdatesTests(unittest.TestCase):
    def test_apply_authoritative_extraction_updates_is_noop_when_state_is_already_current(self) -> None:
        state_json = {"problem": {"one_line": "Manual reporting is slow."}}
        state_meta = {
            "pending_confirm": {},
            "answer_meta": {
                "problem.one_line": {
                    "resolution_status": "answered",
                    "claim_type": "hypothesis",
                    "evidence_level": "E1",
                    "source": "user",
                    "updated_at": "2026-04-04T12:00:00Z",
                }
            },
        }

        next_state_json, next_state_meta, changed = (
            extraction_worker._apply_authoritative_extraction_updates(
                state_json,
                state_meta,
                [("state", "problem.one_line", "Manual reporting is slow.")],
            )
        )

        self.assertFalse(changed)
        self.assertEqual(next_state_json, state_json)
        self.assertEqual(next_state_meta, state_meta)

    def test_apply_authoritative_extraction_updates_refreshes_unknown_answer_meta(self) -> None:
        state_json = {"problem": {"one_line": "Manual reporting is slow."}}
        state_meta = {
            "pending_confirm": {},
            "answer_meta": {
                "problem.one_line": {
                    "resolution_status": "unknown",
                    "claim_type": "hypothesis",
                    "evidence_level": "E0",
                    "source": "user",
                    "updated_at": "2026-04-04T12:00:00Z",
                }
            },
        }

        next_state_json, next_state_meta, changed = (
            extraction_worker._apply_authoritative_extraction_updates(
                state_json,
                state_meta,
                [("state", "problem.one_line", "Manual reporting is slow.")],
            )
        )

        self.assertTrue(changed)
        self.assertEqual(next_state_json["problem"]["one_line"], "Manual reporting is slow.")
        self.assertEqual(
            next_state_meta["answer_meta"]["problem.one_line"]["resolution_status"],
            "answered",
        )

    def test_apply_authoritative_extraction_backfills_unknown_idea_raw(self) -> None:
        state_json = {"problem_user": {"idea": {"raw": "unknown"}}}
        state_meta = {
            "pending_confirm": {},
            "answer_meta": {
                "problem_user.idea.raw": {
                    "resolution_status": "unknown",
                    "claim_type": "hypothesis",
                    "evidence_level": "E0",
                    "source": "user",
                    "updated_at": "2026-04-04T12:00:00Z",
                }
            },
        }

        next_state_json, next_state_meta, changed = (
            extraction_worker._apply_authoritative_extraction_updates(
                state_json,
                state_meta,
                [
                    (
                        "state",
                        "problem.one_line",
                        "Product teams cannot turn scattered interview notes into an evidence-backed MVP priority problem.",
                    )
                ],
            )
        )

        self.assertTrue(changed)
        self.assertEqual(
            next_state_json["problem_user"]["idea"]["raw"],
            "Product teams cannot turn scattered interview notes into an evidence-backed MVP priority problem.",
        )
        self.assertEqual(
            next_state_meta["answer_meta"]["problem_user.idea.raw"][
                "resolution_status"
            ],
            "answered",
        )

    def test_apply_authoritative_extraction_updates_updates_pending_confirm_when_needed(self) -> None:
        state_json = {"problem": {"one_line": "Manual reporting is slow."}}
        state_meta = {"pending_confirm": {}}

        next_state_json, next_state_meta, changed = (
            extraction_worker._apply_authoritative_extraction_updates(
                state_json,
                state_meta,
                [
                    (
                        "pending",
                        "market_strategy.uvp.one_line",
                        "Close faster with audit-ready workflows.",
                    )
                ],
            )
        )

        self.assertTrue(changed)
        self.assertEqual(next_state_json["problem"]["one_line"], "Manual reporting is slow.")
        pending_value = next_state_meta["pending_confirm"]["market_strategy"]["uvp"]["one_line"]
        self.assertEqual(
            pending_value["value"],
            "Close faster with audit-ready workflows.",
        )
        self.assertEqual(pending_value["source"], "ai")
        self.assertEqual(pending_value["evidence_level"], "E0")

    def test_apply_authoritative_extraction_updates_preserves_optional_meta(self) -> None:
        state_json: dict = {}
        state_meta: dict = {}

        _, next_state_meta, changed = extraction_worker._apply_authoritative_extraction_updates(
            state_json,
            state_meta,
            [
                (
                    "state",
                    "market_strategy.business_model.initial_price",
                    {
                        "value": "$49/month",
                        "claim_type": "estimate",
                        "evidence_level": "E2",
                        "resolution_status": "partial",
                    },
                )
            ],
        )

        self.assertTrue(changed)
        self.assertEqual(
            next_state_meta["answer_meta"][
                "market_strategy.business_model.initial_price"
            ]["claim_type"],
            "estimate",
        )
        self.assertEqual(
            next_state_meta["answer_meta"][
                "market_strategy.business_model.initial_price"
            ]["evidence_level"],
            "E2",
        )
        self.assertEqual(
            next_state_meta["answer_meta"][
                "market_strategy.business_model.initial_price"
            ]["resolution_status"],
            "partial",
        )

    def test_apply_authoritative_extraction_updates_canonicalizes_market_type(self) -> None:
        state_json: dict = {}
        state_meta: dict = {}

        next_state_json, _, changed = extraction_worker._apply_authoritative_extraction_updates(
            state_json,
            state_meta,
            [
                (
                    "state",
                    "target_user.market_type_inferred",
                    {"value": "B2B SaaS"},
                )
            ],
        )

        self.assertTrue(changed)
        self.assertEqual(next_state_json["target_user"]["market_type_inferred"], "B2B")

    def test_apply_authoritative_extraction_updates_infers_market_type_from_target_text(self) -> None:
        state_json: dict = {}
        state_meta: dict = {}

        next_state_json, _, changed = extraction_worker._apply_authoritative_extraction_updates(
            state_json,
            state_meta,
            [
                (
                    "state",
                    "target_user.core",
                    "Heads of Product at 20-200 person B2B SaaS companies",
                )
            ],
        )

        self.assertTrue(changed)
        self.assertEqual(next_state_json["target_user"]["market_type_inferred"], "B2B")

    def test_target_user_fallback_extracts_core_and_priority_segment(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "target_user.core",
                "target_user.priority_segment",
                "target_user.market_type_inferred",
            ],
            {},
            (
                "P0 segment: university incubator program managers who support "
                "early-stage software founder teams. Market type: B2B."
            ),
        )

        self.assertEqual(
            remapped["target_user.core"],
            "university incubator program managers who support early-stage software founder teams",
        )
        self.assertEqual(
            remapped["target_user.priority_segment"],
            remapped["target_user.core"],
        )

    def test_impact_fallback_matches_sync_preview_output(self) -> None:
        question_detail = {
            "schema_paths": [
                "impact.time_impact",
                "impact.money_impact",
            ],
        }
        answer = (
            "Time wasted: 3 hours per week\n"
            "Money impact: $500 lost revenue per month"
        )

        sync_result = sync_extraction.prepare_extraction_updates(
            question_detail,
            {},
            "problem",
            answer,
        )
        worker_result = extraction_worker._prepare_authoritative_extraction_updates(
            question_detail["schema_paths"],
            {},
            "problem",
            answer,
        )

        self.assertEqual(worker_result, sync_result)
        self.assertEqual(
            worker_result,
            (
                ["impact.time_impact", "impact.money_impact"],
                [
                    ("state", "impact.time_impact", "3 hours per week"),
                    (
                        "state",
                        "impact.money_impact",
                        "$500 lost revenue per month",
                    ),
                ],
            ),
        )

    def test_sensitive_data_fallback_extracts_data_types_and_compliance(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.security_compliance.data_types",
                "tech_execution.security_compliance.compliance_requirements",
            ],
            {},
            (
                "Data handled: personal info such as user email/name, project text, "
                "mentor comments, and AI-generated summaries. No money, health, "
                "children data, or payment data in MVP. EU users are possible, "
                "so GDPR-style deletion/export and clear consent matter."
            ),
        )

        self.assertIn("personal info", remapped["tech_execution.security_compliance.data_types"])
        self.assertIn(
            "GDPR-style",
            remapped["tech_execution.security_compliance.compliance_requirements"],
        )

    def test_compliance_plan_fallback_extracts_natural_labels(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.security_compliance.audit_requirements",
                "tech_execution.security_compliance.compliance_milestones",
                "tech_execution.security_compliance.data_retention_policy",
            ],
            {},
            (
                "A) Required audits/certs: no formal certification for first "
                "design pilots, but GDPR-style DPA/security checklist first. "
                "B) Retention/deletion: keep workspace data while active, "
                "support export/delete on request, and delete inactive pilot "
                "projects after 12 months unless renewed. C) First milestone: "
                "technical founder owns a DPA/security checklist and "
                "deletion/export workflow before paid pilots in Q3."
            ),
        )

        self.assertIn(
            "GDPR-style",
            remapped["tech_execution.security_compliance.audit_requirements"],
        )
        self.assertIn(
            "Q3",
            remapped["tech_execution.security_compliance.compliance_milestones"],
        )
        self.assertIn(
            "12 months",
            remapped["tech_execution.security_compliance.data_retention_policy"],
        )

    def test_ai_quality_fallback_extracts_metrics_monitoring_and_guardrails(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.data_ai_scalability.model_quality_metrics",
                "tech_execution.data_ai_scalability.monitoring_feedback_loop",
                "tech_execution.data_ai_scalability.fallback_guardrails",
            ],
            {},
            (
                "A) Good output: summaries match confirmed facts and flag unknowns. "
                "B) Quality review: compare extracted fields to user answers weekly. "
                "C) Fallbacks/guardrails: deterministic extraction, timeouts, and manual review."
            ),
        )

        self.assertIn(
            "summaries match confirmed facts",
            remapped["tech_execution.data_ai_scalability.model_quality_metrics"],
        )
        self.assertIn(
            "compare extracted fields",
            remapped["tech_execution.data_ai_scalability.monitoring_feedback_loop"],
        )
        self.assertIn(
            "deterministic extraction",
            remapped["tech_execution.data_ai_scalability.fallback_guardrails"],
        )

    def test_data_scalability_fallback_extracts_s3q5_fields(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.data_ai_scalability.data_sources",
                "tech_execution.data_ai_scalability.data_volume_year1",
                "tech_execution.data_ai_scalability.growth_expectations",
                "tech_execution.data_ai_scalability.ai_usage",
                "tech_execution.data_ai_scalability.performance_expectations",
                "tech_execution.data_ai_scalability.scalability_strategy",
            ],
            {},
            (
                "A) Data sources and ownership: user-generated answers, mentor comments, "
                "and generated reports owned by the workspace.\n"
                "B) Year-1 data volume: 20-50 pilot programs and hundreds of reports; "
                "growth could be 5-10x if pilots convert.\n"
                "C) AI usage: core for extraction, summaries, and reports.\n"
                "D) Performance expectations: chat under 10 seconds and uptime around 99%.\n"
                "E) 10x scaling strategy: queue report tasks, cache artifacts, index tables, "
                "and scale API/worker processes separately."
            ),
        )

        self.assertIn(
            "user-generated answers",
            remapped["tech_execution.data_ai_scalability.data_sources"],
        )
        self.assertIn(
            "20-50 pilot programs",
            remapped["tech_execution.data_ai_scalability.data_volume_year1"],
        )
        self.assertIn(
            "5-10x",
            remapped["tech_execution.data_ai_scalability.growth_expectations"],
        )
        self.assertIn(
            "core for extraction",
            remapped["tech_execution.data_ai_scalability.ai_usage"],
        )
        self.assertIn(
            "under 10 seconds",
            remapped["tech_execution.data_ai_scalability.performance_expectations"],
        )
        self.assertIn(
            "queue report tasks",
            remapped["tech_execution.data_ai_scalability.scalability_strategy"],
        )

    def test_product_scope_fallback_extracts_s3q1_fields(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.product_scope.current_status",
                "tech_execution.product_scope.mvp_definition",
                "tech_execution.product_scope.core_user_journeys",
                "tech_execution.product_scope.non_functional_priorities",
            ],
            {},
            (
                "A) Current status: working prototype.\n"
                "B) MVP boundaries: in MVP are project workspace and DVF report. "
                "Not in MVP are CRM and billing.\n"
                "C) Core journeys: 1) manager creates project; 2) mentor reviews context; "
                "3) team generates report.\n"
                "D) NFR priorities: security because of cohort data; latency because chat "
                "should feel responsive."
            ),
        )

        self.assertIn(
            "working prototype",
            remapped["tech_execution.product_scope.current_status"],
        )
        self.assertIn(
            "project workspace",
            remapped["tech_execution.product_scope.mvp_definition"],
        )
        self.assertEqual(
            len(remapped["tech_execution.product_scope.core_user_journeys"]),
            3,
        )
        self.assertIn(
            "security",
            remapped["tech_execution.product_scope.non_functional_priorities"],
        )

    def test_architecture_components_fallback_trims_reason(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            ["tech_execution.architecture.high_level_components"],
            {},
            (
                "Architecture style: modular monolith for the MVP. Components: "
                "Next.js web client, FastAPI API, Postgres database, prompt "
                "runtime, background report worker, and email/auth service. "
                "Reason: the team can ship faster while keeping clear module "
                "boundaries."
            ),
        )

        self.assertEqual(
            remapped["tech_execution.architecture.high_level_components"],
            [
                "Next.js web client",
                "FastAPI API",
                "Postgres database",
                "prompt runtime",
                "background report worker",
                "email/auth service",
            ],
        )

    def test_data_access_fallback_extracts_rights_access_label(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            ["tech_execution.data_ai_scalability.data_access_rights"],
            {},
            (
                "A) Required data: founder-entered project context, staged "
                "answers, mentor edits, generated summaries/reports, and "
                "organization membership. Rights/access: user-generated and "
                "organization-approved data entered into the workspace.\n"
                "B) Collection/refresh: collected during chat and review screens.\n"
                "C) Quality gaps: vague founder answers and inconsistent terminology."
            ),
        )

        self.assertEqual(
            remapped["tech_execution.data_ai_scalability.data_access_rights"],
            "user-generated and organization-approved data entered into the workspace",
        )

    def test_dependencies_and_risks_fallback_extracts_blocking_fields(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.dependencies.key_integrations",
                "tech_execution.roadmap_risks.top_technical_risks",
            ],
            {},
            (
                "Key integrations/APIs: OpenAI-compatible LLM provider, managed "
                "Postgres, email delivery provider, web/app hosting, and later "
                "Stripe for billing. Top technical risks: LLM latency/cost, email "
                "delivery reliability, and report traceability. Mitigation: "
                "provider abstraction and regression tests."
            ),
        )

        self.assertIn(
            "managed Postgres",
            remapped["tech_execution.dependencies.key_integrations"],
        )
        self.assertIn(
            "report traceability",
            remapped["tech_execution.roadmap_risks.top_technical_risks"],
        )

    def test_top_risks_and_experiments_label_extracts_risks(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            ["tech_execution.roadmap_risks.top_technical_risks"],
            {},
            (
                "A) Team: one technical founder/full-stack engineer. "
                "B) Process: lightweight Kanban and regression tests. "
                "C) 6-12 month roadmap: stabilize core interview/report flow. "
                "D) Top risks and experiments: LLM consistency risk tested "
                "with fixture suites; Stage Gate transition risk tested with "
                "full-path recordings; university privacy/procurement risk "
                "tested with one lightweight DPA/security review."
            ),
        )

        self.assertTrue(
            any(
                "Stage Gate transition risk" in risk
                for risk in remapped[
                    "tech_execution.roadmap_risks.top_technical_risks"
                ]
            ),
        )

    def test_top_tech_worries_label_extracts_risks(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            ["tech_execution.roadmap_risks.top_technical_risks"],
            {},
            (
                "Top tech worries: LLM summaries may miss or invent details, "
                "Stage Gate may advance with incomplete context, reports may "
                "lose traceability to confirmed answers, university users may "
                "expect stronger privacy controls, and chat latency may feel "
                "too slow. Mitigation: confirmed context review, deterministic "
                "stage-transition tests, prompt traces, provider fallbacks, "
                "and visible progress/retry states."
            ),
        )

        self.assertTrue(
            any(
                "Stage Gate" in risk
                for risk in remapped[
                    "tech_execution.roadmap_risks.top_technical_risks"
                ]
            ),
        )

    def test_risk_mitigation_plan_label_extracts_plan(self) -> None:
        remapped = extraction_worker._apply_extraction_fallbacks(
            [
                "tech_execution.roadmap_risks.top_technical_risks",
                "tech_execution.roadmap_risks.risk_mitigation_plan",
            ],
            {},
            (
                "Top technical risks: LLM consistency, stage transition bugs, "
                "and privacy review delays. Risk mitigation plan: fixture-based "
                "regression tests, stage-gate smoke recordings, and a lightweight "
                "DPA/security checklist before pilots."
            ),
        )

        self.assertIn(
            "stage-gate smoke recordings",
            remapped["tech_execution.roadmap_risks.risk_mitigation_plan"],
        )


if __name__ == "__main__":
    unittest.main()
