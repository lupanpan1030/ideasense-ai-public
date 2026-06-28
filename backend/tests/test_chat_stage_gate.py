from app.services.chat_stage_gate import (
    is_stage_gate_ready_for_review,
    resolve_next_stage,
    should_enter_stage_gate_review,
)


def test_stage_gate_ready_for_review_uses_ready_or_current_status() -> None:
    assert is_stage_gate_ready_for_review("awaiting_confirm", "in_progress")
    assert is_stage_gate_ready_for_review(None, "awaiting_confirm")
    assert not is_stage_gate_ready_for_review(None, "in_progress")
    assert not is_stage_gate_ready_for_review(None, None)


def test_should_enter_stage_gate_review_requires_no_missing_paths() -> None:
    assert should_enter_stage_gate_review(
        stage_status_ready=None,
        current_stage_status="in_progress",
        stage="problem",
        variant="default",
        missing_paths=[],
    )
    assert not should_enter_stage_gate_review(
        stage_status_ready=None,
        current_stage_status="in_progress",
        stage="problem",
        variant="default",
        missing_paths=["evidence.key_unknowns[]"],
    )
    assert should_enter_stage_gate_review(
        stage_status_ready="awaiting_confirm",
        current_stage_status="in_progress",
        stage="problem",
        variant="default",
        missing_paths=["evidence.key_unknowns[]"],
    )


def test_resolve_next_stage_maps_known_stage_flow() -> None:
    assert resolve_next_stage("problem") == "market"
    assert resolve_next_stage("market") == "tech"
    assert resolve_next_stage("tech") == "report"
    assert resolve_next_stage("report") is None
    assert resolve_next_stage(None) is None
