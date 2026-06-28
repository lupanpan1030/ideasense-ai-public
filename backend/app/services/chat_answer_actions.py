from dataclasses import dataclass
from typing import Any

from app.services.answer_meta import (
    is_skip_answer_action,
    resolve_skip_resolution_status,
)
from app.services.chat_output_locale import extract_answer_action


@dataclass(frozen=True)
class ChatAnswerAction:
    answer_action: str | None
    skip_requested: bool
    skip_reason: str | None
    skip_resolution_status: str
    force_ai_assist: bool


def extract_skip_reason(message_meta: Any) -> str | None:
    if not isinstance(message_meta, dict):
        return None
    for key in ("skip_reason", "reason"):
        value = message_meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def resolve_chat_answer_action(message_meta: Any) -> ChatAnswerAction:
    answer_action = extract_answer_action(message_meta)
    skip_reason = extract_skip_reason(message_meta)
    return ChatAnswerAction(
        answer_action=answer_action,
        skip_requested=is_skip_answer_action(answer_action),
        skip_reason=skip_reason,
        skip_resolution_status=resolve_skip_resolution_status(
            answer_action,
            skip_reason,
        ),
        force_ai_assist=answer_action == "ai_draft",
    )


def build_skip_decision(
    skip_reason: str | None = None,
    *,
    resolution_status: str = "unknown",
) -> dict:
    labels = {
        "unknown": "User marked this answer as unknown.",
        "undecided": "User has not decided yet.",
        "not_applicable": "User marked this question as not applicable.",
    }
    risk_notes = [labels.get(resolution_status, "User skipped question.")]
    if skip_reason:
        risk_notes.append(f"Skip reason: {skip_reason}.")
    return {
        "final_verdict": "pass",
        "model_verdict": "skipped",
        "missing_points": [],
        "critical_issues": [],
        "followup_questions": [],
        "help_examples": [],
        "followup_message": None,
        "risk_notes": risk_notes,
        "score": {"clarity": 0.0, "completeness": 0.0, "evidence": 0.0},
        "overall": 0.0,
        "unknown": False,
        "threshold": 0.0,
        "skipped": True,
        "skip_reason": skip_reason,
        "resolution_status": resolution_status,
    }
