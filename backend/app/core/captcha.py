from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass


class CaptchaError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptchaConfig:
    provider: str
    secret_key: str | None
    verify_url: str
    required: bool
    min_score: float | None


HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    value = raw.strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float | None) -> float | None:
    raw = os.getenv(key)
    if raw is None:
        return default
    cleaned = raw.strip()
    if not cleaned:
        return default
    try:
        return float(cleaned)
    except ValueError as exc:
        raise RuntimeError(f"{key} must be a float") from exc


def _captcha_required() -> bool:
    if os.getenv("CAPTCHA_REQUIRED") is not None:
        return _env_bool("CAPTCHA_REQUIRED", False)
    return os.getenv("APP_ENV", "").strip().lower() == "production"


def _resolve_provider(value: str | None) -> str:
    provider = (value or "hcaptcha").strip().lower()
    if provider not in {"hcaptcha", "recaptcha"}:
        return "hcaptcha"
    return provider


def _load_config() -> CaptchaConfig:
    provider = _resolve_provider(os.getenv("CAPTCHA_PROVIDER"))
    secret_key = os.getenv("CAPTCHA_SECRET_KEY", "").strip() or None
    verify_url = os.getenv("CAPTCHA_VERIFY_URL", "").strip()
    if not verify_url:
        verify_url = (
            HCAPTCHA_VERIFY_URL if provider == "hcaptcha" else RECAPTCHA_VERIFY_URL
        )
    min_score = None
    if provider == "recaptcha":
        min_score = _env_float("CAPTCHA_MIN_SCORE", 0.5)
    required = _captcha_required()
    if required and not secret_key:
        raise RuntimeError("CAPTCHA_SECRET_KEY is required when CAPTCHA_REQUIRED=1")
    return CaptchaConfig(
        provider=provider,
        secret_key=secret_key,
        verify_url=verify_url,
        required=required,
        min_score=min_score,
    )


def captcha_required() -> bool:
    return _load_config().required


def _verify_captcha_sync(
    config: CaptchaConfig,
    token: str,
    remote_ip: str | None,
) -> None:
    if not config.secret_key:
        raise CaptchaError("Captcha secret key is missing.")
    payload = {
        "secret": config.secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        config.verify_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise CaptchaError("Captcha verification failed.") from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CaptchaError("Captcha verification failed.") from exc
    if not payload.get("success"):
        raise CaptchaError("Captcha verification failed.")
    if config.provider == "recaptcha" and config.min_score is not None:
        score = payload.get("score")
        if isinstance(score, (int, float)) and score < config.min_score:
            raise CaptchaError("Captcha score too low.")


async def verify_captcha(token: str | None, *, remote_ip: str | None = None) -> None:
    config = _load_config()
    if not config.required:
        return
    if not token or not token.strip():
        raise CaptchaError("Captcha token is required.")
    await asyncio.to_thread(
        _verify_captcha_sync, config, token.strip(), remote_ip
    )
