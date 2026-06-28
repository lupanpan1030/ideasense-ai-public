from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.diagnostics import (
    build_context_card,
    build_validation_plan,
    summarize_verification_payload,
)
from app.services.localization import (
    OutputLocale,
    normalize_output_locale,
    output_language_label,
)
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
)
from app.services.qa_digests import (
    build_qa_digests_from_messages as _build_qa_digests_from_messages,
)
from app.services.report_conversation_sources import fetch_report_last_user_message
from app.services.scoring import generate_dvf_scoring
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths
from app.services.stage_payloads import build_stage_payload as _build_stage_payload
from app.services.verification import verify_report_inputs


SUMMARY_STAGES = {"problem", "market", "tech"}
logger = logging.getLogger("ideasense.worker.stage_finalize")
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()
WorkerContextSetter = Callable[[Any, str | None], Awaitable[None]]


async def _commit_if_transaction_open(session) -> None:
    if session.in_transaction():
        await session.commit()


async def _resolve_required_stage_paths(
    session,
    bank_id: Any,
    stage: str,
    variant: str,
) -> list[str]:
    result = await session.execute(
        text(
            "SELECT COALESCE(array_agg(DISTINCT path ORDER BY path), ARRAY[]::text[]) "
            "AS paths "
            "FROM ( "
            "SELECT unnest(COALESCE(schema_paths, ARRAY[]::text[])) AS path "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "AND type_raw ILIKE 'Required%' "
            ") AS stage_paths "
            "WHERE path IS NOT NULL "
            "AND btrim(path) <> ''"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    row = result.mappings().first()
    return list(row.get("paths") or [])


async def _fetch_stage_digest_sources(
    session,
    *,
    org_id: str,
    project_id: str,
    stage: str,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT id, meta, model_name, created_at "
            "FROM conversation_messages "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND stage = :stage "
            "AND role = 'assistant' "
            "AND is_visible "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC, id DESC"
        ),
        {"project_id": project_id, "org_id": org_id, "stage": stage},
    )
    return [dict(row) for row in result.mappings().all()]


def _collect_verification_claim_rows(
    verification_payload: dict[str, Any],
    *,
    org_id: str,
    project_id: str,
    assessment_id: str,
    default_stage: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    evidence_mode = verification_payload.get("evidence_mode")
    for bucket in ("verified_facts", "unsupported_claims"):
        entries = verification_payload.get(bucket) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            claim = entry.get("claim") or entry.get("text")
            if not isinstance(claim, str) or not claim.strip():
                continue
            rows.append(
                {
                    "org_id": org_id,
                    "project_id": project_id,
                    "assessment_id": assessment_id,
                    "stage": entry.get("section") or default_stage,
                    "claim": claim.strip(),
                    "verdict": entry.get("verdict") or "uncertain",
                    "confidence": entry.get("confidence"),
                    "rationale": entry.get("rationale"),
                    "sources": entry.get("sources"),
                    "evidence_mode": evidence_mode,
                }
            )
    return rows


def _sanitize_project_description(value: str | None, max_len: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in {
        "unknown",
        "n/a",
        "none",
        "no description",
        "no description yet",
        "summary unavailable",
        "summary unavailable.",
    }:
        return None
    if cleaned in {"未知", "无", "无描述"}:
        return None
    if len(cleaned) > max_len:
        trimmed = cleaned[: max_len - 3].rstrip()
        return f"{trimmed}..."
    return cleaned


async def _generate_project_description_v0(
    session,
    *,
    title: str | None,
    payload: dict[str, Any],
    summary: str | None,
    output_locale: OutputLocale,
    project_settings: dict | None = None,
) -> tuple[str | None, str | None]:
    context = PROMPT_CONTEXT_BUILDER.project_description(
        title=title,
        payload=payload,
        summary=summary,
        output_language=output_language_label(output_locale),
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
    )
    if not result.ok:
        return None, result.model
    return result.content, result.model


async def run_stage_finalize_v0(
    session,
    payload: dict[str, Any],
    *,
    job_org_id: str | None = None,
    set_worker_context_fn: WorkerContextSetter | None = None,
) -> None:
    project_id = payload.get("project_id")
    stage = payload.get("stage")
    raw_context_version = payload.get("context_version")
    if not project_id or not isinstance(stage, str) or raw_context_version is None:
        raise ValueError("Stage finalize payload missing identifiers.")

    normalized_stage = stage.strip().lower()
    if normalized_stage not in SUMMARY_STAGES:
        raise ValueError(f"Unsupported stage for finalize: {stage}")
    try:
        context_version = int(raw_context_version)
    except (TypeError, ValueError) as exc:
        raise ValueError("Stage finalize payload has invalid context_version.") from exc
    output_locale = normalize_output_locale(
        payload.get("output_locale") if isinstance(payload.get("output_locale"), str) else None
    )

    org_id: str | None = None
    owner_user_id: str | None = None
    bank_id: Any = payload.get("question_bank_version_id")
    variant = payload.get("variant") if isinstance(payload.get("variant"), str) else "default"
    project_settings: dict[str, Any] | None = None
    project_title: str | None = None
    project_description: str | None = None
    assessment_id: str | None = None
    summary_markdown: str | None = None
    state_json: dict[str, Any] = {}
    state_meta: dict[str, Any] = {}
    stage_missing_paths: list[str] = []

    async with session.begin():
        if set_worker_context_fn is not None:
            await set_worker_context_fn(session, job_org_id)
        project_result = await session.execute(
            text(
                "SELECT id, org_id, owner_user_id, title, description, "
                "question_bank_version_id, settings "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id)},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            raise ValueError("Project not found for stage finalize job.")
        org_id = str(project_row.get("org_id")) if project_row.get("org_id") else None
        owner_user_id = (
            str(project_row.get("owner_user_id"))
            if project_row.get("owner_user_id")
            else None
        )
        if not org_id or not owner_user_id:
            raise ValueError("Project missing org or owner for stage finalize job.")

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

        if not bank_id:
            bank_id = project_row.get("question_bank_version_id")
        if not bank_id:
            raise ValueError("Project question bank missing for stage finalize job.")
        project_title = project_row.get("title")
        project_description = project_row.get("description")
        settings = project_row.get("settings")
        project_settings = settings if isinstance(settings, dict) else None

        assessment_result = await session.execute(
            text(
                "SELECT id, final_summary_markdown, draft_summary_markdown, "
                "generated_from_state_version, generator_model, confirmed "
                "FROM project_stage_assessments "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND stage = :stage "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "project_id": str(project_id),
                "org_id": org_id,
                "stage": normalized_stage,
            },
        )
        assessment_row = assessment_result.mappings().first()
        if not assessment_row or not assessment_row.get("confirmed"):
            return
        if int(assessment_row.get("generated_from_state_version") or 0) != context_version:
            return
        assessment_id = str(assessment_row.get("id"))
        summary_markdown = (
            assessment_row.get("final_summary_markdown")
            or assessment_row.get("draft_summary_markdown")
        )

        state_result = await session.execute(
            text(
                "SELECT state_json, state_meta "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": str(project_id), "org_id": org_id},
        )
        state_row = state_result.mappings().first()
        state_json = state_row.get("state_json") if state_row else {}
        if not isinstance(state_json, dict):
            state_json = {}
        state_meta = state_row.get("state_meta") if state_row else {}
        if not isinstance(state_meta, dict):
            state_meta = {}
        required_stage_paths = await _resolve_required_stage_paths(
            session,
            bank_id,
            normalized_stage,
            variant,
        )
        stage_missing_paths = filter_stage_blocking_missing_paths(
            normalized_stage,
            required_stage_paths,
            state_json=state_json,
            state_meta=state_meta,
        )

    if not org_id or not owner_user_id or not assessment_id:
        return

    trace_sink: dict[str, Any] = {}
    dvf_payload: dict[str, Any] | None = None
    risk_matrix: dict[str, Any] | None = None
    total_score: float | None = None
    qa_digests: list[dict[str, Any]] = []
    verification_payload: dict[str, Any] | None = None
    auto_description: str | None = None
    auto_description_model: str | None = None

    async with session.begin():
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
        if summary_markdown:
            try:
                dvf_input = {
                    "project": {
                        "title": project_title,
                        "description": project_description,
                    },
                    "lean_canvas": {},
                    "stage_summaries": {normalized_stage: summary_markdown},
                    "ai_assisted_paths": {},
                    "user_edited_paths": {},
                }
                dvf_payload, _ = await generate_dvf_scoring(
                    session,
                    dvf_input,
                    output_locale=output_locale,
                    project_settings=project_settings,
                    trace_sink=trace_sink,
                )
            except Exception:
                logger.warning(
                    "stage finalize dvf scoring failed",
                    extra={"project_id": str(project_id), "stage": normalized_stage},
                    exc_info=True,
                )

        try:
            message_rows = await _fetch_stage_digest_sources(
                session,
                org_id=org_id,
                project_id=str(project_id),
                stage=normalized_stage,
            )
            qa_digests = await _build_qa_digests_from_messages(
                session,
                message_rows,
                output_locale=output_locale,
                project_settings=project_settings,
            )
        except Exception:
            logger.warning(
                "stage finalize qa digest failed",
                extra={"project_id": str(project_id), "stage": normalized_stage},
                exc_info=True,
            )
        if normalized_stage in {"market", "tech"}:
            try:
                last_user_message = await fetch_report_last_user_message(
                    session,
                    org_id=org_id,
                    project_id=str(project_id),
                )
                verification_payload = await verify_report_inputs(
                    qa_digest_by_stage={normalized_stage: qa_digests},
                    stage_summaries={normalized_stage: summary_markdown},
                    last_user_message=last_user_message,
                    allowed_sections=(normalized_stage,),
                    prompt_session=session,
                    project_settings=project_settings,
                )
                if not (
                    isinstance(verification_payload, dict)
                    and verification_payload.get("enabled")
                ):
                    verification_payload = None
            except Exception:
                logger.warning(
                    "stage finalize verification failed",
                    extra={"project_id": str(project_id), "stage": normalized_stage},
                    exc_info=True,
                )
                verification_payload = None

        if (
            normalized_stage == "problem"
            and not (project_description or "").strip()
            and summary_markdown
        ):
            try:
                stage_payload = await _build_stage_payload(
                    session,
                    bank_id,
                    normalized_stage,
                    variant,
                    state_json,
                    state_meta,
                )
                raw_description, auto_description_model = (
                    await _generate_project_description_v0(
                        session,
                        title=project_title,
                        payload=stage_payload,
                        summary=summary_markdown,
                        output_locale=output_locale,
                        project_settings=project_settings,
                    )
                )
                auto_description = _sanitize_project_description(raw_description)
            except Exception:
                logger.warning(
                    "stage finalize project description failed",
                    extra={"project_id": str(project_id), "stage": normalized_stage},
                    exc_info=True,
                )

    await _commit_if_transaction_open(session)

    if isinstance(dvf_payload, dict):
        scoreboard = dvf_payload.get("dvf_scoreboard") or {}
        if isinstance(scoreboard, dict):
            raw_total_score = scoreboard.get("total_score")
            if isinstance(raw_total_score, (int, float)):
                total_score = float(raw_total_score)
            elif isinstance(raw_total_score, str):
                try:
                    total_score = float(raw_total_score)
                except ValueError:
                    total_score = None
        raw_risk_matrix = dvf_payload.get("risk_matrix")
        risk_matrix = raw_risk_matrix if isinstance(raw_risk_matrix, dict) else None

    scores_json_payload: dict[str, Any] = {}
    if dvf_payload:
        scores_json_payload.update(dvf_payload)
    if trace_sink:
        scores_json_payload["prompt_task_traces"] = trace_sink
    if verification_payload:
        scores_json_payload["verification"] = verification_payload
        scores_json_payload["verification_meta"] = {
            "evidence_mode": verification_payload.get("evidence_mode"),
            "evidence_checked": True,
            "evidence_samples_count": len(
                verification_payload.get("evidence_samples") or []
            ),
            "supported_ratio": (
                verification_payload.get("verdict_counts_overall") or {}
            ).get("supported_ratio"),
            "verification_scope": verification_payload.get("verification_scope") or [],
            "fallback_used": bool(verification_payload.get("fallback_used")),
        }

    context_card = build_context_card(
        stage=normalized_stage,
        state_json=state_json,
        state_meta=state_meta,
        missing_paths=stage_missing_paths,
        verification_summary=summarize_verification_payload(verification_payload),
    )
    validation_plan = build_validation_plan(
        stage=normalized_stage,
        context_card=context_card,
        key_risks=dvf_payload.get("key_risks")
        if isinstance(dvf_payload, dict) and isinstance(dvf_payload.get("key_risks"), list)
        else [],
    )

    async with session.begin():
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
        await session.execute(
            text(
                "UPDATE project_stage_assessments "
                "SET scores_json = COALESCE(scores_json, '{}'::jsonb) || :scores_json, "
                "total_score = :total_score, "
                "risk_matrix = :risk_matrix, "
                "context_card_json = :context_card, "
                "validation_plan_json = :validation_plan, "
                "updated_at = now() "
                "WHERE id = :assessment_id "
                "AND org_id = :org_id "
                "AND project_id = :project_id "
                "AND stage = :stage "
                "AND confirmed "
                "AND deleted_at IS NULL"
            ).bindparams(
                bindparam("scores_json", type_=JSONB),
                bindparam("risk_matrix", type_=JSONB),
                bindparam("context_card", type_=JSONB),
                bindparam("validation_plan", type_=JSONB),
            ),
            {
                "scores_json": scores_json_payload,
                "total_score": total_score,
                "risk_matrix": risk_matrix,
                "context_card": context_card,
                "validation_plan": validation_plan,
                "assessment_id": assessment_id,
                "org_id": org_id,
                "project_id": str(project_id),
                "stage": normalized_stage,
            },
        )

        await session.execute(
            text(
                "UPDATE project_stage_qa_digests "
                "SET deleted_at = now() "
                "WHERE assessment_id = :assessment_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {"assessment_id": assessment_id, "org_id": org_id},
        )
        if qa_digests:
            qa_rows = [
                {
                    "org_id": org_id,
                    "project_id": str(project_id),
                    "assessment_id": assessment_id,
                    "stage": normalized_stage,
                    "question_id": digest.get("question_id"),
                    "answer_summary": digest.get("answer_summary"),
                    "key_points": digest.get("key_points") or [],
                    "source_message_id": digest.get("source_message_id"),
                    "model": digest.get("model"),
                }
                for digest in qa_digests
            ]
            await session.execute(
                text(
                    "INSERT INTO project_stage_qa_digests ("
                    "org_id, project_id, assessment_id, stage, question_id, "
                    "answer_summary, key_points, source_message_id, model"
                    ") VALUES ("
                    ":org_id, :project_id, :assessment_id, :stage, :question_id, "
                    ":answer_summary, :key_points, :source_message_id, :model"
                    ")"
                ),
                qa_rows,
            )

        await session.execute(
            text(
                "UPDATE project_stage_verification_claims "
                "SET deleted_at = now() "
                "WHERE assessment_id = :assessment_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL"
            ),
            {"assessment_id": assessment_id, "org_id": org_id},
        )
        if verification_payload:
            claim_rows = _collect_verification_claim_rows(
                verification_payload,
                org_id=org_id,
                project_id=str(project_id),
                assessment_id=assessment_id,
                default_stage=normalized_stage,
            )
            if claim_rows:
                await session.execute(
                    text(
                        "INSERT INTO project_stage_verification_claims ("
                        "org_id, project_id, assessment_id, stage, claim, verdict, "
                        "confidence, rationale, sources, evidence_mode"
                        ") VALUES ("
                        ":org_id, :project_id, :assessment_id, :stage, :claim, :verdict, "
                        ":confidence, :rationale, :sources, :evidence_mode"
                        ")"
                    ).bindparams(bindparam("sources", type_=JSONB)),
                    claim_rows,
                )

        if auto_description:
            settings_update = {
                "description_source": "ai",
                "description_stage": normalized_stage,
            }
            if auto_description_model:
                settings_update["description_model"] = auto_description_model
            await session.execute(
                text(
                    "UPDATE projects "
                    "SET description = :description, "
                    "settings = COALESCE(settings, '{}'::jsonb) "
                    "|| CAST(:settings AS jsonb), "
                    "updated_at = now() "
                    "WHERE id = :project_id "
                    "AND org_id = :org_id "
                    "AND deleted_at IS NULL "
                    "AND (description IS NULL OR btrim(description) = '')"
                ),
                {
                    "description": auto_description,
                    "settings": json.dumps(settings_update),
                    "project_id": str(project_id),
                    "org_id": org_id,
                },
            )
