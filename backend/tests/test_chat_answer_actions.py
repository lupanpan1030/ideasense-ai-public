from app.services.chat_answer_actions import (
    build_skip_decision,
    extract_skip_reason,
    resolve_chat_answer_action,
)


def test_extract_skip_reason_accepts_supported_meta_keys() -> None:
    assert extract_skip_reason({"skip_reason": "  pricing not decided  "}) == (
        "pricing not decided"
    )
    assert extract_skip_reason({"reason": "not_applicable"}) == "not_applicable"


def test_extract_skip_reason_ignores_empty_or_invalid_values() -> None:
    assert extract_skip_reason({"skip_reason": "   "}) is None
    assert extract_skip_reason({"reason": 123}) is None
    assert extract_skip_reason(None) is None


def test_resolve_chat_answer_action_detects_soft_skip_reason_status() -> None:
    action = resolve_chat_answer_action(
        {
            "answer_action": "skip_soft",
            "skip_reason": "undecided",
        }
    )

    assert action.answer_action == "skip_soft"
    assert action.skip_requested
    assert action.skip_reason == "undecided"
    assert action.skip_resolution_status == "undecided"
    assert not action.force_ai_assist


def test_resolve_chat_answer_action_detects_direct_unknown_action() -> None:
    action = resolve_chat_answer_action({"answer_mode": "unknown"})

    assert action.answer_action == "unknown"
    assert action.skip_requested
    assert action.skip_reason is None
    assert action.skip_resolution_status == "unknown"
    assert not action.force_ai_assist


def test_resolve_chat_answer_action_detects_ai_draft_without_skip() -> None:
    action = resolve_chat_answer_action({"action": "ai_draft"})

    assert action.answer_action == "ai_draft"
    assert not action.skip_requested
    assert action.skip_reason is None
    assert action.skip_resolution_status == "unknown"
    assert action.force_ai_assist


def test_build_skip_decision_preserves_payload_contract() -> None:
    decision = build_skip_decision(
        "pricing not decided",
        resolution_status="undecided",
    )

    assert decision["final_verdict"] == "pass"
    assert decision["model_verdict"] == "skipped"
    assert decision["skipped"]
    assert decision["skip_reason"] == "pricing not decided"
    assert decision["resolution_status"] == "undecided"
    assert decision["score"] == {"clarity": 0.0, "completeness": 0.0, "evidence": 0.0}
    assert decision["risk_notes"] == [
        "User has not decided yet.",
        "Skip reason: pricing not decided.",
    ]
