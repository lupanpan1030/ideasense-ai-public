#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.report_builder import build_assessment_snapshots, build_report_payload  # noqa: E402


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)

SENSITIVE_KEYS = {
    "user_id",
    "owner_user_id",
    "org_id",
    "email",
    "actor_id",
    "invited_by",
    "invited_by_user_id",
}

STAGE_FILTERS = {"problem", "market", "tech", "report"}


def _coerce_async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return f"postgresql+asyncpg://{url[len('postgresql+psycopg2://'):]}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url[len('postgresql://'):]}"
    return url


def resolve_database_url(explicit: str | None) -> str:
    raw = explicit or os.getenv("DATABASE_URL_ADMIN") or os.getenv("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL_ADMIN or DATABASE_URL is required. "
            "You can also pass --database-url."
        )
    return _coerce_async_database_url(raw.strip())


def to_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def redact_text(value: str) -> str:
    value = EMAIL_RE.sub("[redacted-email]", value)
    value = PHONE_RE.sub("[redacted-phone]", value)
    return value


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS or key.lower().endswith("_email"):
                continue
            cleaned[key] = redact_payload(item)
        return cleaned
    return value


def normalize_stage(value: str | None) -> str:
    if not value:
        return "unknown"
    cleaned = value.strip().lower()
    return cleaned if cleaned in STAGE_FILTERS else cleaned or "unknown"


async def build_report(
    conn,
    *,
    project_id: str,
    org_id: str,
    sample_id: str,
    title: str,
    description: str | None,
    stage: str,
) -> dict[str, Any] | None:
    report_result = await conn.execute(
        text(
            "SELECT "
            "p.id, "
            "p.title, "
            "p.description, "
            "p.current_stage, "
            "p.updated_at, "
            "pr.id AS report_id, "
            "pr.content_json, "
            "pr.created_at AS report_created_at "
            "FROM projects p "
            "JOIN project_reports pr "
            "ON pr.project_id = p.id "
            "AND pr.org_id = p.org_id "
            "AND pr.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = :org_id "
            "AND p.deleted_at IS NULL "
            "ORDER BY pr.report_version DESC "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    row = report_result.mappings().first()
    if not row:
        return None

    state_result = await conn.execute(
        text(
            "SELECT state_json, state_meta "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    state_row = state_result.mappings().first()
    state_json = state_row.get("state_json") if state_row else {}
    if not isinstance(state_json, dict):
        state_json = {}
    state_meta = state_row.get("state_meta") if state_row else {}
    if not isinstance(state_meta, dict):
        state_meta = {}

    assessments_result = await conn.execute(
        text(
            "SELECT id, stage, draft_summary_markdown, final_summary_markdown, "
            "confirmed, total_score, confirmed_at, created_at, updated_at "
            "FROM project_stage_assessments "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL"
        ),
        {"project_id": project_id, "org_id": org_id},
    )
    assessment_rows = assessments_result.mappings().all()
    assessments = build_assessment_snapshots(assessment_rows)

    base_payload = build_report_payload(
        row,
        state_json,
        assessments,
        generated_at=row.get("report_created_at"),
        ai_assisted_paths=_normalize_stage_path_map(state_meta, "ai_assisted_paths"),
        user_edited_paths=_normalize_stage_path_map(state_meta, "user_edited_paths"),
    )

    content_json = row.get("content_json")
    if isinstance(content_json, dict):
        payload: dict[str, Any] = {**base_payload, **content_json}
        payload.setdefault("project_id", base_payload.get("project_id"))
        payload.setdefault("generated_at", base_payload.get("generated_at"))
        payload.setdefault("project", base_payload.get("project"))
        payload.setdefault("assessments", base_payload.get("assessments"))
        payload.setdefault("lean_canvas", base_payload.get("lean_canvas"))
        payload.setdefault("dvf_scoreboard", base_payload.get("dvf_scoreboard"))
        payload.setdefault("market_evidence", base_payload.get("market_evidence"))
    else:
        payload = base_payload

    payload["project_id"] = sample_id
    if isinstance(payload.get("project"), dict):
        payload["project"]["id"] = sample_id
        payload["project"]["title"] = title
        payload["project"]["description"] = description
        payload["project"]["current_stage"] = stage

    return payload


def _normalize_stage_path_map(state_meta: dict[str, Any], key: str) -> dict[str, list[str]]:
    if not isinstance(state_meta, dict):
        return {}
    raw = state_meta.get(key)
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for stage, paths in raw.items():
        if not isinstance(stage, str) or not isinstance(paths, list):
            continue
        stage_key = stage.strip().lower()
        if not stage_key:
            continue
        cleaned = [path for path in paths if isinstance(path, str) and path.strip()]
        if cleaned:
            normalized[stage_key] = cleaned
    return normalized


async def import_sample(
    *,
    project_id: str,
    sample_id: str | None,
    title_override: str | None,
    description_override: str | None,
    stage_override: str | None,
    database_url: str | None,
    dry_run: bool,
) -> None:
    engine = create_async_engine(resolve_database_url(database_url))
    async with engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.actor_type', 'system', true)")
        )
        project_result = await conn.execute(
            text(
                "SELECT id, org_id, owner_user_id, title, description, "
                "current_stage, updated_at "
                "FROM projects "
                "WHERE id = :project_id "
                "AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"project_id": project_id},
        )
        project = project_result.mappings().first()
        if not project:
            raise RuntimeError("Project not found.")

        source_project_id = str(project.get("id"))
        org_id = str(project.get("org_id"))
        owner_user_id = project.get("owner_user_id")

        existing = await conn.execute(
            text(
                "SELECT id FROM sample_projects "
                "WHERE source_project_id = :source_project_id"
            ),
            {"source_project_id": source_project_id},
        )
        existing_row = existing.mappings().first()
        resolved_sample_id = (
            str(existing_row.get("id"))
            if existing_row
            else (sample_id or str(uuid4()))
        )

        title = title_override or (project.get("title") or "Untitled sample")
        description = description_override or project.get("description")
        stage = normalize_stage(stage_override or project.get("current_stage"))
        project_updated_at = project.get("updated_at")

        await conn.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": org_id},
        )
        # conversation_messages and project_reports enforce FORCE row-level
        # security via can_view_project*(), which require a user context.
        # A 'system' actor with only org_id set reads back empty, so snapshot
        # as the project owner. sample_projects has no RLS, so this user
        # context does not affect the write below.
        if owner_user_id:
            await conn.execute(
                text("SELECT set_config('app.user_id', :user_id, true)"),
                {"user_id": str(owner_user_id)},
            )

        messages_result = await conn.execute(
            text(
                "SELECT id, role, content, created_at, stage, meta "
                "FROM conversation_messages "
                "WHERE project_id = :project_id "
                "AND org_id = :org_id "
                "AND deleted_at IS NULL "
                "AND is_visible "
                "ORDER BY created_at ASC, id ASC"
            ),
            {"project_id": source_project_id, "org_id": org_id},
        )
        messages: list[dict[str, Any]] = []
        for idx, row in enumerate(messages_result.mappings().all(), start=1):
            meta = row.get("meta")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = None
            payload = {
                "id": f"sample-{idx}",
                "role": row.get("role") or "assistant",
                "content": row.get("content") or "",
                "created_at": to_iso(row.get("created_at")),
                "stage": row.get("stage"),
                "meta": meta if isinstance(meta, dict) else None,
            }
            messages.append(payload)

        report_payload = await build_report(
            conn,
            project_id=source_project_id,
            org_id=org_id,
            sample_id=resolved_sample_id,
            title=title,
            description=description,
            stage=stage,
        )

        messages = redact_payload(messages)
        report_payload = redact_payload(report_payload) if report_payload else None
        title = redact_text(title)
        description = redact_text(description) if description else None

        if dry_run:
            print(
                json.dumps(
                    {
                        "sample_id": resolved_sample_id,
                        "source_project_id": source_project_id,
                        "title": title,
                        "description": description,
                        "stage": stage,
                        "project_updated_at": to_iso(project_updated_at),
                        "messages": messages,
                        "report": report_payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        result = await conn.execute(
            text(
                "INSERT INTO sample_projects "
                "(id, source_project_id, title, description, stage, "
                "project_updated_at, messages, report) "
                "VALUES (:id, :source_project_id, :title, :description, :stage, "
                ":project_updated_at, CAST(:messages AS jsonb), "
                "CAST(:report AS jsonb)) "
                "ON CONFLICT (source_project_id) "
                "WHERE source_project_id IS NOT NULL DO UPDATE SET "
                "title = EXCLUDED.title, "
                "description = EXCLUDED.description, "
                "stage = EXCLUDED.stage, "
                "project_updated_at = EXCLUDED.project_updated_at, "
                "messages = EXCLUDED.messages, "
                "report = EXCLUDED.report "
                "RETURNING id"
            ),
            {
                "id": resolved_sample_id,
                "source_project_id": source_project_id,
                "title": title,
                "description": description,
                "stage": stage,
                "project_updated_at": project_updated_at,
                "messages": json.dumps(messages),
                "report": json.dumps(report_payload) if report_payload else None,
            },
        )
        saved_id = result.scalar() or resolved_sample_id
        print(f"Sample project saved: {saved_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a project as sample data.")
    parser.add_argument("--project-id", required=True, help="Source project UUID.")
    parser.add_argument("--sample-id", help="Optional sample UUID to use.")
    parser.add_argument("--title", help="Override title for the sample.")
    parser.add_argument("--description", help="Override description for the sample.")
    parser.add_argument(
        "--stage",
        help="Override stage (problem, market, tech, report).",
    )
    parser.add_argument(
        "--database-url",
        help="Override database URL (defaults to DATABASE_URL_ADMIN).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print payload only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        import_sample(
            project_id=args.project_id,
            sample_id=args.sample_id,
            title_override=args.title,
            description_override=args.description,
            stage_override=args.stage,
            database_url=args.database_url,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
