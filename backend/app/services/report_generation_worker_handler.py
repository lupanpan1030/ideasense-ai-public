from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import os
from typing import Any

from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database_async import AdminAsyncSessionLocal
from app.core.report_builder import (
    build_assessment_snapshots,
    build_report_input,
    build_report_markdown,
    build_report_payload,
    build_stage_summary_map,
    merge_report_payload,
)
from app.core.report_recovery_sections import build_report_recovery_sections
from app.core.report_sections import build_report_v2_sections
from app.core.usage_limits import enforce_report_daily_limit, record_report_usage
from app.services.diagnostics import (
    build_report_diagnosis,
    build_validation_plan,
    merge_validation_plans,
)
from app.services.localization import (
    DEFAULT_OUTPUT_LOCALE,
    OutputLocale,
    normalize_output_locale,
    normalize_summary_locale_map,
    output_language_label,
)
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
    serialize_prompt_task_trace,
)
from app.services.report_conversation_sources import fetch_report_last_user_message
from app.services.report_quality_observations import (
    persist_report_quality_observation,
)
from app.services.scoring import generate_dvf_scoring
from app.services.stage_runtime import mark_project_stage_passed_from_decision
from app.services.stage_payloads import (
    normalize_ai_assisted_map as _normalize_ai_assisted_map,
    normalize_user_edited_map as _normalize_user_edited_map,
)
from app.services.stage_transition import decide_report_confirmation_complete
from app.services.stage_transition import is_report_generation_recovery_stage
from app.services.verification import verify_report_inputs


LOCK_TTL_SEC = int(os.getenv("WORKER_LOCK_TTL_SEC", "60"))
REPORT_LOCK_TTL_SEC = int(
    os.getenv("WORKER_REPORT_LOCK_TTL_SEC", str(max(LOCK_TTL_SEC, 300)))
)
SUMMARY_STAGES = {"problem", "market", "tech"}
logger = logging.getLogger("ideasense.worker.report_generation")
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()
WorkerContextSetter = Callable[[Any, str | None], Awaitable[None]]


async def _set_report_worker_context(session, org_id: str | None = None) -> None:
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )
    if org_id:
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )


async def _commit_if_transaction_open(session) -> None:
    if session.in_transaction():
        await session.commit()


async def _touch_report_job(
    job_id: int | None,
    org_id: str | None,
    *,
    phase: str | None = None,
) -> None:
    if job_id is None or org_id is None or AdminAsyncSessionLocal is None:
        return
    async with AdminAsyncSessionLocal() as job_session:
        async with job_session.begin():
            await _set_report_worker_context(job_session, org_id)
            await job_session.execute(
                text(
                    "UPDATE background_jobs "
                    "SET payload = CASE "
                    "WHEN CAST(:phase AS text) IS NULL THEN payload "
                    "ELSE COALESCE(payload, '{}'::jsonb) "
                    "|| jsonb_build_object('phase', CAST(:phase AS text)) "
                    "END, "
                    "lock_expires_at = CASE "
                    "WHEN status = 'running' "
                    "THEN now() + (:lock_ttl * interval '1 second') "
                    "ELSE lock_expires_at "
                    "END, "
                    "updated_at = now() "
                    "WHERE id = :job_id "
                    "AND org_id = :org_id "
                    "AND deleted_at IS NULL"
                ).bindparams(bindparam("phase", type_=String)),
                {
                    "job_id": job_id,
                    "org_id": org_id,
                    "phase": phase,
                    "lock_ttl": REPORT_LOCK_TTL_SEC,
                },
            )


async def _fetch_report_qa_digests(
    session,
    assessment_ids: list[str],
) -> dict[str, list[dict[str, Any]]]:
    if not assessment_ids:
        return {}
    result = await session.execute(
        text(
            "SELECT stage, question_id, answer_summary, key_points, created_at "
            "FROM project_stage_qa_digests "
            "WHERE assessment_id IN :assessment_ids "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ).bindparams(bindparam("assessment_ids", expanding=True)),
        {"assessment_ids": assessment_ids},
    )
    digest_by_stage: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for row in result.mappings().all():
        stage = row.get("stage")
        question_id = row.get("question_id")
        if not stage or not question_id:
            continue
        key = (str(stage), str(question_id))
        if key in seen:
            continue
        seen.add(key)
        digest_by_stage.setdefault(str(stage), []).append(
            {
                "question_id": question_id,
                "answer_summary": row.get("answer_summary"),
                "key_points": row.get("key_points") or [],
            }
        )
    return digest_by_stage


async def _generate_structured_report_v0(
    session,
    report_input: dict[str, Any],
    *,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
    trace_sink: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    context = PROMPT_CONTEXT_BUILDER.final_report(
        report_input,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.REPORT_ARTIFACT,
    )
    if trace_sink is not None:
        trace_sink["final_report"] = serialize_prompt_task_trace(result)
    if not result.ok:
        return None, result.model
    return result.parsed, result.model


async def run_report_generation_v0(
    session,
    payload: dict[str, Any],
    *,
    job_id: int | None = None,
    job_org_id: str | None = None,
    set_worker_context_fn: WorkerContextSetter | None = None,
) -> None:
    project_id = payload.get("project_id")
    raw_context_version = payload.get("context_version")
    requested_by_user_id = payload.get("requested_by_user_id")
    if not project_id or raw_context_version is None or not requested_by_user_id:
        raise ValueError("Report generation payload missing identifiers.")
    try:
        context_version = int(raw_context_version)
    except (TypeError, ValueError) as exc:
        raise ValueError("Report generation payload has invalid context_version.") from exc

    output_locale = normalize_output_locale(
        payload.get("output_locale") if isinstance(payload.get("output_locale"), str) else None
    )

    org_id: str | None = None
    owner_user_id: str | None = None
    project_settings: dict[str, Any] | None = None
    project_row_payload: dict[str, Any] = {}
    state_json: dict[str, Any] = {}
    state_meta: dict[str, Any] = {}
    assessments: list[dict[str, Any]] = []
    assessment_ids: list[str] = []
    qa_digest_by_stage: dict[str, list[dict[str, Any]]] = {}
    last_user_message: str | None = None

    async with session.begin():
        if set_worker_context_fn is not None:
            await set_worker_context_fn(session, job_org_id)
        project_result = await session.execute(
            text(
                "SELECT id, org_id, owner_user_id, title, description, current_stage, "
                "stage_status, updated_at, settings "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id)},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            raise ValueError("Project not found for report generation job.")
        org_id = str(project_row.get("org_id")) if project_row.get("org_id") else None
        owner_user_id = (
            str(project_row.get("owner_user_id"))
            if project_row.get("owner_user_id")
            else None
        )
        if not org_id or not owner_user_id:
            raise ValueError("Project missing org or owner for report generation job.")

        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": owner_user_id},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )

        if project_row.get("current_stage") != "report":
            return
        if project_row.get("stage_status") not in {"awaiting_confirm", "passed"}:
            return

        project_settings = (
            project_row.get("settings")
            if isinstance(project_row.get("settings"), dict)
            else None
        )
        project_row_payload = dict(project_row)

        state_result = await session.execute(
            text(
                "SELECT state_json, state_meta, state_version "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        state_row = state_result.mappings().first()
        if not state_row:
            raise ValueError("Project state not found for report generation job.")
        current_context_version = int(state_row.get("state_version") or 0)
        if current_context_version != context_version:
            return
        state_json = state_row.get("state_json")
        if not isinstance(state_json, dict):
            state_json = {}
        state_meta = state_row.get("state_meta")
        if not isinstance(state_meta, dict):
            state_meta = {}

        existing_report_result = await session.execute(
            text(
                "SELECT id "
                "FROM project_reports "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND generated_from_state_version = :state_version "
                "AND COALESCE(NULLIF(content_json->>'artifact_locale', ''), "
                ":default_output_locale) = :output_locale "
                "AND status = 'final' "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "project_id": str(project_id),
                "org_id": org_id,
                "state_version": context_version,
                "output_locale": output_locale,
                "default_output_locale": DEFAULT_OUTPUT_LOCALE,
            },
        )
        if existing_report_result.mappings().first():
            return

        await enforce_report_daily_limit(
            session,
            user_id=str(requested_by_user_id),
        )

        assessments_result = await session.execute(
            text(
                "SELECT id, stage, draft_summary_markdown, final_summary_markdown, "
                "confirmed, total_score, confirmed_at, created_at, updated_at, "
                "context_card_json, validation_plan_json "
                "FROM project_stage_assessments "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND stage IN ('problem','market','tech') "
                "AND deleted_at IS NULL"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        assessment_rows = assessments_result.mappings().all()
        confirmed_stages = {
            row.get("stage")
            for row in assessment_rows
            if row.get("confirmed")
        }
        missing_stages = SUMMARY_STAGES - confirmed_stages
        if missing_stages:
            raise ValueError("All stage summaries must be confirmed before report generation.")
        assessment_ids = [
            str(row.get("id")) for row in assessment_rows if row.get("id")
        ]
        assessments = build_assessment_snapshots(
            assessment_rows,
            summary_locales=normalize_summary_locale_map(state_meta),
        )
        qa_digest_by_stage = await _fetch_report_qa_digests(session, assessment_ids)
        last_user_message = await fetch_report_last_user_message(
            session,
            org_id=org_id,
            project_id=str(project_id),
        )

    if not org_id:
        return

    ai_assisted_map = _normalize_ai_assisted_map(state_meta)
    user_edited_map = _normalize_user_edited_map(state_meta)
    report_payload = build_report_payload(
        project_row_payload,
        state_json,
        assessments,
        artifact_locale=output_locale,
        ai_assisted_paths=ai_assisted_map,
        user_edited_paths=user_edited_map,
    )
    report_input = build_report_input(
        report_payload.get("project") or {},
        report_payload.get("lean_canvas") or {},
        report_payload.get("market_evidence") or {},
        assessments,
        ai_assisted_map,
        user_edited_map,
    )
    prompt_task_traces: dict[str, Any] = {}

    async with session.begin():
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": owner_user_id or requested_by_user_id},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )
        await _touch_report_job(job_id, org_id, phase="running")
        dvf_payload, _ = await generate_dvf_scoring(
            session,
            report_input,
            output_locale=output_locale,
            project_settings=project_settings,
            trace_sink=prompt_task_traces,
        )
        if dvf_payload:
            report_payload = merge_report_payload(report_payload, dvf_payload)

        await _touch_report_job(job_id, org_id, phase="running")
        verification_payload = await verify_report_inputs(
            qa_digest_by_stage=qa_digest_by_stage,
            stage_summaries=build_stage_summary_map(assessments),
            last_user_message=last_user_message,
            allowed_sections=SUMMARY_STAGES,
            prompt_session=session,
            project_settings=project_settings,
        )
        if isinstance(verification_payload, dict) and verification_payload.get("enabled"):
            report_payload["verification"] = verification_payload
            report_payload["verification_meta"] = {
                "evidence_mode": verification_payload.get("evidence_mode"),
                "evidence_checked": True,
                "evidence_samples_count": len(
                    verification_payload.get("evidence_samples") or []
                ),
                "supported_ratio": (
                    verification_payload.get("verdict_counts_overall") or {}
                ).get("supported_ratio"),
                "verification_scope": verification_payload.get("verification_scope")
                or [],
                "fallback_used": bool(verification_payload.get("fallback_used")),
            }

        await _touch_report_job(job_id, org_id, phase="running")
        report_sections, report_model = await _generate_structured_report_v0(
            session,
            report_input,
            output_locale=output_locale,
            project_settings=project_settings,
            trace_sink=prompt_task_traces,
        )

    await _commit_if_transaction_open(session)
    await _touch_report_job(job_id, org_id, phase="finalizing")

    report_payload = merge_report_payload(report_payload, report_sections)
    recovery_sections = build_report_recovery_sections(report_payload)
    if recovery_sections:
        report_payload = merge_report_payload(report_payload, recovery_sections)
        if report_model is None:
            report_model = "deterministic-report-fallback"
        prompt_task_traces["report_recovery"] = {
            "task_key": "report_recovery",
            "status": "fallback",
            "provider": "deterministic",
            "model": "deterministic-report-fallback",
            "recovered_fields": sorted(recovery_sections),
        }
    if prompt_task_traces:
        report_payload["prompt_task_traces"] = prompt_task_traces

    stage_validation_plans = [
        item.get("validation_plan")
        for item in assessments
        if isinstance(item, dict) and isinstance(item.get("validation_plan"), list)
    ]
    prompt_validation_plan = (
        report_payload.get("validation_plan")
        if isinstance(report_payload.get("validation_plan"), list)
        else []
    )
    report_validation_plan = build_validation_plan(
        stage="report",
        context_card={},
        key_risks=report_payload.get("key_risks")
        if isinstance(report_payload.get("key_risks"), list)
        else [],
    )
    final_validation_plan = merge_validation_plans(
        *stage_validation_plans,
        prompt_validation_plan,
        report_validation_plan,
    )
    report_payload["validation_plan"] = final_validation_plan
    prompt_diagnosis = (
        report_payload.get("diagnosis")
        if isinstance(report_payload.get("diagnosis"), dict)
        else {}
    )
    diagnosis_payload = build_report_diagnosis(
        assessments=assessments,
        dvf_confidence=report_payload.get("dvf_confidence")
        if isinstance(report_payload.get("dvf_confidence"), dict)
        else {},
        key_risks=report_payload.get("key_risks")
        if isinstance(report_payload.get("key_risks"), list)
        else [],
    )
    if isinstance(prompt_diagnosis, dict):
        for key in ("summary", "diagnosis_summary", "next_validation_steps"):
            value = prompt_diagnosis.get(key)
            if value:
                diagnosis_payload[key] = value
    diagnosis_payload.setdefault("next_validation_steps", final_validation_plan)
    report_payload["diagnosis"] = diagnosis_payload
    v2_sections = build_report_v2_sections(report_payload)
    report_payload = merge_report_payload(report_payload, v2_sections)
    report_markdown = build_report_markdown(report_payload)
    await _touch_report_job(job_id, org_id, phase="finalizing")
    quality_observation_context: dict[str, Any] | None = None

    async with session.begin():
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": owner_user_id or requested_by_user_id},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )
        lock_result = await session.execute(
            text(
                "SELECT current_stage, stage_status "
                "FROM projects "
                "WHERE id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1 "
                "FOR UPDATE"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        lock_row = lock_result.mappings().first()
        if not lock_row:
            return
        locked_report_decision = decide_report_confirmation_complete(
            current_stage=lock_row.get("current_stage"),
            stage_status=lock_row.get("stage_status"),
        )
        locked_report_recovery = is_report_generation_recovery_stage(
            current_stage=lock_row.get("current_stage"),
            stage_status=lock_row.get("stage_status"),
        )
        if not locked_report_decision.allowed and not locked_report_recovery:
            return
        state_result = await session.execute(
            text(
                "SELECT state_version "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        state_row = state_result.mappings().first()
        if int((state_row or {}).get("state_version") or 0) != context_version:
            return

        version_result = await session.execute(
            text(
                "SELECT COALESCE(MAX(report_version), 0) AS max_version "
                "FROM project_reports "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        version_row = version_result.mappings().first()
        report_version = (version_row.get("max_version") or 0) + 1

        insert_result = await session.execute(
            text(
                "INSERT INTO project_reports ("
                "org_id, project_id, report_version, status, content_markdown, "
                "content_json, diagnosis_json, validation_plan_json, "
                "artifact_schema_version, decision_snapshot_json, "
                "score_rationales_json, risk_register_json, experiment_plan_json, "
                "evidence_index_json, generated_from_state_version, "
                "generator_model, confirmed"
                ") VALUES ("
                ":org_id, :project_id, :report_version, 'final', :content_markdown, "
                ":content_json, :diagnosis_json, :validation_plan_json, "
                ":artifact_schema_version, :decision_snapshot_json, "
                ":score_rationales_json, :risk_register_json, :experiment_plan_json, "
                ":evidence_index_json, :state_version, :generator_model, true"
                ") "
                "RETURNING id"
            ).bindparams(
                bindparam("content_json", type_=JSONB),
                bindparam("diagnosis_json", type_=JSONB),
                bindparam("validation_plan_json", type_=JSONB),
                bindparam("decision_snapshot_json", type_=JSONB),
                bindparam("score_rationales_json", type_=JSONB),
                bindparam("risk_register_json", type_=JSONB),
                bindparam("experiment_plan_json", type_=JSONB),
                bindparam("evidence_index_json", type_=JSONB),
            ),
            {
                "org_id": org_id,
                "project_id": str(project_id),
                "report_version": report_version,
                "content_markdown": report_markdown,
                "content_json": report_payload,
                "diagnosis_json": report_payload.get("diagnosis") or {},
                "validation_plan_json": report_payload.get("validation_plan") or [],
                "artifact_schema_version": "report_v2",
                "decision_snapshot_json": report_payload.get("decision_snapshot") or {},
                "score_rationales_json": report_payload.get("score_rationales") or {},
                "risk_register_json": report_payload.get("risk_register") or [],
                "experiment_plan_json": report_payload.get("experiment_plan") or [],
                "evidence_index_json": report_payload.get("evidence_index") or {},
                "state_version": context_version,
                "generator_model": report_model,
            },
        )
        report_row = insert_result.mappings().first()
        if report_row and report_row.get("id"):
            quality_observation_context = {
                "org_id": org_id,
                "project_id": str(project_id),
                "project_title": project_row_payload.get("title"),
                "report_id": str(report_row.get("id")),
                "report_version": report_version,
                "generated_from_state_version": context_version,
                "report_payload": report_payload,
                "actor_user_id": owner_user_id or requested_by_user_id,
                "generator_model": report_model,
            }
        if locked_report_decision.allowed:
            await mark_project_stage_passed_from_decision(
                session,
                project_id=str(project_id),
                org_id=org_id,
                decision=locked_report_decision,
            )
        await record_report_usage(
            session,
            user_id=str(requested_by_user_id),
        )

    if quality_observation_context:
        await _persist_report_quality_observation_safely(
            session,
            quality_observation_context,
        )


async def _persist_report_quality_observation_safely(
    session,
    context: dict[str, Any],
) -> None:
    try:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": context["org_id"]},
            )
            await session.execute(
                text("SELECT set_config('app.user_id', :user_id, true)"),
                {"user_id": str(context["actor_user_id"])},
            )
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )
            await persist_report_quality_observation(
                session,
                context["report_payload"],
                org_id=str(context["org_id"]),
                project_id=str(context["project_id"]),
                project_title=context.get("project_title"),
                report_id=str(context["report_id"]),
                report_version=int(context["report_version"]),
                generated_from_state_version=int(
                    context["generated_from_state_version"]
                ),
                source={"generator_model": context.get("generator_model")},
            )
    except Exception:
        logger.exception(
            "Failed to persist report quality observation for report %s",
            context.get("report_id"),
        )
