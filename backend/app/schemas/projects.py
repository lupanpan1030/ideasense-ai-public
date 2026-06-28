from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    id: UUID
    org_id: UUID
    owner_user_id: UUID
    title: str
    description: str | None = None
    question_bank_version_id: UUID
    current_stage: str
    current_variant: str
    stage_status: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ProjectsListResponse(BaseModel):
    projects: list[ProjectSummary]
    total: int
    limit: int
    offset: int


class ProjectRecord(BaseModel):
    id: UUID
    org_id: UUID
    owner_user_id: UUID
    title: str
    description: str | None = None
    question_bank_version_id: UUID
    current_stage: str
    current_variant: str
    stage_status: str
    settings: dict
    is_archived: bool
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProjectRuntimeRecord(BaseModel):
    project_id: UUID
    org_id: UUID
    stage: str
    variant: str
    current_question_bank_question_id: UUID | None = None
    next_question_bank_question_id: UUID | None = None
    missing_paths: list[str]
    turn_state: str
    runtime_version: int
    created_at: datetime
    updated_at: datetime


class ProjectQuestionInstance(BaseModel):
    id: UUID
    question_bank_question_id: UUID
    status: str
    asked_count: int
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(BaseModel):
    project: ProjectRecord
    runtime: ProjectRuntimeRecord
    current_question_instance_id: UUID | None = None


class ProjectContextResponse(BaseModel):
    project_id: UUID
    stage: str
    current_question_id: str | None = None
    next_question_id: str | None = None
    turn_state: str
    missing_fields: list[str]
    data: dict[str, Any]
    user_edited_paths: dict[str, list[str]] = {}
    answer_meta: dict[str, dict[str, Any]] = {}
    context_card: dict[str, Any] = Field(default_factory=dict)
    context_version: int
    updated_at: datetime


class ProjectPendingConfirmResponse(BaseModel):
    project_id: UUID
    pending_confirm: dict[str, Any]
    context_version: int
    updated_at: datetime


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    is_archived: bool | None = None


class ProjectActionResponse(BaseModel):
    project: ProjectSummary


class ProjectPendingConfirmUpdateRequest(BaseModel):
    updates: dict[str, Any]
    client_context_version: int | None = None


class ProjectPendingConfirmResolveRequest(BaseModel):
    accept_paths: list[str] = []
    reject_paths: list[str] = []
    client_context_version: int | None = None


class ProjectReportResponse(BaseModel):
    project_id: UUID
    generated_at: str
    artifact_locale: str | None = None
    project: dict[str, Any]
    lean_canvas: dict[str, Any]
    market_evidence: dict[str, Any]
    dvf_confidence: dict[str, Any] | None = None
    dvf_scoreboard: dict[str, Any]
    dvf_assessment: dict[str, Any] | None = None
    key_risks: list[dict[str, Any]]
    diagnosis: dict[str, Any] = Field(default_factory=dict)
    validation_plan: list[dict[str, Any]] = Field(default_factory=list)
    architecture_diagram: dict[str, Any] | None = None
    overall_summary: str | None = None
    data_quality: dict[str, Any] | None = None
    artifact_schema_version: str | None = None
    decision_snapshot: dict[str, Any] = Field(default_factory=dict)
    score_rationales: dict[str, Any] = Field(default_factory=dict)
    risk_register: list[dict[str, Any]] = Field(default_factory=list)
    experiment_plan: list[dict[str, Any]] = Field(default_factory=list)
    evidence_index: dict[str, Any] = Field(default_factory=dict)
    user_edited_paths: dict[str, list[str]] = {}
    assessments: list[dict[str, Any]]


class ProjectReportStatusResponse(BaseModel):
    project_id: UUID
    current_stage: str | None = None
    stage_status: str | None = None
    job_type: str | None = None
    status: str
    retryable: bool = False
    report_id: UUID | None = None
    report_version: int | None = None
    generated_at: str | None = None
    context_version: int | None = None
    next_poll_ms: int = 2000


class ConversationMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    stage: str | None = None
    meta: dict[str, Any] | None = None


class ConversationListResponse(BaseModel):
    messages: list[ConversationMessage]


class ProjectCreateRequest(BaseModel):
    title: str
    description: str | None = None
    output_locale: str | None = None
    # Optional question-bank selector. "default" runs the full assessment;
    # "lite" runs the short DVF demo bank. Constrained to a known allowlist so
    # clients cannot point projects at arbitrary banks.
    bank_key: str | None = None


class ProjectCreateResponse(BaseModel):
    project: ProjectRecord
    runtime: ProjectRuntimeRecord
    question_instance: ProjectQuestionInstance
