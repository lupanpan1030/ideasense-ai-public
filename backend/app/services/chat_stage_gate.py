from __future__ import annotations

from app.services.stage_gate_paths import stage_allows_awaiting_confirm


STAGE_NEXT_MAP = {"problem": "market", "market": "tech", "tech": "report"}


def is_stage_gate_ready_for_review(
    stage_status_ready: str | None,
    current_stage_status: str | None,
) -> bool:
    status_value = stage_status_ready or current_stage_status
    if not isinstance(status_value, str):
        return False
    return status_value.strip().lower() == "awaiting_confirm"


def should_enter_stage_gate_review(
    *,
    stage_status_ready: str | None,
    current_stage_status: str | None,
    stage: str | None,
    variant: str | None,
    missing_paths: list[str] | None,
) -> bool:
    if is_stage_gate_ready_for_review(stage_status_ready, current_stage_status):
        return True
    if missing_paths:
        return False
    return stage_allows_awaiting_confirm(stage, variant)


def resolve_next_stage(stage: str | None) -> str | None:
    if not stage:
        return None
    return STAGE_NEXT_MAP.get(stage)
