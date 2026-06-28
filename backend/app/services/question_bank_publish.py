"""Question-bank draft publish workflow."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.question_bank_drafts import (
    QuestionBankDraftValidationError,
    normalize_question_bank_key,
)


class QuestionBankPublishValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class QuestionBankPublishNotFoundError(RuntimeError):
    pass


class QuestionBankPublishCreateError(RuntimeError):
    pass


def _question_to_raw_payload(question: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": question.get("question_id"),
        "title": question.get("title"),
        "type": question.get("type_raw"),
        "prompt": question.get("prompt"),
        "standard_question": question.get("standard_question"),
        "consultant_tactic": question.get("consultant_tactic"),
        "instruction": question.get("instruction"),
        "validation_rule": question.get("validation_rule"),
        "schema_paths": question.get("schema_paths") or [],
        "expected_key_points": question.get("expected_key_points") or [],
    }
    prompt_meta = question.get("prompt_meta") or {}
    if prompt_meta:
        result["prompt_meta"] = prompt_meta
    notes = question.get("notes")
    if notes:
        result["notes"] = notes
    if question.get("capture_intent") is not None:
        result["capture_intent"] = question.get("capture_intent")
    capture_spec = question.get("capture_spec")
    if capture_spec:
        result["capture_spec"] = capture_spec
    answer_examples = question.get("answer_examples")
    if answer_examples:
        result["answer_examples"] = answer_examples
    if question.get("expected_patch_example") is not None:
        result["expected_patch_example"] = question.get("expected_patch_example")
    if question.get("display_if") is not None:
        result["display_if"] = question.get("display_if")
    return result


def _build_raw_json(
    *, version: str, source: str | None, questions: list[dict[str, Any]]
) -> dict[str, Any]:
    stages: dict[str, Any] = {}
    for stage_name in ("problem", "market", "report"):
        stage_questions = [
            q
            for q in questions
            if q.get("stage") == stage_name and q.get("variant") == "default"
        ]
        if stage_questions:
            stages[stage_name] = {
                "questions": [
                    _question_to_raw_payload(q) for q in stage_questions
                ]
            }

    tech_questions = [q for q in questions if q.get("stage") == "tech"]
    if tech_questions:
        variants: dict[str, Any] = {}
        for question in tech_questions:
            variant = question.get("variant") or "default"
            variants.setdefault(variant, []).append(
                _question_to_raw_payload(question)
            )
        stages["tech"] = variants

    raw_json: dict[str, Any] = {"version": version, "stages": stages}
    if source:
        raw_json["source"] = source
    return raw_json


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


async def _resolve_publish_version(
    session: AsyncSession,
    *,
    bank_key: str,
    requested_version: str | None,
) -> str:
    base_version = (
        requested_version.strip()
        if requested_version and requested_version.strip()
        else datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )

    version = base_version
    suffix = 1
    while True:
        exists = await session.execute(
            text(
                "SELECT 1 "
                "FROM question_bank_versions "
                "WHERE org_id = app_org_id() "
                "AND bank_key = :bank_key "
                "AND version = :version "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"bank_key": bank_key, "version": version},
        )
        if not exists.first():
            return version
        version = f"{base_version}.{suffix}"
        suffix += 1


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


def _question_rows_for_raw_payload(
    question_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "notes": (row.get("meta") or {}).get("notes")
            if isinstance(row.get("meta"), dict)
            else None,
        }
        for row in question_rows
    ]


async def _find_matching_version(
    session: AsyncSession,
    *,
    bank_key: str,
    content_hash: str,
) -> dict[str, Any] | None:
    existing = await session.execute(
        text(
            "SELECT id "
            "FROM question_bank_versions "
            "WHERE org_id = app_org_id() "
            "AND bank_key = :bank_key "
            "AND content_hash = :content_hash "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"bank_key": bank_key, "content_hash": content_hash},
    )
    return existing.mappings().first()


async def _deactivate_current_versions(
    session: AsyncSession,
    *,
    bank_key: str,
) -> None:
    await session.execute(
        text(
            "UPDATE question_bank_versions "
            "SET is_active = false "
            "WHERE org_id = app_org_id() "
            "AND bank_key = :bank_key "
            "AND is_active "
            "AND deleted_at IS NULL"
        ),
        {"bank_key": bank_key},
    )


async def _soft_delete_draft_version(
    session: AsyncSession,
    *,
    draft_id: str,
) -> None:
    await session.execute(
        text(
            "UPDATE question_bank_versions "
            "SET deleted_at = now() "
            "WHERE id = :draft_id"
        ),
        {"draft_id": draft_id},
    )


async def _reactivate_existing_version(
    session: AsyncSession,
    *,
    version_id: str,
    bank_key: str,
    draft_id: str,
) -> dict[str, Any]:
    await _deactivate_current_versions(session, bank_key=bank_key)
    await session.execute(
        text(
            "UPDATE question_bank_versions "
            "SET is_active = true "
            "WHERE id = :version_id"
        ),
        {"version_id": version_id},
    )
    await _soft_delete_draft_version(session, draft_id=draft_id)
    active = await session.execute(
        text(
            "SELECT id, org_id, bank_key, version, source, is_active, "
            "created_at, activated_at "
            "FROM question_bank_versions "
            "WHERE id = :version_id"
        ),
        {"version_id": version_id},
    )
    row = active.mappings().first()
    if not row:
        raise QuestionBankPublishCreateError("Unable to publish question bank")
    return dict(row)


async def _insert_published_version(
    session: AsyncSession,
    *,
    bank_key: str,
    version: str,
    source: str | None,
    raw_yaml: str,
    raw_json: dict[str, Any],
    content_hash: str,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            "INSERT INTO question_bank_versions ("
            "org_id, bank_key, version, source, raw_yaml, raw_json, content_hash, "
            "is_active"
            ") VALUES ("
            "app_org_id(), :bank_key, :version, :source, :raw_yaml, "
            "CAST(:raw_json AS jsonb), :content_hash, true"
            ") "
            "RETURNING id, org_id, bank_key, version, source, is_active, "
            "created_at, activated_at"
        ),
        {
            "bank_key": bank_key,
            "version": version,
            "source": source,
            "raw_yaml": raw_yaml,
            "raw_json": json.dumps(raw_json),
            "content_hash": content_hash,
        },
    )
    new_version = result.mappings().first()
    if not new_version:
        raise QuestionBankPublishCreateError("Unable to publish question bank")
    return dict(new_version)


async def _copy_draft_questions(
    session: AsyncSession,
    *,
    new_version_id: str,
    draft_id: str,
) -> None:
    await session.execute(
        text(
            "INSERT INTO question_bank_questions ("
            "bank_version_id, stage, variant, question_id, order_index, title, "
            "type_raw, prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, "
            "capture_intent, capture_spec, answer_examples, expected_patch_example, "
            "display_if, meta"
            ") "
            "SELECT :new_id, stage, variant, question_id, order_index, title, "
            "type_raw, prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, "
            "capture_intent, capture_spec, answer_examples, expected_patch_example, "
            "display_if, meta "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :draft_id AND deleted_at IS NULL"
        ),
        {"new_id": new_version_id, "draft_id": draft_id},
    )


async def _soft_delete_draft_questions(
    session: AsyncSession,
    *,
    draft_id: str,
) -> None:
    await session.execute(
        text(
            "UPDATE question_bank_questions "
            "SET deleted_at = now() "
            "WHERE bank_version_id = :draft_id "
            "AND deleted_at IS NULL"
        ),
        {"draft_id": draft_id},
    )


async def publish_question_bank_draft(
    session: AsyncSession,
    *,
    bank_key: str,
    version: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    try:
        normalized_key = normalize_question_bank_key(bank_key)
    except QuestionBankDraftValidationError as exc:
        raise QuestionBankPublishValidationError(exc.detail) from exc

    draft = await _fetch_draft_bank(session, normalized_key)
    if not draft:
        raise QuestionBankPublishNotFoundError("Draft not found")

    resolved_version = await _resolve_publish_version(
        session,
        bank_key=normalized_key,
        requested_version=version,
    )
    question_rows = await _fetch_questions(session, str(draft.get("id")))
    raw_questions = _question_rows_for_raw_payload(question_rows)

    resolved_source = source or draft.get("source") or "draft_publish"
    raw_json = _build_raw_json(
        version=resolved_version,
        source=resolved_source,
        questions=raw_questions,
    )
    raw_yaml = yaml.safe_dump(raw_json, sort_keys=False, allow_unicode=True)
    content_hash = hashlib.sha256(raw_yaml.encode("utf-8")).hexdigest()

    existing_row = await _find_matching_version(
        session,
        bank_key=normalized_key,
        content_hash=content_hash,
    )
    draft_id = str(draft.get("id"))
    if existing_row:
        return await _reactivate_existing_version(
            session,
            version_id=str(existing_row.get("id")),
            bank_key=normalized_key,
            draft_id=draft_id,
        )

    await _deactivate_current_versions(session, bank_key=normalized_key)
    new_version = await _insert_published_version(
        session,
        bank_key=normalized_key,
        version=resolved_version,
        source=resolved_source,
        raw_yaml=raw_yaml,
        raw_json=raw_json,
        content_hash=content_hash,
    )
    await _copy_draft_questions(
        session,
        new_version_id=str(new_version.get("id")),
        draft_id=draft_id,
    )
    await _soft_delete_draft_version(session, draft_id=draft_id)
    await _soft_delete_draft_questions(session, draft_id=draft_id)

    return new_version


__all__ = [
    "QuestionBankPublishCreateError",
    "QuestionBankPublishNotFoundError",
    "QuestionBankPublishValidationError",
    "publish_question_bank_draft",
]
