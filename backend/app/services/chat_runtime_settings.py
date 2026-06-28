from __future__ import annotations

import os
from typing import Any

from app.services.prompt_runtime import (
    DEFAULT_PROMPT_TASK_REGISTRY,
    resolve_prompt_task_timeout_ms,
)


def parse_env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def resolve_question_group_settings() -> tuple[bool, int, bool]:
    enabled = parse_env_flag("QUESTION_GROUP_ENABLED", True)
    transition_enabled = parse_env_flag("QUESTION_TRANSITION_ENABLED", True)
    max_questions = int(os.getenv("QUESTION_GROUP_MAX", "3") or 3)
    if max_questions < 1:
        max_questions = 1
    if max_questions == 1:
        enabled = False
    return enabled, max_questions, transition_enabled


def parse_csv_set(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def resolve_question_planner_settings() -> dict[str, Any]:
    enabled = parse_env_flag("QUESTION_PLANNER_ENABLED", True)
    max_questions = int(os.getenv("QUESTION_PLANNER_MAX_QUESTIONS", "3") or 3)
    if max_questions < 1:
        max_questions = 1
    max_schema = int(os.getenv("QUESTION_PLANNER_MAX_SCHEMA", "6") or 6)
    if max_schema < 1:
        max_schema = 1
    timeout_ms = int(os.getenv("QUESTION_PLANNER_TIMEOUT_MS", "1000") or 1000)
    if timeout_ms < 200:
        timeout_ms = 200
    candidate_limit = int(os.getenv("QUESTION_PLANNER_CANDIDATE_LIMIT", "12") or 12)
    if candidate_limit < 1:
        candidate_limit = 1
    min_missing_paths = int(os.getenv("QUESTION_PLANNER_MIN_MISSING_PATHS", "2") or 2)
    if min_missing_paths < 1:
        min_missing_paths = 1
    min_candidates = int(os.getenv("QUESTION_PLANNER_MIN_CANDIDATES", "2") or 2)
    if min_candidates < 1:
        min_candidates = 1
    stages = parse_csv_set(os.getenv("QUESTION_PLANNER_STAGES", "problem,market"))
    return {
        "enabled": enabled,
        "max_questions": max_questions,
        "max_schema": max_schema,
        "timeout_ms": timeout_ms,
        "candidate_limit": candidate_limit,
        "min_missing_paths": min_missing_paths,
        "min_candidates": min_candidates,
        "stages": stages,
    }


def resolve_question_compose_start_timeout_sec(timeout_ms: int | None = None) -> float:
    if timeout_ms is None:
        timeout_ms = (
            resolve_prompt_task_timeout_ms(
                DEFAULT_PROMPT_TASK_REGISTRY.get("question_compose")
            )
            or 3500
        )
    if timeout_ms < 0:
        timeout_ms = 0
    return timeout_ms / 1000


def question_compose_enabled() -> bool:
    return parse_env_flag("QUESTION_COMPOSE_ENABLED", True)


def followup_compose_enabled() -> bool:
    return parse_env_flag("FOLLOWUP_COMPOSE_ENABLED", True)
