from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.answer_meta import set_answer_meta_entry
from app.services.context_backfill import backfill_problem_idea_raw
from app.services.context_paths import (
    set_context_path_value as _set_path,
)
from app.services.answer_extraction_worker_fallbacks import _apply_extraction_fallbacks
from app.services.answer_extraction_worker_market import (
    adjust_answer_extraction_market_missing_paths as _adjust_missing_paths_for_market,
    canonicalize_extracted_value as _canonicalize_extracted_value,
    canonicalize_market_type_fields as _canonicalize_market_type_fields,
)
from app.services.extraction_transforms import (
    build_extraction_targets as _build_extraction_targets,
    extract_value_meta as _extract_value_meta,
    get_nested_state_value as _get_nested_state_value,
    has_explicit_none as _has_explicit_none,
    is_non_empty as _is_non_empty,
    remap_extracted as _remap_extracted,
    split_state_path as _split_state_path,
)
from app.services.project_state_events import record_project_state_event
from app.services.stage_gate_paths import filter_stage_blocking_missing_paths
from app.services.stage_runtime import (
    update_project_runtime_missing_paths_from_decision,
    update_project_stage_status_from_decision,
)
from app.services.stage_transition import decide_stage_ready
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
)


logger = logging.getLogger("ideasense.worker.answer_extraction")
PROMPT_CONTEXT_BUILDER = PromptContextBuilder()
WorkerContextSetter = Callable[[Any, str | None], Awaitable[None]]


async def _commit_if_transaction_open(session) -> None:
    if session.in_transaction():
        await session.commit()


def _should_skip_authoritative_extract_mutation(stage_status: str | None) -> bool:
    return stage_status == "awaiting_confirm"


def _prepare_authoritative_extraction_updates(
    schema_paths: list[str],
    extracted: dict[str, Any],
    current_stage: str,
    user_text: str,
) -> tuple[list[str], list[tuple[str, str, Any]]]:
    remapped = _remap_extracted(
        extracted,
        schema_paths,
        canonicalize_value=_canonicalize_extracted_value,
    )
    remapped = _apply_extraction_fallbacks(schema_paths, remapped, user_text)
    if _has_explicit_none(user_text):
        for path in schema_paths:
            if path.endswith("data_evidence") and not _is_non_empty(remapped.get(path)):
                remapped[path] = "None yet"
    return _build_extraction_targets(
        remapped,
        current_stage,
        canonicalize_value=_canonicalize_extracted_value,
    )


def _answer_meta_needs_refresh(state_meta: dict[str, Any], path: str) -> bool:
    answer_meta = state_meta.get("answer_meta")
    if not isinstance(answer_meta, dict):
        return True
    entry = answer_meta.get(path)
    if not isinstance(entry, dict):
        return True
    return entry.get("resolution_status") != "answered"


def _apply_authoritative_extraction_updates(
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    updates: list[tuple[str, str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    pending_confirm = state_meta.get("pending_confirm")
    if not isinstance(pending_confirm, dict):
        pending_confirm = {}

    changed = False
    for target, path, value in updates:
        value, meta_update = _extract_value_meta(
            value,
            default_source="ai" if target == "pending" else "user",
        )
        value = _canonicalize_extracted_value(path, value)
        current_value = _get_nested_state_value(
            state_json if target == "state" else pending_confirm,
            _split_state_path(path),
        )
        if target == "state":
            if current_value != value:
                _set_path(state_json, path, value)
                changed = True
            if _answer_meta_needs_refresh(state_meta, path):
                set_answer_meta_entry(
                    state_meta,
                    path,
                    **meta_update,
                )
                changed = True
        else:
            pending_value = {"value": value, **meta_update}
            if current_value != pending_value:
                _set_path(pending_confirm, path, pending_value)
                changed = True

    state_meta["pending_confirm"] = pending_confirm
    if backfill_problem_idea_raw(state_json, state_meta, source="user"):
        changed = True
    if _canonicalize_market_type_fields(state_json):
        changed = True
    return state_json, state_meta, changed


async def _extract_with_openai(
    session,
    schema_paths: list[str],
    user_text: str,
    *,
    project_settings: dict | None = None,
) -> dict[str, Any]:
    context = PROMPT_CONTEXT_BUILDER.extraction(schema_paths, user_text)
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
        timeout_minimum_ms=200,
    )
    if not result.ok:
        reason = result.failure.reason if result.failure else "unknown"
        raise RuntimeError(f"extract_answer_v0 prompt task failed: {reason}")
    if not isinstance(result.parsed, dict):
        raise RuntimeError("extract_answer_v0 prompt task returned invalid payload.")
    return result.parsed


async def run_extract_answer_v0(
    session,
    payload: dict[str, Any],
    *,
    job_org_id: str | None = None,
    set_worker_context_fn: WorkerContextSetter | None = None,
) -> None:
    project_id = payload.get("project_id")
    question_instance_id = payload.get("question_instance_id")
    message_id = payload.get("message_id")
    if not project_id or not question_instance_id or not message_id:
        raise ValueError("Job payload missing required identifiers.")

    async with session.begin():
        if set_worker_context_fn is not None:
            await set_worker_context_fn(session, job_org_id)
        project_result = await session.execute(
            text(
                "SELECT id, org_id, owner_user_id, current_stage, current_variant, "
                "stage_status, question_bank_version_id, settings "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": project_id},
        )
        project_row = project_result.mappings().first()
        if not project_row:
            raise ValueError("Project not found for extraction job.")

        org_id = project_row.get("org_id")
        owner_user_id = project_row.get("owner_user_id")
        if not org_id:
            raise ValueError("Project missing org_id.")
        if not owner_user_id:
            raise ValueError("Project missing owner_user_id.")

        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(owner_user_id)},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )

        runtime_result = await session.execute(
            text(
                "SELECT missing_paths "
                "FROM project_runtime "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": project_id, "org_id": org_id},
        )
        runtime_row = runtime_result.mappings().first()
        if not runtime_row:
            raise ValueError("Project runtime not found for extraction job.")
        missing_paths = list(runtime_row.get("missing_paths") or [])

        question_result = await session.execute(
            text(
                "SELECT q.schema_paths, q.stage "
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
            raise ValueError("Question instance not found for extraction job.")

        schema_paths = list(question_row.get("schema_paths") or [])
        if not schema_paths:
            return

        message_result = await session.execute(
            text(
                "SELECT content "
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
            raise ValueError("User messages not found for extraction job.")

        parts: list[str] = []
        for row in message_rows:
            content = row.get("content")
            if isinstance(content, str):
                cleaned = content.strip()
                if cleaned:
                    parts.append(cleaned)
        if not parts:
            raise ValueError("User messages are empty for extraction job.")

        user_text = "\n\n".join(parts)
        current_stage = project_row.get("current_stage") or "problem"
        current_variant = project_row.get("current_variant")
        stage_status = project_row.get("stage_status")
        bank_version_id = project_row.get("question_bank_version_id")

    if _should_skip_authoritative_extract_mutation(stage_status):
        return

    try:
        extracted = await _extract_with_openai(
            session,
            schema_paths,
            user_text,
            project_settings=(
                project_row.get("settings") if isinstance(project_row, dict) else None
            ),
        )
    except RuntimeError as exc:
        logger.warning(
            "authoritative extraction prompt failed; applying local fallbacks: %s",
            exc,
        )
        extracted = {}
    await _commit_if_transaction_open(session)
    resolved_paths, updates = _prepare_authoritative_extraction_updates(
        schema_paths,
        extracted,
        current_stage,
        user_text,
    )

    if not resolved_paths:
        return

    async with session.begin():
        await session.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": str(owner_user_id)},
        )
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": "system"},
        )

        state_result = await session.execute(
            text(
                "SELECT state_json, state_meta, state_version "
                "FROM project_states "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": project_id, "org_id": org_id},
        )
        state_row = state_result.mappings().first()
        state_json = state_row.get("state_json") if state_row else {}
        if not isinstance(state_json, dict):
            state_json = {}
        state_meta = state_row.get("state_meta") if state_row else {}
        if not isinstance(state_meta, dict):
            state_meta = {}
        state_json, state_meta, state_changed = _apply_authoritative_extraction_updates(
            state_json, state_meta, updates
        )

        if not state_row:
            next_version = 1
            await session.execute(
                text(
                    "INSERT INTO project_states ("
                    "project_id, org_id, bank_version_id, "
                    "state_json, state_meta, state_version"
                    ") VALUES ("
                    ":project_id, :org_id, :bank_version_id, "
                    ":state_json, :state_meta, :state_version"
                    ")"
                ).bindparams(
                    bindparam("state_json", type_=JSONB),
                    bindparam("state_meta", type_=JSONB),
                ),
                {
                    "project_id": project_id,
                    "org_id": org_id,
                    "bank_version_id": bank_version_id,
                    "state_json": state_json,
                    "state_meta": state_meta,
                    "state_version": next_version,
                },
            )
            await record_project_state_event(
                session,
                org_id=str(org_id),
                project_id=str(project_id),
                question_instance_id=str(question_instance_id),
                event_type="apply_patch",
                patch_json={
                    "source": "authoritative_extract",
                    "stage": current_stage,
                    "variant": current_variant,
                    "resolved_paths": resolved_paths,
                },
                actor_type="system",
                prev_state_version=0,
                next_state_version=next_version,
            )
        elif state_changed:
            prev_version = state_row.get("state_version") if state_row else 0
            next_version = prev_version + 1
            await session.execute(
                text(
                    "UPDATE project_states "
                    "SET state_json = :state_json, "
                    "state_meta = :state_meta, "
                    "state_version = :state_version "
                    "WHERE project_id = :project_id "
                    "AND org_id = :org_id "
                    "AND deleted_at IS NULL"
                ).bindparams(
                    bindparam("state_json", type_=JSONB),
                    bindparam("state_meta", type_=JSONB),
                ),
                {
                    "project_id": project_id,
                    "org_id": org_id,
                    "state_json": state_json,
                    "state_meta": state_meta,
                    "state_version": next_version,
                },
            )
            await record_project_state_event(
                session,
                org_id=str(org_id),
                project_id=str(project_id),
                question_instance_id=str(question_instance_id),
                event_type="apply_patch",
                patch_json={
                    "source": "authoritative_extract",
                    "stage": current_stage,
                    "variant": current_variant,
                    "resolved_paths": resolved_paths,
                },
                actor_type="system",
                prev_state_version=prev_version,
                next_state_version=next_version,
            )

        updated_missing_paths = [
            path for path in missing_paths if path not in resolved_paths
        ]
        updated_missing_paths = filter_stage_blocking_missing_paths(
            question_row.get("stage") if question_row else None,
            updated_missing_paths,
            state_json=state_json,
            state_meta=state_meta,
        )
        question_stage = question_row.get("stage") if question_row else None
        if question_stage == "market":
            updated_missing_paths = _adjust_missing_paths_for_market(
                state_json, updated_missing_paths, resolved_paths
            )
        stage_ready_decision = decide_stage_ready(
            question_stage,
            updated_missing_paths,
            state_json=state_json,
            state_meta=state_meta,
            variant=current_variant,
        )
        if updated_missing_paths != missing_paths:
            await update_project_runtime_missing_paths_from_decision(
                session,
                project_id=project_id,
                org_id=org_id,
                decision=stage_ready_decision,
            )

            if stage_ready_decision.allowed:
                await update_project_stage_status_from_decision(
                    session,
                    project_id=project_id,
                    org_id=org_id,
                    decision=stage_ready_decision,
                    current_stage=current_stage,
                    require_allowed=True,
                )
