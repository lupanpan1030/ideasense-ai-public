from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.answer_meta import get_answer_meta_map
from app.services.diagnostics import (
    build_context_card,
    summarize_verification_claim_rows,
)
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths
from app.services.stage_payloads import normalize_user_edited_map


async def fetch_project_context(
    session: AsyncSession,
    project_id: Any,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT "
            "p.id AS project_id, "
            "p.current_stage AS project_stage, "
            "p.updated_at AS project_updated_at, "
            "pr.stage AS runtime_stage, "
            "pr.turn_state, "
            "pr.missing_paths, "
            "pr.updated_at AS runtime_updated_at, "
            "cur.question_id AS current_question_id, "
            "nxt.question_id AS next_question_id, "
            "ps.state_json, "
            "ps.state_meta, "
            "ps.state_version, "
            "ps.updated_at AS state_updated_at "
            "FROM projects p "
            "LEFT JOIN project_runtime pr "
            "ON pr.project_id = p.id "
            "AND pr.org_id = p.org_id "
            "AND pr.deleted_at IS NULL "
            "LEFT JOIN question_bank_questions cur "
            "ON cur.id = pr.current_question_bank_question_id "
            "AND cur.deleted_at IS NULL "
            "LEFT JOIN question_bank_questions nxt "
            "ON nxt.id = pr.next_question_bank_question_id "
            "AND nxt.deleted_at IS NULL "
            "LEFT JOIN project_states ps "
            "ON ps.project_id = p.id "
            "AND ps.org_id = p.org_id "
            "AND ps.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    stage = row.get("runtime_stage") or row.get("project_stage") or "problem"
    current_question_id = row.get("current_question_id")
    next_question_id = row.get("next_question_id") or current_question_id
    turn_state = row.get("turn_state") or "draft"
    data = row.get("state_json") or {}
    if not isinstance(data, dict):
        data = {}
    state_meta = row.get("state_meta") or {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    missing_fields = filter_stage_blocking_missing_paths(
        stage,
        list(row.get("missing_paths") or []),
        state_json=data,
        state_meta=state_meta,
    )
    verification_result = await session.execute(
        text(
            "SELECT stage, claim, verdict, confidence, created_at "
            "FROM project_stage_verification_claims "
            "WHERE project_id = :project_id "
            "AND org_id = app_org_id() "
            "AND stage = :stage "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 25"
        ),
        {"project_id": str(project_id), "stage": stage},
    )
    context_version = row.get("state_version")
    if context_version is None:
        context_version = 0

    return {
        "project_id": row.get("project_id"),
        "stage": stage,
        "current_question_id": current_question_id,
        "next_question_id": next_question_id,
        "turn_state": turn_state,
        "missing_fields": missing_fields,
        "data": data,
        "user_edited_paths": normalize_user_edited_map(state_meta),
        "answer_meta": get_answer_meta_map(state_meta),
        "context_card": build_context_card(
            stage=stage,
            state_json=data,
            state_meta=state_meta,
            missing_paths=missing_fields,
            verification_summary=summarize_verification_claim_rows(
                verification_result.mappings().all()
            ),
        ),
        "context_version": context_version,
        "updated_at": row.get("state_updated_at")
        or row.get("project_updated_at")
        or row.get("runtime_updated_at"),
    }


__all__ = ["fetch_project_context"]
