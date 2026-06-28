import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerificationToken:
    token: str
    token_hash: str
    expires_at: datetime


def _token_ttl_hours() -> int:
    raw = os.getenv("EMAIL_VERIFY_TOKEN_TTL_HOURS", "24").strip()
    try:
        return max(1, int(raw))
    except ValueError as exc:
        raise RuntimeError("EMAIL_VERIFY_TOKEN_TTL_HOURS must be an integer") from exc


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> VerificationToken:
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_token_ttl_hours())
    return VerificationToken(token=raw, token_hash=token_hash, expires_at=expires_at)


async def issue_email_verification_token(
    session: AsyncSession, *, user_id: str, email: str
) -> VerificationToken:
    token = _generate_token()
    await session.execute(
        text(
            "UPDATE email_verification_tokens "
            "SET consumed_at = now() "
            "WHERE user_id = :user_id "
            "AND consumed_at IS NULL"
        ),
        {"user_id": user_id},
    )
    await session.execute(
        text(
            "INSERT INTO email_verification_tokens ("
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


async def verify_email_token(session: AsyncSession, *, token: str) -> str:
    cleaned = token.strip()
    if not cleaned:
        raise VerificationError("Verification token is required.")
    token_hash = _hash_token(cleaned)
    result = await session.execute(
        text(
            "SELECT id, user_id, email, expires_at, consumed_at "
            "FROM email_verification_tokens "
            "WHERE token_hash = :token_hash "
            "LIMIT 1"
        ),
        {"token_hash": token_hash},
    )
    row = result.mappings().first()
    if not row:
        raise VerificationError("Verification token is invalid.")
    if row.get("consumed_at"):
        raise VerificationError("Verification token has already been used.")
    expires_at = row.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
        raise VerificationError("Verification token has expired.")

    user_id = row.get("user_id")
    if not user_id:
        raise VerificationError("Verification token is invalid.")

    await session.execute(
        text(
            "UPDATE users "
            "SET email_verified_at = COALESCE(email_verified_at, now()) "
            "WHERE id = :user_id "
            "AND deleted_at IS NULL"
        ),
        {"user_id": str(user_id)},
    )
    await session.execute(
        text(
            "UPDATE email_verification_tokens "
            "SET consumed_at = now() "
            "WHERE id = :token_id"
        ),
        {"token_id": row.get("id")},
    )
    return str(user_id)


async def is_email_verified(session: AsyncSession, *, user_id: str) -> bool:
    result = await session.execute(
        text(
            "SELECT email_verified_at "
            "FROM users "
            "WHERE id = :user_id "
            "AND deleted_at IS NULL "
            "AND is_active IS TRUE"
        ),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    return bool(row and row.get("email_verified_at"))
