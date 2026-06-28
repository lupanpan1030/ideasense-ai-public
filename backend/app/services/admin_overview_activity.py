from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_overview_formatters import (
    _report_status_label,
    _role_label,
)
from app.services.localization import OutputLocale


@dataclass(frozen=True)
class ActivityItem:
    title: str
    detail: str
    created_at: datetime


async def build_admin_overview_activity_feed(
    session: AsyncSession, locale: OutputLocale
) -> list[ActivityItem]:
    activity: list[dict] = []

    invite_rows = await session.execute(
        text(
            "SELECT invitee_email, invited_role, created_at "
            "FROM organization_invitations "
            "WHERE org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 5"
        )
    )
    for row in invite_rows.mappings().all():
        activity.append(
            {
                "title": (
                    f"邀请已发送给 {row.get('invitee_email')}"
                    if locale == "zh"
                    else f"Invite sent to {row.get('invitee_email')}"
                ),
                "detail": (
                    f"角色：{_role_label(row.get('invited_role'), locale)}"
                    if locale == "zh"
                    else f"Role: {_role_label(row.get('invited_role'), locale)}"
                ),
                "created_at": row.get("created_at"),
            }
        )

    member_rows = await session.execute(
        text(
            "SELECT om.created_at, om.org_role, u.display_name, u.email "
            "FROM organization_memberships om "
            "JOIN users u ON u.id = om.user_id "
            "WHERE om.org_id = app_org_id() "
            "AND om.deleted_at IS NULL "
            "ORDER BY om.created_at DESC "
            "LIMIT 5"
        )
    )
    for row in member_rows.mappings().all():
        display = row.get("display_name") or row.get("email") or (
            "成员" if locale == "zh" else "Member"
        )
        activity.append(
            {
                "title": (
                    f"{display} 已加入组织"
                    if locale == "zh"
                    else f"{display} joined the organization"
                ),
                "detail": (
                    f"角色：{_role_label(row.get('org_role'), locale)}"
                    if locale == "zh"
                    else f"Role: {_role_label(row.get('org_role'), locale)}"
                ),
                "created_at": row.get("created_at"),
            }
        )

    cohort_rows = await session.execute(
        text(
            "SELECT name, created_at "
            "FROM cohorts "
            "WHERE org_id = app_org_id() "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 5"
        )
    )
    for row in cohort_rows.mappings().all():
        activity.append(
            {
                "title": (
                    f"已创建队列 {row.get('name')}"
                    if locale == "zh"
                    else f"Cohort {row.get('name')} created"
                ),
                "detail": "",
                "created_at": row.get("created_at"),
            }
        )

    project_rows = await session.execute(
        text(
            "SELECT p.title, p.created_at, u.display_name, u.email "
            "FROM projects p "
            "JOIN users u ON u.id = p.owner_user_id "
            "WHERE p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "ORDER BY p.created_at DESC "
            "LIMIT 5"
        )
    )
    for row in project_rows.mappings().all():
        owner = row.get("display_name") or row.get("email") or (
            "所有者" if locale == "zh" else "Owner"
        )
        activity.append(
            {
                "title": (
                    f"已创建项目 {row.get('title')}"
                    if locale == "zh"
                    else f"Project {row.get('title')} created"
                ),
                "detail": (
                    f"负责人：{owner}" if locale == "zh" else f"Owner: {owner}"
                ),
                "created_at": row.get("created_at"),
            }
        )

    report_rows = await session.execute(
        text(
            "SELECT pr.confirmed, pr.status, pr.created_at, pr.confirmed_at, p.title "
            "FROM project_reports pr "
            "JOIN projects p ON p.id = pr.project_id "
            "WHERE pr.org_id = app_org_id() "
            "AND pr.deleted_at IS NULL "
            "ORDER BY pr.created_at DESC "
            "LIMIT 5"
        )
    )
    for row in report_rows.mappings().all():
        confirmed = row.get("confirmed")
        created_at = row.get("confirmed_at") if confirmed else row.get("created_at")
        title = row.get("title") or ("项目" if locale == "zh" else "Project")
        activity.append(
            {
                "title": (
                    f"{title} 的报告已确认"
                    if locale == "zh" and confirmed
                    else f"{title} 的报告已生成"
                    if locale == "zh"
                    else f"Report confirmed for {title}"
                    if confirmed
                    else f"Report generated for {title}"
                ),
                "detail": (
                    f"状态：{_report_status_label(row.get('status'), locale)}"
                    if locale == "zh"
                    else f"Status: {_report_status_label(row.get('status'), locale)}"
                ),
                "created_at": created_at,
            }
        )

    assignment_rows = await session.execute(
        text(
            "SELECT msa.created_at, "
            "mentor.display_name AS mentor_name, mentor.email AS mentor_email, "
            "student.display_name AS student_name, student.email AS student_email "
            "FROM mentor_student_assignments msa "
            "JOIN users mentor ON mentor.id = msa.mentor_user_id "
            "JOIN users student ON student.id = msa.student_user_id "
            "WHERE msa.org_id = app_org_id() "
            "AND msa.deleted_at IS NULL "
            "ORDER BY msa.created_at DESC "
            "LIMIT 5"
        )
    )
    for row in assignment_rows.mappings().all():
        mentor = row.get("mentor_name") or row.get("mentor_email") or (
            "导师" if locale == "zh" else "Mentor"
        )
        student = row.get("student_name") or row.get("student_email") or (
            "学员" if locale == "zh" else "Student"
        )
        activity.append(
            {
                "title": (
                    "已创建导师分配"
                    if locale == "zh"
                    else "Mentor assignment created"
                ),
                "detail": f"{mentor} -> {student}",
                "created_at": row.get("created_at"),
            }
        )

    activity = [item for item in activity if item.get("created_at")]
    activity.sort(key=lambda item: item["created_at"], reverse=True)
    return [ActivityItem(**item) for item in activity[:6]]
