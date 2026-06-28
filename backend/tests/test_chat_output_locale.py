from app.services.chat_output_locale import (
    extract_answer_action,
    is_quick_action_answer,
    resolve_followup_output_locale,
    resolve_interview_output_locale,
)


def test_interview_locale_prefers_latest_chinese_answer() -> None:
    assert (
        resolve_interview_output_locale(
            "日程管理，AI 拆解任务，AI 分配任务这些",
            "en",
        )
        == "zh"
    )


def test_interview_locale_prefers_latest_english_answer() -> None:
    assert (
        resolve_interview_output_locale(
            "Schedule management and AI task breakdown.",
            "zh",
        )
        == "en"
    )


def test_empty_answer_keeps_requested_locale() -> None:
    assert resolve_interview_output_locale("  ", "zh") == "zh"


def test_quick_action_metadata_prefers_context_language() -> None:
    assert (
        resolve_interview_output_locale(
            "I'm not sure",
            "en",
            context_summary="项目围绕日程管理和 AI 拆解任务。",
            message_meta={"answer_mode": "unknown"},
        )
        == "zh"
    )


def test_quick_action_text_without_context_keeps_requested_locale() -> None:
    assert resolve_interview_output_locale("I'm not sure", "en") == "en"


def test_followup_locale_uses_same_resolution() -> None:
    assert (
        resolve_followup_output_locale(
            "We support instructors and students.",
            "zh",
        )
        == "en"
    )


def test_extract_answer_action_accepts_supported_meta_keys() -> None:
    assert extract_answer_action({"answer_action": "not_applicable"}) == "not_applicable"
    assert extract_answer_action({"action": "ai_draft"}) == "ai_draft"


def test_quick_action_answer_accepts_meta_or_known_text() -> None:
    assert is_quick_action_answer("anything", {"answer_mode": "undecided"})
    assert is_quick_action_answer("Please draft this with AI")
