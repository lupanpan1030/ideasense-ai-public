from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from app.services.localization import OutputLocale

MetricTone = Literal["primary", "success", "warning"]
TrendTone = Literal["success", "warning", "info"]


def _role_label(role: str | None, locale: OutputLocale) -> str:
    labels = {
        "owner": ("Owner", "所有者"),
        "admin": ("Admin", "管理员"),
        "mentor": ("Mentor", "导师"),
        "student": ("Student", "学员"),
    }
    normalized = (role or "").strip().lower()
    english, chinese = labels.get(normalized, (normalized or "Unknown", normalized or "未知"))
    return chinese if locale == "zh" else english


def _report_status_label(status: str | None, locale: OutputLocale) -> str:
    labels = {
        "pending": ("Pending", "待处理"),
        "draft": ("Draft", "草稿"),
        "ready": ("Ready", "已就绪"),
        "confirmed": ("Confirmed", "已确认"),
        "failed": ("Failed", "失败"),
    }
    normalized = (status or "").strip().lower()
    english, chinese = labels.get(normalized, (status or "Unknown", status or "未知"))
    return chinese if locale == "zh" else english


def _stage_label(stage: str, locale: OutputLocale) -> str:
    labels = {
        "problem": ("Problem Statement", "问题定义"),
        "market": ("Market Analysis", "市场分析"),
        "tech": ("Technical Plan", "技术方案"),
        "report": ("Report", "报告"),
    }
    english, chinese = labels.get(stage, (stage, stage))
    return chinese if locale == "zh" else english


def _period_label(days: int, locale: OutputLocale) -> str:
    if locale == "zh":
        return f"前 {days} 天"
    return f"previous {days} days"


def _start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(value: datetime) -> datetime:
    day_start = _start_of_day(value)
    return day_start - timedelta(days=day_start.weekday())


def _bucket_key(value: datetime) -> str:
    return value.date().isoformat()


def _format_delta_counts(
    current: int,
    previous: int,
    period_label: str,
    locale: OutputLocale,
    *,
    invert: bool = False,
) -> tuple[str, MetricTone]:
    if previous <= 0:
        if current <= 0:
            if locale == "zh":
                return f"较{period_label}无变化", "primary"
            return f"No change vs {period_label}", "primary"
        tone: MetricTone = "success" if not invert else "warning"
        if locale == "zh":
            return f"较{period_label} +{current}", tone
        return f"+{current} vs {period_label}", tone

    diff = current - previous
    if invert:
        diff = -diff
    pct_change = (diff / previous) * 100
    if abs(pct_change) < 0.5:
        if locale == "zh":
            return f"较{period_label}持平", "primary"
        return f"Flat vs {period_label}", "primary"
    tone = "success" if pct_change > 0 else "warning"
    sign = "+" if pct_change > 0 else ""
    if locale == "zh":
        return f"较{period_label} {sign}{pct_change:.1f}%", tone
    return f"{sign}{pct_change:.1f}% vs {period_label}", tone


def _format_delta_rate(
    current: float,
    previous: float,
    period_label: str,
    locale: OutputLocale,
) -> tuple[str, MetricTone]:
    if previous <= 0:
        if current <= 0:
            if locale == "zh":
                return f"较{period_label}无变化", "primary"
            return f"No change vs {period_label}", "primary"
        if locale == "zh":
            return f"较{period_label} +{current:.1f} 分", "success"
        return f"+{current:.1f} pts vs {period_label}", "success"

    diff = current - previous
    if abs(diff) < 0.1:
        if locale == "zh":
            return f"较{period_label}持平", "primary"
        return f"Flat vs {period_label}", "primary"
    tone = "success" if diff > 0 else "warning"
    sign = "+" if diff > 0 else ""
    if locale == "zh":
        return f"较{period_label} {sign}{diff:.1f} 分", tone
    return f"{sign}{diff:.1f} pts vs {period_label}", tone


def _format_period_change(
    current: int,
    previous: int,
    period_label: str,
    locale: OutputLocale,
) -> tuple[str, TrendTone]:
    if previous <= 0:
        if current <= 0:
            if locale == "zh":
                return f"较{period_label}无变化", "info"
            return f"No change vs {period_label}", "info"
        if locale == "zh":
            return f"较{period_label} +{current}", "success"
        return f"+{current} vs {period_label}", "success"

    diff = current - previous
    pct_change = (diff / previous) * 100
    if abs(pct_change) < 0.5:
        if locale == "zh":
            return f"较{period_label}持平", "info"
        return f"Flat vs {period_label}", "info"
    tone: TrendTone = "success" if pct_change > 0 else "warning"
    sign = "+" if pct_change > 0 else ""
    if locale == "zh":
        return f"较{period_label} {sign}{pct_change:.1f}%", tone
    return f"{sign}{pct_change:.1f}% vs {period_label}", tone
