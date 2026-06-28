import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWTError


JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"


def _require_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET is required")
    return secret


def _get_expires_minutes() -> int:
    raw = os.getenv("JWT_EXPIRES_MINUTES", "60").strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError("JWT_EXPIRES_MINUTES must be an integer") from exc


def _get_refresh_threshold_minutes() -> int:
    raw = os.getenv("JWT_REFRESH_THRESHOLD_MINUTES", "10").strip()
    try:
        return max(1, int(raw))
    except ValueError as exc:
        raise RuntimeError("JWT_REFRESH_THRESHOLD_MINUTES must be an integer") from exc


def create_access_token(
    *,
    user_id: str,
    actor_type: str = "user",
    email: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=_get_expires_minutes())
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "actor_type": actor_type,
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, _require_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            _require_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
        )
    except PyJWTError as exc:
        raise ValueError("Invalid auth token") from exc


def maybe_refresh_access_token(payload: dict[str, Any]) -> str | None:
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    now = datetime.now(timezone.utc).timestamp()
    remaining = exp - now
    if remaining <= 0:
        return None
    threshold = _get_refresh_threshold_minutes() * 60
    if remaining > threshold:
        return None
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        return None
    actor_type = payload.get("actor_type")
    email = payload.get("email") if isinstance(payload.get("email"), str) else None
    return create_access_token(
        user_id=user_id,
        actor_type=actor_type if isinstance(actor_type, str) else "user",
        email=email,
    )
