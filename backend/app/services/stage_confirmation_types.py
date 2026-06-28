from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.localization import OutputLocale


class StageConfirmationRuntimeError(RuntimeError):
    pass


class StageConfirmationConflictError(RuntimeError):
    pass


class StageConfirmationNotFoundError(RuntimeError):
    pass


class StageConfirmationPermissionError(RuntimeError):
    pass


STAGE_CONFIRMATION_NEXT_MAP = {"problem": "market", "market": "tech", "tech": "report"}


@dataclass(frozen=True)
class ConfirmedStagePersistenceResult:
    assessment_id: Any | None
    context_card: dict[str, Any]
    validation_plan: list[dict[str, Any]]
    scores_json_payload: dict[str, Any] | None


@dataclass(frozen=True)
class StageConfirmationCommitResult:
    assessment_id: Any | None
    next_stage: str
    stage_status: str
    score_status: str
    scores_json: dict[str, Any] | None
    total_score: float | None
    risk_matrix: dict[str, Any] | None
    context_card: dict[str, Any]
    validation_plan: list[dict[str, Any]]
    report_job_status: dict[str, Any] | None


@dataclass(frozen=True)
class PreparedStageConfirmation:
    org_id: str
    project_id: str
    user_id: str
    stage: str
    bank_id: Any
    current_variant: str
    next_stage: str
    next_variant: str
    next_stage_status: str
    state_version: int
    current_stage_missing_paths: list[str]
    summary_markdown: str | None
    summary_model: str | None
    prompt_task_traces: dict[str, Any]
    output_locale: OutputLocale
    current_question_id: Any | None
    next_question_id: Any | None
    missing_paths: list[str]
    question_detail: dict[str, Any] | None
