"""Domain filtering helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .config import verification_allowed_domains
from .constants import _FALLBACK_BLOCKED_DOMAINS


def _parse_allowed_domains() -> List[str]:
    raw = verification_allowed_domains() or ""
    tokens = re.split(r"[,\s]+", raw)
    domains = []
    for item in tokens:
        value = str(item or "").strip().lower()
        if value:
            domains.append(value)
    return domains


def _domain_allowed(domain: str, allowed: List[str]) -> bool:
    if not allowed:
        return True
    value = str(domain or "").strip().lower()
    if not value:
        return False
    for entry in allowed:
        if value == entry:
            return True
        if value.endswith("." + entry):
            return True
    return False


def _domain_blocked(domain: str, blocked: List[str] | set[str]) -> bool:
    value = str(domain or "").strip().lower()
    if not value:
        return False
    for entry in blocked:
        if value == entry:
            return True
        if value.endswith("." + entry):
            return True
    return False


def _filter_evidence_by_domain(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    allowed = _parse_allowed_domains()
    if not allowed:
        return evidence
    filtered: List[Dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "").strip().lower()
        if _domain_allowed(domain, allowed):
            filtered.append(item)
    return filtered


def _maybe_apply_domain_fallback(
    filtered: List[Dict[str, Any]],
    *,
    unfiltered: List[Dict[str, Any]],
    allowed_domains: List[str],
) -> Tuple[List[Dict[str, Any]], bool, str | None]:
    """Return evidence and fallback flags when domain filtering empties results."""
    if not allowed_domains:
        return filtered, False, None
    if filtered:
        return filtered, False, None
    if unfiltered:
        safe_unfiltered = [
            item
            for item in unfiltered
            if not _domain_blocked(item.get("domain"), _FALLBACK_BLOCKED_DOMAINS)
        ]
        if safe_unfiltered:
            return safe_unfiltered, True, "unfiltered_domains"
        return [], True, "unfiltered_domains"
    return filtered, False, None
