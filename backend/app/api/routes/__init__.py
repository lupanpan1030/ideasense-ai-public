from fastapi import APIRouter

from app.core.env import admin_api_enabled, sample_public_enabled
from .assessments import router as assessments_router
from .auth import router as auth_router
from .chat import router as chat_router
from .health import router as health_router
from .invitations import router as invitations_router
from .project_permissions import router as project_permissions_router
from .projects import router as projects_router
from .session import router as session_router
from .user_settings import router as user_settings_router


api_router = APIRouter()
if admin_api_enabled():
    from .admin_cohorts import router as admin_cohorts_router
    from .admin_health import router as admin_health_router
    from .admin_mentor_assignments import router as admin_mentor_assignments_router
    from .admin_org_invites import router as admin_org_invites_router
    from .admin_org_members import router as admin_org_members_router
    from .admin_org_settings import router as admin_org_settings_router
    from .admin_overview import router as admin_overview_router
    from .admin_prompt_templates import router as admin_prompt_templates_router
    from .admin_projects import router as admin_projects_router
    from .admin_question_banks import router as admin_question_banks_router
    from .admin_reports import router as admin_reports_router
    from .platform_admin import router as platform_admin_router

    api_router.include_router(admin_cohorts_router)
    api_router.include_router(admin_health_router)
    api_router.include_router(admin_mentor_assignments_router)
    api_router.include_router(admin_org_invites_router)
    api_router.include_router(admin_org_members_router)
    api_router.include_router(admin_org_settings_router)
    api_router.include_router(admin_overview_router)
    api_router.include_router(admin_prompt_templates_router)
    api_router.include_router(admin_projects_router)
    api_router.include_router(admin_question_banks_router)
    api_router.include_router(admin_reports_router)
    api_router.include_router(platform_admin_router)
api_router.include_router(assessments_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(health_router)
api_router.include_router(invitations_router)
api_router.include_router(project_permissions_router)
api_router.include_router(projects_router)
if sample_public_enabled():
    from .sample import router as sample_router

    api_router.include_router(sample_router)
api_router.include_router(session_router)
api_router.include_router(user_settings_router)
