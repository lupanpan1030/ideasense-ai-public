import os
from pathlib import Path

from dotenv import load_dotenv


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}


def load_backend_env() -> None:
    """Load the backend-local .env regardless of the process cwd."""
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=backend_env, override=False)


def _clean_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def _env_flag_enabled(name: str) -> bool:
    return _clean_env_value(os.getenv(name)) in TRUE_VALUES


def sample_public_enabled() -> bool:
    raw = _clean_env_value(os.getenv("SAMPLE_PUBLIC_ENABLED"))
    if raw is not None:
        return raw in TRUE_VALUES

    return os.getenv("APP_ENV", "").strip().lower() != "production"


def admin_api_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    raw = _clean_env_value(os.getenv("ADMIN_API_ENABLED"))
    if raw is None:
        raw = _clean_env_value(os.getenv("ADMIN_ENABLED"))

    if app_env == "production":
        return raw in TRUE_VALUES

    if raw is None:
        return True
    return raw not in FALSE_VALUES


def require_dev_flags_disabled_in_production() -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "production":
        return

    enabled = [
        name
        for name in ("DEV_AUTH_BYPASS", "DEV_LOGIN_ENABLED")
        if _env_flag_enabled(name)
    ]
    if enabled:
        raise RuntimeError(
            "Refusing to start in production with dev flags enabled: "
            + ", ".join(enabled)
        )
