from app.services import stage_confirmation_types
from app.services import stage_confirmations


def test_stage_confirmation_workflow_reexports_type_owner() -> None:
    assert (
        stage_confirmations.ConfirmedStagePersistenceResult
        is stage_confirmation_types.ConfirmedStagePersistenceResult
    )
    assert (
        stage_confirmations.PreparedStageConfirmation
        is stage_confirmation_types.PreparedStageConfirmation
    )
    assert (
        stage_confirmations.StageConfirmationCommitResult
        is stage_confirmation_types.StageConfirmationCommitResult
    )
    assert (
        stage_confirmations.StageConfirmationConflictError
        is stage_confirmation_types.StageConfirmationConflictError
    )
    assert (
        stage_confirmations.StageConfirmationNotFoundError
        is stage_confirmation_types.StageConfirmationNotFoundError
    )
    assert (
        stage_confirmations.StageConfirmationPermissionError
        is stage_confirmation_types.StageConfirmationPermissionError
    )
    assert (
        stage_confirmations.StageConfirmationRuntimeError
        is stage_confirmation_types.StageConfirmationRuntimeError
    )
    assert (
        stage_confirmations.STAGE_CONFIRMATION_NEXT_MAP
        is stage_confirmation_types.STAGE_CONFIRMATION_NEXT_MAP
    )
