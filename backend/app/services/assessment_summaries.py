from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text

from app.core.llm_router import has_available_provider
from app.services.background_jobs import background_job_sort_time
from app.services.localization import normalize_summary_locale_map
from app.services.prompt_runtime import DEFAULT_PROMPT_TASK_REGISTRY
from app.services.stage_payloads import normalize_user_edited_map
from app.services.stage_verifications import (
    claim_verdict_counts,
    collect_sources_from_claims,
    increment_verification_summary,
    resolve_question_verification_status,
)
from app.services.verification.config import (
    tavily_api_key,
    tavily_search_enabled,
    verification_enabled,
    verification_min_priority,
)
from app.services.verification.priority import (
    extract_verification_priority,
    normalize_priority,
    priority_at_least,
)
from app.services.verification.question_instances import is_verifiable_question_instance
from app.services.verification_jobs import VERIFY_QUESTION_CLAIMS_JOB_TYPE


SUMMARY_STAGES = {"problem", "market", "tech"}


class AssessmentProjectNotFoundError(RuntimeError):
    pass


class AssessmentStageUnsupportedError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageSummaryReadModel:
    stage: str
    draft_summary_markdown: str | None = None
    draft_output_locale: str | None = None
    final_summary_markdown: str | None = None
    final_output_locale: str | None = None
    confirmed: bool = False
    updated_at: Any = None
    user_edited_paths: list[str] = field(default_factory=list)
    context_card: dict[str, Any] = field(default_factory=dict)
    validation_plan: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationSourceReadModel:
    title: str | None = None
    url: str | None = None
    domain: str | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class StageQuestionVerificationReadModel:
    question_id: str
    question_title: str | None = None
    priority: str = "none"
    status: str = "not_checked"
    status_detail: str | None = None
    supported_claims: int = 0
    contradicted_claims: int = 0
    uncertain_claims: int = 0
    total_claims: int = 0
    sources: list[VerificationSourceReadModel] = field(default_factory=list)


@dataclass
class StageVerificationReadModel:
    stage: str
    total: int = 0
    supported: int = 0
    contradicted: int = 0
    uncertain: int = 0
    failed: int = 0
    stale: int = 0
    provider_unavailable: int = 0
    not_checked: int = 0
    verified: int = 0
    verifying: int = 0
    no_evidence: int = 0
    not_applicable: int = 0
    questions: list[StageQuestionVerificationReadModel] = field(default_factory=list)


def resolve_verification_provider_unavailable_reason() -> str | None:
    task = DEFAULT_PROMPT_TASK_REGISTRY.get("claim_verification")
    if not verification_enabled():
        return None
    if not tavily_search_enabled():
        return "search_disabled"
    if not tavily_api_key():
        return "missing_search_provider_key"
    if not has_available_provider(task.provider_task):
        return "missing_judge_provider"
    return None


async def fetch_stage_summary_read_models(
    session,
    *,
    project_id: str,
) -> list[StageSummaryReadModel]:
    project_result = await session.execute(
        text(
            "SELECT id "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id},
    )
    if not project_result.mappings().first():
        raise AssessmentProjectNotFoundError("Project not found.")

    state_result = await session.execute(
        text(
            "SELECT state_meta "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id},
    )
    state_row = state_result.mappings().first()
    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    summary_locale_map = normalize_summary_locale_map(state_meta)
    user_edited_map = normalize_user_edited_map(state_meta)

    result = await session.execute(
        text(
            "SELECT stage, draft_summary_markdown, final_summary_markdown, "
            "confirmed, updated_at, context_card_json, validation_plan_json "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "ORDER BY CASE stage "
            "WHEN 'problem' THEN 1 "
            "WHEN 'market' THEN 2 "
            "WHEN 'tech' THEN 3 "
            "ELSE 4 END"
        ),
        {"project_id": project_id},
    )
    summaries: list[StageSummaryReadModel] = []
    for row in result.mappings().all():
        stage_value = row.get("stage") or ""
        stage_key = stage_value.strip().lower() if isinstance(stage_value, str) else ""
        locale_payload = summary_locale_map.get(stage_key, {})
        summaries.append(
            StageSummaryReadModel(
                stage=stage_value,
                draft_summary_markdown=row.get("draft_summary_markdown"),
                draft_output_locale=locale_payload.get("draft"),
                final_summary_markdown=row.get("final_summary_markdown"),
                final_output_locale=locale_payload.get("final"),
                confirmed=bool(row.get("confirmed")),
                updated_at=row.get("updated_at"),
                user_edited_paths=user_edited_map.get(stage_key, []),
                context_card=row.get("context_card_json")
                if isinstance(row.get("context_card_json"), dict)
                else {},
                validation_plan=row.get("validation_plan_json")
                if isinstance(row.get("validation_plan_json"), list)
                else [],
            )
        )
    return summaries


async def fetch_project_stage_verification_read_models(
    session,
    *,
    project_id: str,
    stage: str | None = None,
) -> list[StageVerificationReadModel]:
    normalized_stage = stage.strip().lower() if isinstance(stage, str) else None
    if normalized_stage and normalized_stage not in SUMMARY_STAGES:
        raise AssessmentStageUnsupportedError("Stage not supported.")

    project_result = await session.execute(
        text(
            "SELECT id "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id},
    )
    if not project_result.mappings().first():
        raise AssessmentProjectNotFoundError("Project not found.")

    stage_filter = [normalized_stage] if normalized_stage else sorted(SUMMARY_STAGES)
    provider_unavailable_reason = resolve_verification_provider_unavailable_reason()
    question_result = await session.execute(
        text(
            "SELECT qi.id AS question_instance_id, qi.answered_at, "
            "qi.status, qi.final_answer_text, "
            "q.id AS question_bank_question_id, q.question_id, q.title, "
            "q.stage, q.order_index, q.prompt_meta "
            "FROM project_question_instances qi "
            "JOIN question_bank_questions q "
            "ON q.id = qi.question_bank_question_id "
            "WHERE qi.project_id = :project_id "
            "AND qi.org_id = app_org_id() "
            "AND qi.deleted_at IS NULL "
            "AND q.deleted_at IS NULL "
            "AND q.stage IN :stages "
            "ORDER BY CASE q.stage "
            "WHEN 'problem' THEN 1 "
            "WHEN 'market' THEN 2 "
            "WHEN 'tech' THEN 3 "
            "ELSE 4 END, q.order_index ASC"
        ).bindparams(bindparam("stages", expanding=True)),
        {"project_id": project_id, "stages": stage_filter},
    )
    question_rows = [
        row
        for row in question_result.mappings().all()
        if is_verifiable_question_instance(
            row.get("status"),
            row.get("final_answer_text"),
        )
    ]

    min_priority = verification_min_priority()
    question_items = []
    for row in question_rows:
        prompt_meta = row.get("prompt_meta") or {}
        priority = extract_verification_priority(
            {"prompt_meta": prompt_meta, "question_id": row.get("question_id")}
        )
        priority = normalize_priority(priority)
        if not priority_at_least(priority, min_priority):
            continue
        question_items.append({**row, "priority": priority})

    question_ids = [
        row.get("question_bank_question_id")
        for row in question_items
        if row.get("question_bank_question_id")
    ]
    claims_by_question: dict[str, list[dict[str, Any]]] = {}
    if question_ids:
        claim_result = await session.execute(
            text(
                "SELECT question_bank_question_id, question_id, stage, "
                "claim, verdict, confidence, rationale, sources, priority, "
                "batch_id, created_at "
                "FROM project_stage_verification_claims "
                "WHERE project_id = :project_id "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL "
                "AND question_bank_question_id IN :question_ids "
                "ORDER BY created_at DESC"
            ).bindparams(bindparam("question_ids", expanding=True)),
            {"project_id": project_id, "question_ids": question_ids},
        )
        for row in claim_result.mappings().all():
            key = str(row.get("question_bank_question_id"))
            claims_by_question.setdefault(key, []).append(row)

    job_result = await session.execute(
        text(
            "SELECT id, payload, status, last_error, created_at, updated_at, completed_at "
            "FROM background_jobs "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND job_type = :job_type "
            "AND status IN ('queued','running','failed','cancelled') "
            "AND deleted_at IS NULL"
        ),
        {"project_id": project_id, "job_type": VERIFY_QUESTION_CLAIMS_JOB_TYPE},
    )
    pending_question_ids: set[str] = set()
    failed_job_by_question: dict[str, dict[str, Any]] = {}
    for row in job_result.mappings().all():
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        qid = payload.get("question_bank_question_id")
        if not isinstance(qid, str) or not qid:
            continue
        job_status = str(row.get("status") or "").strip().lower()
        if job_status in {"queued", "running"}:
            pending_question_ids.add(qid)
        elif job_status in {"failed", "cancelled"}:
            existing = failed_job_by_question.get(qid)
            candidate = dict(row)
            if (
                background_job_sort_time(candidate)
                or datetime.min.replace(tzinfo=timezone.utc)
            ) >= (
                background_job_sort_time(existing)
                or datetime.min.replace(tzinfo=timezone.utc)
            ):
                failed_job_by_question[qid] = candidate

    summaries: dict[str, StageVerificationReadModel] = {
        stage_key: StageVerificationReadModel(stage=stage_key)
        for stage_key in stage_filter
    }
    for row in question_items:
        stage_key = row.get("stage") or "problem"
        question_bank_id = row.get("question_bank_question_id")
        if not question_bank_id:
            continue
        question_key = str(question_bank_id)
        claims = claims_by_question.get(question_key, [])
        answered_at = row.get("answered_at")
        latest_claim_time = None
        if claims:
            latest_claim_time = max(
                (entry.get("created_at") for entry in claims if entry.get("created_at")),
                default=None,
            )
        is_stale = bool(answered_at and latest_claim_time and answered_at > latest_claim_time)
        if is_stale:
            claims = []
        pending = question_key in pending_question_ids
        failed_job = failed_job_by_question.get(question_key)
        failed_at = background_job_sort_time(failed_job)
        failed = bool(
            failed_job
            and (
                answered_at is None
                or failed_at is None
                or failed_at >= answered_at
            )
        )

        if claims:
            batches: dict[str, list[dict[str, Any]]] = {}
            for claim in claims:
                batch_id = claim.get("batch_id")
                batch_key = str(batch_id) if batch_id else "legacy"
                batches.setdefault(batch_key, []).append(claim)
            latest_batch = max(
                batches.values(),
                key=lambda items: max(
                    (entry.get("created_at") for entry in items if entry.get("created_at")),
                    default=datetime.min.replace(tzinfo=timezone.utc),
                ),
            )
        else:
            latest_batch = []

        verdict_counts = claim_verdict_counts(latest_batch)
        verification_status = resolve_question_verification_status(
            pending=pending,
            stale=is_stale,
            latest_batch=latest_batch,
            failed=failed,
            provider_unavailable_reason=provider_unavailable_reason,
        )
        sources = collect_sources_from_claims(latest_batch, limit=3)
        question_summary = StageQuestionVerificationReadModel(
            question_id=row.get("question_id"),
            question_title=row.get("title"),
            priority=row.get("priority") or "none",
            status=verification_status,
            status_detail=provider_unavailable_reason
            if verification_status == "provider_unavailable"
            else None,
            supported_claims=verdict_counts["supported"],
            contradicted_claims=verdict_counts["contradicted"],
            uncertain_claims=verdict_counts["uncertain"],
            total_claims=len(latest_batch),
            sources=[
                VerificationSourceReadModel(**source)
                for source in sources
                if isinstance(source, dict)
            ],
        )
        summary = summaries.setdefault(stage_key, StageVerificationReadModel(stage=stage_key))
        summary.questions.append(question_summary)
        increment_verification_summary(summary, verification_status)

    return [summaries[key] for key in stage_filter]


__all__ = [
    "AssessmentProjectNotFoundError",
    "AssessmentStageUnsupportedError",
    "SUMMARY_STAGES",
    "StageQuestionVerificationReadModel",
    "StageSummaryReadModel",
    "StageVerificationReadModel",
    "VerificationSourceReadModel",
    "fetch_project_stage_verification_read_models",
    "fetch_stage_summary_read_models",
    "resolve_verification_provider_unavailable_reason",
]
