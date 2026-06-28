"""Question-bank draft creation workflow."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


QUESTION_BANK_KEY_ERROR = "bank_key must be lowercase, trimmed, and contain no spaces"


class QuestionBankDraftValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class QuestionBankDraftConflictError(RuntimeError):
    pass


class QuestionBankDraftNotFoundError(RuntimeError):
    pass


class QuestionBankDraftCreateError(RuntimeError):
    pass


def normalize_question_bank_key(bank_key: str) -> str:
    cleaned = bank_key.strip().lower()
    if not cleaned or any(ch.isspace() for ch in cleaned):
        raise QuestionBankDraftValidationError(QUESTION_BANK_KEY_ERROR)
    return cleaned


async def create_question_bank_draft(
    session: AsyncSession,
    *,
    bank_key: str,
) -> dict[str, Any]:
    normalized_key = normalize_question_bank_key(bank_key)

    existing_result = await session.execute(
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
        {"bank_key": normalized_key},
    )
    existing = existing_result.mappings().first()
    if existing:
        raise QuestionBankDraftConflictError("Draft already exists")

    active_result = await session.execute(
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
        {"bank_key": normalized_key},
    )
    active = active_result.mappings().first()
    if not active:
        raise QuestionBankDraftNotFoundError("Active question bank not found")

    draft_result = await session.execute(
        text(
            "INSERT INTO question_bank_versions ("
            "org_id, bank_key, version, source, raw_yaml, raw_json, "
            "content_hash, is_active"
            ") VALUES ("
            "app_org_id(), :bank_key, 'draft', :source, :raw_yaml, "
            "CAST(:raw_json AS jsonb), "
            "NULL, false"
            ") "
            "RETURNING id, org_id, bank_key, version, source, is_active, "
            "created_at, activated_at"
        ),
        {
            "bank_key": normalized_key,
            "source": f"draft_from:{active.get('version')}",
            "raw_yaml": active.get("raw_yaml"),
            "raw_json": json.dumps(active.get("raw_json") or {}),
        },
    )
    draft = draft_result.mappings().first()
    if not draft:
        raise QuestionBankDraftCreateError("Unable to create draft")

    await session.execute(
        text(
            "INSERT INTO question_bank_questions ("
            "bank_version_id, stage, variant, question_id, order_index, title, "
            "type_raw, prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, "
            "capture_intent, capture_spec, answer_examples, expected_patch_example, "
            "display_if, meta"
            ") "
            "SELECT :draft_id, stage, variant, question_id, order_index, title, "
            "type_raw, prompt, standard_question, consultant_tactic, instruction, "
            "validation_rule, schema_paths, expected_key_points, prompt_meta, "
            "capture_intent, capture_spec, answer_examples, expected_patch_example, "
            "display_if, meta "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :active_id AND deleted_at IS NULL"
        ),
        {"draft_id": str(draft.get("id")), "active_id": str(active.get("id"))},
    )

    return dict(draft)


__all__ = [
    "QUESTION_BANK_KEY_ERROR",
    "QuestionBankDraftConflictError",
    "QuestionBankDraftCreateError",
    "QuestionBankDraftNotFoundError",
    "QuestionBankDraftValidationError",
    "create_question_bank_draft",
    "normalize_question_bank_key",
]
