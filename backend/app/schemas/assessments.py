from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StageConfirmRequest(BaseModel):
    project_id: UUID
    client_context_version: int | None = None
    output_locale: str | None = None


class StageConfirmResponse(BaseModel):
    assessment_id: UUID | None = None
    next_stage: str | None = None
    stage_status: str | None = None
    score_status: str | None = None
    scores_json: dict[str, Any] | None = None
    total_score: float | None = None
    risk_matrix: dict[str, Any] | None = None
    context_card: dict[str, Any] | None = None
    validation_plan: list[dict[str, Any]] = Field(default_factory=list)
    report_job_status: dict[str, Any] | None = None


class StageDraftResponse(BaseModel):
    assessment_id: UUID | None = None
    project_id: UUID
    stage: str
    stage_status: str | None = None
    draft_summary_text: str
    draft_output_locale: str | None = None
    context_version: int | None = None
    context_updated_at: datetime | None = None
    score_status: str | None = None
    generation_status: str = "ready"
    retryable: bool = False
    last_error: str | None = None


class StageSummaryItem(BaseModel):
    stage: str
    draft_summary_markdown: str | None = None
    draft_output_locale: str | None = None
    final_summary_markdown: str | None = None
    final_output_locale: str | None = None
    confirmed: bool
    updated_at: datetime | None = None
    user_edited_paths: list[str] = Field(default_factory=list)
    context_card: dict[str, Any] = Field(default_factory=dict)
    validation_plan: list[dict[str, Any]] = Field(default_factory=list)


class StageSummariesResponse(BaseModel):
    project_id: UUID
    summaries: list[StageSummaryItem]


class VerificationSource(BaseModel):
    title: str | None = None
    url: str | None = None
    domain: str | None = None
    snippet: str | None = None


class StageQuestionVerification(BaseModel):
    question_id: str
    question_title: str | None = None
    priority: str = "none"
    status: str = "not_checked"
    status_detail: str | None = None
    supported_claims: int = 0
    contradicted_claims: int = 0
    uncertain_claims: int = 0
    total_claims: int = 0
    sources: list[VerificationSource] = Field(default_factory=list)


class StageVerificationSummary(BaseModel):
    stage: str
    total: int = 0
    supported: int = 0
    contradicted: int = 0
    uncertain: int = 0
    failed: int = 0
    stale: int = 0
    provider_unavailable: int = 0
    not_checked: int = 0
    verified: int = 0
    verifying: int = 0
    no_evidence: int = 0
    not_applicable: int = 0
    questions: list[StageQuestionVerification] = Field(default_factory=list)


class ProjectVerificationResponse(BaseModel):
    project_id: UUID
    stages: list[StageVerificationSummary]


class VerificationRefreshResponse(BaseModel):
    project_id: UUID
    stage: str | None = None
    enqueued: int = 0
    skipped: int = 0
