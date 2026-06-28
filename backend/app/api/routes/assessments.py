from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ActorContext,
    get_actor_context,
    get_db_session,
    normalize_org_header,
    require_verified_system_actor,
    resolve_verified_org_context,
    set_system_rls_context,
    set_system_actor,
)
from app.core.database_async import AdminAsyncSessionLocal
from app.core.llm_router import has_available_provider
from app.core.usage_limits import UsageLimitError
from app.schemas.assessments import (
    ProjectVerificationResponse,
    StageConfirmRequest,
    StageConfirmResponse,
    StageDraftResponse,
    StageQuestionVerification,
    StageSummariesResponse,
    StageSummaryItem,
    StageVerificationSummary,
    VerificationRefreshResponse,
    VerificationSource,
)
from app.services.assessment_summaries import (
    SUMMARY_STAGES,
    AssessmentProjectNotFoundError,
    AssessmentStageUnsupportedError,
    fetch_project_stage_verification_read_models,
    fetch_stage_summary_read_models,
)
from app.services.localization import (
    DEFAULT_OUTPUT_LOCALE,
    normalize_output_locale,
)
from app.services.stage_confirmations import (
    StageConfirmationConflictError,
    StageConfirmationNotFoundError,
    StageConfirmationPermissionError,
    StageConfirmationRuntimeError,
    STAGE_CONFIRMATION_NEXT_MAP,
    commit_prepared_stage_confirmation_workflow,
    prepare_stage_confirmation_workflow,
)
from app.services.report_confirmations import (
    ReportConfirmationConflictError,
    ReportConfirmationNotFoundError,
    ReportConfirmationPermissionError,
    confirm_project_report_stage_workflow,
)
from app.services.stage_drafts import (
    STAGE_DRAFT_CONTEXT_CONFLICT,
    STAGE_DRAFT_MISSING_QUESTION_BANK,
    STAGE_DRAFT_NOT_READY,
    STAGE_DRAFT_STAGE_CHANGED,
    StageDraftNotFoundError,
    StageDraftPermissionError,
    prepare_project_stage_draft_workflow,
)
from app.services.verification_refresh import (
    VerificationRefreshProjectNotFoundError,
    VerificationRefreshStageUnsupportedError,
    refresh_project_stage_verification_workflow,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])

REPORT_READY_MESSAGE = (
    "Report stage ready. Review the stage summaries to generate the final report."
)


def _stage_confirmation_http_exception(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


@router.get("/project/{project_id}/summaries", response_model=StageSummariesResponse)
async def get_stage_summaries(
    project_id: UUID,
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_db_session),
) -> StageSummariesResponse:
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )
    async with AdminAsyncSessionLocal() as admin_session:
        async with admin_session.begin():
            await require_verified_system_actor(
                admin_session,
                user_id=str(actor.user_id),
                detail="Verify your email to access stage summaries.",
            )
    try:
        summary_models = await fetch_stage_summary_read_models(
            session,
            project_id=str(project_id),
        )
    except AssessmentProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return StageSummariesResponse(
        project_id=project_id,
        summaries=[
            StageSummaryItem(
                stage=item.stage,
                draft_summary_markdown=item.draft_summary_markdown,
                draft_output_locale=item.draft_output_locale,
                final_summary_markdown=item.final_summary_markdown,
                final_output_locale=item.final_output_locale,
                confirmed=item.confirmed,
                updated_at=item.updated_at,
                user_edited_paths=item.user_edited_paths,
                context_card=item.context_card,
                validation_plan=item.validation_plan,
            )
            for item in summary_models
        ],
    )


@router.get("/project/{project_id}/verification", response_model=ProjectVerificationResponse)
async def get_project_stage_verification(
    project_id: UUID,
    stage: str | None = Query(default=None, alias="stage"),
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectVerificationResponse:
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )
    async with AdminAsyncSessionLocal() as admin_session:
        async with admin_session.begin():
            await require_verified_system_actor(
                admin_session,
                user_id=str(actor.user_id),
                detail="Verify your email to access stage summaries.",
            )

    try:
        verification_models = await fetch_project_stage_verification_read_models(
            session,
            project_id=str(project_id),
            stage=stage,
        )
    except AssessmentStageUnsupportedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AssessmentProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ProjectVerificationResponse(
        project_id=project_id,
        stages=[
            StageVerificationSummary(
                stage=item.stage,
                total=item.total,
                supported=item.supported,
                contradicted=item.contradicted,
                uncertain=item.uncertain,
                failed=item.failed,
                stale=item.stale,
                provider_unavailable=item.provider_unavailable,
                not_checked=item.not_checked,
                verified=item.verified,
                verifying=item.verifying,
                no_evidence=item.no_evidence,
                not_applicable=item.not_applicable,
                questions=[
                    StageQuestionVerification(
                        question_id=question.question_id,
                        question_title=question.question_title,
                        priority=question.priority,
                        status=question.status,
                        status_detail=question.status_detail,
                        supported_claims=question.supported_claims,
                        contradicted_claims=question.contradicted_claims,
                        uncertain_claims=question.uncertain_claims,
                        total_claims=question.total_claims,
                        sources=[
                            VerificationSource(
                                title=source.title,
                                url=source.url,
                                domain=source.domain,
                                snippet=source.snippet,
                            )
                            for source in question.sources
                        ],
                    )
                    for question in item.questions
                ],
            )
            for item in verification_models
        ],
    )


@router.post(
    "/project/{project_id}/verification/refresh",
    response_model=VerificationRefreshResponse,
)
async def refresh_project_stage_verification(
    project_id: UUID,
    stage: str | None = Query(default=None, alias="stage"),
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_db_session),
) -> VerificationRefreshResponse:
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )
    async with AdminAsyncSessionLocal() as admin_session:
        async with admin_session.begin():
            await require_verified_system_actor(
                admin_session,
                user_id=str(actor.user_id),
                detail="Verify your email to access stage summaries.",
            )

    try:
        refresh_result = await refresh_project_stage_verification_workflow(
            session,
            project_id=str(project_id),
            stage=stage,
            prepare_write_actor=set_system_actor,
        )
    except VerificationRefreshStageUnsupportedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VerificationRefreshProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return VerificationRefreshResponse(
        project_id=project_id,
        stage=refresh_result.normalized_stage,
        enqueued=refresh_result.enqueued,
        skipped=refresh_result.skipped,
    )


@router.get("/{stage}/draft", response_model=StageDraftResponse)
async def get_stage_draft(
    stage: str,
    project_id: UUID = Query(..., alias="project_id"),
    client_context_version: int | None = Query(default=None, alias="client_context_version"),
    output_locale: str | None = Query(default=None, alias="output_locale"),
    retry: bool = Query(default=False, alias="retry"),
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> StageDraftResponse:
    normalized_stage = stage.strip().lower()
    resolved_output_locale = normalize_output_locale(output_locale)
    if normalized_stage not in SUMMARY_STAGES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not supported for draft summary.",
        )

    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )

    _require_llm_provider("stage_summary")

    explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            access = await resolve_verified_org_context(
                session,
                user_id=str(actor.user_id),
                explicit_org_id=explicit_org_id,
                email_detail="Verify your email to access stage summaries.",
                no_org_detail="No active organization membership.",
            )
            await set_system_rls_context(
                session,
                user_id=str(actor.user_id),
                org_id=access.org_id,
            )

            try:
                draft_result = await prepare_project_stage_draft_workflow(
                    session,
                    project_id=str(project_id),
                    org_id=access.org_id,
                    user_id=str(actor.user_id),
                    stage=normalized_stage,
                    client_context_version=client_context_version,
                    output_locale=resolved_output_locale,
                    retry=retry,
                )
            except StageDraftNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            except StageDraftPermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc
            except UsageLimitError as exc:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(exc),
                ) from exc

            if draft_result.error == STAGE_DRAFT_STAGE_CHANGED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project stage changed. Refresh and try again.",
                )
            if draft_result.error == STAGE_DRAFT_NOT_READY:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Stage is not ready for draft summary.",
                )
            if draft_result.error == STAGE_DRAFT_CONTEXT_CONFLICT:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Context updated while you were away. Refresh and try again.",
                )
            if draft_result.error == STAGE_DRAFT_MISSING_QUESTION_BANK:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Project question bank is missing.",
                )
            return StageDraftResponse(
                assessment_id=draft_result.assessment_id,
                project_id=project_id,
                stage=normalized_stage,
                stage_status=draft_result.stage_status,
                draft_summary_text=draft_result.draft_summary_text,
                draft_output_locale=draft_result.draft_output_locale,
                context_version=draft_result.context_version,
                context_updated_at=draft_result.context_updated_at,
                score_status=None,
                generation_status=draft_result.generation_status,
                retryable=draft_result.retryable,
                last_error=draft_result.last_error,
            )


def _require_llm_provider(task: str) -> None:
    if not has_available_provider(task):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No LLM provider available for {task}.",
        )


async def _confirm_report_stage(
    payload: StageConfirmRequest,
    actor: ActorContext,
    explicit_org_id: str | None,
) -> StageConfirmResponse:
    resolved_output_locale = normalize_output_locale(payload.output_locale)
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            access = await resolve_verified_org_context(
                session,
                user_id=str(actor.user_id),
                explicit_org_id=explicit_org_id,
                email_detail="Verify your email to continue beyond the problem stage.",
                no_org_detail="No active organization membership.",
            )
            await set_system_rls_context(
                session,
                user_id=str(actor.user_id),
                org_id=access.org_id,
            )

            try:
                report_result = await confirm_project_report_stage_workflow(
                    session,
                    project_id=str(payload.project_id),
                    org_id=access.org_id,
                    user_id=str(actor.user_id),
                    client_context_version=payload.client_context_version,
                    output_locale=resolved_output_locale,
                    default_output_locale=DEFAULT_OUTPUT_LOCALE,
                )
            except ReportConfirmationNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            except ReportConfirmationConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            except ReportConfirmationPermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc
            except UsageLimitError as exc:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(exc),
                ) from exc
            return StageConfirmResponse(
                assessment_id=None,
                next_stage=None,
                stage_status=report_result.stage_status,
                validation_plan=report_result.validation_plan,
                report_job_status=report_result.report_job_status,
            )


@router.post("/{stage}/confirm", response_model=StageConfirmResponse)
async def confirm_stage(
    stage: str,
    payload: StageConfirmRequest,
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> StageConfirmResponse:
    normalized_stage = stage.strip().lower()
    resolved_output_locale = normalize_output_locale(payload.output_locale)
    explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
    if normalized_stage == "report":
        return await _confirm_report_stage(payload, actor, explicit_org_id)
    if normalized_stage not in STAGE_CONFIRMATION_NEXT_MAP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not supported for confirmation.",
        )
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for assessments.",
        )

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            access = await resolve_verified_org_context(
                session,
                user_id=str(actor.user_id),
                explicit_org_id=explicit_org_id,
                email_detail="Verify your email to continue beyond the problem stage.",
                no_org_detail="No active organization membership.",
            )
            org_id_value = access.org_id
            await set_system_rls_context(
                session,
                user_id=str(actor.user_id),
                org_id=org_id_value,
            )

            try:
                prepared = await prepare_stage_confirmation_workflow(
                    session,
                    org_id=org_id_value,
                    project_id=str(payload.project_id),
                    user_id=str(actor.user_id),
                    stage=normalized_stage,
                    client_context_version=payload.client_context_version,
                    output_locale=resolved_output_locale,
                    is_verified=access.email_verified,
                )
            except StageConfirmationNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            except StageConfirmationConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            except StageConfirmationRuntimeError as exc:
                raise _stage_confirmation_http_exception(exc) from exc
            except UsageLimitError as exc:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=str(exc),
                ) from exc

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            access = await resolve_verified_org_context(
                session,
                user_id=str(actor.user_id),
                explicit_org_id=explicit_org_id,
                email_detail="Verify your email to continue beyond the problem stage.",
                no_org_detail="No active organization membership.",
            )
            if access.org_id != org_id_value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Organization changed. Refresh and try again.",
                )
            await set_system_rls_context(
                session,
                user_id=str(actor.user_id),
                org_id=access.org_id,
            )

            try:
                commit_result = await commit_prepared_stage_confirmation_workflow(
                    session,
                    prepared=prepared,
                    report_ready_message=REPORT_READY_MESSAGE,
                )
            except StageConfirmationNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            except StageConfirmationPermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc
            except StageConfirmationConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc
            except StageConfirmationRuntimeError as exc:
                raise _stage_confirmation_http_exception(exc) from exc

    return StageConfirmResponse(
        assessment_id=commit_result.assessment_id,
        next_stage=commit_result.next_stage,
        stage_status=commit_result.stage_status,
        score_status=commit_result.score_status,
        scores_json=commit_result.scores_json,
        total_score=commit_result.total_score,
        risk_matrix=commit_result.risk_matrix,
        context_card=commit_result.context_card,
        validation_plan=commit_result.validation_plan,
        report_job_status=commit_result.report_job_status,
    )
