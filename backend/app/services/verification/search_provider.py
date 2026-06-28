"""Search provider access for verification."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .config import (
    tavily_api_key,
    tavily_api_url,
    tavily_search_enabled,
    verification_enabled,
    verification_timeout_s,
)
from .constants import _DEFAULT_TAVILY_URL

logger = logging.getLogger("ideasense.services.verification")


def _provider_enabled(mode: str) -> bool:
    if not verification_enabled():
        return False
    if not tavily_api_key():
        return False
    return bool(tavily_search_enabled())


def _tavily_search(query: str, *, max_results: int) -> List[Dict[str, Any]]:
    if not _provider_enabled("search"):
        return []
    api_key = tavily_api_key()
    if not api_key:
        return []
    url = tavily_api_url() or _DEFAULT_TAVILY_URL
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=verification_timeout_s()) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        logger.warning("Tavily search failed: HTTP %s %s body=%s", exc.code, exc.reason, body[:500])
        return []
    except urllib.error.URLError as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return []
    results = data.get("results")
    if isinstance(results, list):
        return results
    return []


async def _search_evidence(query: str, *, max_results: int) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_tavily_search, query, max_results=max_results)


def _extract_tavily_results(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("results", "sources"):
            items = payload.get(key)
            if isinstance(items, list):
                return items
        for key in ("data", "result", "response"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                items = _extract_tavily_results(nested)
                if items:
                    return items
            elif isinstance(nested, list):
                return nested
    return []


def _compact_evidence(results: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    for item in results[:limit]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        domain = ""
        if url:
            match = re.search(r"https?://([^/]+)", url)
            if match:
                domain = match.group(1)
        compact.append(
            {
                "title": str(item.get("title") or ""),
                "url": url,
                "domain": domain,
                "snippet": str(item.get("content") or item.get("snippet") or ""),
            }
        )
    return compact
