"""Environment-backed configuration for verification."""

from __future__ import annotations

import os


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    value = raw.strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_str(key: str, default: str) -> str:
    raw = os.getenv(key)
    if raw is None:
        return default
    value = raw.strip()
    return value or default


def verification_enabled() -> bool:
    return _env_bool("IDEASENSE_VERIFICATION_ENABLED", True)


def tavily_search_enabled() -> bool:
    return _env_bool("IDEASENSE_TAVILY_SEARCH_ENABLED", True)


def tavily_api_key() -> str | None:
    value = os.getenv("TAVILY_API_KEY", "").strip()
    return value or None


def tavily_api_url() -> str | None:
    value = os.getenv("TAVILY_API_URL", "").strip()
    return value or None


def verification_max_claims() -> int:
    return max(1, _env_int("IDEASENSE_VERIFICATION_MAX_CLAIMS", 8))


def verification_max_results() -> int:
    return max(1, _env_int("IDEASENSE_VERIFICATION_MAX_RESULTS", 3))


def verification_timeout_s() -> float:
    return max(1.0, _env_float("IDEASENSE_VERIFICATION_TIMEOUT_S", 8.0))


def verification_per_section() -> int:
    return max(1, _env_int("IDEASENSE_VERIFICATION_PER_SECTION", 3))


def verification_allowed_domains() -> str:
    return os.getenv("IDEASENSE_VERIFICATION_ALLOWED_DOMAINS", "")


def verification_min_priority() -> str:
    return _env_str("IDEASENSE_VERIFICATION_MIN_PRIORITY", "medium").lower()


def verification_stage_max_questions() -> int:
    return max(1, _env_int("IDEASENSE_VERIFICATION_STAGE_MAX", 5))
