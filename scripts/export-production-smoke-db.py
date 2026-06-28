#!/usr/bin/env python3
"""Export production smoke DB evidence with the app RLS context set."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILES = (REPO_ROOT / "backend" / ".env", REPO_ROOT / ".env")


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _resolve_database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for key in ("DATABASE_URL_ADMIN", "DATABASE_URL"):
        value = os.getenv(key)
        if value:
            return value
    env_values: dict[str, str] = {}
    for path in DEFAULT_ENV_FILES:
        env_values.update(_load_env_file(path))
    for key in ("DATABASE_URL_ADMIN", "DATABASE_URL"):
        value = env_values.get(key)
        if value:
            return value
    raise SystemExit("DATABASE_URL_ADMIN or DATABASE_URL is required.")


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = str(value)
    return " ".join(text.split())


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _serialize_cell(row.get(column)) for column in columns})
    return len(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _fetch_rows(cur: RealDictCursor, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _write_report_v2_export(
    artifact_dir: Path,
    report_rows: list[dict[str, Any]],
) -> int:
    reports: list[dict[str, Any]] = []
    for row in report_rows:
        reports.append(
            {
                "id": row.get("id"),
                "project_id": row.get("project_id"),
                "org_id": row.get("org_id"),
                "report_version": row.get("report_version"),
                "status": row.get("status"),
                "generated_from_state_version": row.get("generated_from_state_version"),
                "artifact_schema_version": row.get("artifact_schema_version"),
                "decision_snapshot": row.get("decision_snapshot_json")
                if isinstance(row.get("decision_snapshot_json"), dict)
                else {},
                "score_rationales": row.get("score_rationales_json")
                if isinstance(row.get("score_rationales_json"), dict)
                else {},
                "risk_register": row.get("risk_register_json")
                if isinstance(row.get("risk_register_json"), list)
                else [],
                "experiment_plan": row.get("experiment_plan_json")
                if isinstance(row.get("experiment_plan_json"), list)
                else [],
                "evidence_index": row.get("evidence_index_json")
                if isinstance(row.get("evidence_index_json"), dict)
                else {},
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )
    _write_json(
        artifact_dir / "db-report-v2.json",
        {
            "artifact_schema_version": "production_report_v2_export_v1",
            "reports": reports,
            "latest_report": reports[0] if reports else None,
        },
    )
    return len(reports)


EXPORTS: list[tuple[str, list[str], str]] = [
    (
        "db-user.csv",
        [
            "id",
            "email",
            "email_verified_at",
            "created_at",
            "updated_at",
            "deleted_at",
        ],
        """
        SELECT id::text, email, email_verified_at, created_at, updated_at, deleted_at
        FROM users
        WHERE id = %s
        """,
    ),
    (
        "db-project.csv",
        [
            "id",
            "org_id",
            "owner_user_id",
            "title",
            "current_stage",
            "current_variant",
            "stage_status",
            "created_at",
            "updated_at",
            "deleted_at",
        ],
        """
        SELECT id::text, org_id::text, owner_user_id::text, title, current_stage,
               current_variant, stage_status, created_at, updated_at, deleted_at
        FROM projects
        WHERE id = %s
        """,
    ),
    (
        "db-runtime.csv",
        [
            "project_id",
            "org_id",
            "stage",
            "variant",
            "current_question_bank_question_id",
            "next_question_bank_question_id",
            "turn_state",
            "missing_paths",
            "runtime_version",
            "created_at",
            "updated_at",
            "deleted_at",
        ],
        """
        SELECT project_id::text, org_id::text, stage, variant,
               current_question_bank_question_id::text,
               next_question_bank_question_id::text,
               turn_state, missing_paths, runtime_version, created_at, updated_at,
               deleted_at
        FROM project_runtime
        WHERE project_id = %s
        ORDER BY updated_at DESC
        """,
    ),
    (
        "db-project-states.csv",
        [
            "project_id",
            "org_id",
            "state_schema_version",
            "state_version",
            "state_keys",
            "state_meta_keys",
            "state_preview",
            "state_meta_preview",
            "created_at",
            "updated_at",
            "deleted_at",
        ],
        """
        SELECT project_id::text, org_id::text, state_schema_version, state_version,
               ARRAY(SELECT jsonb_object_keys(COALESCE(state_json, '{}'::jsonb))) AS state_keys,
               ARRAY(SELECT jsonb_object_keys(COALESCE(state_meta, '{}'::jsonb))) AS state_meta_keys,
               left(COALESCE(state_json, '{}'::jsonb)::text, 2000) AS state_preview,
               left(COALESCE(state_meta, '{}'::jsonb)::text, 2000) AS state_meta_preview,
               created_at, updated_at, deleted_at
        FROM project_states
        WHERE project_id = %s
        ORDER BY updated_at DESC
        """,
    ),
    (
        "db-project-state-events.csv",
        [
            "id",
            "event_type",
            "actor_type",
            "actor_user_id",
            "model_name",
            "prev_state_version",
            "next_state_version",
            "created_at",
        ],
        """
        SELECT id, event_type, actor_type, actor_user_id::text, model_name,
               prev_state_version, next_state_version, created_at
        FROM project_state_events
        WHERE project_id = %s
        ORDER BY created_at ASC
        """,
    ),
    (
        "db-stage-assessments.csv",
        [
            "id",
            "stage",
            "confirmed",
            "generated_from_state_version",
            "generator_model",
            "total_score",
            "confirmed_at",
            "created_at",
            "updated_at",
            "draft_preview",
            "final_preview",
        ],
        """
        SELECT id::text, stage, confirmed, generated_from_state_version,
               generator_model, total_score, confirmed_at, created_at, updated_at,
               left(COALESCE(draft_summary_markdown, ''), 500) AS draft_preview,
               left(COALESCE(final_summary_markdown, ''), 500) AS final_preview
        FROM project_stage_assessments
        WHERE project_id = %s
        ORDER BY CASE stage WHEN 'problem' THEN 1 WHEN 'market' THEN 2
                 WHEN 'tech' THEN 3 ELSE 4 END
        """,
    ),
    (
        "db-background-jobs.csv",
        [
            "id",
            "job_type",
            "status",
            "attempts",
            "max_attempts",
            "priority",
            "run_at",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "last_error",
        ],
        """
        SELECT id, job_type, status, attempts, max_attempts, priority, run_at,
               started_at, completed_at, created_at, updated_at,
               left(COALESCE(last_error, ''), 500) AS last_error
        FROM background_jobs
        WHERE project_id = %s
        ORDER BY created_at ASC, id ASC
        """,
    ),
    (
        "db-report.csv",
        [
            "id",
            "report_version",
            "status",
            "generated_from_state_version",
            "generator_model",
            "confirmed",
            "confirmed_at",
            "created_at",
            "updated_at",
            "content_preview",
        ],
        """
        SELECT id::text, report_version, status, generated_from_state_version,
               generator_model, confirmed, confirmed_at, created_at, updated_at,
               left(COALESCE(content_markdown, ''), 500) AS content_preview
        FROM project_reports
        WHERE project_id = %s
        ORDER BY report_version DESC
        """,
    ),
    (
        "db-conversation-counts.csv",
        ["stage", "role", "message_count", "first_at", "last_at"],
        """
        SELECT stage, role, count(*) AS message_count, min(created_at) AS first_at,
               max(created_at) AS last_at
        FROM conversation_messages
        WHERE project_id = %s
        GROUP BY stage, role
        ORDER BY stage, role
        """,
    ),
    (
        "db-conversation-messages.csv",
        [
            "id",
            "role",
            "stage",
            "variant",
            "client_message_id",
            "request_id",
            "model_name",
            "latency_ms",
            "token_prompt",
            "token_output",
            "created_at",
            "deleted_at",
            "content_preview",
            "meta",
        ],
        """
        SELECT id, role, stage, variant, client_message_id::text, request_id::text,
               model_name, latency_ms, token_prompt, token_output, created_at,
               deleted_at, left(COALESCE(content, ''), 240) AS content_preview,
               meta
        FROM conversation_messages
        WHERE project_id = %s
        ORDER BY created_at ASC, id ASC
        """,
    ),
]


def export_project(project_id: str, artifact_dir: Path, database_url: str) -> None:
    counts: dict[str, int] = {}
    with psycopg2.connect(database_url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, org_id::text, owner_user_id::text, current_stage,
                       current_variant, stage_status
                FROM projects
                WHERE id = %s
                """,
                (project_id,),
            )
            project = cur.fetchone()
            if not project:
                raise SystemExit(f"Project not found: {project_id}")
            org_id = project["org_id"]
            user_id = project["owner_user_id"]
            cur.execute(
                """
                SELECT set_config('app.org_id', %s, true),
                       set_config('app.user_id', %s, true),
                       set_config('app.actor_type', 'user', true)
                """,
                (org_id, user_id),
            )
            cur.execute(
                "SELECT current_database() AS database_name, current_user AS database_user, "
                "inet_server_addr()::text AS server_addr, inet_server_port() AS server_port"
            )
            identity = dict(cur.fetchone())

            for file_name, columns, sql in EXPORTS:
                params = (user_id,) if file_name == "db-user.csv" else (project_id,)
                rows = _fetch_rows(cur, sql, params)
                counts[file_name] = _write_csv(artifact_dir / file_name, columns, rows)

            report_v2_rows = _fetch_rows(
                cur,
                """
                SELECT id::text, project_id::text, org_id::text, report_version,
                       status, generated_from_state_version, artifact_schema_version,
                       decision_snapshot_json, score_rationales_json,
                       risk_register_json, experiment_plan_json, evidence_index_json,
                       created_at, updated_at
                FROM project_reports
                WHERE project_id = %s
                ORDER BY report_version DESC
                """,
                (project_id,),
            )
            counts["db-report-v2.json"] = _write_report_v2_export(
                artifact_dir,
                report_v2_rows,
            )

            identity_payload = {
                **identity,
                "project_id": project_id,
                "org_id": org_id,
                "user_id": user_id,
                "current_stage": project["current_stage"],
                "current_variant": project["current_variant"],
                "stage_status": project["stage_status"],
                "rls_context_set": True,
                "row_counts": counts,
                "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            (artifact_dir / "db-identity.json").write_text(
                json.dumps(identity_payload, ensure_ascii=True, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            conn.rollback()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    export_project(
        project_id=args.project_id,
        artifact_dir=Path(args.artifact_dir),
        database_url=_resolve_database_url(args.database_url),
    )
    print(f"Exported smoke DB evidence for project {args.project_id}.")


if __name__ == "__main__":
    main()
