from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class StageQuestionPromptMissingError(RuntimeError):
    pass


class StageStarterQuestionMissingError(RuntimeError):
    pass


async def resolve_stage_initial_questions(
    session: AsyncSession,
    *,
    bank_id: Any,
    stage: str,
    variant: str,
) -> tuple[Any, Any | None]:
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
        raise StageStarterQuestionMissingError(
            "Question bank has no starter questions for this stage."
        )
    current_id = rows[0]
    next_id = rows[1] if len(rows) > 1 else None
    return current_id, next_id


async def resolve_tech_entry_variant(
    session: AsyncSession,
    *,
    bank_id: Any,
) -> str:
    """Pick the tech-stage entry variant supported by this bank.

    The full bank enters tech via the "router" proficiency check (S3Q0) before
    branching to "pro"/"lite". Lighter banks (e.g. the lite/demo bank) only
    define the "lite" variant, so entering at "router" would find no starter
    question. Derive the entry variant from what the bank actually defines:
    prefer "router", then "lite", else any available tech variant.
    """
    result = await session.execute(
        text(
            "SELECT DISTINCT variant "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = 'tech' "
            "AND deleted_at IS NULL"
        ),
        {"bank_id": str(bank_id)},
    )
    variants = {row[0] for row in result.fetchall() if row[0]}
    if "router" in variants:
        return "router"
    if "lite" in variants:
        return "lite"
    return next(iter(variants), "router")


async def resolve_stage_missing_paths(
    session: AsyncSession,
    *,
    bank_id: Any,
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
    return list(row.get("paths") or [])


async def fetch_stage_question_detail(
    session: AsyncSession,
    question_id: Any,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            "SELECT id, question_id, prompt, stage, variant, type_raw, "
            "validation_rule, instruction, standard_question, schema_paths, "
            "expected_key_points, prompt_meta "
            "FROM question_bank_questions "
            "WHERE id = :question_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"question_id": str(question_id)},
    )
    row = result.mappings().first()
    if not row or not row.get("prompt"):
        raise StageQuestionPromptMissingError("Question prompt not found.")
    return dict(row)


def build_stage_question_meta_payload(
    question_detail: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(question_detail, dict):
        return None
    prompt_meta = question_detail.get("prompt_meta")
    if not isinstance(prompt_meta, dict):
        return None
    ui = prompt_meta.get("ui")
    if not isinstance(ui, dict) or not ui:
        return None
    return {
        "question_id": question_detail.get("question_id"),
        "stage": question_detail.get("stage"),
        "variant": question_detail.get("variant"),
        "ui": ui,
    }


__all__ = [
    "StageQuestionPromptMissingError",
    "StageStarterQuestionMissingError",
    "build_stage_question_meta_payload",
    "fetch_stage_question_detail",
    "resolve_stage_initial_questions",
    "resolve_stage_missing_paths",
]
