"""Load and render prompt templates for LLM prompts."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROMPT_ROOT = Path(__file__).resolve().parent.parent / "prompts"
_IF_BLOCK_RE = re.compile(r"{{#if\s+([a-zA-Z0-9_]+)\s*}}(.*?){{/if}}", re.DOTALL)


@lru_cache(maxsize=128)
def load_prompt(template_name: str) -> str:
    """Load a prompt template by relative name."""
    path = _PROMPT_ROOT / f"{template_name}.md"
    return path.read_text(encoding="utf-8")


def render_text(text: str, **vars: Any) -> str:
    """Render a text template with simple variable and if-block replacement."""

    def _replace_if(match: re.Match[str]) -> str:
        key = match.group(1)
        content = match.group(2)
        if vars.get(key):
            return content
        return ""

    rendered = _IF_BLOCK_RE.sub(_replace_if, text)
    for key, value in vars.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def render_prompt(template_name: str, **vars: Any) -> str:
    """Load a prompt template and render it with variables."""
    return render_text(load_prompt(template_name), **vars)


__all__ = ["load_prompt", "render_prompt", "render_text"]
