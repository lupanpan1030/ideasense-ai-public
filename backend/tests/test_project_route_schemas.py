from app.api.routes import projects
from app.schemas import projects as project_schemas


def test_project_route_reexports_schema_owned_dtos() -> None:
    assert projects.ProjectCreateRequest is project_schemas.ProjectCreateRequest
    assert projects.ProjectCreateResponse is project_schemas.ProjectCreateResponse
    assert projects.ProjectReportResponse is project_schemas.ProjectReportResponse
    assert (
        projects.ProjectPendingConfirmResponse
        is project_schemas.ProjectPendingConfirmResponse
    )
