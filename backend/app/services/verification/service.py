"""Verification service entry point."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from .claim_selection import (
    _build_search_query,
    _rewrite_claim_for_search,
    _select_claims,
    _select_claims_by_section,
)
from .config import (
    verification_enabled,
    verification_max_claims,
    verification_max_results,
    verification_per_section,
)
from .constants import _SECTION_KEYS
from .domains import _filter_evidence_by_domain, _maybe_apply_domain_fallback, _parse_allowed_domains
from .judge import _aggregate_confidence, _judge_claim, _select_claim_samples, _tally_verdicts
from .search_provider import _compact_evidence, _provider_enabled, _search_evidence
from .text_utils import _dedupe_terms, _extract_keywords, _is_internal_claim, _is_strong_assertion, _evidence_relevant

logger = logging.getLogger("ideasense.services.verification")


async def verify_report_inputs(
    *,
    qa_digest_by_stage: Dict[str, List[Dict[str, Any]]],
    stage_summaries: Dict[str, str],
    last_user_message: Optional[str],
    evidence_mode: Optional[str] = None,
    allowed_sections: Optional[Iterable[str]] = None,
    per_section_limit: int | None = None,
    prompt_session: Any | None = None,
    project_settings: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    mode = "search"
    if not _provider_enabled(mode):
        logger.info(
            "Verification skipped | enabled=%s mode=%s",
            verification_enabled(),
            mode,
        )
        return {
            "enabled": False,
            "verified_facts": [],
            "unsupported_claims": [],
            "confidence_by_section": {},
            "evidence_sources": [],
        }

    max_claims = verification_max_claims()
    max_results = verification_max_results()
    allowed_domains = _parse_allowed_domains()

    allowed_sections_list = (
        [str(s or "").strip().lower() for s in allowed_sections]
        if allowed_sections is not None
        else []
    )
    allowed_sections_list = [s for s in allowed_sections_list if s]
    limit_per_section = per_section_limit or verification_per_section()
    if allowed_sections_list:
        max_claims_total = min(max_claims, max(1, int(limit_per_section)) * len(allowed_sections_list))
        claims = _select_claims_by_section(
            qa_digest_by_stage,
            stage_summaries,
            allowed_sections=allowed_sections_list,
            per_section_limit=limit_per_section,
            max_claims=max_claims_total,
        )
    else:
        claims = _select_claims(qa_digest_by_stage, stage_summaries, max_claims)
    verification_scope = allowed_sections_list or None
    context_terms = _extract_keywords(" ".join(str(v) for v in (stage_summaries or {}).values()))
    if last_user_message:
        context_terms = _dedupe_terms(context_terms + _extract_keywords(last_user_message))
    fallback_used = False
    fallback_mode: Optional[str] = None
    verified_facts: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    verdicts_by_section: Dict[str, List[Dict[str, Any]]] = {k: [] for k in _SECTION_KEYS}
    all_verdicts: List[Dict[str, Any]] = []
    evidence_samples: List[Dict[str, Any]] = []
    evidence_samples_by_section: Dict[str, List[Dict[str, Any]]] = {}
    seen_sources: set[str] = set()

    for item in claims:
        claim_text = str(item.get("text") or "").strip()
        section = str(item.get("section") or "").strip().lower() or "problem"
        if _is_internal_claim(claim_text):
            rewritten = _rewrite_claim_for_search(item)
            if not rewritten:
                entry = {
                    "claim": claim_text,
                    "section": section,
                    "verdict": "uncertain",
                    "confidence": "Low",
                    "rationale": "Internal or user-reported claim; external verification not applicable.",
                    "sources": [],
                }
                verdicts_by_section.setdefault(section, []).append(entry)
                all_verdicts.append(entry)
                unsupported.append(entry)
                continue
            claim_text = rewritten
            item = {**item, "text": claim_text}
        query_text = _build_search_query(item, context_terms)
        results = await _search_evidence(query_text, max_results=max_results)
        compact = _compact_evidence(results, limit=max_results)
        filtered = _filter_evidence_by_domain(compact)
        evidence, used_fallback, fallback_mode_candidate = _maybe_apply_domain_fallback(
            filtered,
            unfiltered=compact,
            allowed_domains=allowed_domains,
        )
        if used_fallback:
            fallback_used = True
            fallback_mode = fallback_mode_candidate
        strong_claim = _is_strong_assertion(claim_text)
        if strong_claim and not evidence:
            judgment = {
                "verdict": "uncertain",
                "confidence": "Low",
                "rationale": "Quantitative or operational claim requires external evidence.",
            }
        else:
            judgment = await _judge_claim(
                claim=claim_text,
                evidence=evidence,
                session=prompt_session,
                project_settings=project_settings,
            )
        verdict = judgment.get("verdict")
        entry = {
            "claim": claim_text,
            "section": section,
            "verdict": verdict,
            "confidence": judgment.get("confidence"),
            "rationale": judgment.get("rationale"),
            "sources": evidence,
        }
        verdicts_by_section.setdefault(section, []).append(entry)
        all_verdicts.append(entry)
        if verdict == "supported":
            verified_facts.append(entry)
        else:
            unsupported.append(entry)
        for src in evidence:
            if verdict != "supported":
                continue
            if not _evidence_relevant(claim_text, [src]):
                continue
            key = src.get("url") or src.get("domain") or src.get("title")
            if not key or key in seen_sources:
                continue
            seen_sources.add(key)
            evidence_samples.append(src)
            evidence_samples_by_section.setdefault(section, []).append(src)

    confidence_by_section = {
        section: _aggregate_confidence(items)
        for section, items in verdicts_by_section.items()
        if items
    }
    if verification_scope:
        for section in _SECTION_KEYS:
            if section not in verification_scope:
                confidence_by_section.setdefault(section, "Low")

    verdict_counts_by_section = {
        section: _tally_verdicts(items)
        for section, items in verdicts_by_section.items()
        if items
    }
    verdict_counts_overall = _tally_verdicts(all_verdicts)
    claim_samples = _select_claim_samples(all_verdicts, limit=3)

    evidence_sources: List[str] = []
    evidence_sources.append("Desk research (public sources)")
    if last_user_message:
        evidence_sources.append("user-provided information")

    return {
        "enabled": True,
        "evidence_mode": mode,
        "verification_scope": verification_scope,
        "fallback_used": fallback_used,
        "fallback_mode": fallback_mode,
        "verified_facts": verified_facts,
        "unsupported_claims": unsupported,
        "confidence_by_section": confidence_by_section,
        "verdict_counts_by_section": verdict_counts_by_section,
        "verdict_counts_overall": verdict_counts_overall,
        "claim_samples": claim_samples,
        "evidence_sources": evidence_sources,
        "evidence_samples": evidence_samples[:12],
        "evidence_samples_by_section": {
            section: items[:6]
            for section, items in evidence_samples_by_section.items()
        },
    }
