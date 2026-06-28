from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ActorContext,
    get_actor_context,
    get_db_session,
    normalize_org_header,
    resolve_org_membership,
    set_system_actor,
)
from app.core.database_async import AdminAsyncSessionLocal
from app.core.email_verification import is_email_verified
from app.schemas.projects import (
    ConversationListResponse,
    ProjectActionResponse,
    ProjectContextResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDetailResponse,
    ProjectPendingConfirmResolveRequest,
    ProjectPendingConfirmResponse,
    ProjectPendingConfirmUpdateRequest,
    ProjectQuestionInstance,
    ProjectRecord,
    ProjectReportResponse,
    ProjectReportStatusResponse,
    ProjectRuntimeRecord,
    ProjectSummary,
    ProjectUpdateRequest,
    ProjectsListResponse,
)
from app.services.report_jobs import resolve_report_generation_status
from app.services.localization import (
    normalize_output_locale,
)
from app.services.pending_confirms import (
    fetch_project_pending_confirm,
    PendingConfirmConflictError,
    PendingConfirmConfigurationError,
    PendingConfirmForbiddenError,
    PendingConfirmNotFoundError,
    PendingConfirmValidationError,
    resolve_pending_confirm_workflow,
    update_pending_confirm_workflow,
)
from app.services.project_contexts import fetch_project_context
from app.services.project_creation import (
    ProjectCreationConflictError,
    ProjectCreationConfigurationError,
    ProjectCreationForbiddenError,
    ProjectCreationInputValidationError,
    ProjectCreationRecordsError,
    ProjectCreationQuestionSetupError,
    create_project_workflow,
)
from app.services.project_conversations import (
    ConversationCursorValidationError,
    fetch_project_conversation_list,
    maybe_localize_latest_question_prompt,
    normalize_conversation_cursor,
)
from app.services.project_details import (
    ProjectRuntimeMissingError,
    fetch_project_detail,
)
from app.services.project_listings import fetch_project_list
from app.services.project_mutations import (
    ProjectMutationValidationError,
    soft_delete_project,
    update_project_summary,
)
from app.services.project_question_prompts import QuestionPromptMissingError
from app.services.project_report_access import (
    ProjectReportAccessDeniedError,
    ProjectReportAccessConfigurationError,
    ProjectReportEmailVerificationError,
    ProjectReportAccessNotFoundError,
    ensure_project_report_access_gate,
)
from app.services.project_reports import fetch_project_report_payload

router = APIRouter(prefix="/projects", tags=["projects"])


def _fields_set(payload: BaseModel) -> set[str]:
    model_fields_set = getattr(payload, "model_fields_set", None)
    if isinstance(model_fields_set, set):
        return model_fields_set
    return getattr(payload, "__fields_set__", set())


ALLOWED_PROJECT_BANK_KEYS = {"default", "lite"}


async def _require_project_report_access_gate(
    session: AsyncSession,
    *,
    actor_user_id: UUID,
    project_id: UUID,
) -> None:
    try:
        await ensure_project_report_access_gate(
            session,
            admin_session_factory=AdminAsyncSessionLocal,
            set_system_actor_fn=set_system_actor,
            is_email_verified_fn=is_email_verified,
            actor_user_id=actor_user_id,
            project_id=project_id,
        )
    except ProjectReportAccessConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.detail,
        ) from exc
    except ProjectReportEmailVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc
    except ProjectReportAccessNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ProjectReportAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get("", response_model=ProjectsListResponse)
async def list_projects(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    stage: str | None = Query(default=None),
    archived: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
) -> ProjectsListResponse:
    try:
        payload = await fetch_project_list(
            session,
            owner_user_id=actor.user_id,
            limit=limit,
            offset=offset,
            stage=stage,
            archived=archived,
            sort=sort,
            order=order,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ProjectsListResponse(**payload)


@router.post("", response_model=ProjectCreateResponse)
async def create_project(
    payload: ProjectCreateRequest,
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> ProjectCreateResponse:
    explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
    try:
        created_records = await create_project_workflow(
            admin_session_factory=AdminAsyncSessionLocal,
            set_system_actor_fn=set_system_actor,
            resolve_org_membership_fn=resolve_org_membership,
            actor_user_id=actor.user_id,
            explicit_org_id=explicit_org_id,
            title=payload.title,
            description=payload.description,
            bank_key=payload.bank_key,
            allowed_bank_keys=ALLOWED_PROJECT_BANK_KEYS,
        )
    except ProjectCreationInputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except ProjectCreationForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc
    except ProjectCreationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        ) from exc
    except (
        ProjectCreationConfigurationError,
        ProjectCreationQuestionSetupError,
        ProjectCreationRecordsError,
    ) as exc:
        detail = exc.detail if hasattr(exc, "detail") else str(exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from exc

    return ProjectCreateResponse(
        project=ProjectRecord(**created_records.project),
        runtime=ProjectRuntimeRecord(**created_records.runtime),
        question_instance=ProjectQuestionInstance(**created_records.question_instance),
    )


@router.patch("/{project_id}", response_model=ProjectActionResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectActionResponse:
    fields_set = _fields_set(payload)
    try:
        row = await update_project_summary(
            session,
            project_id=project_id,
            fields_set=fields_set,
            title=payload.title,
            description=payload.description,
            is_archived=payload.is_archived,
        )
    except ProjectMutationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return ProjectActionResponse(project=ProjectSummary(**row))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await soft_delete_project(session, project_id=project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectDetailResponse:
    try:
        payload = await fetch_project_detail(session, project_id)
    except ProjectRuntimeMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return ProjectDetailResponse(**payload)


@router.get("/{project_id}/context", response_model=ProjectContextResponse)
async def get_project_context(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectContextResponse:
    payload = await fetch_project_context(session, project_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return ProjectContextResponse(**payload)


@router.get(
    "/{project_id}/context/pending",
    response_model=ProjectPendingConfirmResponse,
)
async def get_project_pending_confirm(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectPendingConfirmResponse:
    payload = await fetch_project_pending_confirm(session, project_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return ProjectPendingConfirmResponse(**payload)


@router.patch(
    "/{project_id}/context/pending",
    response_model=ProjectPendingConfirmResponse,
)
async def update_project_pending_confirm(
    project_id: UUID,
    payload: ProjectPendingConfirmUpdateRequest,
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> ProjectPendingConfirmResponse:
    explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
    try:
        response_payload = await update_pending_confirm_workflow(
            admin_session_factory=AdminAsyncSessionLocal,
            set_system_actor_fn=set_system_actor,
            resolve_org_membership_fn=resolve_org_membership,
            actor_user_id=actor.user_id,
            explicit_org_id=explicit_org_id,
            project_id=project_id,
            updates=payload.updates,
            client_context_version=payload.client_context_version,
        )
    except PendingConfirmValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    except PendingConfirmForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc
    except PendingConfirmNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PendingConfirmConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PendingConfirmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.detail,
        ) from exc

    return ProjectPendingConfirmResponse(**response_payload)


@router.post(
    "/{project_id}/context/pending/resolve",
    response_model=ProjectPendingConfirmResponse,
)
async def resolve_project_pending_confirm(
    project_id: UUID,
    payload: ProjectPendingConfirmResolveRequest,
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> ProjectPendingConfirmResponse:
    explicit_org_id = normalize_org_header(x_org_id) if x_org_id else None
    try:
        response_payload = await resolve_pending_confirm_workflow(
            admin_session_factory=AdminAsyncSessionLocal,
            set_system_actor_fn=set_system_actor,
            resolve_org_membership_fn=resolve_org_membership,
            actor_user_id=actor.user_id,
            explicit_org_id=explicit_org_id,
            project_id=project_id,
            accept_paths=payload.accept_paths,
            reject_paths=payload.reject_paths,
            client_context_version=payload.client_context_version,
        )
    except PendingConfirmForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc
    except PendingConfirmNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PendingConfirmConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PendingConfirmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.detail,
        ) from exc

    return ProjectPendingConfirmResponse(**response_payload)


@router.get("/{project_id}/report", response_model=ProjectReportResponse)
async def get_project_report(
    project_id: UUID,
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_db_session),
    output_locale: str | None = None,
) -> ProjectReportResponse:
    resolved_output_locale = normalize_output_locale(output_locale)
    await _require_project_report_access_gate(
        session,
        actor_user_id=actor.user_id,
        project_id=project_id,
    )

    payload = await fetch_project_report_payload(
        session,
        project_id,
        output_locale=resolved_output_locale,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return ProjectReportResponse(**payload)


@router.get("/{project_id}/report/status", response_model=ProjectReportStatusResponse)
async def get_project_report_status(
    project_id: UUID,
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_db_session),
    output_locale: str | None = None,
) -> ProjectReportStatusResponse:
    resolved_output_locale = normalize_output_locale(output_locale)
    await _require_project_report_access_gate(
        session,
        actor_user_id=actor.user_id,
        project_id=project_id,
    )

    status_payload = await resolve_report_generation_status(
        session,
        project_id=str(project_id),
        output_locale=resolved_output_locale,
    )
    return ProjectReportStatusResponse(**status_payload)


@router.get("/{project_id}/conversations", response_model=ConversationListResponse)
async def list_project_conversations(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    before: str | None = Query(default=None),
    before_id: int | None = Query(default=None),
    output_locale: str | None = Query(default=None),
) -> ConversationListResponse:
    resolved_output_locale = normalize_output_locale(output_locale)
    try:
        cursor = normalize_conversation_cursor(
            before=before,
            before_id=before_id,
        )
    except ConversationCursorValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if cursor.is_first_page:
        try:
            await maybe_localize_latest_question_prompt(
                session,
                project_id=project_id,
                output_locale=resolved_output_locale,
                set_system_actor_fn=set_system_actor,
            )
        except QuestionPromptMissingError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    payload = await fetch_project_conversation_list(
        session,
        project_id=project_id,
        limit=limit,
        cursor=cursor,
    )
    return ConversationListResponse(**payload)
