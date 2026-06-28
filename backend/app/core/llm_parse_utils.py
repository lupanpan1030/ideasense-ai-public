"""Shared parsing helpers for LLM JSON outputs."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

LLM_JSON_FALLBACK_LOG_CODE = "llm_json_fallback_used"


def _strip_markdown_code_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return content

    lines = stripped.splitlines()
    if len(lines) < 2 or not lines[0].startswith("```"):
        return content
    if lines[-1].strip() != "```":
        return content
    return "\n".join(lines[1:-1]).strip()


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object from LLM output.

    Handles fenced JSON directly and falls back to a single JSON object embedded in
    surrounding prose. Multiple JSON objects are rejected rather than truncating.
    """
    normalized = _strip_markdown_code_fence(content)
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        start = normalized.find("{")
        if start == -1:
            raise
        decoder = json.JSONDecoder()
        try:
            parsed, end = decoder.raw_decode(normalized[start:])
        except json.JSONDecodeError:
            raise exc
        trailing = normalized[start + end :]
        if "{" in trailing:
            raise ValueError(
                "LLM response contains multiple or malformed JSON objects."
            )
        logger.warning(
            "%s: recovered JSON object from wrapped LLM output",
            LLM_JSON_FALLBACK_LOG_CODE,
            extra={"event_code": LLM_JSON_FALLBACK_LOG_CODE},
        )
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object.")
    return parsed


__all__ = ["LLM_JSON_FALLBACK_LOG_CODE", "parse_json_object"]
