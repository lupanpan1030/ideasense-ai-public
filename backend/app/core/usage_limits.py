from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UsageLimitError(RuntimeError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class UsageLimits:
    per_minute: int
    per_day: int


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


def get_llm_usage_limits(is_verified: bool) -> UsageLimits:
    if is_verified:
        return UsageLimits(
            per_minute=_get_int_env("LLM_RATE_LIMIT_MINUTE_VERIFIED", 30),
            per_day=_get_int_env("LLM_RATE_LIMIT_DAY_VERIFIED", 300),
        )
    return UsageLimits(
        per_minute=_get_int_env("LLM_RATE_LIMIT_MINUTE_UNVERIFIED", 10),
        per_day=_get_int_env("LLM_RATE_LIMIT_DAY_UNVERIFIED", 60),
    )


def get_report_daily_limit() -> int:
    return _get_int_env("REPORT_DAILY_LIMIT_PER_USER", 5)


def _bucket_start(now: datetime, bucket_type: str) -> datetime:
    if bucket_type == "minute":
        return now.replace(second=0, microsecond=0)
    if bucket_type == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError("Unsupported bucket type")


async def _fetch_report_count(
    session: AsyncSession, *, user_id: str, bucket_start: datetime
) -> int:
    result = await session.execute(
        text(
            "SELECT report_count "
            "FROM report_usage_buckets "
            "WHERE user_id = :user_id "
            "AND bucket_start = :bucket_start "
            "LIMIT 1"
        ),
        {"user_id": user_id, "bucket_start": bucket_start},
    )
    row = result.mappings().first()
    return int(row.get("report_count") if row else 0)


async def enforce_report_daily_limit(
    session: AsyncSession, *, user_id: str
) -> None:
    limit = get_report_daily_limit()
    if limit <= 0:
        return
    now = datetime.now(timezone.utc)
    day_start = _bucket_start(now, "day")
    current_count = await _fetch_report_count(
        session, user_id=user_id, bucket_start=day_start
    )
    if current_count >= limit:
        retry_after = int(
            max(1, (day_start + timedelta(days=1) - now).total_seconds())
        )
        raise UsageLimitError(
            "Daily report limit reached. Please try again tomorrow.",
            retry_after_seconds=retry_after,
        )


async def record_report_usage(session: AsyncSession, *, user_id: str) -> int:
    now = datetime.now(timezone.utc)
    day_start = _bucket_start(now, "day")
    result = await session.execute(
        text(
            "INSERT INTO report_usage_buckets (user_id, bucket_start, report_count) "
            "VALUES (:user_id, :bucket_start, 1) "
            "ON CONFLICT (user_id, bucket_start) DO UPDATE SET "
            "report_count = report_usage_buckets.report_count + 1, "
            "updated_at = now() "
            "RETURNING report_count"
        ),
        {"user_id": user_id, "bucket_start": day_start},
    )
    row = result.mappings().first()
    return int(row.get("report_count") if row else 1)


async def _increment_bucket(
    session: AsyncSession, *, user_id: str, bucket_type: str, bucket_start: datetime
) -> int:
    result = await session.execute(
        text(
            "INSERT INTO llm_usage_buckets (user_id, bucket_type, bucket_start, request_count) "
            "VALUES (:user_id, :bucket_type, :bucket_start, 1) "
            "ON CONFLICT (user_id, bucket_type, bucket_start) DO UPDATE SET "
            "request_count = llm_usage_buckets.request_count + 1, "
            "updated_at = now() "
            "RETURNING request_count"
        ),
        {
            "user_id": user_id,
            "bucket_type": bucket_type,
            "bucket_start": bucket_start,
        },
    )
    row = result.mappings().first()
    return int(row.get("request_count") if row else 1)


async def enforce_llm_usage_limits(
    session: AsyncSession, *, user_id: str, is_verified: bool
) -> None:
    limits = get_llm_usage_limits(is_verified)
    now = datetime.now(timezone.utc)

    minute_start = _bucket_start(now, "minute")
    minute_count = await _increment_bucket(
        session,
        user_id=user_id,
        bucket_type="minute",
        bucket_start=minute_start,
    )
    if minute_count > limits.per_minute:
        retry_after = 60 - now.second
        raise UsageLimitError(
            "Too many requests. Please wait a moment and try again.",
            retry_after_seconds=retry_after,
        )

    day_start = _bucket_start(now, "day")
    day_count = await _increment_bucket(
        session,
        user_id=user_id,
        bucket_type="day",
        bucket_start=day_start,
    )
    if day_count > limits.per_day:
        raise UsageLimitError(
            "Daily usage limit reached. Please try again tomorrow.",
            retry_after_seconds=None,
        )
