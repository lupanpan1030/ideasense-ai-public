import types
import unittest
from unittest.mock import patch

from app.services import stage_finalize_worker_handler
from app.services.stage_finalize_worker_handler import (
    _collect_verification_claim_rows,
    _generate_project_description_v0,
    _sanitize_project_description,
)


def test_sanitize_project_description_removes_placeholder_values() -> None:
    assert _sanitize_project_description("unknown") is None
    assert _sanitize_project_description("无描述") is None
    assert _sanitize_project_description("  Evidence-backed MVP scoring.  ") == (
        "Evidence-backed MVP scoring."
    )


def test_collect_verification_claim_rows_preserves_supported_and_unsupported_claims() -> None:
    rows = _collect_verification_claim_rows(
        {
            "evidence_mode": "live",
            "verified_facts": [
                {
                    "claim": "Three pilot teams completed the workflow.",
                    "section": "market",
                    "verdict": "supported",
                    "confidence": 0.82,
                    "sources": [{"title": "Pilot notes"}],
                }
            ],
            "unsupported_claims": [
                {
                    "text": "The report is already enterprise-ready.",
                    "verdict": "unsupported",
                    "rationale": "No deployment evidence.",
                }
            ],
        },
        org_id="org-1",
        project_id="project-1",
        assessment_id="assessment-1",
        default_stage="tech",
    )

    assert rows == [
        {
            "org_id": "org-1",
            "project_id": "project-1",
            "assessment_id": "assessment-1",
            "stage": "market",
            "claim": "Three pilot teams completed the workflow.",
            "verdict": "supported",
            "confidence": 0.82,
            "rationale": None,
            "sources": [{"title": "Pilot notes"}],
            "evidence_mode": "live",
        },
        {
            "org_id": "org-1",
            "project_id": "project-1",
            "assessment_id": "assessment-1",
            "stage": "tech",
            "claim": "The report is already enterprise-ready.",
            "verdict": "unsupported",
            "confidence": None,
            "rationale": "No deployment evidence.",
            "sources": None,
            "evidence_mode": "live",
        },
    ]


class StageFinalizePromptRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_project_description_uses_prompt_runtime_boundary(self) -> None:
        async def fake_executor(_session, context, **kwargs):
            self.assertEqual(context.task_key, "project_description")
            self.assertEqual(
                kwargs["expected_mutation"],
                stage_finalize_worker_handler.PromptMutationClass.VALIDATED_CONTEXT_UPDATE,
            )
            return types.SimpleNamespace(
                ok=True,
                content="Evidence-backed MVP scoring.",
                model="test-model",
            )

        with patch.object(
            stage_finalize_worker_handler,
            "execute_prompt_task",
            new=fake_executor,
        ):
            description, model = await _generate_project_description_v0(
                None,
                title="IdeaSense",
                payload={"problem": {"target_user": "student founders"}},
                summary="Students need clearer startup assessment.",
                output_locale="en",
            )

        self.assertEqual(description, "Evidence-backed MVP scoring.")
        self.assertEqual(model, "test-model")
