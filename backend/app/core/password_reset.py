import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PasswordResetError(RuntimeError):
    pass


@dataclass(frozen=True)
class PasswordResetToken:
    token: str
    token_hash: str
    expires_at: datetime


@dataclass(frozen=True)
class PasswordResetRecord:
    token_id: str
    user_id: str
    email: str


def _token_ttl_hours() -> int:
    raw = os.getenv("PASSWORD_RESET_TOKEN_TTL_HOURS", "2").strip()
    try:
        return max(1, int(raw))
    except ValueError as exc:
        raise RuntimeError("PASSWORD_RESET_TOKEN_TTL_HOURS must be an integer") from exc


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> PasswordResetToken:
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_token_ttl_hours())
    return PasswordResetToken(token=raw, token_hash=token_hash, expires_at=expires_at)


async def issue_password_reset_token(
    session: AsyncSession, *, user_id: str, email: str
) -> PasswordResetToken:
    token = _generate_token()
    await session.execute(
        text(
            "UPDATE password_reset_tokens "
            "SET consumed_at = now() "
            "WHERE user_id = :user_id "
            "AND consumed_at IS NULL"
        ),
        {"user_id": user_id},
    )
    await session.execute(
        text(
            "INSERT INTO password_reset_tokens ("
            "user_id, email, token_hash, expires_at"
            ") VALUES ("
            ":user_id, :email, :token_hash, :expires_at"
            ")"
        ),
        {
            "user_id": user_id,
            "email": email,
            "token_hash": token.token_hash,
            "expires_at": token.expires_at,
        },
    )
    return token


async def verify_password_reset_token(
    session: AsyncSession, *, token: str
) -> PasswordResetRecord:
    cleaned = token.strip()
    if not cleaned:
        raise PasswordResetError("Reset token is required.")
    token_hash = _hash_token(cleaned)
    result = await session.execute(
        text(
            "SELECT id, user_id, email, expires_at, consumed_at "
            "FROM password_reset_tokens "
            "WHERE token_hash = :token_hash "
            "LIMIT 1"
        ),
        {"token_hash": token_hash},
    )
    row = result.mappings().first()
    if not row:
        raise PasswordResetError("Reset token is invalid.")
    if row.get("consumed_at"):
        raise PasswordResetError("Reset token has already been used.")
    expires_at = row.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
        raise PasswordResetError("Reset token has expired.")

    user_id = row.get("user_id")
    email = row.get("email")
    if not user_id or not email:
        raise PasswordResetError("Reset token is invalid.")

    return PasswordResetRecord(
        token_id=str(row.get("id")),
        user_id=str(user_id),
        email=str(email),
    )
