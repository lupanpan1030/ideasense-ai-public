from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RateLimitError(RuntimeError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class RateLimitSettings:
    window_seconds: int
    max_count: int


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip()
    if not cleaned:
        return default
    try:
        return int(cleaned)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def load_rate_limit_settings(
    prefix: str,
    *,
    default_window_seconds: int,
    default_max_count: int,
) -> RateLimitSettings:
    return RateLimitSettings(
        window_seconds=_get_int_env(
            f"{prefix}_WINDOW_SECONDS", default_window_seconds
        ),
        max_count=_get_int_env(f"{prefix}_MAX", default_max_count),
    )


def _bucket_start(now: datetime, window_seconds: int) -> datetime:
    timestamp = int(now.timestamp())
    start_ts = timestamp - (timestamp % window_seconds)
    return datetime.fromtimestamp(start_ts, tz=timezone.utc)


def _hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _increment_bucket(
    session: AsyncSession,
    *,
    scope: str,
    key: str,
    window_seconds: int,
) -> tuple[int, datetime]:
    now = datetime.now(timezone.utc)
    bucket_start = _bucket_start(now, window_seconds)
    key_hash = _hash_key(f"{scope}:{key}")
    result = await session.execute(
        text(
            "INSERT INTO rate_limit_buckets "
            "(scope, key_hash, window_seconds, bucket_start, request_count) "
            "VALUES (:scope, :key_hash, :window_seconds, :bucket_start, 1) "
            "ON CONFLICT (scope, key_hash, window_seconds, bucket_start) "
            "DO UPDATE SET request_count = rate_limit_buckets.request_count + 1, "
            "updated_at = now() "
            "RETURNING request_count"
        ),
        {
            "scope": scope,
            "key_hash": key_hash,
            "window_seconds": window_seconds,
            "bucket_start": bucket_start,
        },
    )
    row = result.mappings().first()
    return int(row.get("request_count") if row else 1), bucket_start


async def get_rate_limit_count(
    session: AsyncSession,
    *,
    scope: str,
    key: str,
    window_seconds: int,
) -> int:
    if window_seconds <= 0:
        return 0
    now = datetime.now(timezone.utc)
    bucket_start = _bucket_start(now, window_seconds)
    key_hash = _hash_key(f"{scope}:{key}")
    result = await session.execute(
        text(
            "SELECT request_count "
            "FROM rate_limit_buckets "
            "WHERE scope = :scope "
            "AND key_hash = :key_hash "
            "AND window_seconds = :window_seconds "
            "AND bucket_start = :bucket_start "
            "LIMIT 1"
        ),
        {
            "scope": scope,
            "key_hash": key_hash,
            "window_seconds": window_seconds,
            "bucket_start": bucket_start,
        },
    )
    row = result.mappings().first()
    return int(row.get("request_count") if row else 0)


async def increment_rate_limit(
    session: AsyncSession,
    *,
    scope: str,
    key: str,
    window_seconds: int,
) -> int:
    count, _ = await _increment_bucket(
        session,
        scope=scope,
        key=key,
        window_seconds=window_seconds,
    )
    return count


async def enforce_rate_limit(
    session: AsyncSession,
    *,
    scope: str,
    key: str,
    window_seconds: int,
    max_count: int,
) -> None:
    if max_count <= 0 or window_seconds <= 0:
        return
    count, bucket_start = await _increment_bucket(
        session,
        scope=scope,
        key=key,
        window_seconds=window_seconds,
    )
    if count <= max_count:
        return
    now = datetime.now(timezone.utc)
    retry_after = int(
        max(1, (bucket_start + timedelta(seconds=window_seconds) - now).total_seconds())
    )
    raise RateLimitError(
        "Too many requests. Please wait and try again.",
        retry_after_seconds=retry_after,
    )
