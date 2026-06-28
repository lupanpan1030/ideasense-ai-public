import pytest

from app.services.chat_router_mode import (
    apply_router_mode_selection_guard,
    augment_router_mode_message_meta,
    extract_mode_from_state,
    extract_router_mode_from_message_meta,
    extract_router_mode_from_text,
    normalize_router_mode,
    require_router_mode,
    resolve_explicit_router_mode,
)


def test_normalize_router_mode_accepts_only_supported_modes() -> None:
    assert normalize_router_mode(" Pro ") == "pro"
    assert normalize_router_mode("LITE") == "lite"
    assert normalize_router_mode("mid") is None
    assert normalize_router_mode(None) is None


def test_extract_router_mode_from_message_meta_accepts_option_aliases() -> None:
    assert extract_router_mode_from_message_meta({"selected_option": "developer"}) == (
        "pro"
    )
    assert extract_router_mode_from_message_meta({"selected_option_key": "plain"}) == (
        "lite"
    )
    assert extract_router_mode_from_message_meta({"mode": "lite"}) == "lite"
    assert extract_router_mode_from_message_meta({"selected_option_key": "other"}) is None


def test_extract_router_mode_from_text_accepts_pro_and_lite_phrases() -> None:
    assert extract_router_mode_from_text("I am a software engineer") == "pro"
    assert extract_router_mode_from_text("prefer plain language please") == "lite"
    assert extract_router_mode_from_text("not very technical") == "lite"
    assert extract_router_mode_from_text("let me think about it") is None


def test_resolve_explicit_router_mode_prefers_meta_then_text_then_state() -> None:
    state_json = {"tech_execution": {"meta": {"mode": "lite"}}}

    assert (
        resolve_explicit_router_mode(
            state_json,
            {"selected_option_key": "pro"},
            "prefer plain language",
        )
        == "pro"
    )
    assert (
        resolve_explicit_router_mode(
            state_json,
            None,
            "I work as a developer",
        )
        == "pro"
    )
    assert resolve_explicit_router_mode(state_json) == "lite"


def test_extract_mode_from_state_ignores_invalid_state_shapes() -> None:
    assert extract_mode_from_state({"tech_execution": {"meta": {"mode": "pro"}}}) == (
        "pro"
    )
    assert extract_mode_from_state({"tech_execution": {"meta": {"mode": "mid"}}}) is None
    assert extract_mode_from_state(None) is None


def test_augment_router_mode_message_meta_adds_free_text_selection_only_for_router() -> None:
    assert augment_router_mode_message_meta(
        {"existing": True},
        "I am a technical founder",
        runtime_stage="tech",
        runtime_variant="router",
    ) == {
        "existing": True,
        "selected_option_key": "pro",
        "router_mode_source": "free_text",
    }
    assert augment_router_mode_message_meta(
        {"selected_option_key": "lite"},
        "I am a technical founder",
        runtime_stage="tech",
        runtime_variant="router",
    ) == {"selected_option_key": "lite"}
    assert augment_router_mode_message_meta(
        {},
        "I am a technical founder",
        runtime_stage="problem",
        runtime_variant="router",
    ) == {}


def test_require_router_mode_rejects_missing_or_invalid_mode() -> None:
    assert require_router_mode("pro") == "pro"
    with pytest.raises(RuntimeError, match="Router mode must be selected explicitly"):
        require_router_mode(None)
    with pytest.raises(RuntimeError, match="Router mode must be selected explicitly"):
        require_router_mode("mid")


def test_apply_router_mode_selection_guard_passes_through_explicit_mode() -> None:
    decision = {"final_verdict": "pass", "model_verdict": "pass"}

    next_decision, chosen_mode, followup_message = apply_router_mode_selection_guard(
        {},
        decision,
        state_json={},
        message_meta={"selected_option_key": "lite"},
    )

    assert next_decision is decision
    assert chosen_mode == "lite"
    assert followup_message is None


def test_apply_router_mode_selection_guard_requires_explicit_mode() -> None:
    decision = {"final_verdict": "pass", "model_verdict": "pass", "score": {}}

    next_decision, chosen_mode, followup_message = apply_router_mode_selection_guard(
        {},
        decision,
        state_json={},
        latest_answer="not sure yet",
        output_locale="en",
    )

    assert chosen_mode is None
    assert followup_message
    assert next_decision["final_verdict"] == "needs_info"
    assert next_decision["model_verdict"] == "needs_info"
    assert next_decision["score"] == {}
    assert next_decision["missing_points"] == [
        "Select either the pro or lite technical path."
    ]
    assert next_decision["risk_notes"] == [
        "Router mode requires an explicit user selection."
    ]


def test_apply_router_mode_selection_guard_keeps_non_pass_decision() -> None:
    decision = {"final_verdict": "needs_info", "model_verdict": "needs_info"}

    next_decision, chosen_mode, followup_message = apply_router_mode_selection_guard(
        {},
        decision,
        state_json={"tech_execution": {"meta": {"mode": "pro"}}},
    )

    assert next_decision is decision
    assert chosen_mode is None
    assert followup_message is None
