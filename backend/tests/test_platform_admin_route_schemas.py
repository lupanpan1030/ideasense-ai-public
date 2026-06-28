from app.api.routes import platform_admin
from app.schemas import platform_admin as platform_admin_schemas


def test_platform_admin_route_uses_schema_owned_dtos() -> None:
    assert platform_admin.OrgSummary is platform_admin_schemas.OrgSummary
    assert platform_admin.OrgListResponse is platform_admin_schemas.OrgListResponse
    assert platform_admin.OrgUpdateRequest is platform_admin_schemas.OrgUpdateRequest
    assert platform_admin.PromptTemplateInfo is platform_admin_schemas.PromptTemplateInfo
    assert (
        platform_admin.PromptTemplateListResponse
        is platform_admin_schemas.PromptTemplateListResponse
    )
    assert (
        platform_admin.PromptTemplateCreateRequest
        is platform_admin_schemas.PromptTemplateCreateRequest
    )
    assert platform_admin.PlatformAdminItem is platform_admin_schemas.PlatformAdminItem
    assert (
        platform_admin.PlatformAdminListResponse
        is platform_admin_schemas.PlatformAdminListResponse
    )
    assert (
        platform_admin.PlatformAdminUpsertRequest
        is platform_admin_schemas.PlatformAdminUpsertRequest
    )
    assert (
        platform_admin.PlatformSettingsResponse
        is platform_admin_schemas.PlatformSettingsResponse
    )
    assert (
        platform_admin.PlatformSettingsUpdateRequest
        is platform_admin_schemas.PlatformSettingsUpdateRequest
    )
    assert (
        platform_admin.ReportQualityObservationDetail
        is platform_admin_schemas.ReportQualityObservationDetail
    )
    assert (
        platform_admin.ReportQualityObservationListResponse
        is platform_admin_schemas.ReportQualityObservationListResponse
    )
    assert (
        platform_admin.ReportQualitySummaryResponse
        is platform_admin_schemas.ReportQualitySummaryResponse
    )
