import re
from typing import Any

from app.services.answer_meta import normalize_answer_action
from app.services.localization import OutputLocale


CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
QUICK_ACTION_ANSWERS = {
    "i'm not sure",
    "i am not sure",
    "i haven't decided yet",
    "i have not decided yet",
    "this does not apply here",
    "please draft this with ai",
}


def extract_answer_action(message_meta: Any) -> str | None:
    if not isinstance(message_meta, dict):
        return None
    for key in ("answer_mode", "answer_action", "action"):
        action = normalize_answer_action(message_meta.get(key))
        if action:
            return action
    return None


def is_quick_action_answer(
    latest_answer: str | None,
    message_meta: Any | None = None,
) -> bool:
    if extract_answer_action(message_meta):
        return True
    if not isinstance(latest_answer, str):
        return False
    cleaned = re.sub(r"\s+", " ", latest_answer.strip().lower())
    return cleaned in QUICK_ACTION_ANSWERS


def resolve_interview_output_locale(
    latest_answer: str | None,
    requested_output_locale: OutputLocale,
    *,
    context_summary: str | None = None,
    message_meta: Any | None = None,
) -> OutputLocale:
    if not isinstance(latest_answer, str) or not latest_answer.strip():
        return requested_output_locale
    if is_quick_action_answer(latest_answer, message_meta):
        if isinstance(context_summary, str) and CJK_PATTERN.search(context_summary):
            return "zh"
        return requested_output_locale
    if CJK_PATTERN.search(latest_answer):
        return "zh"
    if re.search(r"[A-Za-z]", latest_answer):
        return "en"
    return requested_output_locale


def resolve_followup_output_locale(
    latest_answer: str | None,
    requested_output_locale: OutputLocale,
    *,
    context_summary: str | None = None,
    message_meta: Any | None = None,
) -> OutputLocale:
    return resolve_interview_output_locale(
        latest_answer,
        requested_output_locale,
        context_summary=context_summary,
        message_meta=message_meta,
    )
