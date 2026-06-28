from app.api.routes import assessments
from app.schemas import assessments as assessment_schemas


def test_assessment_route_reexports_schema_owned_dtos() -> None:
    assert assessments.StageConfirmRequest is assessment_schemas.StageConfirmRequest
    assert assessments.StageConfirmResponse is assessment_schemas.StageConfirmResponse
    assert assessments.StageDraftResponse is assessment_schemas.StageDraftResponse
    assert assessments.StageSummaryItem is assessment_schemas.StageSummaryItem
    assert assessments.StageSummariesResponse is assessment_schemas.StageSummariesResponse
    assert assessments.VerificationSource is assessment_schemas.VerificationSource
    assert (
        assessments.StageQuestionVerification
        is assessment_schemas.StageQuestionVerification
    )
    assert assessments.StageVerificationSummary is assessment_schemas.StageVerificationSummary
    assert (
        assessments.ProjectVerificationResponse
        is assessment_schemas.ProjectVerificationResponse
    )
    assert (
        assessments.VerificationRefreshResponse
        is assessment_schemas.VerificationRefreshResponse
    )
