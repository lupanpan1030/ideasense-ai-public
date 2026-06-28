from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.diagnostics import (
    build_context_card,
    build_validation_plan,
    summarize_verification_payload,
)


@dataclass(frozen=True)
class ConfirmedStageArtifactPayload:
    context_card: dict[str, Any]
    validation_plan: list[dict[str, Any]]
    scores_json_payload: dict[str, Any] | None


def build_confirmed_stage_artifact_payload(
    *,
    stage: str,
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    missing_paths: list[str],
    prompt_task_traces: dict[str, Any] | None,
) -> ConfirmedStageArtifactPayload:
    context_card = build_context_card(
        stage=stage,
        state_json=state_json,
        state_meta=state_meta,
        missing_paths=missing_paths,
        verification_summary=summarize_verification_payload(None),
    )
    validation_plan = build_validation_plan(
        stage=stage,
        context_card=context_card,
        key_risks=[],
    )
    scores_json_payload = (
        {"prompt_task_traces": dict(prompt_task_traces)}
        if prompt_task_traces
        else None
    )
    return ConfirmedStageArtifactPayload(
        context_card=context_card,
        validation_plan=validation_plan,
        scores_json_payload=scores_json_payload,
    )
