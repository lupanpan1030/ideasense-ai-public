"""Judgment helpers for verification."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.prompt_runtime import (
    PromptContextBuilder,
    PromptMutationClass,
    execute_prompt_task,
)

from .text_utils import _evidence_relevant, _normalize_verdict

PROMPT_CONTEXT_BUILDER = PromptContextBuilder()


def _aggregate_confidence(
    verdicts: List[Dict[str, Any]],
) -> str:
    if not verdicts:
        return "Low"
    supported = sum(1 for v in verdicts if v.get("verdict") == "supported")
    total = len(verdicts)
    if supported >= max(2, total * 0.6):
        return "High"
    if supported >= max(1, total * 0.3):
        return "Medium"
    return "Low"


def _tally_verdicts(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {key: 0 for key in ("supported", "contradicted", "uncertain")}
    for item in entries:
        verdict = _normalize_verdict(item.get("verdict"))
        counts[verdict] += 1
    total = sum(counts.values())
    supported = counts.get("supported", 0)
    ratio = (supported / total) if total else 0.0
    counts["total"] = total
    counts["supported_ratio"] = ratio
    return counts


def _select_claim_samples(entries: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    verdict_order = {"supported": 0, "contradicted": 1, "uncertain": 2}

    def _order(item: Dict[str, Any]) -> int:
        return verdict_order.get(_normalize_verdict(item.get("verdict")), 3)

    sorted_entries = sorted(entries, key=_order)
    samples: List[Dict[str, Any]] = []
    for item in sorted_entries:
        if len(samples) >= limit:
            break
        sources = item.get("sources") or []
        compact_sources = []
        if _normalize_verdict(item.get("verdict")) == "supported":
            for src in sources[:2]:
                if not isinstance(src, dict):
                    continue
                compact_sources.append(
                    {
                        "title": str(src.get("title") or ""),
                        "domain": str(src.get("domain") or ""),
                        "snippet": str(src.get("snippet") or ""),
                    }
                )
        samples.append(
            {
                "claim": str(item.get("claim") or ""),
                "verdict": _normalize_verdict(item.get("verdict")),
                "evidence": compact_sources,
            }
        )
    return samples


async def _judge_claim(
    *,
    claim: str,
    evidence: List[Dict[str, Any]],
    session: Any | None = None,
    project_settings: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if session is None:
        return {
            "verdict": "uncertain",
            "confidence": "Low",
            "rationale": "Verification runtime unavailable.",
        }

    context = PROMPT_CONTEXT_BUILDER.claim_verification(
        claim=claim,
        evidence=evidence,
    )
    result = await execute_prompt_task(
        session,
        context,
        project_settings=project_settings,
        expected_mutation=PromptMutationClass.NONE,
    )
    if not result.ok:
        return {
            "verdict": "uncertain",
            "confidence": "Low",
            "rationale": "Verification failed due to model error.",
        }

    data = result.parsed if isinstance(result.parsed, dict) else {}

    verdict = str(data.get("verdict") or "uncertain").strip().lower()
    confidence = str(data.get("confidence") or "Low").strip().capitalize()
    rationale = str(data.get("rationale") or "").strip()
    if verdict not in {"supported", "contradicted", "uncertain"}:
        verdict = "uncertain"
    if confidence not in {"High", "Medium", "Low"}:
        confidence = "Low"
    if verdict == "supported" and not _evidence_relevant(claim, evidence):
        verdict = "uncertain"
        confidence = "Low"
        rationale = "Evidence does not directly support the claim."
    return {
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
    }
