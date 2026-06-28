from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.services.stage_transition import (
    STAGE_STATUS_AWAITING_CONFIRM,
    STAGE_STATUS_IN_PROGRESS,
)


@dataclass(frozen=True)
class StageStateSnapshot:
    state_json: dict[str, Any]
    state_meta: dict[str, Any]
    state_version: int


@dataclass(frozen=True)
class StageConfirmationDefaults:
    next_stage: str
    next_variant: str
    next_stage_status: str


def normalize_stage_state_snapshot(state_row: Any) -> StageStateSnapshot:
    state_json = state_row.get("state_json") if state_row else {}
    if not isinstance(state_json, dict):
        state_json = {}

    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}

    state_version = state_row.get("state_version") if state_row else 0
    if state_version is None:
        state_version = 0

    return StageStateSnapshot(
        state_json=state_json,
        state_meta=state_meta,
        state_version=int(state_version),
    )


def resolve_stage_confirmation_defaults(
    *,
    stage: str,
    next_stage_map: dict[str, str],
) -> StageConfirmationDefaults | None:
    next_stage = next_stage_map.get(stage)
    if not next_stage:
        return None

    return StageConfirmationDefaults(
        next_stage=next_stage,
        next_variant="router" if next_stage == "tech" else "default",
        next_stage_status=(
            STAGE_STATUS_AWAITING_CONFIRM
            if next_stage == "report"
            else STAGE_STATUS_IN_PROGRESS
        ),
    )


def extract_stage_prompt_task_traces(
    assessment_row: Any,
) -> dict[str, Any]:
    existing_scores_json = (
        assessment_row.get("scores_json") if assessment_row else None
    )
    if isinstance(existing_scores_json, dict) and isinstance(
        existing_scores_json.get("prompt_task_traces"),
        dict,
    ):
        return deepcopy(existing_scores_json["prompt_task_traces"])
    return {}


def build_prepared_stage_confirmation_payload(
    *,
    org_id: str,
    project_id: str,
    user_id: str,
    stage: str,
    bank_id: Any,
    current_variant: str,
    defaults: StageConfirmationDefaults,
    next_variant: str,
    next_stage_status: str,
    state_snapshot: StageStateSnapshot,
    current_stage_missing_paths: list[str],
    assessment_row: Any,
    prompt_task_traces: dict[str, Any],
    output_locale: str,
    current_question_id: Any | None,
    next_question_id: Any | None,
    missing_paths: list[str],
    question_detail: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "org_id": org_id,
        "project_id": project_id,
        "user_id": user_id,
        "stage": stage,
        "bank_id": bank_id,
        "current_variant": current_variant,
        "next_stage": defaults.next_stage,
        "next_variant": next_variant,
        "next_stage_status": next_stage_status,
        "state_version": state_snapshot.state_version,
        "current_stage_missing_paths": current_stage_missing_paths,
        "summary_markdown": (
            assessment_row.get("draft_summary_markdown")
            if assessment_row
            else None
        ),
        "summary_model": (
            assessment_row.get("generator_model") if assessment_row else None
        ),
        "prompt_task_traces": prompt_task_traces,
        "output_locale": output_locale,
        "current_question_id": current_question_id,
        "next_question_id": next_question_id,
        "missing_paths": missing_paths,
        "question_detail": question_detail,
    }
