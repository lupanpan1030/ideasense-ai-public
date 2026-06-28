"""Question-bank draft YAML/JSON import workflow."""

from __future__ import annotations

import json
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.question_bank_drafts import (
    QuestionBankDraftValidationError,
    normalize_question_bank_key,
)


class QuestionBankDraftImportValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class QuestionBankDraftImportNotFoundError(RuntimeError):
    pass


def _normalize_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "replace").strip().lower()
    if mode not in {"replace", "merge"}:
        raise QuestionBankDraftImportValidationError("mode must be replace or merge")
    return mode


def _parse_yaml_payload(raw_yaml: str) -> dict[str, Any]:
    if not raw_yaml.strip():
        raise QuestionBankDraftImportValidationError("yaml is required")

    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        raise QuestionBankDraftImportValidationError("Invalid YAML") from exc

    if not isinstance(data, dict):
        raise QuestionBankDraftImportValidationError("YAML root must be a mapping")
    return data


def _parse_json_payload(raw_json: str) -> dict[str, Any]:
    if not raw_json.strip():
        raise QuestionBankDraftImportValidationError("json is required")

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise QuestionBankDraftImportValidationError("Invalid JSON") from exc

    if not isinstance(data, dict):
        raise QuestionBankDraftImportValidationError("JSON root must be an object")
    return data


def _iter_questions(data: dict[str, Any]) -> list[dict[str, Any]]:
    stages = data.get("stages") or {}
    if not isinstance(stages, dict):
        raise QuestionBankDraftImportValidationError("stages must be a mapping")

    rows: list[dict[str, Any]] = []
    for stage, block in stages.items():
        if stage in {"problem", "market", "report"}:
            questions = (block or {}).get("questions", [])
            if questions is None:
                questions = []
            for index, question in enumerate(questions, 1):
                rows.append(
                    {
                        "stage": stage,
                        "variant": "default",
                        "order_index": index,
                        "question": question or {},
                    }
                )
        elif stage == "tech":
            if not isinstance(block, dict):
                raise QuestionBankDraftImportValidationError(
                    "tech stage must map variants to question lists"
                )
            for variant, questions in block.items():
                if questions is None:
                    questions = []
                for index, question in enumerate(questions, 1):
                    rows.append(
                        {
                            "stage": stage,
                            "variant": variant,
                            "order_index": index,
                            "question": question or {},
                        }
                    )
        else:
            raise QuestionBankDraftImportValidationError(
                f"unsupported stage: {stage}"
            )
    return rows


def _build_question_payload(row: dict[str, Any]) -> dict[str, Any]:
    question = row["question"]
    notes = question.get("notes")
    meta = {}
    if notes:
        meta["notes"] = notes

    return {
        "stage": row["stage"],
        "variant": row["variant"],
        "order_index": row["order_index"],
        "question_id": question.get("id"),
        "title": question.get("title"),
        "type_raw": question.get("type"),
        "prompt": question.get("prompt"),
        "standard_question": question.get("standard_question"),
        "consultant_tactic": question.get("consultant_tactic"),
        "instruction": question.get("instruction"),
        "validation_rule": question.get("validation_rule"),
        "schema_paths": question.get("schema_paths") or [],
        "expected_key_points": question.get("expected_key_points") or [],
        "prompt_meta": question.get("prompt_meta") or {},
        "capture_intent": question.get("capture_intent"),
        "capture_spec": question.get("capture_spec") or {},
        "answer_examples": question.get("answer_examples") or [],
        "expected_patch_example": question.get("expected_patch_example"),
        "display_if": question.get("display_if"),
        "meta": meta,
    }


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


async def _apply_question_import(
    session: AsyncSession,
    *,
    draft_id: str,
    question_rows: list[dict[str, Any]],
    mode: str,
) -> None:
    if mode == "replace":
        await session.execute(
            text(
                "UPDATE question_bank_questions "
                "SET deleted_at = now() "
                "WHERE bank_version_id = :bank_version_id "
                "AND deleted_at IS NULL"
            ),
            {"bank_version_id": draft_id},
        )

        values = []
        for row in question_rows:
            payload_row = _build_question_payload(row)
            values.append(
                {
                    "bank_version_id": draft_id,
                    **payload_row,
                    "prompt_meta": json.dumps(payload_row.get("prompt_meta") or {}),
                    "capture_spec": json.dumps(payload_row.get("capture_spec") or {}),
                    "meta": json.dumps(payload_row.get("meta") or {}),
                }
            )

        if values:
            await session.execute(
                text(
                    "INSERT INTO question_bank_questions ("
                    "bank_version_id, stage, variant, question_id, order_index, title, "
                    "type_raw, prompt, standard_question, consultant_tactic, instruction, "
                    "validation_rule, schema_paths, expected_key_points, prompt_meta, "
                    "capture_intent, capture_spec, answer_examples, expected_patch_example, "
                    "display_if, meta"
                    ") VALUES ("
                    ":bank_version_id, :stage, :variant, :question_id, :order_index, "
                    ":title, :type_raw, :prompt, :standard_question, :consultant_tactic, "
                    ":instruction, :validation_rule, :schema_paths, :expected_key_points, "
                    "CAST(:prompt_meta AS jsonb), :capture_intent, "
                    "CAST(:capture_spec AS jsonb), :answer_examples, :expected_patch_example, "
                    ":display_if, CAST(:meta AS jsonb)"
                    ")"
                ),
                values,
            )
        return

    existing_rows = await _fetch_questions(session, draft_id)
    existing = {
        (row.get("stage"), row.get("variant"), row.get("question_id")): row
        for row in existing_rows
    }
    max_order: dict[tuple[str, str], int] = {}
    for row in existing_rows:
        key = (row.get("stage"), row.get("variant"))
        max_order[key] = max(max_order.get(key, 0), row.get("order_index") or 0)

    for row in question_rows:
        payload_row = _build_question_payload(row)
        key = (payload_row["stage"], payload_row["variant"], payload_row["question_id"])
        existing_row = existing.get(key)
        if existing_row:
            await session.execute(
                text(
                    "UPDATE question_bank_questions "
                    "SET title = :title, type_raw = :type_raw, prompt = :prompt, "
                    "standard_question = :standard_question, "
                    "consultant_tactic = :consultant_tactic, "
                    "instruction = :instruction, validation_rule = :validation_rule, "
                    "schema_paths = :schema_paths, expected_key_points = :expected_key_points, "
                    "prompt_meta = CAST(:prompt_meta AS jsonb), "
                    "capture_intent = :capture_intent, "
                    "capture_spec = CAST(:capture_spec AS jsonb), "
                    "answer_examples = :answer_examples, "
                    "expected_patch_example = :expected_patch_example, "
                    "display_if = :display_if, "
                    "meta = CAST(:meta AS jsonb) "
                    "WHERE id = :row_id"
                ),
                {
                    **payload_row,
                    "prompt_meta": json.dumps(payload_row.get("prompt_meta") or {}),
                    "capture_spec": json.dumps(payload_row.get("capture_spec") or {}),
                    "meta": json.dumps(payload_row.get("meta") or {}),
                    "row_id": existing_row.get("id"),
                },
            )
        else:
            key_stage = (payload_row["stage"], payload_row["variant"])
            next_order = max_order.get(key_stage, 0) + 1
            max_order[key_stage] = next_order
            payload_row["order_index"] = next_order
            await session.execute(
                text(
                    "INSERT INTO question_bank_questions ("
                    "bank_version_id, stage, variant, question_id, order_index, title, "
                    "type_raw, prompt, standard_question, consultant_tactic, instruction, "
                    "validation_rule, schema_paths, expected_key_points, prompt_meta, "
                    "capture_intent, capture_spec, answer_examples, expected_patch_example, "
                    "display_if, meta"
                    ") VALUES ("
                    ":bank_version_id, :stage, :variant, :question_id, :order_index, "
                    ":title, :type_raw, :prompt, :standard_question, :consultant_tactic, "
                    ":instruction, :validation_rule, :schema_paths, :expected_key_points, "
                    "CAST(:prompt_meta AS jsonb), :capture_intent, "
                    "CAST(:capture_spec AS jsonb), :answer_examples, :expected_patch_example, "
                    ":display_if, CAST(:meta AS jsonb)"
                    ")"
                ),
                {
                    "bank_version_id": draft_id,
                    **payload_row,
                    "prompt_meta": json.dumps(payload_row.get("prompt_meta") or {}),
                    "capture_spec": json.dumps(payload_row.get("capture_spec") or {}),
                    "meta": json.dumps(payload_row.get("meta") or {}),
                },
            )


async def _update_draft_payload(
    session: AsyncSession,
    *,
    draft_id: str,
    mode: str,
    raw_yaml: str | None,
    raw_json: dict[str, Any] | None,
) -> None:
    if mode == "replace":
        payload_yaml = raw_yaml
        if payload_yaml is None:
            payload_yaml = yaml.safe_dump(
                raw_json or {},
                sort_keys=False,
                allow_unicode=True,
            )
        await session.execute(
            text(
                "UPDATE question_bank_versions "
                "SET raw_yaml = :raw_yaml, raw_json = CAST(:raw_json AS jsonb), "
                "updated_at = now() "
                "WHERE id = :bank_version_id"
            ),
            {
                "raw_yaml": payload_yaml,
                "raw_json": json.dumps(raw_json or {}),
                "bank_version_id": draft_id,
            },
        )
        return

    await session.execute(
        text(
            "UPDATE question_bank_versions "
            "SET updated_at = now() "
            "WHERE id = :bank_version_id"
        ),
        {"bank_version_id": draft_id},
    )


async def _resolve_draft(
    session: AsyncSession,
    *,
    bank_key: str,
) -> dict[str, Any]:
    try:
        normalized_key = normalize_question_bank_key(bank_key)
    except QuestionBankDraftValidationError as exc:
        raise QuestionBankDraftImportValidationError(exc.detail) from exc

    draft = await _fetch_draft_bank(session, normalized_key)
    if not draft:
        raise QuestionBankDraftImportNotFoundError("Draft not found")
    return dict(draft)


async def _import_question_bank_draft_data(
    session: AsyncSession,
    *,
    draft: dict[str, Any],
    data: dict[str, Any],
    raw_yaml: str | None,
    mode: str | None,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    question_rows = _iter_questions(data)
    draft_id = str(draft.get("id"))
    await _apply_question_import(
        session,
        draft_id=draft_id,
        question_rows=question_rows,
        mode=normalized_mode,
    )
    await _update_draft_payload(
        session,
        draft_id=draft_id,
        mode=normalized_mode,
        raw_yaml=raw_yaml,
        raw_json=data,
    )

    rows = await _fetch_questions(session, draft_id)
    return {"draft": dict(draft), "questions": rows}


async def import_question_bank_draft_yaml(
    session: AsyncSession,
    *,
    bank_key: str,
    raw_yaml: str,
    mode: str | None = None,
) -> dict[str, Any]:
    draft = await _resolve_draft(session, bank_key=bank_key)
    data = _parse_yaml_payload(raw_yaml or "")
    return await _import_question_bank_draft_data(
        session,
        draft=draft,
        data=data,
        raw_yaml=raw_yaml or "",
        mode=mode,
    )


async def import_question_bank_draft_json(
    session: AsyncSession,
    *,
    bank_key: str,
    raw_json: str,
    mode: str | None = None,
) -> dict[str, Any]:
    draft = await _resolve_draft(session, bank_key=bank_key)
    data = _parse_json_payload(raw_json or "")
    return await _import_question_bank_draft_data(
        session,
        draft=draft,
        data=data,
        raw_yaml=None,
        mode=mode,
    )


__all__ = [
    "QuestionBankDraftImportNotFoundError",
    "QuestionBankDraftImportValidationError",
    "import_question_bank_draft_json",
    "import_question_bank_draft_yaml",
]
