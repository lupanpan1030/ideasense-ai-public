from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NeedsInfoTurnResult:
    assistant_content: str
    question_meta_payload: dict[str, Any] | None
    question_stream_context: dict[str, Any]


@dataclass(frozen=True)
class ChatStateUpdateResult:
    state_json: dict[str, Any] | None
    state_meta: dict[str, Any] | None


@dataclass(frozen=True)
class RuntimeMetadataUpdateResult:
    updated_missing_paths: list[str]
    stage_status_ready: str | None


@dataclass(frozen=True)
class TransitionTurnResult:
    assistant_content: str
    stage_gate_ready_payload: dict[str, Any] | None


@dataclass(frozen=True)
class NextQuestionTurnResult:
    assistant_content: str
    question_meta_payload: dict[str, Any] | None
    question_stream_context: dict[str, Any]


@dataclass(frozen=True)
class StandardNextTurnResult:
    assistant_content: str
    question_meta_payload: dict[str, Any] | None
    question_stream_context: dict[str, Any] | None
    stage_gate_ready_payload: dict[str, Any] | None


def build_answer_scores_payload(
    decision: dict[str, Any],
    *,
    skip_requested: bool,
    prompt_task_traces: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scores_payload = {
        "verdict": decision["final_verdict"],
        "model_verdict": decision["model_verdict"],
        "missing_points": decision["missing_points"],
        "critical_issues": decision["critical_issues"],
        "followup_questions": decision["followup_questions"],
        "help_examples": decision["help_examples"],
        "risk_notes": decision["risk_notes"],
        "score": decision["score"],
        "overall": decision["overall"],
    }
    if skip_requested:
        scores_payload["verdict"] = "skipped"
        scores_payload["model_verdict"] = "skipped"
    if prompt_task_traces:
        scores_payload["prompt_task_traces"] = prompt_task_traces
    if decision.get("partial_advance"):
        scores_payload["partial_advance"] = True
        scores_payload["partial_resolved_paths"] = decision.get(
            "partial_resolved_paths",
        )
        scores_payload["partial_unknown_paths"] = decision.get(
            "partial_unknown_paths",
        )
    return scores_payload
