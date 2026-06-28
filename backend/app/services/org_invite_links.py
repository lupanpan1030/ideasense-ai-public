from __future__ import annotations

import os
from urllib.parse import urlparse


LOCAL_APP_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


class InviteLinkConfigurationError(RuntimeError):
    """Raised when invite links cannot be safely constructed."""


def _first_non_blank_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def _app_env_is_production() -> bool:
    return os.getenv("APP_ENV", "").strip().lower() == "production"


def _is_local_app_base_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.hostname in LOCAL_APP_HOSTS


def resolve_app_base_url() -> str:
    raw = _first_non_blank_env(
        "APP_BASE_URL", "FRONTEND_URL", "NEXT_PUBLIC_APP_URL"
    )
    if not raw:
        if _app_env_is_production():
            raise InviteLinkConfigurationError(
                "APP_BASE_URL is required in production to build invite links."
            )
        raw = "http://localhost:3000"

    if _app_env_is_production() and _is_local_app_base_url(raw):
        raise InviteLinkConfigurationError(
            "APP_BASE_URL must be a public app URL in production."
        )

    return raw.rstrip("/")


def build_invite_link(token: str) -> str:
    base_url = resolve_app_base_url()
    return f"{base_url}/join?token={token}"
