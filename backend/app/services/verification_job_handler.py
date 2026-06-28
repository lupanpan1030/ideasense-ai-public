from __future__ import annotations

from collections.abc import Awaitable, Callable
import uuid
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.verification import verify_report_inputs
from app.services.verification.config import (
    verification_enabled,
    verification_min_priority,
    verification_per_section,
)
from app.services.verification.question_instances import (
    is_verifiable_question_instance,
)
from app.services.verification.priority import (
    extract_verification_priority,
    normalize_priority,
    priority_at_least,
)

WorkerContextSetter = Callable[[Any, str | None], Awaitable[None]]


def _dedupe_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def _extract_fallback_claim(user_text: str) -> str | None:
    for raw_line in user_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if len(line) > 280:
            return line[:280].rstrip() + "..."
        return line
    return None


async def _set_verification_worker_context(
    session,
    *,
    org_id: str,
    user_id: str,
) -> None:
    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": str(org_id)},
    )
    await session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )


async def run_verify_question_claims_v0(
    session,
    payload: dict[str, Any],
    *,
    job_org_id: str | None = None,
    set_worker_context_fn: WorkerContextSetter | None = None,
) -> None:
    project_id = payload.get("project_id")
    question_instance_id = payload.get("question_instance_id")
    if not project_id or not question_instance_id:
        raise ValueError("Job payload missing required identifiers.")

    if not verification_enabled():
        return

    async with session.begin():
        if set_worker_context_fn is not None:
            await set_worker_context_fn(session, job_org_id)
        project_result = await session.execute(
            text(
                "SELECT id, org_id, owner_user_id "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": project_id},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            raise ValueError("Project not found for verification job.")

        org_id = project_row.get("org_id")
        owner_user_id = project_row.get("owner_user_id")
        if not org_id or not owner_user_id:
            raise ValueError("Project missing org or owner.")

        await _set_verification_worker_context(
            session,
            org_id=str(org_id),
            user_id=str(owner_user_id),
        )

        question_result = await session.execute(
            text(
                "SELECT qi.status, qi.final_answer_text, "
                "q.id, q.question_id, q.stage, q.title, q.prompt_meta "
                "FROM project_question_instances qi "
                "JOIN question_bank_questions q "
                "ON q.id = qi.question_bank_question_id "
                "WHERE qi.id = :question_instance_id "
                "AND qi.project_id = :project_id "
                "AND qi.org_id = :org_id "
                "AND qi.deleted_at IS NULL "
                "AND q.deleted_at IS NULL "
                "LIMIT 1"
            ),
            {
                "question_instance_id": question_instance_id,
                "project_id": project_id,
                "org_id": org_id,
            },
        )
        question_row = question_result.mappings().first()
        if not question_row:
            raise ValueError("Question instance not found for verification job.")

        if not is_verifiable_question_instance(
            question_row.get("status"),
            question_row.get("final_answer_text"),
        ):
            return

        question_id = question_row.get("question_id")
        stage = (question_row.get("stage") or "problem").strip().lower()
        prompt_meta = question_row.get("prompt_meta") or {}
        question_detail = {"prompt_meta": prompt_meta, "question_id": question_id}
        payload_priority = payload.get("priority")
        priority = (
            normalize_priority(payload_priority)
            if payload_priority
            else extract_verification_priority(question_detail)
        )
        priority = normalize_priority(priority)
        if not priority_at_least(priority, verification_min_priority()):
            return

        message_result = await session.execute(
            text(
                "SELECT id, content "
                "FROM conversation_messages "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND role = 'user' "
                "AND question_instance_id = :question_instance_id "
                "AND deleted_at IS NULL "
                "ORDER BY id ASC"
            ),
            {
                "project_id": project_id,
                "org_id": org_id,
                "question_instance_id": question_instance_id,
            },
        )
        message_rows = message_result.mappings().all()
        if not message_rows:
            return

        parts: list[str] = []
        latest_message_id: int | None = None
        for row in message_rows:
            content = row.get("content")
            if isinstance(content, str):
                cleaned = content.strip()
                if cleaned:
                    parts.append(cleaned)
            if isinstance(row.get("id"), int):
                latest_message_id = row.get("id")
        user_text = "\n\n".join(parts).strip()
        if not user_text:
            return

        assistant_result = await session.execute(
            text(
                "SELECT id, meta "
                "FROM conversation_messages "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND role = 'assistant' "
                "AND question_instance_id = :question_instance_id "
                "AND deleted_at IS NULL "
                "ORDER BY id DESC "
                "LIMIT 1"
            ),
            {
                "project_id": project_id,
                "org_id": org_id,
                "question_instance_id": question_instance_id,
            },
        )
        assistant_row = assistant_result.mappings().first()
        meta = assistant_row.get("meta") if assistant_row else {}
        key_points: list[str] = []
        if isinstance(meta, dict):
            raw_points = meta.get("key_points") or []
            if isinstance(raw_points, list):
                key_points = _dedupe_texts(
                    [str(item) for item in raw_points if isinstance(item, str)]
                )
        rolling_summary = None
        if isinstance(meta, dict):
            summary_value = meta.get("rolling_summary")
            if isinstance(summary_value, str) and summary_value.strip():
                rolling_summary = summary_value.strip()

    if not key_points and not rolling_summary:
        fallback_claim = _extract_fallback_claim(user_text)
        if fallback_claim:
            key_points = [fallback_claim]

    qa_digest_by_stage = {
        stage: [
            {
                "question_id": question_id,
                "answer_summary": rolling_summary,
                "key_points": key_points,
                "source_message_id": latest_message_id,
            }
        ]
    }
    async with session.begin():
        await _set_verification_worker_context(
            session,
            org_id=str(org_id),
            user_id=str(owner_user_id),
        )
        verification_payload = await verify_report_inputs(
            qa_digest_by_stage=qa_digest_by_stage,
            stage_summaries={},
            last_user_message=user_text,
            allowed_sections=[stage],
            per_section_limit=verification_per_section(),
            prompt_session=session,
        )
    if not isinstance(verification_payload, dict) or not verification_payload.get(
        "enabled"
    ):
        return

    batch_id = uuid.uuid4()
    evidence_mode = verification_payload.get("evidence_mode")
    entries: list[dict[str, Any]] = []
    for bucket in ("verified_facts", "unsupported_claims"):
        items = verification_payload.get(bucket) or []
        if not isinstance(items, list):
            continue
        for entry in items:
            if not isinstance(entry, dict):
                continue
            claim = entry.get("claim") or entry.get("text")
            if not isinstance(claim, str) or not claim.strip():
                continue
            entries.append(
                {
                    "claim": claim.strip(),
                    "section": entry.get("section") or stage,
                    "verdict": entry.get("verdict") or "uncertain",
                    "confidence": entry.get("confidence"),
                    "rationale": entry.get("rationale"),
                    "sources": entry.get("sources"),
                }
            )

    if not entries:
        return

    question_bank_id = question_row.get("id")
    async with session.begin():
        await _set_verification_worker_context(
            session,
            org_id=str(org_id),
            user_id=str(owner_user_id),
        )

        if question_bank_id:
            await session.execute(
                text(
                    "UPDATE project_stage_verification_claims "
                    "SET deleted_at = now() "
                    "WHERE project_id = :project_id "
                    "AND org_id = :org_id "
                    "AND question_bank_question_id = :question_bank_question_id "
                    "AND deleted_at IS NULL"
                ),
                {
                    "project_id": project_id,
                    "org_id": org_id,
                    "question_bank_question_id": question_bank_id,
                },
            )

        rows = []
        seen_claims: set[str] = set()
        for entry in entries:
            claim_text = entry.get("claim") or ""
            if claim_text in seen_claims:
                continue
            seen_claims.add(claim_text)
            rows.append(
                {
                    "org_id": str(org_id),
                    "project_id": str(project_id),
                    "assessment_id": None,
                    "stage": stage,
                    "question_id": question_id,
                    "question_bank_question_id": question_bank_id,
                    "source_message_id": latest_message_id,
                    "priority": priority,
                    "batch_id": str(batch_id),
                    "claim": claim_text,
                    "verdict": entry.get("verdict") or "uncertain",
                    "confidence": entry.get("confidence"),
                    "rationale": entry.get("rationale"),
                    "sources": entry.get("sources"),
                    "evidence_mode": evidence_mode,
                }
            )

        if rows:
            await session.execute(
                text(
                    "INSERT INTO project_stage_verification_claims ("
                    "org_id, project_id, assessment_id, stage, question_id, "
                    "question_bank_question_id, source_message_id, priority, batch_id, "
                    "claim, verdict, confidence, rationale, sources, evidence_mode"
                    ") VALUES ("
                    ":org_id, :project_id, :assessment_id, :stage, :question_id, "
                    ":question_bank_question_id, :source_message_id, :priority, :batch_id, "
                    ":claim, :verdict, :confidence, :rationale, :sources, :evidence_mode"
                    ")"
                ).bindparams(bindparam("sources", type_=JSONB)),
                rows,
            )


__all__ = ["run_verify_question_claims_v0"]
