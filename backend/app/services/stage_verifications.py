from __future__ import annotations

from typing import Any, Protocol


class StageVerificationSummaryLike(Protocol):
    total: int
    supported: int
    contradicted: int
    uncertain: int
    verified: int
    no_evidence: int
    verifying: int
    not_applicable: int
    not_checked: int
    failed: int
    stale: int
    provider_unavailable: int


def is_not_applicable_rationale(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return "not applicable" in lowered or "internal" in lowered or "user-reported" in lowered


def claim_verdict_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"supported": 0, "contradicted": 0, "uncertain": 0}
    for claim in claims:
        verdict = str(claim.get("verdict") or "uncertain").strip().lower()
        if verdict not in counts:
            verdict = "uncertain"
        counts[verdict] += 1
    return counts


def resolve_question_verification_status(
    *,
    pending: bool,
    stale: bool,
    latest_batch: list[dict[str, Any]],
    failed: bool,
    provider_unavailable_reason: str | None,
) -> str:
    if pending:
        return "verifying"
    if stale:
        return "stale"
    if latest_batch:
        if all(is_not_applicable_rationale(entry.get("rationale")) for entry in latest_batch):
            return "not_applicable"
        counts = claim_verdict_counts(latest_batch)
        if counts["contradicted"] > 0:
            return "contradicted"
        if counts["supported"] > 0:
            return "supported"
        return "uncertain"
    if failed:
        return "failed"
    if provider_unavailable_reason:
        return "provider_unavailable"
    return "not_checked"


def increment_verification_summary(
    summary: StageVerificationSummaryLike,
    status_value: str,
) -> None:
    summary.total += 1
    if status_value == "supported":
        summary.supported += 1
        summary.verified += 1
    elif status_value == "contradicted":
        summary.contradicted += 1
        summary.no_evidence += 1
    elif status_value == "uncertain":
        summary.uncertain += 1
        summary.no_evidence += 1
    elif status_value == "verifying":
        summary.verifying += 1
    elif status_value == "not_applicable":
        summary.not_applicable += 1
    elif status_value == "failed":
        summary.failed += 1
        summary.no_evidence += 1
    elif status_value == "stale":
        summary.stale += 1
        summary.no_evidence += 1
    elif status_value == "provider_unavailable":
        summary.provider_unavailable += 1
        summary.no_evidence += 1
    else:
        summary.not_checked += 1
        summary.no_evidence += 1


def collect_sources_from_claims(
    claims: list[dict[str, Any]], limit: int = 3
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for claim in claims:
        raw_sources = claim.get("sources") or []
        if not isinstance(raw_sources, list):
            continue
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            url = source.get("url") if isinstance(source.get("url"), str) else None
            domain = (
                source.get("domain") if isinstance(source.get("domain"), str) else None
            )
            title = source.get("title") if isinstance(source.get("title"), str) else None
            key = url or domain or title
            if not key or key in seen:
                continue
            seen.add(key)
            sources.append(source)
            if len(sources) >= limit:
                return sources
    return sources
