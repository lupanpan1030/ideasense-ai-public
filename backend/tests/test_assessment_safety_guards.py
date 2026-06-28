import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.api import deps  # noqa: E402
from app.api.routes import assessments  # noqa: E402
from app.services import (  # noqa: E402
    assessment_summaries,
    project_permissions,
    stage_confirmations,
    stage_drafts,
    stage_finalize_jobs,
    stage_summary_jobs,
    stage_verifications,
    verification_refresh,
)
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths  # noqa: E402


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _route_function_source(relative_path: str, function_name: str) -> str:
    source = (BACKEND_ROOT / relative_path).read_text()
    marker = f"async def {function_name}"
    start = source.index(marker)
    next_route = source.find("\n\n@router.", start + 1)
    end = next_route if next_route != -1 else len(source)
    return source[start:end]


class _Result:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def first(self) -> dict | None:
        return self._row


class _Session:
    def __init__(self, row: dict | None) -> None:
        self._row = row
        self.calls: list[dict] = []

    async def execute(self, _statement, params=None) -> _Result:
        self.calls.append(params or {})
        return _Result(self._row)


class _RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None) -> _Result:  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return _Result(None)


class ProjectMutationAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_project_mutation_service_returns_bool(self) -> None:
        allowed_session = _Session({"?column?": 1})
        denied_session = _Session(None)

        self.assertTrue(
            await project_permissions.can_mutate_project(
                allowed_session,
                project_id="project-1",
                org_id="org-1",
                user_id="user-1",
            )
        )
        self.assertFalse(
            await project_permissions.can_mutate_project(
                denied_session,
                project_id="project-1",
                org_id="org-1",
                user_id="mentor-1",
            )
        )

    async def test_assessment_route_does_not_redefine_project_mutation_access(
        self,
    ) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()

        self.assertNotIn("def _require_project_mutation_access", route_source)
        self.assertIn("prepare_project_stage_draft_workflow", route_source)
        self.assertIn("confirm_project_report_stage_workflow", route_source)


class AssessmentRouteAccessContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_system_rls_context_sets_user_org_and_system_actor(self) -> None:
        session = _RecordingSession()

        await deps.set_system_rls_context(
            session,
            user_id="user-1",
            org_id="org-1",
        )

        self.assertEqual(
            [params for _statement, params in session.calls],
            [
                {"user_id": "user-1"},
                {"org_id": "org-1"},
                {"actor_type": "system"},
            ],
        )
        self.assertIn("set_config('app.user_id'", session.calls[0][0])
        self.assertIn("set_config('app.org_id'", session.calls[1][0])
        self.assertIn("set_config('app.actor_type'", session.calls[2][0])

    async def test_verified_org_context_uses_dependency_owner(self) -> None:
        session = _RecordingSession()
        with (
            patch.object(deps, "set_system_actor", new_callable=AsyncMock) as set_actor,
            patch.object(
                deps,
                "is_email_verified",
                new_callable=AsyncMock,
                return_value=True,
            ) as email_verified,
            patch.object(
                deps,
                "resolve_org_membership",
                new_callable=AsyncMock,
                return_value={"org_id": "org-1"},
            ) as resolve_membership,
        ):
            access = await deps.resolve_verified_org_context(
                session,
                user_id="user-1",
                explicit_org_id="org-1",
                email_detail="Verify your email.",
                no_org_detail="No active organization membership.",
            )

        self.assertEqual(access.org_id, "org-1")
        self.assertTrue(access.email_verified)
        set_actor.assert_awaited_once_with(session)
        email_verified.assert_awaited_once_with(session, user_id="user-1")
        resolve_membership.assert_awaited_once_with(
            session,
            user_id="user-1",
            explicit_org_id="org-1",
        )

    def test_assessment_route_uses_access_context_dependency_owner(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()

        self.assertIn("require_verified_system_actor", route_source)
        self.assertIn("resolve_verified_org_context", route_source)
        self.assertIn("set_system_rls_context", route_source)
        self.assertNotIn("is_email_verified", route_source)
        self.assertNotIn("resolve_org_membership", route_source)
        self.assertNotIn("SELECT set_config('app.user_id'", route_source)
        self.assertNotIn("SELECT set_config('app.org_id'", route_source)


class StageDraftCacheTests(unittest.TestCase):
    def test_stage_confirmation_imports_stage_gate_filter(self) -> None:
        self.assertIs(
            stage_confirmations.filter_stage_blocking_missing_paths,
            filter_stage_blocking_missing_paths,
        )

    def test_stage_draft_cache_reuses_matching_locale_only(self) -> None:
        self.assertTrue(
            stage_drafts.can_reuse_stage_draft_cache(
                existing_summary="Summary",
                existing_version=3,
                state_version=3,
                existing_draft_locale="en",
                requested_output_locale="en",
            )
        )
        self.assertFalse(
            stage_drafts.can_reuse_stage_draft_cache(
                existing_summary="Summary",
                existing_version=3,
                state_version=3,
                existing_draft_locale="en",
                requested_output_locale="zh",
            )
        )

    def test_stage_draft_cache_treats_missing_locale_as_default_only(self) -> None:
        self.assertTrue(
            stage_drafts.can_reuse_stage_draft_cache(
                existing_summary="Summary",
                existing_version=3,
                state_version=3,
                existing_draft_locale=None,
                requested_output_locale=assessments.DEFAULT_OUTPUT_LOCALE,
            )
        )
        self.assertFalse(
            stage_drafts.can_reuse_stage_draft_cache(
                existing_summary="Summary",
                existing_version=3,
                state_version=3,
                existing_draft_locale=None,
                requested_output_locale="zh",
            )
        )


class StageSummaryBackgroundStatusTests(unittest.TestCase):
    def test_stage_summary_job_idempotency_key_includes_context_and_locale(self) -> None:
        key = stage_summary_jobs.stage_summary_job_idempotency_key(
            "project-1",
            "Problem",
            7,
            "zh",
        )

        self.assertEqual(key, "stage-summary:project-1:problem:7:zh")

    def test_stage_summary_status_prefers_ready_summary(self) -> None:
        self.assertEqual(
            stage_drafts.resolve_stage_summary_generation_status(
                has_ready_summary=True,
                job_status="failed",
            ),
            "ready",
        )

    def test_stage_summary_status_maps_queue_lifecycle(self) -> None:
        cases = {
            "queued": "queued",
            "running": "running",
            " Running ": "running",
            "failed": "failed",
            "cancelled": "failed",
            " CANCELLED ": "failed",
            "succeeded": "failed",
            None: "queued",
        }
        for job_status, expected in cases.items():
            with self.subTest(job_status=job_status):
                self.assertEqual(
                    stage_drafts.resolve_stage_summary_generation_status(
                        has_ready_summary=False,
                        job_status=job_status,
                    ),
                    expected,
                )

    def test_stage_summary_status_reports_stale_before_job_status(self) -> None:
        self.assertEqual(
            stage_drafts.resolve_stage_summary_generation_status(
                has_ready_summary=False,
                job_status="running",
                stale=True,
            ),
            "stale",
                )


class StageFinalizeJobTests(unittest.TestCase):
    def test_stage_finalize_idempotency_key_includes_context_and_locale(self) -> None:
        key = stage_finalize_jobs.stage_finalize_idempotency_key(
            "project-1",
            "Market",
            8,
            "zh",
        )

        self.assertEqual(key, "stage-finalize:project-1:market:8:zh")


class AssessmentSourceGuardTests(unittest.TestCase):
    def test_question_instance_insert_is_idempotent(self) -> None:
        source = (BACKEND_ROOT / "app/services/stage_confirmations.py").read_text()

        self.assertIn(
            "ON CONFLICT (project_id, question_bank_question_id)",
            source,
        )
        self.assertIn("WHERE deleted_at IS NULL", source)

    def test_report_confirmation_rechecks_stage_under_lock(self) -> None:
        source = (BACKEND_ROOT / "app/services/report_confirmations.py").read_text()

        self.assertIn("SELECT current_stage, stage_status", source)
        self.assertIn("FOR UPDATE", source)

    def test_report_and_verification_llm_calls_use_prompt_runtime(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()
        self.assertNotIn("call_llm(", route_source)
        for prompt_execution_symbol in (
            "execute_prompt_task",
            "PromptContextBuilder",
            "PromptMutationClass",
            "render_prompt_messages",
        ):
            self.assertNotIn(prompt_execution_symbol, route_source)
        for stale_helper in (
            "_build_summary_prompt",
            "_build_project_description_prompt",
            "_generate_stage_summary",
            "_generate_project_description",
            "_generate_structured_report",
        ):
            self.assertNotIn(f"async def {stale_helper}", route_source)

        for relative_path in (
            "app/services/stage_summary_worker_handler.py",
            "app/services/stage_finalize_worker_handler.py",
            "app/services/report_generation_worker_handler.py",
            "app/services/verification/judge.py",
        ):
            source = (BACKEND_ROOT / relative_path).read_text()
            self.assertNotIn("call_llm(", source)
            self.assertIn("execute_prompt_task", source)

    def test_admin_prompt_template_helpers_use_service_owner(self) -> None:
        service_source = (
            BACKEND_ROOT / "app/services/prompt_templates.py"
        ).read_text()
        self.assertIn("def prompt_template_row_to_payload", service_source)
        self.assertIn("async def resolve_unique_prompt_template_version", service_source)
        self.assertIn("async def create_prompt_template_revision", service_source)

        for route_path in (
            "app/api/routes/admin_prompt_templates.py",
            "app/api/routes/platform_admin.py",
        ):
            route_source = (BACKEND_ROOT / route_path).read_text()
            self.assertNotIn("def _row_to_prompt_template", route_source)
            self.assertNotIn("async def _resolve_unique_version", route_source)

        for route_path, function_name in (
            ("app/api/routes/admin_prompt_templates.py", "create_prompt_template"),
            ("app/api/routes/platform_admin.py", "create_global_prompt_template"),
        ):
            create_source = _route_function_source(route_path, function_name)
            self.assertNotIn("INSERT INTO prompt_templates", create_source)
            self.assertNotIn("UPDATE prompt_templates", create_source)

    def test_admin_question_bank_draft_create_uses_service_owner(self) -> None:
        service_source = (
            BACKEND_ROOT / "app/services/question_bank_drafts.py"
        ).read_text()
        self.assertIn("def normalize_question_bank_key", service_source)
        self.assertIn("async def create_question_bank_draft", service_source)

        route_source = (
            BACKEND_ROOT / "app/api/routes/admin_question_banks.py"
        ).read_text()
        self.assertIn("create_question_bank_draft", route_source)

        create_source = _route_function_source(
            "app/api/routes/admin_question_banks.py",
            "create_draft",
        )
        self.assertNotIn("INSERT INTO question_bank_versions", create_source)
        self.assertNotIn("INSERT INTO question_bank_questions", create_source)
        self.assertNotIn("UPDATE question_bank_versions", create_source)

    def test_admin_question_bank_draft_publish_uses_service_owner(self) -> None:
        service_source = (
            BACKEND_ROOT / "app/services/question_bank_publish.py"
        ).read_text()
        self.assertIn("async def publish_question_bank_draft", service_source)

        route_source = (
            BACKEND_ROOT / "app/api/routes/admin_question_banks.py"
        ).read_text()
        self.assertIn("publish_question_bank_draft", route_source)
        self.assertNotIn("def _build_raw_json", route_source)
        self.assertNotIn("def _question_to_yaml_dict", route_source)

        publish_source = _route_function_source(
            "app/api/routes/admin_question_banks.py",
            "publish_draft",
        )
        for pattern in (
            "INSERT INTO question_bank_versions",
            "UPDATE question_bank_versions",
            "DELETE FROM question_bank_versions",
            "INSERT INTO question_bank_questions",
            "UPDATE question_bank_questions",
            "DELETE FROM question_bank_questions",
            "yaml.safe_dump",
            "hashlib.sha256",
        ):
            self.assertNotIn(pattern, publish_source)

    def test_admin_question_bank_draft_import_uses_service_owner(self) -> None:
        service_source = (
            BACKEND_ROOT / "app/services/question_bank_draft_imports.py"
        ).read_text()
        self.assertIn("async def import_question_bank_draft_yaml", service_source)
        self.assertIn("async def import_question_bank_draft_json", service_source)

        route_source = (
            BACKEND_ROOT / "app/api/routes/admin_question_banks.py"
        ).read_text()
        self.assertIn("import_question_bank_draft_yaml", route_source)
        self.assertIn("import_question_bank_draft_json", route_source)
        self.assertNotIn("import yaml", route_source)
        self.assertNotIn("async def _apply_question_import", route_source)
        self.assertNotIn("def _iter_questions", route_source)
        self.assertNotIn("def _build_question_payload", route_source)
        self.assertNotIn("def _normalize_mode", route_source)

        for function_name in ("import_draft", "import_draft_json"):
            import_source = _route_function_source(
                "app/api/routes/admin_question_banks.py",
                function_name,
            )
            for pattern in (
                "INSERT INTO question_bank_versions",
                "UPDATE question_bank_versions",
                "DELETE FROM question_bank_versions",
                "INSERT INTO question_bank_questions",
                "UPDATE question_bank_questions",
                "DELETE FROM question_bank_questions",
                "yaml.safe_load",
                "yaml.safe_dump",
                "json.loads",
            ):
                self.assertNotIn(pattern, import_source)

    def test_stage_confirm_consumes_ready_draft_instead_of_generating_summary(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()
        confirm_source = route_source[route_source.index("async def confirm_stage") :]
        service_source = (
            BACKEND_ROOT / "app/services/stage_confirmations.py"
        ).read_text()

        self.assertNotIn(
            "summary_markdown, summary_model = await _generate_stage_summary",
            confirm_source,
        )
        self.assertIn(
            "Stage summary is still being prepared. Refresh and try again.",
            service_source,
        )
        self.assertIn("prepare_stage_confirmation_workflow", confirm_source)

    def test_assessment_read_models_use_service_owner(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()
        service_source = (
            BACKEND_ROOT / "app/services/assessment_summaries.py"
        ).read_text()

        self.assertIn("fetch_stage_summary_read_models", route_source)
        self.assertIn("fetch_project_stage_verification_read_models", route_source)
        self.assertIn("async def fetch_stage_summary_read_models", service_source)
        self.assertIn(
            "async def fetch_project_stage_verification_read_models",
            service_source,
        )
        self.assertNotIn("project_stage_verification_claims", route_source)

    def test_stage_summary_background_job_is_registered_in_route_and_worker(self) -> None:
        draft_source = (BACKEND_ROOT / "app/services/stage_drafts.py").read_text()
        worker_source = (BACKEND_ROOT / "app/worker.py").read_text()
        handler_source = (
            BACKEND_ROOT / "app/services/stage_summary_worker_handler.py"
        ).read_text()
        job_source = (BACKEND_ROOT / "app/services/stage_summary_jobs.py").read_text()

        self.assertIn('STAGE_SUMMARY_JOB_TYPE = "stage_summary_v0"', job_source)
        self.assertIn("enqueue_stage_summary_job", draft_source)
        self.assertIn("STAGE_SUMMARY_JOB_TYPE", worker_source)
        self.assertIn("run_stage_summary_v0", worker_source)
        self.assertIn("async def run_stage_summary_v0", handler_source)

    def test_stage_finalize_background_job_is_registered_in_route_and_worker(self) -> None:
        service_source = (
            BACKEND_ROOT / "app/services/stage_confirmations.py"
        ).read_text()
        worker_source = (BACKEND_ROOT / "app/worker.py").read_text()
        handler_source = (
            BACKEND_ROOT / "app/services/stage_finalize_worker_handler.py"
        ).read_text()
        job_source = (BACKEND_ROOT / "app/services/stage_finalize_jobs.py").read_text()

        self.assertIn('STAGE_FINALIZE_JOB_TYPE = "stage_finalize_v0"', job_source)
        self.assertIn("enqueue_stage_finalize_job", service_source)
        self.assertIn("run_stage_finalize_v0", worker_source)
        self.assertIn("async def run_stage_finalize_v0", handler_source)
        self.assertIn("STAGE_FINALIZE_JOB_TYPE", worker_source)

    def test_report_generation_background_job_is_registered_in_route_and_worker(self) -> None:
        stage_confirm_source = (
            BACKEND_ROOT / "app/services/stage_confirmations.py"
        ).read_text()
        report_confirm_source = (
            BACKEND_ROOT / "app/services/report_confirmations.py"
        ).read_text()
        worker_source = (BACKEND_ROOT / "app/worker.py").read_text()
        handler_source = (
            BACKEND_ROOT / "app/services/report_generation_worker_handler.py"
        ).read_text()

        self.assertIn(
            'REPORT_GENERATION_JOB_TYPE = "report_generation_v0"',
            (BACKEND_ROOT / "app/services/report_jobs.py").read_text(),
        )
        self.assertIn("enqueue_report_generation_job", stage_confirm_source)
        self.assertIn("enqueue_report_generation_job", report_confirm_source)
        self.assertIn("run_report_generation_v0", worker_source)
        self.assertIn("async def run_report_generation_v0", handler_source)
        self.assertIn("REPORT_GENERATION_JOB_TYPE", worker_source)

    def test_stage_confirm_defers_post_confirm_ai_work(self) -> None:
        source = (BACKEND_ROOT / "app/services/stage_confirmations.py").read_text()
        confirm_source = source[
            source.index("async def commit_stage_confirmation_workflow") :
        ]

        self.assertIn("enqueue_report_generation_job", confirm_source)
        self.assertIn("enqueue_stage_finalize_job", confirm_source)
        self.assertNotIn("await generate_dvf_scoring(", confirm_source)
        self.assertNotIn("await verify_report_inputs(", confirm_source)
        self.assertNotIn("await _build_qa_digests_from_messages(", confirm_source)
        self.assertNotIn("await _run_question_rewrite(", confirm_source)

    def test_tech_confirm_enqueues_report_before_stage_finalize(self) -> None:
        source = (BACKEND_ROOT / "app/services/stage_confirmations.py").read_text()
        confirm_source = source[
            source.index("async def commit_stage_confirmation_workflow") :
        ]

        self.assertLess(
            confirm_source.index("enqueue_report_generation_job"),
            confirm_source.index("enqueue_stage_finalize_job"),
        )


class ChatVerificationEnqueueGuardTests(unittest.TestCase):
    def test_chat_sync_extraction_preview_uses_service_owner(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/chat.py").read_text()
        evaluation_source = (
            BACKEND_ROOT / "app/services/chat_turn_evaluation.py"
        ).read_text()
        service_source = (
            BACKEND_ROOT / "app/services/chat_sync_extraction_preview.py"
        ).read_text()

        self.assertIn("def build_sync_extraction_preview", service_source)
        self.assertIn("chat_sync_extraction_preview", evaluation_source)
        self.assertNotIn("answer_extraction_worker_handler", service_source)

        for stale_helper in (
            "_build_sync_extraction_preview",
            "_prepare_extraction_updates",
            "_apply_extraction_updates_to_state",
            "_apply_extraction_fallbacks",
            "_update_ai_assisted_paths",
            "_canonicalize_market_type_fields",
            "_infer_frequency_from_answer",
            "_should_soft_pass",
        ):
            self.assertNotIn(f"def {stale_helper}", route_source)
            self.assertNotIn(f"async def {stale_helper}", route_source)

    def test_sync_extraction_does_not_suppress_verification_job(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/chat.py").read_text()
        service_source = (
            BACKEND_ROOT / "app/services/chat_background_jobs.py"
        ).read_text()
        verify_index = service_source.index("enqueue_answer_question_verification_job")
        guard_window = service_source[max(0, verify_index - 1400) : verify_index]

        self.assertNotIn("not did_sync_extract", guard_window)
        self.assertIn("enqueue_chat_pass_background_jobs", route_source)
        self.assertNotIn("enqueue_answer_question_verification_job", route_source)


class VerificationStatusResolverTests(unittest.TestCase):
    def test_disabled_verification_is_not_a_provider_gap(self) -> None:
        with patch.object(assessment_summaries, "verification_enabled", return_value=False):
            self.assertIsNone(
                assessment_summaries.resolve_verification_provider_unavailable_reason()
            )

    def test_assessment_route_does_not_redefine_verification_provider_gap(self) -> None:
        route_source = (BACKEND_ROOT / "app/api/routes/assessments.py").read_text()

        self.assertNotIn("_verification_provider_unavailable_reason", route_source)
        self.assertIs(
            verification_refresh.resolve_verification_provider_unavailable_reason,
            assessment_summaries.resolve_verification_provider_unavailable_reason,
        )

    def test_pending_job_reports_verifying(self) -> None:
        self.assertEqual(
            stage_verifications.resolve_question_verification_status(
                pending=True,
                stale=False,
                latest_batch=[],
                failed=False,
                provider_unavailable_reason=None,
            ),
            "verifying",
        )

    def test_stale_result_reports_stale_before_failed(self) -> None:
        self.assertEqual(
            stage_verifications.resolve_question_verification_status(
                pending=False,
                stale=True,
                latest_batch=[],
                failed=True,
                provider_unavailable_reason=None,
            ),
            "stale",
        )

    def test_contradicted_claim_takes_priority_over_supported(self) -> None:
        self.assertEqual(
            stage_verifications.resolve_question_verification_status(
                pending=False,
                stale=False,
                latest_batch=[
                    {"verdict": "supported"},
                    {"verdict": "contradicted"},
                ],
                failed=False,
                provider_unavailable_reason=None,
            ),
            "contradicted",
        )

    def test_provider_gap_is_not_reported_as_no_evidence(self) -> None:
        self.assertEqual(
            stage_verifications.resolve_question_verification_status(
                pending=False,
                stale=False,
                latest_batch=[],
                failed=False,
                provider_unavailable_reason="missing_search_provider_key",
            ),
            "provider_unavailable",
        )

    def test_not_applicable_batch_reports_not_applicable(self) -> None:
        self.assertEqual(
            stage_verifications.resolve_question_verification_status(
                pending=False,
                stale=False,
                latest_batch=[
                    {"rationale": "Not applicable for an internal workflow."},
                    {"rationale": "User-reported context only."},
                ],
                failed=False,
                provider_unavailable_reason=None,
            ),
            "not_applicable",
        )

    def test_collect_sources_deduplicates_and_limits(self) -> None:
        sources = stage_verifications.collect_sources_from_claims(
            [
                {
                    "sources": [
                        {"url": "https://example.com/a", "title": "A"},
                        {"url": "https://example.com/a", "title": "A duplicate"},
                        {"domain": "example.org", "title": "B"},
                    ]
                },
                {"sources": [{"title": "C"}]},
            ],
            limit=2,
        )

        self.assertEqual(
            sources,
            [
                {"url": "https://example.com/a", "title": "A"},
                {"domain": "example.org", "title": "B"},
            ],
        )

    def test_increment_summary_counts_provider_gap_as_no_evidence(self) -> None:
        summary = assessments.StageVerificationSummary(stage="problem")

        stage_verifications.increment_verification_summary(
            summary,
            "provider_unavailable",
        )

        self.assertEqual(summary.total, 1)
        self.assertEqual(summary.provider_unavailable, 1)
        self.assertEqual(summary.no_evidence, 1)


if __name__ == "__main__":
    unittest.main()
