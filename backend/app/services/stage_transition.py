from dataclasses import dataclass
from typing import Any

from app.services.stage_gate_paths import (
    filter_stage_blocking_missing_paths,
    stage_allows_awaiting_confirm,
)

STAGE_STATUS_IN_PROGRESS = "in_progress"
STAGE_STATUS_AWAITING_CONFIRM = "awaiting_confirm"
STAGE_STATUS_PASSED = "passed"


@dataclass(frozen=True)
class StageTransitionDecision:
    stage: str | None
    variant: str | None
    next_stage_status: str
    allowed: bool
    reason: str
    missing_paths: list[str]
    current_stage_update: str | None = None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def decide_stage_ready(
    stage: str | None,
    missing_paths: list[str] | None,
    *,
    state_json: Any,
    state_meta: Any = None,
    variant: str | None = None,
) -> StageTransitionDecision:
    normalized_stage = _normalize_text(stage)
    normalized_variant = _normalize_text(variant)
    updated_missing_paths = filter_stage_blocking_missing_paths(
        normalized_stage,
        missing_paths,
        state_json=state_json,
        state_meta=state_meta,
    )

    if normalized_stage is None:
        return StageTransitionDecision(
            stage=None,
            variant=normalized_variant,
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_missing",
            missing_paths=updated_missing_paths,
        )

    if normalized_stage == "report":
        return StageTransitionDecision(
            stage=normalized_stage,
            variant=normalized_variant,
            next_stage_status=STAGE_STATUS_AWAITING_CONFIRM,
            allowed=True,
            reason="report_stage_ready",
            missing_paths=updated_missing_paths,
        )

    if updated_missing_paths:
        return StageTransitionDecision(
            stage=normalized_stage,
            variant=normalized_variant,
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="blocking_paths_missing",
            missing_paths=updated_missing_paths,
        )

    if not stage_allows_awaiting_confirm(normalized_stage, normalized_variant):
        return StageTransitionDecision(
            stage=normalized_stage,
            variant=normalized_variant,
            next_stage_status=STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_disallows_auto_awaiting_confirm",
            missing_paths=[],
        )

    return StageTransitionDecision(
        stage=normalized_stage,
        variant=normalized_variant,
        next_stage_status=STAGE_STATUS_AWAITING_CONFIRM,
        allowed=True,
        reason="blocking_paths_resolved",
        missing_paths=[],
    )


def decide_next_stage_after_confirmation(
    next_stage: str,
    missing_paths: list[str] | None,
    *,
    state_json: Any,
    state_meta: Any = None,
    variant: str | None = None,
) -> StageTransitionDecision:
    return decide_stage_ready(
        next_stage,
        missing_paths,
        state_json=state_json,
        state_meta=state_meta,
        variant=variant,
    )


def decide_stage_confirmation_advance(
    *,
    requested_stage: str,
    current_stage: str | None,
    stage_status: str | None,
    next_stage: str,
    next_stage_status: str,
) -> StageTransitionDecision:
    normalized_requested = _normalize_text(requested_stage)
    normalized_current = _normalize_text(current_stage)
    normalized_status = _normalize_text(stage_status)
    normalized_next = _normalize_text(next_stage)
    normalized_next_status = (
        _normalize_text(next_stage_status) or STAGE_STATUS_IN_PROGRESS
    )

    if normalized_current != normalized_requested:
        return StageTransitionDecision(
            stage=normalized_requested,
            variant=None,
            next_stage_status=normalized_status or STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_mismatch",
            missing_paths=[],
        )

    if normalized_status != STAGE_STATUS_AWAITING_CONFIRM:
        return StageTransitionDecision(
            stage=normalized_requested,
            variant=None,
            next_stage_status=normalized_status or STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_not_awaiting_confirm",
            missing_paths=[],
        )

    return StageTransitionDecision(
        stage=normalized_requested,
        variant=None,
        next_stage_status=normalized_next_status,
        allowed=True,
        reason="user_confirmed_stage",
        missing_paths=[],
        current_stage_update=normalized_next,
    )


def decide_stage_question_answer(
    *,
    current_stage: str | None,
    stage_status: str | None,
) -> StageTransitionDecision:
    normalized_current = _normalize_text(current_stage)
    normalized_status = _normalize_text(stage_status) or STAGE_STATUS_IN_PROGRESS

    if normalized_current is None:
        return StageTransitionDecision(
            stage=None,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_missing",
            missing_paths=[],
        )

    if normalized_current == "report":
        return StageTransitionDecision(
            stage=normalized_current,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_blocks_questions",
            missing_paths=[],
        )

    if normalized_status == STAGE_STATUS_PASSED:
        return StageTransitionDecision(
            stage=normalized_current,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_passed",
            missing_paths=[],
        )

    if normalized_status != STAGE_STATUS_IN_PROGRESS:
        return StageTransitionDecision(
            stage=normalized_current,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_not_in_progress",
            missing_paths=[],
        )

    return StageTransitionDecision(
        stage=normalized_current,
        variant=None,
        next_stage_status=normalized_status,
        allowed=True,
        reason="stage_allows_questions",
        missing_paths=[],
    )


def decide_stage_draft_generation(
    *,
    requested_stage: str,
    current_stage: str | None,
    stage_status: str | None,
) -> StageTransitionDecision:
    normalized_requested = _normalize_text(requested_stage)
    normalized_current = _normalize_text(current_stage)
    normalized_status = _normalize_text(stage_status) or STAGE_STATUS_IN_PROGRESS

    if normalized_current != normalized_requested:
        return StageTransitionDecision(
            stage=normalized_requested,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_mismatch",
            missing_paths=[],
        )

    if normalized_status != STAGE_STATUS_AWAITING_CONFIRM:
        return StageTransitionDecision(
            stage=normalized_requested,
            variant=None,
            next_stage_status=normalized_status,
            allowed=False,
            reason="stage_not_awaiting_confirm",
            missing_paths=[],
        )

    return StageTransitionDecision(
        stage=normalized_requested,
        variant=None,
        next_stage_status=normalized_status,
        allowed=True,
        reason="stage_allows_draft_generation",
        missing_paths=[],
    )


def decide_report_confirmation_complete(
    *,
    current_stage: str | None,
    stage_status: str | None,
) -> StageTransitionDecision:
    normalized_current = _normalize_text(current_stage)
    normalized_status = _normalize_text(stage_status)

    if normalized_current != "report":
        return StageTransitionDecision(
            stage="report",
            variant=None,
            next_stage_status=normalized_status or STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_mismatch",
            missing_paths=[],
        )

    if normalized_status != STAGE_STATUS_AWAITING_CONFIRM:
        return StageTransitionDecision(
            stage="report",
            variant=None,
            next_stage_status=normalized_status or STAGE_STATUS_IN_PROGRESS,
            allowed=False,
            reason="stage_not_awaiting_confirm",
            missing_paths=[],
        )

    return StageTransitionDecision(
        stage="report",
        variant=None,
        next_stage_status=STAGE_STATUS_PASSED,
        allowed=True,
        reason="report_confirmed",
        missing_paths=[],
    )


def is_report_generation_recovery_stage(
    *,
    current_stage: str | None,
    stage_status: str | None,
) -> bool:
    return (
        _normalize_text(current_stage) == "report"
        and _normalize_text(stage_status) == STAGE_STATUS_PASSED
    )


def next_stage_starts_in_review(
    next_stage: str,
    next_stage_status: str | None,
) -> bool:
    return (
        _normalize_text(next_stage) != "report"
        and _normalize_text(next_stage_status) == STAGE_STATUS_AWAITING_CONFIRM
    )
