from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text

from app.core.database_async import AdminAsyncSessionLocal
from app.core.llm_router import has_available_provider
from app.services.chat_question_filters import (
    adjust_missing_paths_for_market,
    should_skip_non_required_question,
)
from app.services.chat_question_planning import question_overlaps_only_deferred_paths
from app.services.chat_router_mode import require_router_mode
from app.services.chat_runtime_settings import question_compose_enabled
from app.services.project_question_prompts import (
    run_chat_question_rewrite,
)
from app.services.stage_gate_paths import (
    filter_stage_blocking_missing_paths,
    resolve_stage_blocking_paths,
)


async def fetch_chat_question_detail(session, question_id: UUID) -> dict:
    result = await session.execute(
        text(
            "SELECT id, question_id, title, prompt, bank_version_id, stage, variant, "
            "order_index, type_raw, validation_rule, instruction, "
            "standard_question, schema_paths, expected_key_points, prompt_meta "
            "FROM question_bank_questions "
            "WHERE id = :question_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"question_id": str(question_id)},
    )
    row = result.mappings().first()
    if not row or not row.get("prompt"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question prompt not found.",
        )
    return row


async def resolve_initial_questions(
    session,
    bank_id: UUID,
    stage: str,
    variant: str,
) -> tuple[UUID, UUID | None]:
    result = await session.execute(
        text(
            "SELECT id "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "ORDER BY order_index ASC "
            "LIMIT 2"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    rows = [row.get("id") for row in result.mappings().all() if row.get("id")]
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question bank has no starter questions for this stage.",
        )
    current_id = rows[0]
    next_id = rows[1] if len(rows) > 1 else None
    return current_id, next_id


async def resolve_next_question_id(
    session,
    detail: dict,
    *,
    state_json: dict | None = None,
    missing_paths: list[str] | None = None,
    defer_schema_paths: list[str] | None = None,
    skip_optional: bool = False,
) -> UUID | None:
    order_index = detail.get("order_index") or 0
    while True:
        result = await session.execute(
            text(
                "SELECT id, question_id, title, prompt, bank_version_id, stage, "
                "variant, order_index, type_raw, validation_rule, instruction, "
                "standard_question, schema_paths, expected_key_points, prompt_meta "
                "FROM question_bank_questions "
                "WHERE bank_version_id = :bank_version_id "
                "AND stage = :stage "
                "AND variant = :variant "
                "AND deleted_at IS NULL "
                "AND order_index > :order_index "
                "ORDER BY order_index ASC "
                "LIMIT 1"
            ),
            {
                "bank_version_id": detail.get("bank_version_id"),
                "stage": detail.get("stage"),
                "variant": detail.get("variant"),
                "order_index": order_index,
            },
        )
        row = result.mappings().first()
        if not row:
            return None
        if skip_optional and should_skip_non_required_question(
            row, state_json, missing_paths
        ):
            order_index = row.get("order_index") or order_index
            continue
        if skip_optional and question_overlaps_only_deferred_paths(
            row, missing_paths, defer_schema_paths
        ):
            order_index = row.get("order_index") or order_index
            continue
        return row.get("id")


async def resolve_askable_question_id(
    session,
    question_id: UUID | None,
    *,
    state_json: dict | None,
    missing_paths: list[str] | None,
    defer_schema_paths: list[str] | None = None,
    skip_optional: bool = False,
) -> UUID | None:
    current_id = question_id
    while current_id:
        detail = await fetch_chat_question_detail(session, current_id)
        should_skip = skip_optional and (
            should_skip_non_required_question(detail, state_json, missing_paths)
            or question_overlaps_only_deferred_paths(
                detail, missing_paths, defer_schema_paths
            )
        )
        if not should_skip:
            return current_id
        current_id = await resolve_next_question_id(
            session,
            detail,
            state_json=state_json,
            missing_paths=missing_paths,
            defer_schema_paths=defer_schema_paths,
            skip_optional=skip_optional,
        )
    return None


async def resolve_missing_paths(
    session,
    bank_id: UUID,
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
            ") AS required_paths "
            "WHERE path IS NOT NULL "
            "AND btrim(path) <> ''"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    row = result.mappings().first()
    return resolve_stage_blocking_paths(stage, list(row.get("paths") or []))


async def resolve_repair_question(
    session,
    bank_id: UUID,
    stage: str,
    variant: str,
    missing_paths: list[str],
    project_id: str,
) -> UUID | None:
    if not missing_paths:
        return None

    result = await session.execute(
        text(
            "SELECT id, schema_paths, order_index "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    rows = result.mappings().all()
    if not rows:
        return None

    asked_result = await session.execute(
        text(
            "SELECT DISTINCT question_bank_question_id "
            "FROM project_question_instances "
            "WHERE project_id = :project_id "
            "AND deleted_at IS NULL"
        ),
        {"project_id": project_id},
    )
    asked = {
        row.get("question_bank_question_id")
        for row in asked_result.mappings().all()
        if row.get("question_bank_question_id")
    }

    best_row = None
    best_key = None
    for row in rows:
        schema_paths = row.get("schema_paths") or []
        if not isinstance(schema_paths, list):
            schema_paths = list(schema_paths)
        overlap = [path for path in missing_paths if path in schema_paths]
        if not overlap:
            continue
        overlap_count = len(overlap)
        is_unasked = row.get("id") not in asked
        order_index = (
            row.get("order_index") if row.get("order_index") is not None else 0
        )
        key = (-overlap_count, 0 if is_unasked else 1, order_index)
        if best_key is None or key < best_key:
            best_key = key
            best_row = row

    if not best_row:
        return None
    return best_row.get("id")


async def plan_question_prompt(
    gate_context: dict,
    resolved_paths: list[str],
    chosen_mode: str | None,
) -> tuple[UUID | None, str | None]:
    if AdminAsyncSessionLocal is None:
        return None, None

    runtime_stage = gate_context.get("runtime_stage")
    runtime_variant = gate_context.get("runtime_variant")
    bank_version_id = gate_context.get("bank_version_id")
    next_question_id = gate_context.get("next_question_id")
    current_question_id = gate_context.get("current_question_id")
    state_json = gate_context.get("state_json")
    state_meta = gate_context.get("state_meta")
    runtime_missing_paths = list(gate_context.get("runtime_missing_paths") or [])
    updated_missing_paths = [
        path for path in runtime_missing_paths if path not in resolved_paths
    ]
    updated_missing_paths = filter_stage_blocking_missing_paths(
        runtime_stage,
        updated_missing_paths,
        state_json=state_json,
        state_meta=state_meta,
    )
    if runtime_stage == "market":
        updated_missing_paths = adjust_missing_paths_for_market(
            state_json, updated_missing_paths, resolved_paths
        )
    question_id: UUID | None = None
    question_detail: dict | None = None

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": gate_context.get("org_id")},
            )
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )

            if runtime_stage == "tech" and runtime_variant == "router":
                if not bank_version_id:
                    return None, None
                chosen_mode = require_router_mode(chosen_mode)
                question_id, _ = await resolve_initial_questions(
                    session,
                    bank_version_id,
                    "tech",
                    chosen_mode,
                )
            else:
                repair_question_id = None
                if not next_question_id and updated_missing_paths:
                    if not bank_version_id:
                        return None, None
                    repair_question_id = await resolve_repair_question(
                        session,
                        bank_version_id,
                        runtime_stage,
                        runtime_variant,
                        updated_missing_paths,
                        gate_context.get("project_id"),
                    )
                    if not repair_question_id:
                        repair_question_id = current_question_id

                if next_question_id or repair_question_id:
                    question_id = next_question_id or repair_question_id

            if question_id:
                try:
                    question_detail = await fetch_chat_question_detail(
                        session, question_id
                    )
                except HTTPException:
                    return None, None

            if not question_detail:
                return None, None

            if question_compose_enabled() and has_available_provider(
                "question_compose"
            ):
                return question_id, None

            rewritten = await run_chat_question_rewrite(
                session,
                question_detail,
                gate_context.get("latest_answer"),
                output_locale=gate_context.get("output_locale", "en"),
                project_settings=gate_context.get("project_settings"),
            )
            if rewritten:
                return question_id, rewritten
            return question_id, question_detail.get("prompt")


async def ensure_question_instance(
    session,
    project_id: str,
    question_id: UUID,
) -> UUID:
    result = await session.execute(
        text(
            "INSERT INTO project_question_instances ("
            "org_id, project_id, question_bank_question_id"
            ") VALUES ("
            "app_org_id(), :project_id, :question_id"
            ") "
            "ON CONFLICT (project_id, question_bank_question_id) "
            "WHERE deleted_at IS NULL "
            "DO UPDATE SET updated_at = now() "
            "RETURNING id"
        ),
        {
            "project_id": project_id,
            "question_id": question_id,
        },
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to initialize question instance.",
        )
    return row.get("id")


async def resolve_answer_rubric_id(session) -> UUID:
    result = await session.execute(
        text(
            "SELECT id "
            "FROM evaluation_rubrics "
            "WHERE org_id IS NULL "
            "AND rubric_key = 'default' "
            "AND rubric_version = 'v1' "
            "AND scope = 'answer' "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        )
    )
    row = result.mappings().first()
    rubric_id = row.get("id") if row else None
    if not rubric_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer evaluation rubric is missing.",
        )
    return rubric_id
