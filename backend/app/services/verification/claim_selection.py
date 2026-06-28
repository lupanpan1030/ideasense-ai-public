"""Claim selection helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .constants import _ANCHOR_TERMS, _EXTERNAL_HINT_TOKENS, _KNOWN_COMPETITORS, _MARKET_SEARCHABLE_QIDS
from .text_utils import _claim_score, _dedupe_claims, _dedupe_terms, _extract_keywords, _normalize_text


_AI_ASSISTED_MARKER_PATTERN = re.compile(r"ai-assisted|ai assist|ai辅助|ai补全", re.IGNORECASE)


def _is_searchable_claim(item: Dict[str, Any]) -> bool:
    qid = str(item.get("question_id") or "").strip().upper()
    if qid in _MARKET_SEARCHABLE_QIDS:
        return True
    text = _normalize_text(str(item.get("text") or ""))
    if any(token in text for token in _EXTERNAL_HINT_TOKENS):
        return True
    return False


def _rewrite_claim_for_search(item: Dict[str, Any]) -> Optional[str]:
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    qid = str(item.get("question_id") or "").strip().upper()
    normalized = _normalize_text(text)

    if qid in {"S2Q3"} or "subscription" in normalized or "pricing" in normalized:
        return "Subscription-based pricing with free trials is common among SaaS products."

    if qid in {"S2Q5", "S2Q11"} or "competitor" in normalized or "alternative" in normalized:
        found = [name for name in _KNOWN_COMPETITORS if name.lower() in normalized]
        if found:
            names = ", ".join(found[:4])
            return f"{names} are commonly used tools for product planning and documentation."
        return "Product planning and documentation tools (e.g., Notion, Airtable) are common alternatives."

    if qid in {"S2Q9"} or "tam" in normalized or "sam" in normalized:
        return "Innovation management and idea evaluation software categories exist."

    if qid in {"S2Q4"} or "trend" in normalized:
        return "Digital product and SaaS markets continue to grow, supporting new tooling demand."

    if qid in {"S2Q6"} or "sales cycle" in normalized:
        return "B2B SaaS purchases often involve multiple stakeholders and a multi-step sales cycle."

    return None


def _build_search_query(item: Dict[str, Any], context_terms: List[str]) -> str:
    text = str(item.get("text") or "").strip()
    section = str(item.get("section") or "").strip().lower()
    qid = str(item.get("question_id") or "").strip().upper()
    normalized = _normalize_text(text)

    base_terms = _extract_keywords(text)
    extras: List[str] = []

    if qid in {"S2Q4", "S2Q9"} or "market size" in normalized or "tam" in normalized or "sam" in normalized:
        extras += ["market size", "TAM", "SAM", "SOM"]
    if qid in {"S2Q4"} or "trend" in normalized or "growing" in normalized or "declin" in normalized:
        extras += ["market growth", "trend"]
    if qid in {"S2Q6"} or "sales cycle" in normalized or "buying committee" in normalized:
        extras += ["sales cycle", "b2b", "saas"]
    if qid in {"S2Q5", "S2Q11"} or "competitor" in normalized or "alternative" in normalized:
        extras += ["competitors", "alternatives"]
    if "pricing" in normalized or "price" in normalized or "subscription" in normalized:
        extras += ["pricing", "subscription model"]
    if section == "market" and not extras:
        extras += ["market", "pricing", "competition"]

    anchor_context = [t for t in context_terms if t.lower() in _ANCHOR_TERMS][:3]
    other_context = [t for t in context_terms if t.lower() not in _ANCHOR_TERMS][:3]
    terms = _dedupe_terms(base_terms + anchor_context + other_context + extras)

    if not any(t.lower() in _ANCHOR_TERMS for t in terms):
        terms = _dedupe_terms(terms + ["startup", "idea", "validation"])

    return " ".join(terms[:12]).strip() or text


def _extract_claims_from_digest(
    qa_digest_by_stage: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for stage, items in qa_digest_by_stage.items():
        for entry in items or []:
            question_id = str(entry.get("question_id") or "").strip()
            key_points = entry.get("key_points") or []
            if isinstance(key_points, list):
                for point in key_points:
                    text = str(point or "").strip()
                    if text:
                        claims.append(
                            {
                                "text": text,
                                "section": stage,
                                "question_id": question_id,
                                "source": "key_point",
                            }
                        )
            summary = str(entry.get("answer_summary") or "").strip()
            if summary:
                claims.append(
                    {
                        "text": summary,
                        "section": stage,
                        "question_id": question_id,
                        "source": "summary",
                    }
                )
    return claims


def _extract_claims_from_summaries(
    stage_summaries: Dict[str, str],
) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for stage, summary in (stage_summaries or {}).items():
        if not summary:
            continue
        for line in str(summary).splitlines():
            text = line.strip("-• ").strip()
            if not text:
                continue
            if text.lstrip().startswith("#"):
                continue
            lower = text.lower()
            if _AI_ASSISTED_MARKER_PATTERN.search(text):
                continue
            if lower.startswith("evidence"):
                continue
            if lower.startswith("confidence"):
                continue
            if "user confirmed" in lower:
                continue
            if lower.startswith("open questions"):
                continue
            if len(text) < 12:
                continue
            claims.append({"text": text, "section": stage})
    return claims


def _select_claims(
    qa_digest_by_stage: Dict[str, List[Dict[str, Any]]],
    stage_summaries: Dict[str, str],
    max_claims: int,
) -> List[Dict[str, Any]]:
    claims = _extract_claims_from_digest(qa_digest_by_stage)
    claims.extend(_extract_claims_from_summaries(stage_summaries))
    claims = _dedupe_claims(claims)
    claims = sorted(
        claims,
        key=lambda c: _claim_score(str(c.get("text") or "")),
        reverse=True,
    )
    return claims[:max_claims]


def _select_claims_by_section(
    qa_digest_by_stage: Dict[str, List[Dict[str, Any]]],
    stage_summaries: Dict[str, str],
    *,
    allowed_sections: Iterable[str],
    per_section_limit: int,
    max_claims: int,
) -> List[Dict[str, Any]]:
    allowed = [str(s or "").strip().lower() for s in allowed_sections]
    allowed = [s for s in allowed if s]
    if not allowed:
        return _select_claims(qa_digest_by_stage, stage_summaries, max_claims)

    claims = _extract_claims_from_digest(qa_digest_by_stage)
    claims.extend(_extract_claims_from_summaries(stage_summaries))
    claims = [c for c in claims if str(c.get("section") or "").strip().lower() in allowed]
    market_claims = [c for c in claims if str(c.get("section") or "").strip().lower() == "market"]
    searchable_market = [c for c in market_claims if _is_searchable_claim(c)]
    if searchable_market:
        claims = [c for c in claims if str(c.get("section") or "").strip().lower() != "market"]
        claims.extend(searchable_market)
    claims = _dedupe_claims(claims)

    grouped: Dict[str, List[Dict[str, Any]]] = {key: [] for key in allowed}
    for item in claims:
        section = str(item.get("section") or "").strip().lower()
        if section in grouped:
            grouped[section].append(item)

    selected: List[Dict[str, Any]] = []
    limit = max(1, int(per_section_limit))
    for section in allowed:
        ranked = sorted(
            grouped.get(section, []),
            key=lambda c: _claim_score(str(c.get("text") or "")),
            reverse=True,
        )
        selected.extend(ranked[:limit])
        if len(selected) >= max_claims:
            break

    return selected[:max_claims]
