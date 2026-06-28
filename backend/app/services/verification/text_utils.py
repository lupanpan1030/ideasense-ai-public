"""Text processing helpers for verification."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List

from .constants import (
    _ANCHOR_TERMS,
    _EXTERNAL_HINT_TOKENS,
    _INTERNAL_CLAIM_TOKENS,
    _INTERNAL_STRONG_TOKENS,
    _STOPWORDS,
    _STRONG_CLAIM_KEYWORDS,
    _VERDICT_KEYS,
)


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    keywords = [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]
    return keywords[:20]


def _is_strong_assertion(claim: str) -> bool:
    text = _normalize_text(claim)
    if re.search(r"\d", text):
        return True
    if "%" in text or "$" in text:
        return True
    for key in _STRONG_CLAIM_KEYWORDS:
        if key in text:
            return True
    return False


def _is_internal_claim(text: str) -> bool:
    normalized = _normalize_text(text)
    if any(token in normalized for token in _INTERNAL_STRONG_TOKENS):
        return True
    if _is_strong_assertion(normalized):
        return False
    if any(token in normalized for token in _INTERNAL_CLAIM_TOKENS):
        if any(token in normalized for token in _EXTERNAL_HINT_TOKENS):
            return False
        return True
    return False


def _evidence_relevant(claim: str, evidence: List[Dict[str, str]]) -> bool:
    keywords = _extract_keywords(claim)
    if not keywords:
        return False
    anchors = [k for k in keywords if k in _ANCHOR_TERMS]
    for item in evidence:
        if not isinstance(item, dict):
            continue
        text = f"{item.get('title') or ''} {item.get('snippet') or ''}".lower()
        if not text.strip():
            continue
        matches = sum(1 for k in keywords if k in text)
        if matches >= 3:
            if anchors and not any(a in text for a in anchors):
                continue
            return True
        if len(keywords) <= 4 and matches >= 2:
            if anchors and not any(a in text for a in anchors):
                continue
            return True
        if matches / max(1, len(keywords)) >= 0.35:
            if anchors and not any(a in text for a in anchors):
                continue
            return True
    return False


def _dedupe_claims(claims: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[str] = set()
    unique: List[Dict[str, str]] = []
    for item in claims:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        key = _normalize_text(text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _claim_score(text: str) -> int:
    if not text:
        return 0
    score = 0
    normalized = _normalize_text(text)
    if _is_strong_assertion(text):
        score += 5
    if any(token in normalized for token in _EXTERNAL_HINT_TOKENS):
        score += 3
    keywords = _extract_keywords(text)
    score += min(len(keywords), 6)
    score += min(len(text) // 30, 4)
    return score


def _dedupe_terms(terms: List[str]) -> List[str]:
    seen: set[str] = set()
    unique: List[str] = []
    for term in terms:
        value = str(term or "").strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _normalize_verdict(value: str) -> str:
    verdict = str(value or "").strip().lower()
    if verdict in _VERDICT_KEYS:
        return verdict
    return "uncertain"
