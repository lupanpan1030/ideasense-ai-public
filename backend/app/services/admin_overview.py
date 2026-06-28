from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.localization import OutputLocale
from app.services.admin_overview_activity import (
    ActivityItem,
    build_admin_overview_activity_feed,
)
from app.services.admin_overview_formatters import (
    MetricTone,
    TrendTone,
    _bucket_key,
    _format_delta_counts,
    _format_delta_rate,
    _format_period_change,
    _period_label,
    _stage_label,
    _start_of_day,
    _start_of_week,
)

STAGE_WEIGHTS = {
    "problem": 25,
    "market": 50,
    "tech": 75,
    "report": 100,
}

@dataclass(frozen=True)
class OverviewMetric:
    label: str
    value: str
    delta: str
    tone: MetricTone
    series: list[int]


@dataclass(frozen=True)
class EnrollmentTrend:
    label: str
    sublabel: str
    total: str
    change: str
    tone: TrendTone
    series: list[int]


@dataclass(frozen=True)
class CohortProgressItem:
    id: str
    name: str
    progress: int
    meta: str


@dataclass(frozen=True)
class PendingAction:
    title: str
    detail: str
    tone: MetricTone


@dataclass(frozen=True)
class UpcomingDeadline:
    title: str
    due_at: datetime | None = None


@dataclass(frozen=True)
class InsightHighlight:
    title: str
    detail: str


@dataclass(frozen=True)
class AdminOverviewPayload:
    overview_metrics: list[OverviewMetric]
    enrollment_trend: EnrollmentTrend
    cohort_progress: list[CohortProgressItem]
    pending_actions: list[PendingAction]
    upcoming_deadlines: list[UpcomingDeadline]
    activity_feed: list[ActivityItem]
    insight_highlights: list[InsightHighlight]


async def _fetch_scalar(session: AsyncSession, sql: str, params: dict) -> int:
    result = await session.execute(text(sql), params)
    return int(result.scalar() or 0)


async def _fetch_bucketed_counts(
    session: AsyncSession,
    sql: str,
    params: dict,
    buckets: list[datetime],
) -> list[int]:
    result = await session.execute(text(sql), params)
    rows = result.mappings().all()
    counts = {
        _bucket_key(row.get("bucket")): int(row.get("count") or 0)
        for row in rows
    }
    return [counts.get(_bucket_key(bucket), 0) for bucket in buckets]

async def build_admin_overview_payload(
    session: AsyncSession,
    locale: OutputLocale,
) -> AdminOverviewPayload:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    month_ago = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)

    day_start = _start_of_day(now) - timedelta(days=29)
    day_end = _start_of_day(now) + timedelta(days=1)
    prev_day_start = day_start - timedelta(days=30)

    week_start = _start_of_week(now) - timedelta(weeks=7)
    week_end = _start_of_week(now) + timedelta(weeks=1)
    weekly_buckets = [week_start + timedelta(weeks=idx) for idx in range(8)]
    daily_buckets = [day_start + timedelta(days=idx) for idx in range(30)]

    members_total = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND status = 'active' "
        "AND deleted_at IS NULL",
        {},
    )

    members_period_sql = (
        "SELECT COUNT(*) FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND status = 'active' "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end"
    )
    members_current_period = await _fetch_scalar(
        session,
        members_period_sql,
        {"start": week_ago, "end": now},
    )
    members_previous_period = await _fetch_scalar(
        session,
        members_period_sql,
        {"start": two_weeks_ago, "end": week_ago},
    )

    members_delta, members_tone = _format_delta_counts(
        members_current_period,
        members_previous_period,
        _period_label(7, locale),
        locale,
    )

    members_series = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('week', created_at) AS bucket, COUNT(*) AS count "
        "FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND status = 'active' "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": week_start, "end": week_end},
        weekly_buckets,
    )

    cohorts_active = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM cohorts "
        "WHERE org_id = app_org_id() "
        "AND is_archived IS FALSE "
        "AND deleted_at IS NULL",
        {},
    )

    cohorts_period_sql = (
        "SELECT COUNT(*) FROM cohorts "
        "WHERE org_id = app_org_id() "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end"
    )
    cohorts_current_period = await _fetch_scalar(
        session,
        cohorts_period_sql,
        {"start": month_ago, "end": now},
    )
    cohorts_previous_period = await _fetch_scalar(
        session,
        cohorts_period_sql,
        {"start": two_months_ago, "end": month_ago},
    )

    cohorts_delta, cohorts_tone = _format_delta_counts(
        cohorts_current_period,
        cohorts_previous_period,
        _period_label(30, locale),
        locale,
    )

    cohorts_series = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('week', created_at) AS bucket, COUNT(*) AS count "
        "FROM cohorts "
        "WHERE org_id = app_org_id() "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": week_start, "end": week_end},
        weekly_buckets,
    )

    projects_total = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM projects "
        "WHERE org_id = app_org_id() "
        "AND deleted_at IS NULL",
        {},
    )

    projects_total_prev = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM projects "
        "WHERE org_id = app_org_id() "
        "AND deleted_at IS NULL "
        "AND created_at <= :cutoff",
        {"cutoff": month_ago},
    )

    completed_total = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM ("
        "  SELECT project_id, MIN(confirmed_at) AS confirmed_at "
        "  FROM project_reports "
        "  WHERE org_id = app_org_id() "
        "  AND confirmed IS TRUE "
        "  AND deleted_at IS NULL "
        "  GROUP BY project_id"
        ") AS completed",
        {},
    )

    completed_total_prev = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM ("
        "  SELECT project_id, MIN(confirmed_at) AS confirmed_at "
        "  FROM project_reports "
        "  WHERE org_id = app_org_id() "
        "  AND confirmed IS TRUE "
        "  AND deleted_at IS NULL "
        "  GROUP BY project_id"
        ") AS completed "
        "WHERE confirmed_at <= :cutoff",
        {"cutoff": month_ago},
    )

    completion_rate = (
        (completed_total / projects_total) * 100 if projects_total else 0.0
    )
    completion_rate_prev = (
        (completed_total_prev / projects_total_prev) * 100
        if projects_total_prev
        else 0.0
    )

    completion_delta, completion_tone = _format_delta_rate(
        completion_rate, completion_rate_prev, _period_label(30, locale), locale
    )

    project_creation_series = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('week', created_at) AS bucket, COUNT(*) AS count "
        "FROM projects "
        "WHERE org_id = app_org_id() "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": week_start, "end": week_end},
        weekly_buckets,
    )

    completion_series_raw = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('week', confirmed_at) AS bucket, COUNT(*) AS count "
        "FROM ("
        "  SELECT project_id, MIN(confirmed_at) AS confirmed_at "
        "  FROM project_reports "
        "  WHERE org_id = app_org_id() "
        "  AND confirmed IS TRUE "
        "  AND deleted_at IS NULL "
        "  GROUP BY project_id"
        ") AS confirmed "
        "WHERE confirmed_at >= :start AND confirmed_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": week_start, "end": week_end},
        weekly_buckets,
    )

    completion_series: list[int] = []
    cumulative_projects = 0
    cumulative_completed = 0
    for idx in range(8):
        cumulative_projects += project_creation_series[idx]
        cumulative_completed += completion_series_raw[idx]
        if cumulative_projects:
            rate = round((cumulative_completed / cumulative_projects) * 100)
        else:
            rate = 0
        completion_series.append(int(rate))

    pending_invites = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM organization_invitations "
        "WHERE org_id = app_org_id() "
        "AND status = 'pending' "
        "AND deleted_at IS NULL "
        "AND (expires_at IS NULL OR expires_at >= :now)",
        {"now": now},
    )

    pending_assignments = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM mentor_student_assignments "
        "WHERE org_id = app_org_id() "
        "AND status = 'pending' "
        "AND deleted_at IS NULL",
        {},
    )

    pending_projects = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM projects "
        "WHERE org_id = app_org_id() "
        "AND stage_status = 'awaiting_confirm' "
        "AND is_archived IS FALSE "
        "AND deleted_at IS NULL",
        {},
    )

    pending_total = pending_invites + pending_assignments + pending_projects

    pending_invites_period_sql = (
        "SELECT COUNT(*) FROM organization_invitations "
        "WHERE org_id = app_org_id() "
        "AND status = 'pending' "
        "AND deleted_at IS NULL "
        "AND (expires_at IS NULL OR expires_at >= :now) "
        "AND created_at >= :start AND created_at < :end"
    )

    pending_invites_current = await _fetch_scalar(
        session,
        pending_invites_period_sql,
        {"start": week_ago, "end": now, "now": now},
    )
    pending_invites_prev = await _fetch_scalar(
        session,
        pending_invites_period_sql,
        {"start": two_weeks_ago, "end": week_ago, "now": now},
    )

    pending_period_sql = (
        "SELECT COUNT(*) FROM {table} "
        "WHERE org_id = app_org_id() "
        "AND {status_clause} "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end"
    )

    pending_assignments_current = await _fetch_scalar(
        session,
        pending_period_sql.format(
            table="mentor_student_assignments",
            status_clause="status = 'pending'",
        ),
        {"start": week_ago, "end": now},
    )
    pending_assignments_prev = await _fetch_scalar(
        session,
        pending_period_sql.format(
            table="mentor_student_assignments",
            status_clause="status = 'pending'",
        ),
        {"start": two_weeks_ago, "end": week_ago},
    )

    pending_projects_current = await _fetch_scalar(
        session,
        pending_period_sql.format(
            table="projects",
            status_clause="stage_status = 'awaiting_confirm' AND is_archived IS FALSE",
        ),
        {"start": week_ago, "end": now},
    )
    pending_projects_prev = await _fetch_scalar(
        session,
        pending_period_sql.format(
            table="projects",
            status_clause="stage_status = 'awaiting_confirm' AND is_archived IS FALSE",
        ),
        {"start": two_weeks_ago, "end": week_ago},
    )

    pending_current_period = (
        pending_invites_current
        + pending_assignments_current
        + pending_projects_current
    )
    pending_previous_period = (
        pending_invites_prev + pending_assignments_prev + pending_projects_prev
    )

    pending_delta, pending_tone = _format_delta_counts(
        pending_current_period,
        pending_previous_period,
        _period_label(7, locale),
        locale,
        invert=True,
    )

    pending_series = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('week', created_at) AS bucket, COUNT(*) AS count "
        "FROM ("
        "  SELECT created_at FROM organization_invitations "
        "  WHERE org_id = app_org_id() "
        "  AND status = 'pending' "
        "  AND deleted_at IS NULL "
        "  AND (expires_at IS NULL OR expires_at >= :now) "
        "  UNION ALL "
        "  SELECT created_at FROM mentor_student_assignments "
        "  WHERE org_id = app_org_id() "
        "  AND status = 'pending' "
        "  AND deleted_at IS NULL "
        "  UNION ALL "
        "  SELECT created_at FROM projects "
        "  WHERE org_id = app_org_id() "
        "  AND stage_status = 'awaiting_confirm' "
        "  AND is_archived IS FALSE "
        "  AND deleted_at IS NULL "
        ") AS pending_items "
        "WHERE created_at >= :start AND created_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": week_start, "end": week_end, "now": now},
        weekly_buckets,
    )

    members_daily_series = await _fetch_bucketed_counts(
        session,
        "SELECT date_trunc('day', created_at) AS bucket, COUNT(*) AS count "
        "FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND status = 'active' "
        "AND deleted_at IS NULL "
        "AND created_at >= :start AND created_at < :end "
        "GROUP BY bucket ORDER BY bucket",
        {"start": day_start, "end": day_end},
        daily_buckets,
    )

    members_prev_total = await _fetch_scalar(
        session,
        members_period_sql,
        {"start": prev_day_start, "end": day_start},
    )

    enrollment_total = sum(members_daily_series)
    enrollment_change, enrollment_tone = _format_period_change(
        enrollment_total, members_prev_total, _period_label(30, locale), locale
    )

    cohort_rows = await session.execute(
        text(
            "SELECT c.id, c.name, c.updated_at, "
            "COUNT(p.id) AS project_count, "
            "COUNT(p.id) FILTER (WHERE p.current_stage = 'problem') AS problem_count, "
            "COUNT(p.id) FILTER (WHERE p.current_stage = 'market') AS market_count, "
            "COUNT(p.id) FILTER (WHERE p.current_stage = 'tech') AS tech_count, "
            "COUNT(p.id) FILTER (WHERE p.current_stage = 'report') AS report_count "
            "FROM cohorts c "
            "LEFT JOIN projects p "
            "ON p.cohort_id = c.id "
            "AND p.deleted_at IS NULL "
            "AND p.is_archived IS FALSE "
            "WHERE c.org_id = app_org_id() "
            "AND c.deleted_at IS NULL "
            "AND c.is_archived IS FALSE "
            "GROUP BY c.id, c.name, c.updated_at "
            "ORDER BY c.updated_at DESC "
            "LIMIT 4"
        )
    )

    cohort_progress: list[CohortProgressItem] = []
    for row in cohort_rows.mappings().all():
        project_count = int(row.get("project_count") or 0)
        stage_counts = {
            "problem": int(row.get("problem_count") or 0),
            "market": int(row.get("market_count") or 0),
            "tech": int(row.get("tech_count") or 0),
            "report": int(row.get("report_count") or 0),
        }
        if project_count:
            weighted_sum = sum(
                stage_counts[stage] * STAGE_WEIGHTS[stage] for stage in STAGE_WEIGHTS
            )
            progress = round(weighted_sum / project_count)
            dominant_stage = max(stage_counts, key=stage_counts.get)
            meta = (
                f"项目最多的阶段：{_stage_label(dominant_stage, locale)}"
                if locale == "zh"
                else f"Most projects: {_stage_label(dominant_stage, locale)}"
            )
        else:
            progress = 0
            meta = "还没有项目" if locale == "zh" else "No projects yet"

        cohort_progress.append(
            CohortProgressItem(
                id=str(row.get("id")),
                name=row.get("name"),
                progress=int(progress),
                meta=meta,
            )
        )

    upcoming_rows = await session.execute(
        text(
            "SELECT name, end_at, start_at "
            "FROM cohorts "
            "WHERE org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "AND is_archived IS FALSE "
            "AND COALESCE(end_at, start_at) IS NOT NULL "
            "AND COALESCE(end_at, start_at) >= :now "
            "ORDER BY COALESCE(end_at, start_at) ASC "
            "LIMIT 3"
        ),
        {"now": now},
    )

    upcoming_deadlines: list[UpcomingDeadline] = []
    for row in upcoming_rows.mappings().all():
        if row.get("end_at") is not None:
            title = (
                f"队列 {row.get('name')} 结束"
                if locale == "zh"
                else f"Cohort {row.get('name')} ends"
            )
            due_at = row.get("end_at")
        else:
            title = (
                f"队列 {row.get('name')} 开始"
                if locale == "zh"
                else f"Cohort {row.get('name')} starts"
            )
            due_at = row.get("start_at")
        upcoming_deadlines.append(UpcomingDeadline(title=title, due_at=due_at))

    activity_feed = await build_admin_overview_activity_feed(session, locale)

    mentors_count = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND org_role = 'mentor' "
        "AND status = 'active' "
        "AND deleted_at IS NULL",
        {},
    )
    students_count = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM organization_memberships "
        "WHERE org_id = app_org_id() "
        "AND org_role = 'student' "
        "AND status = 'active' "
        "AND deleted_at IS NULL",
        {},
    )

    if mentors_count <= 0 and students_count > 0:
        mentor_detail = (
            "还没有活跃导师。请补充导师以平衡支持。"
            if locale == "zh"
            else "No active mentors yet. Add mentors to balance support."
        )
    elif mentors_count <= 0:
        mentor_detail = "还没有活跃导师。" if locale == "zh" else "No active mentors yet."
    else:
        ratio = students_count / mentors_count if mentors_count else 0
        mentor_detail = (
            f"当前导师与学员比例为 1:{ratio:.1f}。"
            if locale == "zh"
            else f"Mentor-to-student ratio is 1:{ratio:.1f}."
        )

    cohort_student_count = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM cohort_memberships "
        "WHERE org_id = app_org_id() "
        "AND role_in_cohort = 'student' "
        "AND status = 'active' "
        "AND deleted_at IS NULL",
        {},
    )

    if cohorts_active:
        avg_students = cohort_student_count / cohorts_active
        cohort_detail = (
            f"{cohorts_active} 个活跃队列中，平均每个队列有 {avg_students:.1f} 名学员。"
            if locale == "zh"
            else f"Average {avg_students:.1f} students per cohort across "
            f"{cohorts_active} active cohorts."
        )
    else:
        cohort_detail = "还没有活跃队列。" if locale == "zh" else "No active cohorts yet."

    reports_confirmed = await _fetch_scalar(
        session,
        "SELECT COUNT(*) FROM project_reports "
        "WHERE org_id = app_org_id() "
        "AND confirmed IS TRUE "
        "AND deleted_at IS NULL "
        "AND confirmed_at >= :start",
        {"start": week_ago},
    )

    if reports_confirmed:
        reports_detail = (
            f"过去 7 天已确认 {reports_confirmed} 份报告。"
            if locale == "zh"
            else f"{reports_confirmed} reports confirmed in the last 7 days."
        )
    else:
        reports_detail = (
            "过去 7 天没有已确认报告。"
            if locale == "zh"
            else "No reports confirmed in the last 7 days."
        )

    overview_metrics = [
        OverviewMetric(
            label="成员总数" if locale == "zh" else "Total members",
            value=str(members_total),
            delta=members_delta,
            tone=members_tone,
            series=members_series,
        ),
        OverviewMetric(
            label="活跃队列" if locale == "zh" else "Active cohorts",
            value=str(cohorts_active),
            delta=cohorts_delta,
            tone=cohorts_tone,
            series=cohorts_series,
        ),
        OverviewMetric(
            label="完成率" if locale == "zh" else "Completion rate",
            value=f"{round(completion_rate)}%",
            delta=completion_delta,
            tone=completion_tone,
            series=completion_series,
        ),
        OverviewMetric(
            label="待处理事项" if locale == "zh" else "Pending actions",
            value=str(pending_total),
            delta=pending_delta,
            tone=pending_tone,
            series=pending_series,
        ),
    ]

    pending_actions = [
        PendingAction(
            title="待处理导师分配" if locale == "zh" else "Mentor assignments pending",
            detail=(
                f"{pending_assignments} 个分配等待接受"
                if locale == "zh" and pending_assignments
                else "暂无待处理导师分配"
                if locale == "zh"
                else f"{pending_assignments} assignments awaiting acceptance"
                if pending_assignments
                else "No pending mentor assignments"
            ),
            tone="warning" if pending_assignments else "primary",
        ),
        PendingAction(
            title="成员邀请" if locale == "zh" else "Member invites",
            detail=(
                f"{pending_invites} 条邀请等待接受"
                if locale == "zh" and pending_invites
                else "暂无待接受邀请"
                if locale == "zh"
                else f"{pending_invites} invites awaiting acceptance"
                if pending_invites
                else "No pending invites"
            ),
            tone="primary",
        ),
        PendingAction(
            title="待确认项目" if locale == "zh" else "Projects awaiting confirmation",
            detail=(
                f"{pending_projects} 个项目需要阶段确认"
                if locale == "zh" and pending_projects
                else "暂无待确认项目"
                if locale == "zh"
                else f"{pending_projects} projects need stage confirmation"
                if pending_projects
                else "No projects awaiting confirmation"
            ),
            tone="warning" if pending_projects else "primary",
        ),
    ]

    enrollment_trend = EnrollmentTrend(
        label="新增成员趋势" if locale == "zh" else "Enrollment trend",
        sublabel=(
            "过去 30 天新增成员" if locale == "zh" else "New members over the last 30 days"
        ),
        total=str(enrollment_total),
        change=enrollment_change,
        tone=enrollment_tone,
        series=members_daily_series,
    )

    insight_highlights = [
        InsightHighlight(
            title="导师覆盖" if locale == "zh" else "Mentor coverage",
            detail=mentor_detail,
        ),
        InsightHighlight(
            title="队列参与度" if locale == "zh" else "Cohort participation",
            detail=cohort_detail,
        ),
        InsightHighlight(
            title="报告推进情况" if locale == "zh" else "Reports momentum",
            detail=reports_detail,
        ),
    ]

    return AdminOverviewPayload(
        overview_metrics=overview_metrics,
        enrollment_trend=enrollment_trend,
        cohort_progress=cohort_progress,
        pending_actions=pending_actions,
        upcoming_deadlines=upcoming_deadlines,
        activity_feed=activity_feed,
        insight_highlights=insight_highlights,
    )
