import asyncio
import logging
import time
from contextlib import suppress
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import (
    ActorContext,
    get_actor_context,
    normalize_org_header,
    resolve_org_membership,
    set_system_actor,
)
from app.core.database_async import AdminAsyncSessionLocal
from app.core.email_verification import is_email_verified
from app.services.chat_ai_assist import (
    ai_draft_message_parts as _ai_draft_message_parts,
    ai_draft_unavailable_message as _ai_draft_unavailable_message,
    format_ai_draft_message as _format_ai_draft_message,
    is_ai_assist_request as _is_ai_assist_request,
    mark_ai_draft_requested as _mark_ai_draft_requested,
    persist_ai_draft_message as _persist_ai_draft_message,
    run_ai_assist_draft_stream as _run_ai_assist_draft_stream,
)
from app.services.chat_answer_actions import (
    resolve_chat_answer_action,
)
from app.services.chat_background_jobs import enqueue_chat_pass_background_jobs
from app.services.chat_context_reads import (
    fetch_chat_answer_history as _fetch_chat_answer_history,
    fetch_chat_question_detail_context as _fetch_chat_question_detail_context,
    fetch_chat_state_context as _fetch_chat_state_context,
)
from app.services.chat_followup_compose import (
    QUESTION_COMPOSE_FALLBACK_SOURCE,
)
from app.services.chat_output_locale import (
    resolve_interview_output_locale as _resolve_interview_output_locale,
)
from app.services.chat_question_runtime import (
    ensure_question_instance as _ensure_question_instance,
    plan_question_prompt as _plan_question_prompt,
    resolve_answer_rubric_id as _resolve_answer_rubric_id,
)
from app.services.chat_router_mode import (
    augment_router_mode_message_meta as _augment_router_mode_message_meta,
    resolve_explicit_router_mode as _resolve_explicit_router_mode,  # noqa: F401 - kept as a test/helper module export.
)
from app.services.chat_runtime_settings import (
    resolve_question_group_settings as _resolve_question_group_settings,
    resolve_question_planner_settings as _resolve_question_planner_settings,
)
from app.services.chat_turn_evaluation import (
    evaluate_chat_turn as _evaluate_chat_turn,
)
from app.services.chat_turn_preflight import (
    build_chat_gate_context as _build_chat_gate_context,
    insert_chat_user_message as _insert_chat_user_message,
)
from app.services.chat_turn_commit import (
    apply_chat_state_updates as _apply_chat_state_updates,
    commit_answer_status as _commit_answer_status,
    commit_needs_info_turn as _commit_needs_info_turn,
    commit_router_mode_next_turn as _commit_router_mode_next_turn,
    commit_standard_next_turn as _commit_standard_next_turn,
    insert_answer_evaluation as _insert_answer_evaluation,
    update_runtime_metadata_after_answer as _update_runtime_metadata_after_answer,
)
from app.services.chat_turn_payloads import (
    build_answer_scores_payload as _build_answer_scores_payload,
)
from app.services.chat_stream.events import (
    build_stream_error_payload as _build_stream_error_payload,
    build_turn_event_meta as _build_turn_event_meta,
    sse_event as _sse_event,
    sse_status_event as _sse_status_event,
    stream_text_events as _stream_text_events,
)
from app.services.chat_stream.latency import (
    latency_span as _latency_span,
    log_chat_stream_latency as _log_chat_stream_latency,
    record_latency_span as _record_latency_span,
)
from app.services.chat_stream.message_persistence import (
    persist_fallback_question_message as _persist_fallback_question_message,
)
from app.services.chat_stream.question_response import (
    stream_question_response_events as _stream_question_response_events,
)
from app.services.localization import (
    normalize_output_locale,
)
from app.services.stage_transition import (
    decide_stage_question_answer,
)
from app.services.prompt_output_parsers import (
    AnswerGateScore,  # noqa: F401 - kept as a test/helper module export.
)
from app.core.usage_limits import UsageLimitError, enforce_llm_usage_limits

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("ideasense.chat")

class ChatStreamRequest(BaseModel):
    project_id: UUID
    message: str
    message_meta: dict[str, Any] | None = None
    client_message_id: UUID | None = None
    output_locale: Literal["en", "zh"] | None = None


def _cancel_pending_read_tasks(tasks: list[asyncio.Task[Any]]) -> None:
    for task in tasks:
        task.add_done_callback(_consume_background_task_result)
        if not task.done():
            task.cancel()


def _consume_background_task_result(task: asyncio.Task[Any]) -> None:
    with suppress(asyncio.CancelledError):
        try:
            task.result()
        except Exception:
            logger.warning("background chat task failed", exc_info=True)


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> StreamingResponse:
    output_locale = normalize_output_locale(payload.output_locale)
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message is required.",
        )
    message_meta = (
        payload.message_meta if isinstance(payload.message_meta, dict) else None
    )
    answer_action_context = resolve_chat_answer_action(message_meta)
    answer_action = answer_action_context.answer_action
    skip_requested = answer_action_context.skip_requested
    skip_reason = answer_action_context.skip_reason
    skip_resolution_status = answer_action_context.skip_resolution_status
    force_ai_assist = answer_action_context.force_ai_assist
    turn_request_id = str(uuid4())
    client_message_id = (
        str(payload.client_message_id) if payload.client_message_id else None
    )
    turn_event_meta: dict[str, Any] = {
        "request_id": turn_request_id,
        "client_message_id": client_message_id,
    }

    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for chat streaming.",
        )

    async def raw_event_stream(
        latency_spans: dict[str, float],
        stream_context: dict[str, Any],
    ):
        yield _sse_status_event("checking_answer", output_locale, turn_event_meta)

        explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
        assistant_content = ""
        stage_gate_ready_payload = None
        question_meta_payload = None
        early_stream = None
        early_stream_model = None
        early_stream_context: dict[str, Any] | None = None
        gate_context: dict[str, Any] = {}
        question_stream_context: dict[str, Any] | None = None
        queued_extract_job = False
        extract_queued_payload: dict[str, Any] | None = None
        preflight_started_at = time.perf_counter()
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                with _latency_span(latency_spans, "preflight.membership"):
                    await set_system_actor(session)
                    membership = await resolve_org_membership(
                        session,
                        user_id=str(actor.user_id),
                        explicit_org_id=explicit_org_id,
                    )
                    org_id = membership.get("org_id")
                    if not org_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="No active organization membership.",
                        )

                with _latency_span(latency_spans, "preflight.rls_context"):
                    await session.execute(
                        text("SELECT set_config('app.user_id', :user_id, true)"),
                        {"user_id": str(actor.user_id)},
                    )
                    await session.execute(
                        text("SELECT set_config('app.org_id', :org_id, true)"),
                        {"org_id": str(org_id)},
                    )
                    await session.execute(
                        text("SELECT set_config('app.actor_type', :actor_type, true)"),
                        {"actor_type": "user"},
                    )

                with _latency_span(latency_spans, "preflight.project_runtime"):
                    result = await session.execute(
                        text(
                            "SELECT "
                            "p.id AS project_id, "
                            "p.question_bank_version_id, "
                            "p.current_stage, "
                            "p.current_variant, "
                            "p.stage_status, "
                            "p.settings, "
                            "pr.stage AS runtime_stage, "
                            "pr.variant AS runtime_variant, "
                            "pr.current_question_bank_question_id, "
                            "pr.next_question_bank_question_id, "
                            "pr.missing_paths, "
                            "pr.runtime_version "
                            "FROM projects p "
                            "JOIN project_runtime pr "
                            "ON pr.project_id = p.id "
                            "AND pr.org_id = p.org_id "
                            "AND pr.deleted_at IS NULL "
                            "WHERE p.id = :project_id "
                            "AND p.org_id = app_org_id() "
                            "AND p.deleted_at IS NULL "
                            "LIMIT 1"
                        ),
                        {"project_id": str(payload.project_id)},
                    )
                    row = result.mappings().first()
                    if not row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Project not found.",
                        )

                    question_action_decision = decide_stage_question_answer(
                        current_stage=row.get("current_stage"),
                        stage_status=row.get("stage_status"),
                    )
                    if question_action_decision.reason == "stage_blocks_questions":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Chat is disabled for report stage.",
                        )
                    if question_action_decision.reason == "stage_not_in_progress":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                "Stage is waiting for confirmation. Review or confirm "
                                "the stage before answering more questions."
                            ),
                        )
                    if question_action_decision.reason == "stage_passed":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Stage is already complete.",
                        )
                    if not question_action_decision.allowed:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Project stage is not ready for chat.",
                        )

                with _latency_span(latency_spans, "preflight.email_verification"):
                    is_verified = await is_email_verified(
                        session, user_id=str(actor.user_id)
                    )
                    current_stage = row.get("current_stage")
                    if not is_verified and current_stage != "problem":
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Verify your email to continue beyond the problem stage.",
                        )
                with _latency_span(latency_spans, "preflight.usage_limit"):
                    try:
                        await enforce_llm_usage_limits(
                            session, user_id=str(actor.user_id), is_verified=is_verified
                        )
                    except UsageLimitError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=str(exc),
                        ) from exc

                with _latency_span(latency_spans, "preflight.question_instance"):
                    current_question_id = row.get("current_question_bank_question_id")
                    if not current_question_id:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Current question not initialized.",
                        )

                    instance_result = await session.execute(
                        text(
                            "SELECT id "
                            "FROM project_question_instances "
                            "WHERE project_id = :project_id "
                            "AND question_bank_question_id = :question_id "
                            "AND deleted_at IS NULL "
                            "LIMIT 1"
                        ),
                        {
                            "project_id": row.get("project_id"),
                            "question_id": current_question_id,
                        },
                    )
                    instance_row = instance_result.mappings().first()
                    if not instance_row:
                        current_question_instance_id = await _ensure_question_instance(
                            session,
                            row.get("project_id"),
                            current_question_id,
                        )
                    else:
                        current_question_instance_id = instance_row.get("id")

                project_id_value = str(row.get("project_id"))
                org_id_value = str(org_id)
                user_id_value = str(actor.user_id)
                effective_message_meta = _augment_router_mode_message_meta(
                    message_meta,
                    message,
                    runtime_stage=row.get("runtime_stage"),
                    runtime_variant=row.get("runtime_variant"),
                )
                parallel_read_tasks = [
                    asyncio.create_task(
                        _fetch_chat_question_detail_context(
                            org_id=org_id_value,
                            user_id=user_id_value,
                            project_id=project_id_value,
                            question_id=current_question_id,
                            question_instance_id=current_question_instance_id,
                            latency_spans=latency_spans,
                        )
                    ),
                    asyncio.create_task(
                        _fetch_chat_state_context(
                            org_id=org_id_value,
                            user_id=user_id_value,
                            project_id=project_id_value,
                            latency_spans=latency_spans,
                        )
                    ),
                    asyncio.create_task(
                        _fetch_chat_answer_history(
                            org_id=org_id_value,
                            user_id=user_id_value,
                            project_id=project_id_value,
                            question_instance_id=current_question_instance_id,
                            latency_spans=latency_spans,
                        )
                    ),
                ]

                try:
                    with _latency_span(latency_spans, "preflight.insert_user_message"):
                        user_message_id = await _insert_chat_user_message(
                            session,
                            project_id=row.get("project_id"),
                            actor_user_id=str(actor.user_id),
                            stage=row.get("runtime_stage"),
                            variant=row.get("runtime_variant"),
                            question_instance_id=current_question_instance_id,
                            content=message,
                            message_meta=effective_message_meta,
                            client_message_id=client_message_id,
                            request_id=turn_request_id,
                        )
                        if user_message_id is None:
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Unable to persist user message.",
                            )
                    (
                        question_detail,
                        (state_json, state_meta),
                        previous_answer_parts,
                    ) = await asyncio.gather(*parallel_read_tasks)
                except Exception:
                    _cancel_pending_read_tasks(parallel_read_tasks)
                    raise
                turn_event_meta["user_message_id"] = int(user_message_id)
                turn_event_meta["source_message_id"] = int(user_message_id)

                gate_context = _build_chat_gate_context(
                    project_row=row,
                    org_id=str(org_id),
                    current_question_id=current_question_id,
                    current_question_instance_id=current_question_instance_id,
                    user_message_id=user_message_id,
                    request_id=turn_request_id,
                    client_message_id=client_message_id,
                    question_detail=question_detail,
                    state_json=state_json,
                    state_meta=state_meta,
                    previous_answer_parts=previous_answer_parts,
                    latest_message=message,
                    message_meta=effective_message_meta,
                    output_locale=output_locale,
                )
                cleaned_message = gate_context["latest_answer"]
                context_summary = gate_context.get("context_summary")

                stream_context["project_id"] = gate_context.get("project_id")
                if force_ai_assist or _is_ai_assist_request(message):
                    ai_assist_started_at = time.perf_counter()
                    draft_output_locale = _resolve_interview_output_locale(
                        cleaned_message,
                        output_locale,
                        context_summary=context_summary,
                        message_meta=effective_message_meta,
                    )
                    await _mark_ai_draft_requested(
                        session,
                        project_id=str(row.get("project_id")),
                        question_instance_id=current_question_instance_id,
                    )
                    stream_result, draft_model, _output_locale, draft = (
                        await _run_ai_assist_draft_stream(
                            session,
                            question_detail,
                            context_summary,
                            cleaned_message,
                            output_locale=draft_output_locale,
                            project_settings=gate_context.get("project_settings"),
                        )
                    )
                    if stream_result:
                        early_stream = stream_result.stream
                        early_stream_model = draft_model
                        early_stream_context = {
                            "project_id": str(row.get("project_id")),
                            "org_id": str(org_id),
                            "stage": row.get("runtime_stage"),
                            "variant": row.get("runtime_variant"),
                            "question_instance_id": current_question_instance_id,
                            "output_locale": draft_output_locale,
                            "request_id": turn_request_id,
                            "client_message_id": client_message_id,
                            "user_message_id": int(user_message_id),
                        }
                    else:
                        if not draft:
                            assistant_content = _ai_draft_unavailable_message(
                                draft_output_locale
                            )
                        else:
                            assistant_content = _format_ai_draft_message(
                                draft,
                                output_locale=draft_output_locale,
                            )
                        await _persist_ai_draft_message(
                            session,
                            project_id=str(row.get("project_id")),
                            org_id=str(org_id),
                            stage=row.get("runtime_stage"),
                            variant=row.get("runtime_variant"),
                            question_instance_id=current_question_instance_id,
                            assistant_content=assistant_content,
                            draft=draft,
                            draft_model=draft_model,
                            content_locale=draft_output_locale,
                        )

                    _record_latency_span(
                        latency_spans,
                        "preflight.ai_assist",
                        ai_assist_started_at,
                    )
                    early_response = True
                else:
                    early_response = False

        _record_latency_span(latency_spans, "preflight", preflight_started_at)
        if "early_response" in locals() and early_response:
            final_content = assistant_content
            if early_stream and early_stream_context:
                event_meta = _build_turn_event_meta(early_stream_context)
                draft_chunks: list[str] = []
                draft_output_locale = normalize_output_locale(
                    early_stream_context.get("output_locale")
                )
                intro, draft_prefix, guidance = _ai_draft_message_parts(
                    draft_output_locale
                )
                prefix = f"{intro}\n\n{draft_prefix}"
                suffix = f"\n\n{guidance}"

                first_chunk_sent = False
                async for chunk in early_stream:
                    if not chunk:
                        continue
                    if not first_chunk_sent:
                        first_chunk_sent = True
                        yield _sse_event("assistant_first_token", event_meta)
                        if prefix:
                            yield _sse_event("token", {"delta": prefix, **event_meta})
                    draft_chunks.append(chunk)
                    yield _sse_event("token", {"delta": chunk, **event_meta})

                if not first_chunk_sent:
                    final_content = _ai_draft_unavailable_message(draft_output_locale)
                    async for event in _stream_text_events(
                        final_content,
                        event_meta=event_meta,
                        emit_markers=True,
                    ):
                        yield event
                    draft_text = None
                else:
                    if suffix:
                        yield _sse_event("token", {"delta": suffix, **event_meta})
                    draft_raw = "".join(draft_chunks)
                    final_content = f"{prefix}{draft_raw}{suffix}"
                    draft_text = draft_raw.strip().strip('"').strip("'").strip()

                async with AdminAsyncSessionLocal() as session:
                    async with session.begin():
                        await set_system_actor(session)
                        await session.execute(
                            text("SELECT set_config('app.user_id', :user_id, true)"),
                            {"user_id": str(actor.user_id)},
                        )
                        await session.execute(
                            text("SELECT set_config('app.org_id', :org_id, true)"),
                            {"org_id": early_stream_context["org_id"]},
                        )
                        await session.execute(
                            text(
                                "SELECT set_config('app.actor_type', :actor_type, true)"
                            ),
                            {"actor_type": "system"},
                        )
                        await _persist_ai_draft_message(
                            session,
                            project_id=early_stream_context["project_id"],
                            org_id=early_stream_context["org_id"],
                            stage=early_stream_context.get("stage"),
                            variant=early_stream_context.get("variant"),
                            question_instance_id=early_stream_context[
                                "question_instance_id"
                            ],
                            assistant_content=final_content,
                            draft=draft_text,
                            draft_model=early_stream_model,
                            content_locale=draft_output_locale,
                        )
                if first_chunk_sent:
                    yield _sse_event("assistant_done", event_meta)
            elif final_content:
                async for event in _stream_text_events(
                    final_content,
                    event_meta=turn_event_meta,
                    emit_markers=True,
                ):
                    yield event
            yield _sse_event("done", {"status": "ok", **turn_event_meta})

            return
        group_enabled, group_max, transition_enabled = (
            _resolve_question_group_settings()
        )
        planner_settings = _resolve_question_planner_settings()

        evaluation = await _evaluate_chat_turn(
            gate_context,
            previous_answer_count=len(previous_answer_parts),
            skip_requested=skip_requested,
            skip_reason=skip_reason,
            skip_resolution_status=skip_resolution_status,
            latency_spans=latency_spans,
        )
        decision = evaluation.decision
        gate_model = evaluation.gate_model
        extracted_payload = evaluation.extracted_payload
        resolved_paths = evaluation.resolved_paths
        extraction_updates = evaluation.extraction_updates
        schema_paths = evaluation.schema_paths
        partial_unknown_paths = evaluation.partial_unknown_paths
        followup_message = evaluation.followup_message
        prompt_task_traces = evaluation.prompt_task_traces
        rolling_summary = evaluation.rolling_summary
        key_points = evaluation.key_points
        chosen_mode = evaluation.chosen_mode
        gate_context = evaluation.gate_context

        planned_question_id = None
        planned_question_prompt = None
        if decision["final_verdict"] == "pass":
            yield _sse_status_event(
                "preparing_next_question",
                output_locale,
                turn_event_meta,
            )
            planned_question_id, planned_question_prompt = await _plan_question_prompt(
                gate_context,
                resolved_paths,
                chosen_mode,
            )

        db_commit_started_at = time.perf_counter()
        async with AdminAsyncSessionLocal() as session:
            async with session.begin():
                with _latency_span(latency_spans, "db_commit.membership"):
                    await set_system_actor(session)
                    membership = await resolve_org_membership(
                        session,
                        user_id=str(actor.user_id),
                        explicit_org_id=explicit_org_id,
                    )
                    org_id = membership.get("org_id")
                    if not org_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="No active organization membership.",
                        )

                with _latency_span(latency_spans, "db_commit.rls_context"):
                    await session.execute(
                        text("SELECT set_config('app.user_id', :user_id, true)"),
                        {"user_id": str(actor.user_id)},
                    )
                    await session.execute(
                        text("SELECT set_config('app.org_id', :org_id, true)"),
                        {"org_id": str(org_id)},
                    )
                    await session.execute(
                        text("SELECT set_config('app.actor_type', :actor_type, true)"),
                        {"actor_type": "system"},
                    )

                with _latency_span(latency_spans, "db_commit.runtime_check"):
                    runtime_check = await session.execute(
                        text(
                            "SELECT runtime_version, current_question_bank_question_id, "
                            "next_question_bank_question_id, stage, variant, missing_paths "
                            "FROM project_runtime "
                            "WHERE project_id = :project_id "
                            "AND org_id = :org_id "
                            "AND deleted_at IS NULL "
                            "LIMIT 1"
                        ),
                        {
                            "project_id": gate_context["project_id"],
                            "org_id": str(org_id),
                        },
                    )
                    runtime_row = runtime_check.mappings().first()
                    if not runtime_row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Project runtime not found.",
                        )

                    if (
                        int(runtime_row.get("runtime_version") or 0)
                        != gate_context["runtime_version"]
                        or runtime_row.get("current_question_bank_question_id")
                        != gate_context["current_question_id"]
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Project runtime changed. Refresh and try again.",
                        )

                with _latency_span(latency_spans, "db_commit.rubric"):
                    rubric_id = await _resolve_answer_rubric_id(session)
                scores_payload = _build_answer_scores_payload(
                    decision,
                    skip_requested=skip_requested,
                    prompt_task_traces=prompt_task_traces,
                )
                evaluator_model = gate_model
                request_id = str(uuid4())

                if decision["final_verdict"] != "pass":
                    needs_info_result = await _commit_needs_info_turn(
                        session,
                        org_id=str(org_id),
                        gate_context=gate_context,
                        runtime_row=runtime_row,
                        decision=decision,
                        followup_message=followup_message,
                        rolling_summary=rolling_summary,
                        key_points=key_points,
                        request_id=request_id,
                        turn_event_meta=turn_event_meta,
                        latency_spans=latency_spans,
                    )
                    assistant_content = needs_info_result.assistant_content
                    question_meta_payload = needs_info_result.question_meta_payload
                    question_stream_context = needs_info_result.question_stream_context
                else:
                    await _commit_answer_status(
                        session,
                        org_id=str(org_id),
                        gate_context=gate_context,
                        skip_requested=skip_requested,
                        answer_action=answer_action,
                        skip_resolution_status=skip_resolution_status,
                        skip_reason=skip_reason,
                        latency_spans=latency_spans,
                    )
                    runtime_stage = runtime_row.get("stage")
                    runtime_variant = runtime_row.get("variant")
                    next_question_id = runtime_row.get("next_question_bank_question_id")
                    runtime_missing_paths = list(runtime_row.get("missing_paths") or [])
                    updated_missing_paths = runtime_missing_paths
                    stage_status_ready = None
                    state_json = None
                    state_meta = None

                    state_update_result = await _apply_chat_state_updates(
                        session,
                        org_id=str(org_id),
                        gate_context=gate_context,
                        runtime_stage=runtime_stage,
                        runtime_variant=runtime_variant,
                        resolved_paths=resolved_paths,
                        extraction_updates=extraction_updates,
                        schema_paths=schema_paths,
                        skip_requested=skip_requested,
                        skip_resolution_status=skip_resolution_status,
                        skip_reason=skip_reason,
                        partial_unknown_paths=partial_unknown_paths,
                        latency_spans=latency_spans,
                    )
                    state_json = state_update_result.state_json
                    state_meta = state_update_result.state_meta

                    runtime_metadata_result = (
                        await _update_runtime_metadata_after_answer(
                            session,
                            org_id=str(org_id),
                            gate_context=gate_context,
                            runtime_stage=runtime_stage,
                            runtime_variant=runtime_variant,
                            runtime_missing_paths=runtime_missing_paths,
                            resolved_paths=resolved_paths,
                            skip_requested=skip_requested,
                            state_json=state_json,
                            state_meta=state_meta,
                            latency_spans=latency_spans,
                        )
                    )
                    updated_missing_paths = runtime_metadata_result.updated_missing_paths
                    stage_status_ready = runtime_metadata_result.stage_status_ready

                    next_turn_started_at = time.perf_counter()
                    if runtime_stage == "tech" and runtime_variant == "router":
                        router_next_turn = await _commit_router_mode_next_turn(
                            session,
                            org_id=str(org_id),
                            gate_context=gate_context,
                            decision=decision,
                            chosen_mode=chosen_mode,
                            group_enabled=group_enabled,
                            group_max=group_max,
                            transition_enabled=transition_enabled,
                            planner_settings=planner_settings,
                            planned_question_id=planned_question_id,
                            planned_question_prompt=planned_question_prompt,
                            rolling_summary=rolling_summary,
                            key_points=key_points,
                            request_id=request_id,
                            turn_event_meta=turn_event_meta,
                        )
                        assistant_content = router_next_turn.assistant_content
                        question_meta_payload = router_next_turn.question_meta_payload
                        question_stream_context = router_next_turn.question_stream_context
                    else:
                        standard_next_turn = await _commit_standard_next_turn(
                            session,
                            org_id=str(org_id),
                            gate_context=gate_context,
                            runtime_row=runtime_row,
                            runtime_stage=runtime_stage,
                            runtime_variant=runtime_variant,
                            next_question_id=next_question_id,
                            updated_missing_paths=updated_missing_paths,
                            state_json=state_json,
                            stage_status_ready=stage_status_ready,
                            schema_paths=schema_paths,
                            decision=decision,
                            group_enabled=group_enabled,
                            group_max=group_max,
                            transition_enabled=transition_enabled,
                            planner_settings=planner_settings,
                            planned_question_id=planned_question_id,
                            planned_question_prompt=planned_question_prompt,
                            rolling_summary=rolling_summary,
                            key_points=key_points,
                            request_id=request_id,
                            turn_event_meta=turn_event_meta,
                        )
                        assistant_content = standard_next_turn.assistant_content
                        question_meta_payload = standard_next_turn.question_meta_payload
                        question_stream_context = (
                            standard_next_turn.question_stream_context
                        )
                        stage_gate_ready_payload = (
                            standard_next_turn.stage_gate_ready_payload
                        )

                    _record_latency_span(
                        latency_spans,
                        "db_commit.next_turn",
                        next_turn_started_at,
                    )

                    background_jobs_result = await enqueue_chat_pass_background_jobs(
                        session,
                        decision=decision,
                        skip_requested=skip_requested,
                        schema_paths=schema_paths,
                        gate_context=gate_context,
                        turn_event_meta=turn_event_meta,
                    )
                    queued_extract_job = background_jobs_result.queued_extract_job
                    extract_queued_payload = (
                        background_jobs_result.extract_queued_payload
                    )
                    if latency_spans is not None:
                        latency_spans.update(background_jobs_result.latency_spans)

                if question_stream_context:
                    with _latency_span(
                        latency_spans,
                        "db_commit.persist_fallback_message",
                    ):
                        await _persist_fallback_question_message(
                            session,
                            question_stream_context,
                            fallback_source=(
                                question_stream_context.get("fallback_source")
                                or QUESTION_COMPOSE_FALLBACK_SOURCE
                            ),
                        )

                with _latency_span(latency_spans, "db_commit.answer_evaluation"):
                    await _insert_answer_evaluation(
                        session,
                        org_id=str(org_id),
                        gate_context=gate_context,
                        rubric_id=str(rubric_id),
                        scores_payload=scores_payload,
                        overall_score=decision["overall"],
                        feedback_markdown=assistant_content,
                        evaluator_model=evaluator_model,
                        request_id=request_id,
                    )

        _record_latency_span(latency_spans, "db_commit", db_commit_started_at)
        if extract_queued_payload:
            yield _sse_event("extract_queued", extract_queued_payload)
        if queued_extract_job:
            yield _sse_status_event(
                "preparing_context",
                output_locale,
                turn_event_meta,
            )

        if question_meta_payload:
            yield _sse_event(
                "question_meta",
                {**question_meta_payload, **turn_event_meta},
            )
        if question_stream_context:
            question_stream_context.update(turn_event_meta)
            question_stream_context["latency_spans"] = latency_spans
            yield _sse_status_event(
                "composing_response",
                output_locale,
                turn_event_meta,
            )
            async for event in _stream_question_response_events(
                question_stream_context,
                actor_user_id=actor.user_id,
            ):
                yield event
        elif assistant_content:
            yield _sse_status_event(
                "composing_response",
                output_locale,
                turn_event_meta,
            )
            async for event in _stream_text_events(
                assistant_content,
                event_meta=turn_event_meta,
                emit_markers=True,
            ):
                yield event
        if stage_gate_ready_payload:
            yield _sse_event(
                "stage_gate_ready",
                {**stage_gate_ready_payload, **turn_event_meta},
            )
        yield _sse_event("done", {"status": "ok", **turn_event_meta})

    async def event_stream():
        latency_spans: dict[str, float] = {}
        stream_context: dict[str, Any] = {}
        total_started_at = time.perf_counter()
        try:
            async for event in raw_event_stream(
                latency_spans,
                stream_context,
            ):
                yield event
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error_payload = _build_stream_error_payload(exc)
            project_id = stream_context.get("project_id")
            if error_payload.get("code") == status.HTTP_500_INTERNAL_SERVER_ERROR:
                logger.exception(
                    "chat stream failed; project_id=%s",
                    project_id,
                )
            else:
                logger.warning(
                    "chat stream rejected; project_id=%s status_code=%s detail=%s",
                    project_id,
                    error_payload.get("code"),
                    error_payload.get("detail"),
                )
            _log_chat_stream_latency(
                status_value="error",
                spans=latency_spans,
                started_at=total_started_at,
                project_id=project_id,
            )
            yield _sse_event("error", error_payload)
            yield _sse_event(
                "done",
                {"status": "error", "detail": error_payload.get("detail")},
            )
        else:
            _log_chat_stream_latency(
                status_value="ok",
                spans=latency_spans,
                started_at=total_started_at,
                project_id=stream_context.get("project_id"),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
