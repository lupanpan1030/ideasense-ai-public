import logging
import os
import urllib.parse
from dataclasses import dataclass

try:
    import resend
except ModuleNotFoundError:
    resend = None


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailConfig:
    api_key: str | None
    sender: str | None
    reply_to: str | None
    verify_base_url: str | None
    app_env: str


def _mask_secret(value: str | None) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "<set>"
    return f"{value[:4]}...{value[-4:]}"


def _flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _token_link_logging_enabled() -> bool:
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        return False
    return _flag_enabled("EMAIL_LOG_TOKEN_LINKS")


def _load_email_config() -> EmailConfig:
    return EmailConfig(
        api_key=os.getenv("RESEND_API_KEY", "").strip() or None,
        sender=os.getenv("EMAIL_FROM", "").strip() or None,
        reply_to=os.getenv("EMAIL_REPLY_TO", "").strip() or None,
        verify_base_url=os.getenv("EMAIL_VERIFY_BASE_URL", "").strip() or None,
        app_env=os.getenv("APP_ENV", "").strip().lower(),
    )


def _require_email_config(config: EmailConfig) -> None:
    if config.app_env != "production":
        return
    missing = []
    if not config.api_key:
        missing.append("RESEND_API_KEY")
    if not config.sender:
        missing.append("EMAIL_FROM")
    if not config.verify_base_url:
        missing.append("EMAIL_VERIFY_BASE_URL")
    if missing:
        raise RuntimeError(
            "Email verification is required in production; missing "
            + ", ".join(missing)
        )


def _resolve_sender(config: EmailConfig) -> str:
    if config.sender:
        return config.sender
    return "IdeaSense AI <ideasenseai@gmail.com>"


def _resolve_verify_base_url(config: EmailConfig) -> str:
    if config.verify_base_url:
        return config.verify_base_url
    return "http://localhost:3000"


def log_email_diagnostics() -> None:
    config = _load_email_config()
    diag_logger = logging.getLogger("uvicorn.error")
    diag_logger.warning(
        "Email config: APP_ENV=%s RESEND_API_KEY_CONFIGURED=%s EMAIL_FROM_CONFIGURED=%s EMAIL_REPLY_TO_CONFIGURED=%s EMAIL_VERIFY_BASE_URL_CONFIGURED=%s",
        config.app_env or "<empty>",
        bool(config.api_key),
        bool(config.sender),
        bool(config.reply_to),
        bool(config.verify_base_url),
    )

def build_verification_link(token: str) -> str:
    config = _load_email_config()
    _require_email_config(config)
    base_url = _resolve_verify_base_url(config).rstrip("/")
    encoded_token = urllib.parse.quote(token)
    return f"{base_url}/verify-email#token={encoded_token}"


def send_verification_email(*, to_email: str, token: str) -> None:
    config = _load_email_config()
    _require_email_config(config)
    verify_link = build_verification_link(token)
    subject = "Verify your email for IdeaSenseAI"
    text = (
        "Verify your email to unlock full IdeaSenseAI access.\n\n"
        f"Verification link: {verify_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html = (
        "<p>Verify your email to unlock full IdeaSenseAI access.</p>"
        f"<p><a href=\"{verify_link}\">Verify email</a></p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )

    if not config.api_key:
        if _token_link_logging_enabled():
            logger.warning("Resend not configured; verification link: %s", verify_link)
        else:
            logger.info(
                "Resend not configured; verification email skipped. "
                "Set EMAIL_LOG_TOKEN_LINKS=1 to log local token links."
            )
        return

    from_email = _resolve_sender(config)
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": text,
        "html": html,
    }
    if config.reply_to:
        payload["reply_to"] = config.reply_to
    try:
        if resend is None:
            raise RuntimeError("resend package is required when RESEND_API_KEY is set")
        resend.api_key = config.api_key
        resend.Emails.send(payload)
    except Exception as exc:
        logger.exception("Resend send failed")
        raise RuntimeError(f"Resend request failed: {exc}") from exc


def build_password_reset_link(token: str) -> str:
    config = _load_email_config()
    _require_email_config(config)
    base_url = _resolve_verify_base_url(config).rstrip("/")
    encoded_token = urllib.parse.quote(token)
    return f"{base_url}/reset-password#token={encoded_token}"


def send_password_reset_email(*, to_email: str, token: str) -> None:
    config = _load_email_config()
    _require_email_config(config)
    reset_link = build_password_reset_link(token)
    subject = "Reset your IdeaSenseAI password"
    text = (
        "We received a request to reset your IdeaSenseAI password.\n\n"
        f"Reset link: {reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html = (
        "<p>We received a request to reset your IdeaSenseAI password.</p>"
        f"<p><a href=\"{reset_link}\">Reset password</a></p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )

    if not config.api_key:
        if _token_link_logging_enabled():
            logger.warning(
                "Resend not configured; password reset link: %s",
                reset_link,
            )
        else:
            logger.info(
                "Resend not configured; password reset email skipped. "
                "Set EMAIL_LOG_TOKEN_LINKS=1 to log local token links."
            )
        return

    from_email = _resolve_sender(config)
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": text,
        "html": html,
    }
    if config.reply_to:
        payload["reply_to"] = config.reply_to
    try:
        if resend is None:
            raise RuntimeError("resend package is required when RESEND_API_KEY is set")
        resend.api_key = config.api_key
        resend.Emails.send(payload)
    except Exception as exc:
        logger.exception("Resend send failed")
        raise RuntimeError(f"Resend request failed: {exc}") from exc
