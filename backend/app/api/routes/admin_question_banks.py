from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_org_capability
from app.services.question_bank_drafts import (
    QUESTION_BANK_KEY_ERROR,
    QuestionBankDraftConflictError,
    QuestionBankDraftCreateError,
    QuestionBankDraftNotFoundError,
    QuestionBankDraftValidationError,
    create_question_bank_draft,
    normalize_question_bank_key,
)
from app.services.question_bank_draft_imports import (
    QuestionBankDraftImportNotFoundError,
    QuestionBankDraftImportValidationError,
    import_question_bank_draft_json,
    import_question_bank_draft_yaml,
)
from app.services.question_bank_publish import (
    QuestionBankPublishCreateError,
    QuestionBankPublishNotFoundError,
    QuestionBankPublishValidationError,
    publish_question_bank_draft,
)

router = APIRouter(prefix="/admin-api/question-banks", tags=["admin"])


class QuestionBankVersionInfo(BaseModel):
    id: str
    bank_key: str
    version: str
    source: str | None
    org_id: str | None
    is_active: bool
    created_at: datetime | None
    activated_at: datetime | None = None


class QuestionBankQuestion(BaseModel):
    question_id: str
    stage: str
    variant: str
    order_index: int
    title: str | None = None
    type_raw: str | None = None
    prompt: str | None = None
    standard_question: str | None = None
    consultant_tactic: str | None = None
    instruction: str | None = None
    validation_rule: str | None = None
    schema_paths: list[str] = Field(default_factory=list)
    expected_key_points: list[str] = Field(default_factory=list)
    prompt_meta: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class DraftResponse(BaseModel):
    version: QuestionBankVersionInfo
    questions: list[QuestionBankQuestion] = Field(default_factory=list)


class QuestionUpdateRequest(BaseModel):
    title: str | None = None
    type_raw: str | None = None
    prompt: str | None = None
    standard_question: str | None = None
    consultant_tactic: str | None = None
    instruction: str | None = None
    validation_rule: str | None = None
    schema_paths: list[str] | None = None
    expected_key_points: list[str] | None = None
    prompt_meta: dict[str, Any] | None = None
    notes: str | None = None


class ImportRequest(BaseModel):
    yaml: str
    mode: str | None = None


class ImportJsonRequest(BaseModel):
    json_payload: str = Field(alias="json")
    mode: str | None = None


class ReorderGroupRequest(BaseModel):
    stage: str
    variant: str
    question_ids: list[str]


class ReorderRequest(BaseModel):
    groups: list[ReorderGroupRequest]


class PublishRequest(BaseModel):
    version: str | None = None
    source: str | None = None


def _fields_set(payload: BaseModel) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if isinstance(model_fields_set, set):
        return model_fields_set
    return getattr(payload, "__fields_set__", set())


def _normalize_bank_key(bank_key: str) -> str:
    try:
        return normalize_question_bank_key(bank_key)
    except QuestionBankDraftValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc


def _row_to_version(row: dict[str, Any]) -> QuestionBankVersionInfo:
    return QuestionBankVersionInfo(
        id=str(row.get("id")),
        bank_key=row.get("bank_key") or "",
        version=row.get("version") or "",
        source=row.get("source"),
        org_id=str(row.get("org_id")) if row.get("org_id") else None,
        is_active=bool(row.get("is_active")),
        created_at=row.get("created_at"),
        activated_at=row.get("activated_at"),
    )


def _row_to_question(row: dict[str, Any]) -> QuestionBankQuestion:
    meta = row.get("meta") or {}
    return QuestionBankQuestion(
        question_id=row.get("question_id") or "",
        stage=row.get("stage") or "",
        variant=row.get("variant") or "",
        order_index=row.get("order_index") or 0,
        title=row.get("title"),
        type_raw=row.get("type_raw"),
        prompt=row.get("prompt"),
        standard_question=row.get("standard_question"),
        consultant_tactic=row.get("consultant_tactic"),
        instruction=row.get("instruction"),
        validation_rule=row.get("validation_rule"),
        schema_paths=list(row.get("schema_paths") or []),
        expected_key_points=list(row.get("expected_key_points") or []),
        prompt_meta=row.get("prompt_meta") or {},
        notes=meta.get("notes") if isinstance(meta, dict) else None,
    )


def _normalize_stage_variant(stage: str, variant: str) -> tuple[str, str]:
    normalized_stage = stage.strip().lower()
    normalized_variant = variant.strip().lower()
    if not normalized_stage or not normalized_variant:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="stage and variant are required",
        )
    return normalized_stage, normalized_variant


def _normalize_question_ids(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="question_ids must be strings",
            )
        value = item.strip()
        if not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="question_ids cannot be empty",
            )
        cleaned.append(value)
    if len(set(cleaned)) != len(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="question_ids must be unique",
        )
    return cleaned


async def _fetch_active_bank(
    session: AsyncSession, bank_key: str
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT id, org_id, bank_key, version, source, raw_yaml, raw_json, "
            "is_active, created_at, activated_at "
            "FROM question_bank_versions "
            "WHERE bank_key = :bank_key "
            "AND is_active "
            "AND deleted_at IS NULL "
            "AND (org_id = app_org_id() OR org_id IS NULL) "
            "ORDER BY (org_id IS NULL) ASC, activated_at DESC "
            "LIMIT 1"
        ),
        {"bank_key": bank_key},
    )
    return result.mappings().first()


async def _fetch_draft_bank(
    session: AsyncSession, bank_key: str
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT id, org_id, bank_key, version, source, is_active, "
            "created_at, activated_at "
            "FROM question_bank_versions "
            "WHERE bank_key = :bank_key "
            "AND org_id = app_org_id() "
            "AND version = 'draft' "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"bank_key": bank_key},
    )
    return result.mappings().first()


async def _fetch_questions(
    session: AsyncSession, bank_version_id: str
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT id, question_id, stage, variant, order_index, title, type_raw, "
            "prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, meta, "
            "capture_intent, capture_spec, answer_examples, expected_patch_example, "
            "display_if "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_version_id "
            "AND deleted_at IS NULL "
            "ORDER BY stage, variant, order_index"
        ),
        {"bank_version_id": bank_version_id},
    )
    return list(result.mappings().all())


async def _fetch_question_group(
    session: AsyncSession, bank_version_id: str, stage: str, variant: str
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT id, question_id, order_index "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_version_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "ORDER BY order_index"
        ),
        {
            "bank_version_id": bank_version_id,
            "stage": stage,
            "variant": variant,
        },
    )
    return list(result.mappings().all())


@router.get("/{bank_key}/active", response_model=QuestionBankVersionInfo)
async def get_active_bank(
    bank_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> QuestionBankVersionInfo:
    await require_org_capability(session, "can_manage_question_bank")
    normalized_key = _normalize_bank_key(bank_key)
    active = await _fetch_active_bank(session, normalized_key)
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active question bank not found",
        )
    return _row_to_version(active)


@router.get("/{bank_key}/active/details", response_model=DraftResponse)
async def get_active_bank_details(
    bank_key: str,
    session: AsyncSession = Depends(get_db_session),
    include_questions: bool = Query(True),
) -> DraftResponse:
    await require_org_capability(session, "can_manage_question_bank")
    normalized_key = _normalize_bank_key(bank_key)
    active = await _fetch_active_bank(session, normalized_key)
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active question bank not found",
        )
    questions: list[QuestionBankQuestion] = []
    if include_questions:
        rows = await _fetch_questions(session, str(active.get("id")))
        questions = [_row_to_question(row) for row in rows]
    return DraftResponse(version=_row_to_version(active), questions=questions)


@router.get("/{bank_key}/draft", response_model=DraftResponse)
async def get_draft(
    bank_key: str,
    session: AsyncSession = Depends(get_db_session),
    include_questions: bool = Query(True),
) -> DraftResponse:
    await require_org_capability(session, "can_manage_question_bank")
    normalized_key = _normalize_bank_key(bank_key)
    draft = await _fetch_draft_bank(session, normalized_key)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    questions: list[QuestionBankQuestion] = []
    if include_questions:
        rows = await _fetch_questions(session, str(draft.get("id")))
        questions = [_row_to_question(row) for row in rows]
    return DraftResponse(
        version=_row_to_version(draft),
        questions=questions,
    )


@router.post("/{bank_key}/draft", response_model=QuestionBankVersionInfo)
async def create_draft(
    bank_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> QuestionBankVersionInfo:
    await require_org_capability(session, "can_manage_question_bank")
    try:
        draft = await create_question_bank_draft(session, bank_key=bank_key)
    except QuestionBankDraftValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail or QUESTION_BANK_KEY_ERROR,
        ) from exc
    except QuestionBankDraftConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except QuestionBankDraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except QuestionBankDraftCreateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return _row_to_version(draft)


@router.patch("/{bank_key}/draft/questions/{question_code}", response_model=QuestionBankQuestion)
async def update_draft_question(
    bank_key: str,
    question_code: str,
    payload: QuestionUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> QuestionBankQuestion:
    await require_org_capability(session, "can_manage_question_bank")
    normalized_key = _normalize_bank_key(bank_key)
    draft = await _fetch_draft_bank(session, normalized_key)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    fields_set = _fields_set(payload)
    if not fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided",
        )

    row_result = await session.execute(
        text(
            "SELECT id, meta "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_version_id "
            "AND question_id = :question_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"bank_version_id": str(draft.get("id")), "question_id": question_code},
    )
    row = row_result.mappings().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in draft",
        )

    updates: list[str] = []
    params: dict[str, Any] = {"question_row_id": str(row.get("id"))}

    def _maybe(field: str, column: str) -> None:
        if field in fields_set:
            updates.append(f"{column} = :{field}")
            params[field] = getattr(payload, field)

    _maybe("title", "title")
    _maybe("type_raw", "type_raw")
    _maybe("prompt", "prompt")
    _maybe("standard_question", "standard_question")
    _maybe("consultant_tactic", "consultant_tactic")
    _maybe("instruction", "instruction")
    _maybe("validation_rule", "validation_rule")
    _maybe("schema_paths", "schema_paths")
    _maybe("expected_key_points", "expected_key_points")

    if "prompt_meta" in fields_set:
        updates.append("prompt_meta = CAST(:prompt_meta AS jsonb)")
        params["prompt_meta"] = json.dumps(payload.prompt_meta or {})

    if "notes" in fields_set:
        updates.append(
            "meta = jsonb_set(COALESCE(meta, '{}'::jsonb), '{notes}', "
            "to_jsonb(:notes), true)"
        )
        params["notes"] = payload.notes

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid fields provided",
        )

    await session.execute(
        text(
            "UPDATE question_bank_questions "
            f"SET {', '.join(updates)} "
            "WHERE id = :question_row_id"
        ),
        params,
    )

    updated = await session.execute(
        text(
            "SELECT question_id, stage, variant, order_index, title, type_raw, "
            "prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, meta "
            "FROM question_bank_questions "
            "WHERE id = :question_row_id"
        ),
        {"question_row_id": str(row.get("id"))},
    )
    return _row_to_question(updated.mappings().first())


@router.post("/{bank_key}/draft/import", response_model=DraftResponse)
async def import_draft(
    bank_key: str,
    payload: ImportRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DraftResponse:
    await require_org_capability(session, "can_manage_question_bank")
    try:
        imported = await import_question_bank_draft_yaml(
            session,
            bank_key=bank_key,
            raw_yaml=payload.yaml or "",
            mode=payload.mode,
        )
    except QuestionBankDraftImportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except QuestionBankDraftImportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    questions = [_row_to_question(row) for row in imported["questions"]]
    return DraftResponse(
        version=_row_to_version(imported["draft"]),
        questions=questions,
    )


@router.post("/{bank_key}/draft/import-json", response_model=DraftResponse)
async def import_draft_json(
    bank_key: str,
    payload: ImportJsonRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DraftResponse:
    await require_org_capability(session, "can_manage_question_bank")
    try:
        imported = await import_question_bank_draft_json(
            session,
            bank_key=bank_key,
            raw_json=payload.json_payload or "",
            mode=payload.mode,
        )
    except QuestionBankDraftImportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except QuestionBankDraftImportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    questions = [_row_to_question(row) for row in imported["questions"]]
    return DraftResponse(
        version=_row_to_version(imported["draft"]),
        questions=questions,
    )


@router.patch("/{bank_key}/draft/reorder", response_model=DraftResponse)
async def reorder_draft_questions(
    bank_key: str,
    payload: ReorderRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DraftResponse:
    await require_org_capability(session, "can_manage_question_bank")
    normalized_key = _normalize_bank_key(bank_key)
    draft = await _fetch_draft_bank(session, normalized_key)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    if not payload.groups:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="groups is required",
        )

    for group in payload.groups:
        stage, variant = _normalize_stage_variant(group.stage, group.variant)
        question_ids = _normalize_question_ids(group.question_ids)

        existing_rows = await _fetch_question_group(
            session, str(draft.get("id")), stage, variant
        )
        if not existing_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage/variant not found in draft: {stage}/{variant}",
            )

        existing_map = {
            row.get("question_id"): row.get("id") for row in existing_rows
        }
        existing_ids = set(existing_map.keys())
        incoming_ids = set(question_ids)
        if incoming_ids != existing_ids:
            missing = sorted(existing_ids - incoming_ids)
            extra = sorted(incoming_ids - existing_ids)
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if extra:
                details.append(f"unknown: {', '.join(extra)}")
            message = "; ".join(details) if details else "question_ids mismatch"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            )

        ordered_ids = [existing_map[qid] for qid in question_ids]
        orders = list(range(1, len(ordered_ids) + 1))

        await session.execute(
            text(
                "UPDATE question_bank_questions AS q "
                "SET order_index = data.order_index "
                "FROM ("
                "SELECT unnest(:ids)::uuid AS id, unnest(:orders)::int AS order_index"
                ") AS data "
                "WHERE q.id = data.id"
            ),
            {"ids": ordered_ids, "orders": orders},
        )

    await session.execute(
        text(
            "UPDATE question_bank_versions "
            "SET updated_at = now() "
            "WHERE id = :bank_version_id"
        ),
        {"bank_version_id": str(draft.get("id"))},
    )

    rows = await _fetch_questions(session, str(draft.get("id")))
    questions = [_row_to_question(row) for row in rows]
    return DraftResponse(version=_row_to_version(draft), questions=questions)


@router.post("/{bank_key}/draft/publish", response_model=QuestionBankVersionInfo)
async def publish_draft(
    bank_key: str,
    payload: PublishRequest,
    session: AsyncSession = Depends(get_db_session),
) -> QuestionBankVersionInfo:
    await require_org_capability(session, "can_manage_question_bank")
    try:
        published = await publish_question_bank_draft(
            session,
            bank_key=bank_key,
            version=payload.version,
            source=payload.source,
        )
    except QuestionBankPublishValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except QuestionBankPublishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except QuestionBankPublishCreateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return _row_to_version(published)
