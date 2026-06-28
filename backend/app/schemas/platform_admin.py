from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class OrgSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    settings: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None


class OrgListResponse(BaseModel):
    orgs: list[OrgSummary]
    total: int
    limit: int
    offset: int


class OrgUpdateRequest(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None


class PromptTemplateInfo(BaseModel):
    id: str
    template_key: str
    version: str
    content: str
    purpose: str
    stage: str | None
    variant: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None


class PromptTemplateListResponse(BaseModel):
    templates: list[PromptTemplateInfo]


class PromptTemplateCreateRequest(BaseModel):
    content: str
    purpose: str | None = None
    stage: str | None = None
    variant: str | None = None
    version: str | None = None


class PlatformAdminItem(BaseModel):
    user_id: UUID
    email: str | None = None
    display_name: str | None = None
    role: str
    status: str
    created_at: datetime | None
    updated_at: datetime | None


class PlatformAdminListResponse(BaseModel):
    admins: list[PlatformAdminItem]


class PlatformAdminUpsertRequest(BaseModel):
    user_id: UUID | None = None
    email: str | None = None
    role: str = "admin"
    status: str = "active"


class PlatformSettingEntry(BaseModel):
    key: str
    value: Any
    updated_by: UUID | None = None
    updated_by_email: str | None = None
    updated_by_name: str | None = None
    created_at: datetime | None
    updated_at: datetime | None


class PlatformSettingsResponse(BaseModel):
    settings: dict[str, Any]
    entries: list[PlatformSettingEntry]


class PlatformSettingsUpdateRequest(BaseModel):
    settings: dict[str, Any] | None = None
    remove: list[str] | None = None


class ReportQualityObservationItem(BaseModel):
    id: UUID
    org_id: UUID
    org_name: str | None = None
    org_slug: str | None = None
    project_id: UUID
    project_title: str | None = None
    report_id: UUID
    report_version: int
    generated_from_state_version: int
    observation_schema_version: str
    status: str
    failed_invariants: list[str]
    warning_invariants: list[str]
    score_snapshot: dict[str, Any]
    evidence_counts: dict[str, Any]
    canonical_boundaries: dict[str, Any]
    observed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class ReportQualityObservationDetail(ReportQualityObservationItem):
    observation: dict[str, Any]


class ReportQualityObservationListResponse(BaseModel):
    observations: list[ReportQualityObservationItem]
    total: int
    limit: int
    offset: int


class ReportQualityStatusCount(BaseModel):
    status: str
    count: int


class ReportQualityInvariantCount(BaseModel):
    invariant_id: str
    severity: str
    count: int


class ReportQualitySummaryResponse(BaseModel):
    total: int
    status_counts: list[ReportQualityStatusCount]
    invariant_counts: list[ReportQualityInvariantCount]
