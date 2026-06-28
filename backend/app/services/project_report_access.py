from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectReportAccessNotFoundError(RuntimeError):
    """Raised when the project is not visible in the current org context."""


class ProjectReportAccessDeniedError(RuntimeError):
    """Raised when the current org cannot view project facts for reports."""


class ProjectReportAccessConfigurationError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProjectReportEmailVerificationError(PermissionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


SetSystemActorFn = Callable[[AsyncSession], Awaitable[None]]
IsEmailVerifiedFn = Callable[..., Awaitable[bool]]


async def ensure_project_report_access(
    session: AsyncSession,
    project_id: UUID,
) -> None:
    access_result = await session.execute(
        text(
            "SELECT "
            "p.id, "
            "can_view_project_facts(:project_id, app_org_id()) AS can_view_facts "
            "FROM projects p "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    access_row = access_result.mappings().first()
    if not access_row:
        raise ProjectReportAccessNotFoundError("Project not found.")
    if not access_row.get("can_view_facts"):
        raise ProjectReportAccessDeniedError("Report access denied.")


async def ensure_project_report_access_gate(
    session: AsyncSession,
    *,
    admin_session_factory: Any | None,
    set_system_actor_fn: SetSystemActorFn,
    is_email_verified_fn: IsEmailVerifiedFn,
    actor_user_id: Any,
    project_id: UUID,
) -> None:
    if admin_session_factory is None:
        raise ProjectReportAccessConfigurationError(
            "DATABASE_URL_ADMIN is required for reports."
        )

    async with admin_session_factory() as admin_session:
        async with admin_session.begin():
            await set_system_actor_fn(admin_session)
            if not await is_email_verified_fn(
                admin_session,
                user_id=str(actor_user_id),
            ):
                raise ProjectReportEmailVerificationError(
                    "Verify your email to access reports."
                )

    await ensure_project_report_access(session, project_id)
