from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.permissions import require_platform_admin
from app.schemas.platform_admin import (
    OrgListResponse,
    OrgSummary,
    OrgUpdateRequest,
    PlatformAdminItem,
    PlatformAdminListResponse,
    PlatformAdminUpsertRequest,
    PlatformSettingsResponse,
    PlatformSettingsUpdateRequest,
    PromptTemplateCreateRequest,
    PromptTemplateInfo,
    PromptTemplateListResponse,
    ReportQualityObservationDetail,
    ReportQualityObservationListResponse,
    ReportQualitySummaryResponse,
)
from app.services.platform_orgs import (
    PlatformOrgNotFoundError,
    PlatformOrgValidationError,
    fetch_platform_orgs_payload,
    update_platform_org_payload,
)
from app.services.platform_admin_users import (
    PlatformAdminUserNotFoundError,
    PlatformAdminUsersValidationError,
    list_platform_admin_payloads,
    upsert_platform_admin_payload,
)
from app.services.platform_report_quality import (
    PlatformReportQualityNotFoundError,
    PlatformReportQualityValidationError,
    fetch_report_quality_summary_payload,
    get_report_quality_observation_payload,
    list_report_quality_observation_payloads,
)
from app.services.platform_settings import (
    PlatformSettingsValidationError,
    fetch_platform_settings_payload,
    update_platform_settings_payload,
)
from app.services.prompt_templates import (
    PromptTemplateRevisionCreateError,
    PromptTemplateRevisionValidationError,
    create_prompt_template_revision,
    list_active_global_prompt_template_payloads,
)

router = APIRouter(prefix="/platform-api", tags=["platform"])


@router.get(
    "/report-quality/summary",
    response_model=ReportQualitySummaryResponse,
)
async def get_report_quality_summary(
    session: AsyncSession = Depends(get_db_session),
    status: str | None = Query(default=None),
    org_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    report_id: UUID | None = Query(default=None),
    observed_from: datetime | None = Query(default=None),
    observed_to: datetime | None = Query(default=None),
    q: str | None = Query(default=None),
) -> ReportQualitySummaryResponse:
    await require_platform_admin(session)
    try:
        payload = await fetch_report_quality_summary_payload(
            session,
            quality_status=status,
            org_id=org_id,
            project_id=project_id,
            report_id=report_id,
            observed_from=observed_from,
            observed_to=observed_to,
            q=q,
        )
    except PlatformReportQualityValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc
    return ReportQualitySummaryResponse(**payload)


@router.get(
    "/report-quality/observations",
    response_model=ReportQualityObservationListResponse,
)
async def list_report_quality_observations(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(default=None),
    org_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    report_id: UUID | None = Query(default=None),
    observed_from: datetime | None = Query(default=None),
    observed_to: datetime | None = Query(default=None),
    q: str | None = Query(default=None),
) -> ReportQualityObservationListResponse:
    await require_platform_admin(session)
    try:
        payload = await list_report_quality_observation_payloads(
            session,
            limit=limit,
            offset=offset,
            quality_status=status,
            org_id=org_id,
            project_id=project_id,
            report_id=report_id,
            observed_from=observed_from,
            observed_to=observed_to,
            q=q,
        )
    except PlatformReportQualityValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc
    return ReportQualityObservationListResponse(**payload)


@router.get(
    "/report-quality/observations/{observation_id}",
    response_model=ReportQualityObservationDetail,
)
async def get_report_quality_observation(
    observation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ReportQualityObservationDetail:
    await require_platform_admin(session)
    try:
        payload = await get_report_quality_observation_payload(
            session,
            observation_id=observation_id,
        )
    except PlatformReportQualityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report quality observation not found",
        ) from exc
    return ReportQualityObservationDetail(**payload)


@router.get("/orgs", response_model=OrgListResponse)
async def list_orgs(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(default=None),
) -> OrgListResponse:
    await require_platform_admin(session)
    return OrgListResponse(
        **await fetch_platform_orgs_payload(
            session,
            limit=limit,
            offset=offset,
            q=q,
        )
    )


@router.patch("/orgs/{org_id}", response_model=OrgSummary)
async def update_org(
    org_id: UUID,
    payload: OrgUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> OrgSummary:
    await require_platform_admin(session)
    try:
        org_payload = await update_platform_org_payload(
            session,
            org_id=org_id,
            name=payload.name,
            settings=payload.settings,
        )
    except PlatformOrgValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except PlatformOrgNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
    return OrgSummary(**org_payload)


@router.get("/prompts", response_model=PromptTemplateListResponse)
async def list_global_prompt_templates(
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateListResponse:
    await require_platform_admin(session)
    templates = [
        PromptTemplateInfo(**payload)
        for payload in await list_active_global_prompt_template_payloads(session)
    ]
    return PromptTemplateListResponse(templates=templates)


@router.post("/prompts/{template_key}", response_model=PromptTemplateInfo)
async def create_global_prompt_template(
    template_key: str,
    payload: PromptTemplateCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PromptTemplateInfo:
    await require_platform_admin(session)
    try:
        created = await create_prompt_template_revision(
            session,
            template_key=template_key,
            content=payload.content,
            purpose=payload.purpose,
            stage=payload.stage,
            variant=payload.variant,
            version=payload.version,
            scope="global",
        )
    except PromptTemplateRevisionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except PromptTemplateRevisionCreateError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return PromptTemplateInfo(**created)


@router.get("/admins", response_model=PlatformAdminListResponse)
async def list_platform_admins(
    session: AsyncSession = Depends(get_db_session),
) -> PlatformAdminListResponse:
    await require_platform_admin(session)
    admins = [
        PlatformAdminItem(**payload)
        for payload in await list_platform_admin_payloads(session)
    ]
    return PlatformAdminListResponse(admins=admins)


@router.post("/admins", response_model=PlatformAdminItem)
async def upsert_platform_admin(
    payload: PlatformAdminUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PlatformAdminItem:
    await require_platform_admin(session)
    try:
        admin_payload = await upsert_platform_admin_payload(
            session,
            user_id=payload.user_id,
            email=payload.email,
            role=payload.role,
            status=payload.status,
        )
    except PlatformAdminUsersValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except PlatformAdminUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
    return PlatformAdminItem(**admin_payload)


@router.get("/settings", response_model=PlatformSettingsResponse)
async def get_platform_settings(
    session: AsyncSession = Depends(get_db_session),
) -> PlatformSettingsResponse:
    await require_platform_admin(session)
    return PlatformSettingsResponse(**await fetch_platform_settings_payload(session))


@router.patch("/settings", response_model=PlatformSettingsResponse)
async def update_platform_settings(
    payload: PlatformSettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PlatformSettingsResponse:
    await require_platform_admin(session)
    try:
        response_payload = await update_platform_settings_payload(
            session,
            settings_payload=payload.settings,
            remove_payload=payload.remove,
        )
    except PlatformSettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    return PlatformSettingsResponse(**response_payload)
