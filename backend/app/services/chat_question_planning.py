"""Chat question planning and grouped prompt helpers."""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from app.services.localization import OutputLocale, output_language_label
from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
)

PROMPT_CONTEXT_BUILDER = PromptContextBuilder()
FetchQuestionDetail = Callable[[Any, UUID], Awaitable[dict]]
ResolveNextQuestionId = Callable[..., Awaitable[UUID | None]]


def build_question_meta_payload(question_detail: dict | None) -> dict[str, Any] | None:
    if not isinstance(question_detail, dict):
        return None
    prompt_meta = question_detail.get("prompt_meta")
    if not isinstance(prompt_meta, dict):
        return None
    ui = prompt_meta.get("ui")
    if not isinstance(ui, dict) or not ui:
        return None
    question_id = question_detail.get("question_id")
    stage = question_detail.get("stage")
    variant = question_detail.get("variant")
    return {
        "question_id": question_id,
        "stage": stage,
        "variant": variant,
        "ui": ui,
    }


def build_question_group_payload(
    question_detail: dict,
    question_ids: list[str],
    *,
    plan_id: UUID | None = None,
) -> dict[str, Any] | None:
    if not question_ids:
        return None
    payload: dict[str, Any] = {"question_ids": question_ids}
    if plan_id:
        payload["plan_id"] = str(plan_id)
    prompt = question_detail.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        payload["prompt"] = prompt.strip()
    schema_paths = question_detail.get("schema_paths")
    if isinstance(schema_paths, list) and schema_paths:
        payload["schema_paths"] = schema_paths
    expected_points = question_detail.get("expected_key_points")
    if isinstance(expected_points, list) and expected_points:
        payload["expected_key_points"] = expected_points
    validation_rule = question_detail.get("validation_rule")
    if isinstance(validation_rule, str) and validation_rule.strip():
        payload["validation_rule"] = validation_rule.strip()
    instruction = question_detail.get("instruction")
    if isinstance(instruction, str) and instruction.strip():
        payload["instruction"] = instruction.strip()
    standard_question = question_detail.get("standard_question")
    if isinstance(standard_question, str) and standard_question.strip():
        payload["standard_question"] = standard_question.strip()
    return payload


def question_supports_grouping(question_detail: dict) -> bool:
    prompt_meta = question_detail.get("prompt_meta")
    if isinstance(prompt_meta, dict):
        ui = prompt_meta.get("ui")
        if isinstance(ui, dict) and ui:
            return False
    return True


def question_schema_paths(question_detail: dict) -> list[str]:
    schema_paths = question_detail.get("schema_paths") or []
    if isinstance(schema_paths, list):
        return [path for path in schema_paths if isinstance(path, str)]
    return []


def question_has_missing_paths(
    question_detail: dict, missing_paths: list[str]
) -> bool:
    if not missing_paths:
        return True
    schema_paths = question_schema_paths(question_detail)
    if not schema_paths:
        return True
    return any(path in missing_paths for path in schema_paths)


def question_overlaps_only_deferred_paths(
    question_detail: dict,
    missing_paths: list[str] | None,
    defer_schema_paths: list[str] | None,
) -> bool:
    if not missing_paths or not defer_schema_paths:
        return False
    schema_paths = set(question_schema_paths(question_detail))
    if not schema_paths:
        return False
    deferred = {path for path in defer_schema_paths if isinstance(path, str)}
    overlap = {path for path in missing_paths if path in schema_paths}
    return bool(overlap) and overlap.issubset(deferred)


def _merge_group_strings(values: list[str]) -> str | None:
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return "\n".join(f"- {value}" for value in cleaned)


def _merge_group_details(
    question_details: list[dict],
    combined_prompt: str,
) -> dict:
    base = dict(question_details[0])
    schema_paths: list[str] = []
    expected_points: list[str] = []
    validation_rules: list[str] = []
    instructions: list[str] = []
    standard_questions: list[str] = []
    type_raw_values: list[str] = []

    for detail in question_details:
        schema_paths.extend(question_schema_paths(detail))
        expected_points.extend(
            [
                item
                for item in detail.get("expected_key_points") or []
                if isinstance(item, str) and item.strip()
            ]
        )
        rule = detail.get("validation_rule")
        if isinstance(rule, str) and rule.strip():
            validation_rules.append(rule)
        instruction = detail.get("instruction")
        if isinstance(instruction, str) and instruction.strip():
            instructions.append(instruction)
        standard = detail.get("standard_question")
        if isinstance(standard, str) and standard.strip():
            standard_questions.append(standard)
        type_raw = detail.get("type_raw")
        if isinstance(type_raw, str) and type_raw.strip():
            type_raw_values.append(type_raw)

    base["prompt"] = combined_prompt
    base["schema_paths"] = sorted(set(schema_paths))
    base["expected_key_points"] = sorted(set(expected_points))
    merged_rule = _merge_group_strings(validation_rules)
    if merged_rule:
        base["validation_rule"] = merged_rule
    merged_instruction = _merge_group_strings(instructions)
    if merged_instruction:
        base["instruction"] = merged_instruction
    merged_standard = _merge_group_strings(standard_questions)
    if merged_standard:
        base["standard_question"] = merged_standard
    if any("required" in value.lower() for value in type_raw_values):
        base["type_raw"] = "Required"
    base["prompt_meta"] = {}
    return base


def _build_group_prompt(
    prompts: list[str],
    *,
    transition: str | None,
) -> str:
    cleaned_prompts = [
        prompt.strip() for prompt in prompts if prompt and prompt.strip()
    ]
    if not cleaned_prompts:
        return transition or ""
    if len(cleaned_prompts) == 1:
        if transition:
            return f"{transition.strip()}\n\n{cleaned_prompts[0]}".strip()
        return cleaned_prompts[0]
    lines: list[str] = []
    if transition:
        lines.append(transition.strip())
    for idx, prompt in enumerate(cleaned_prompts, start=1):
        prefix = f"{idx}) "
        if "\n" in prompt:
            first, *rest = prompt.splitlines()
            block = "\n".join(
                [f"{prefix}{first.strip()}"] + [line.rstrip() for line in rest]
            )
            lines.append(block)
        else:
            lines.append(f"{prefix}{prompt}")
    return "\n\n".join(lines).strip()


def _build_transition_text(
    question_detail: dict,
    latest_answer: str | None,
) -> str:
    return "Got it. To keep momentum, I want to clarify a few key points:"


def apply_transition_prefix(
    prompt: str,
    question_detail: dict,
    latest_answer: str | None,
) -> str:
    if not prompt:
        return prompt
    transition = _build_transition_text(question_detail, latest_answer)
    if not transition:
        return prompt
    return f"{transition}\n\n{prompt}".strip()


def _planner_stage_allowed(stage: str | None, allowed: set[str]) -> bool:
    if not stage:
        return False
    if not allowed:
        return True
    return stage.lower() in allowed


def should_attempt_question_planner(
    *,
    planner_settings: dict[str, Any],
    stage: str | None,
    question_detail: dict,
    missing_paths: list[str],
) -> bool:
    if not planner_settings.get("enabled"):
        return False
    if planner_settings.get("max_questions", 1) < 2:
        return False
    if not _planner_stage_allowed(stage, planner_settings.get("stages", set())):
        return False
    if not question_supports_grouping(question_detail):
        return False
    min_missing_paths = int(planner_settings.get("min_missing_paths") or 1)
    meaningful_missing_paths = {
        path.strip() for path in missing_paths if isinstance(path, str) and path.strip()
    }
    return len(meaningful_missing_paths) >= min_missing_paths


def _format_candidate_list(candidates: list[dict]) -> str:
    lines: list[str] = []
    for idx, detail in enumerate(candidates, start=1):
        prompt = detail.get("prompt") or ""
        prompt_clean = re.sub(r"\s+", " ", prompt).strip()
        question_id = detail.get("question_id") or ""
        schema_paths = detail.get("schema_paths") or []
        schema_paths = [
            path.strip()
            for path in schema_paths
            if isinstance(path, str) and path.strip()
        ]
        schema_block = ", ".join(schema_paths)
        label = f"{idx}) {question_id}".strip()
        if schema_block:
            lines.append(f"{label} {prompt_clean}\n   schema_paths: {schema_block}")
        else:
            lines.append(f"{label} {prompt_clean}")
    return "\n".join(lines)


async def fetch_question_planner_candidates(
    session: Any,
    base_question_detail: dict,
    missing_paths: list[str],
    candidate_limit: int,
) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT id, question_id, prompt, bank_version_id, stage, variant, "
            "order_index, type_raw, validation_rule, instruction, "
            "standard_question, schema_paths, expected_key_points, prompt_meta "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_version_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "ORDER BY order_index ASC"
        ),
        {
            "bank_version_id": base_question_detail.get("bank_version_id"),
            "stage": base_question_detail.get("stage"),
            "variant": base_question_detail.get("variant"),
        },
    )
    rows = [row for row in result.mappings().all() if row]
    base_id = base_question_detail.get("id")
    base_row = None
    filtered: list[dict] = []

    for row in rows:
        if not row.get("prompt"):
            continue
        if not question_supports_grouping(row):
            continue
        if row.get("id") == base_id:
            base_row = row
        if not question_has_missing_paths(row, missing_paths):
            continue
        filtered.append(row)

    if not base_row and base_question_detail.get("prompt"):
        base_row = base_question_detail
    if base_row:
        filtered = [base_row] + [
            row for row in filtered if row.get("id") != base_row.get("id")
        ]

    if candidate_limit and len(filtered) > candidate_limit:
        return filtered[:candidate_limit]
    return filtered


def _build_question_plan_context(
    *,
    stage: str | None,
    variant: str | None,
    output_locale: OutputLocale,
    missing_paths: list[str],
    latest_answer: str | None,
    candidates: list[dict],
    max_questions: int,
    max_schema: int,
) -> Any | None:
    if not candidates:
        return None
    candidate_list = _format_candidate_list(candidates)
    return PROMPT_CONTEXT_BUILDER.question_plan(
        stage=stage,
        variant=variant,
        missing_paths=missing_paths,
        latest_answer=latest_answer,
        candidate_list=candidate_list,
        max_questions=max_questions,
        max_schema=max_schema,
        output_language=output_language_label(output_locale),
    )


def _normalize_planner_selection(
    payload: dict[str, Any],
    candidates: list[dict],
    *,
    max_questions: int,
    max_schema: int,
) -> tuple[list[dict], str | None]:
    if not candidates:
        return [], None
    candidate_map: dict[str, int] = {}
    for idx, detail in enumerate(candidates, start=1):
        detail_id = detail.get("id")
        if detail_id:
            candidate_map[str(detail_id).lower()] = idx
        question_id = detail.get("question_id")
        if isinstance(question_id, str) and question_id.strip():
            candidate_map[question_id.strip().lower()] = idx
        candidate_map[str(idx)] = idx

    indices: list[int] = []
    raw_indices = payload.get("question_indices") or payload.get("indices")
    if isinstance(raw_indices, list):
        for raw in raw_indices:
            try:
                idx = int(str(raw).strip())
            except ValueError:
                continue
            if 1 <= idx <= len(candidates):
                indices.append(idx)

    if not indices:
        raw_ids = payload.get("question_ids") or payload.get("question_qids") or []
        if isinstance(raw_ids, list):
            for raw in raw_ids:
                key = str(raw).strip().lower()
                idx = candidate_map.get(key)
                if idx:
                    indices.append(idx)

    seen: set[int] = set()
    ordered_indices: list[int] = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            ordered_indices.append(idx)

    if 1 not in ordered_indices:
        ordered_indices.insert(0, 1)

    if max_questions and len(ordered_indices) > max_questions:
        ordered_indices = ordered_indices[:max_questions]

    selected: list[dict] = []
    schema_set: set[str] = set()
    for idx in ordered_indices:
        detail = candidates[idx - 1]
        schema_paths = question_schema_paths(detail)
        new_paths = [path for path in schema_paths if path not in schema_set]
        if selected and max_schema and len(schema_set) + len(new_paths) > max_schema:
            break
        selected.append(detail)
        schema_set.update(new_paths)

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        prompt = None
    return selected, prompt


async def resolve_question_group_plan(
    session: Any,
    base_question_detail: dict,
    base_prompt: str,
    updated_missing_paths: list[str],
    latest_answer: str | None,
    *,
    output_locale: OutputLocale,
    max_questions: int,
    max_schema: int,
    timeout_ms: int,
    candidate_limit: int,
    min_candidates: int = 1,
    project_settings: dict | None = None,
    resolve_next_question_id: ResolveNextQuestionId | None = None,
) -> tuple[dict, list[str], UUID | None, dict[str, Any]] | None:
    if max_questions < 1 or not updated_missing_paths:
        return None
    if resolve_next_question_id is None:
        raise ValueError("resolve_next_question_id is required")
    if not question_supports_grouping(base_question_detail):
        return None

    candidates = await fetch_question_planner_candidates(
        session,
        base_question_detail,
        updated_missing_paths,
        candidate_limit,
    )
    if not candidates:
        return None
    if len(candidates) < max(1, min_candidates):
        return None

    context = _build_question_plan_context(
        stage=base_question_detail.get("stage"),
        variant=base_question_detail.get("variant"),
        output_locale=output_locale,
        missing_paths=updated_missing_paths,
        latest_answer=latest_answer,
        candidates=candidates,
        max_questions=max_questions,
        max_schema=max_schema,
    )
    if not context:
        return None

    t0 = time.monotonic()
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.DECISION_ONLY,
        timeout_override_ms=timeout_ms,
        timeout_minimum_ms=200,
    )
    if not result.ok or not isinstance(result.parsed, dict):
        return None
    latency_ms = int((time.monotonic() - t0) * 1000)

    selected_details, prompt = _normalize_planner_selection(
        result.parsed,
        candidates,
        max_questions=max_questions,
        max_schema=max_schema,
    )
    if not selected_details:
        return None

    ordered_details = sorted(
        selected_details,
        key=lambda detail: (
            detail.get("order_index") if detail.get("order_index") is not None else 0
        ),
    )
    prompts = [detail.get("prompt") or "" for detail in ordered_details]
    if len(ordered_details) == 1:
        transition = _build_transition_text(base_question_detail, latest_answer)
        prompt = _build_group_prompt(
            prompts,
            transition=transition,
        )
    elif not prompt:
        transition = _build_transition_text(base_question_detail, latest_answer)
        prompt = _build_group_prompt(
            prompts,
            transition=transition,
        )

    merged_detail = _merge_group_details(ordered_details, prompt)
    question_ids = [
        str(detail.get("id")) for detail in ordered_details if detail.get("id")
    ]
    question_codes = [
        str(detail.get("question_id")).strip()
        for detail in ordered_details
        if detail.get("question_id")
    ]
    last_detail = ordered_details[-1]
    next_id = await resolve_next_question_id(
        session,
        last_detail,
        missing_paths=updated_missing_paths,
        skip_optional=True,
    )

    plan_meta = {
        "model": result.model,
        "provider": result.provider,
        "latency_ms": latency_ms,
        "candidate_count": len(candidates),
        "selected_count": len(ordered_details),
        "question_ids": question_ids,
        "question_codes": question_codes,
        "missing_paths": updated_missing_paths,
        "planner_version": "v1",
    }
    return merged_detail, question_ids, next_id, plan_meta


async def persist_question_plan(
    session: Any,
    *,
    org_id: str,
    project_id: str,
    stage: str | None,
    variant: str | None,
    question_instance_id: UUID | None,
    question_bank_question_ids: list[str],
    question_codes: list[str],
    schema_paths: list[str],
    prompt: str,
    model: str | None,
    latency_ms: int | None,
    meta: dict[str, Any] | None,
) -> UUID | None:
    if not stage or not variant or not prompt or not question_bank_question_ids:
        return None
    normalized_ids: list[str] = []
    for raw_id in question_bank_question_ids:
        try:
            normalized_ids.append(str(UUID(str(raw_id))))
        except Exception:
            continue
    if not normalized_ids:
        return None
    result = await session.execute(
        text(
            "INSERT INTO question_plans ("
            "org_id, project_id, stage, variant, question_instance_id, "
            "question_bank_question_ids, question_ids, schema_paths, prompt, "
            "model, latency_ms, meta"
            ") VALUES ("
            "app_org_id(), :project_id, :stage, :variant, :question_instance_id, "
            ":question_bank_question_ids, :question_ids, :schema_paths, :prompt, "
            ":model, :latency_ms, :meta"
            ") RETURNING id"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": project_id,
            "stage": stage,
            "variant": variant,
            "question_instance_id": (
                str(question_instance_id) if question_instance_id else None
            ),
            "question_bank_question_ids": normalized_ids,
            "question_ids": question_codes,
            "schema_paths": schema_paths,
            "prompt": prompt,
            "model": model,
            "latency_ms": latency_ms,
            "meta": meta or {},
        },
    )
    row = result.mappings().first()
    if not row:
        return None
    return row.get("id")


async def resolve_question_group(
    session: Any,
    base_question_detail: dict,
    base_prompt: str,
    updated_missing_paths: list[str],
    latest_answer: str | None = None,
    *,
    max_questions: int,
    fetch_question_detail: FetchQuestionDetail | None = None,
    resolve_next_question_id: ResolveNextQuestionId | None = None,
) -> tuple[dict, list[str], UUID | None]:
    if max_questions < 2:
        return base_question_detail, [str(base_question_detail.get("id"))], None
    if fetch_question_detail is None:
        raise ValueError("fetch_question_detail is required")
    if resolve_next_question_id is None:
        raise ValueError("resolve_next_question_id is required")
    if not question_supports_grouping(base_question_detail):
        return base_question_detail, [str(base_question_detail.get("id"))], None

    prompts: list[str] = [base_prompt]
    details: list[dict] = [base_question_detail]
    question_ids: list[str] = [str(base_question_detail.get("id"))]

    next_id = await resolve_next_question_id(
        session,
        base_question_detail,
        missing_paths=updated_missing_paths,
        skip_optional=True,
    )
    while next_id and len(details) < max_questions:
        detail = await fetch_question_detail(session, next_id)
        if not question_supports_grouping(detail):
            break
        if not question_has_missing_paths(detail, updated_missing_paths):
            next_id = await resolve_next_question_id(
                session,
                detail,
                missing_paths=updated_missing_paths,
                skip_optional=True,
            )
            continue
        prompts.append(detail.get("prompt") or "")
        details.append(detail)
        question_ids.append(str(detail.get("id")))
        next_id = await resolve_next_question_id(
            session,
            detail,
            missing_paths=updated_missing_paths,
            skip_optional=True,
        )

    if len(details) == 1:
        return base_question_detail, question_ids, next_id

    transition = _build_transition_text(base_question_detail, latest_answer)
    combined_prompt = _build_group_prompt(prompts, transition=transition)
    merged_detail = _merge_group_details(details, combined_prompt)
    return merged_detail, question_ids, next_id


async def fetch_group_meta(
    session: Any,
    *,
    project_id: str,
    question_instance_id: UUID,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT meta "
            "FROM conversation_messages "
            "WHERE project_id = :project_id "
            "AND question_instance_id = :question_instance_id "
            "AND role = 'assistant' "
            "AND deleted_at IS NULL "
            "ORDER BY id DESC "
            "LIMIT 1"
        ),
        {"project_id": project_id, "question_instance_id": question_instance_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    meta = row.get("meta")
    if not isinstance(meta, dict):
        return None
    group = meta.get("question_group")
    return group if isinstance(group, dict) else None


def apply_group_override(
    question_detail: dict,
    group_meta: dict[str, Any],
) -> dict:
    merged = dict(question_detail)
    prompt = group_meta.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        merged["prompt"] = prompt
    schema_paths = group_meta.get("schema_paths")
    if isinstance(schema_paths, list) and schema_paths:
        merged["schema_paths"] = schema_paths
    expected_points = group_meta.get("expected_key_points")
    if isinstance(expected_points, list) and expected_points:
        merged["expected_key_points"] = expected_points
    validation_rule = group_meta.get("validation_rule")
    if isinstance(validation_rule, str) and validation_rule.strip():
        merged["validation_rule"] = validation_rule
    instruction = group_meta.get("instruction")
    if isinstance(instruction, str) and instruction.strip():
        merged["instruction"] = instruction
    standard_question = group_meta.get("standard_question")
    if isinstance(standard_question, str) and standard_question.strip():
        merged["standard_question"] = standard_question
    merged["prompt_meta"] = {}
    return merged
