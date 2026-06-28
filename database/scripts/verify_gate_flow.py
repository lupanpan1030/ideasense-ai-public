#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request

import psycopg2

from db_context import set_system_actor

API_BASE_URL = os.getenv("IDEASENSE_API_BASE_URL", "http://localhost:8000/api/v1")
API_TOKEN = os.getenv("IDEASENSE_API_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL_ADMIN") or os.getenv("DATABASE_URL")
BAD_ANSWER = os.getenv("IDEASENSE_BAD_ANSWER", "I don't know.")
GOOD_ANSWER = os.getenv(
    "IDEASENSE_GOOD_ANSWER",
    "We are building a web app that lets university founders run structured "
    "customer interviews. It records interview notes, tags pain points, and "
    "summarizes patterns to guide an MVP. This is a high-level description only; "
    "no user segment details.",
)


def _request_json(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise SystemExit(
            f"HTTP {exc.code} {method} {path}: {error_body}"
        ) from exc
    if not body:
        return {}
    return json.loads(body)


def _stream_chat(project_id: str, message: str) -> str:
    url = f"{API_BASE_URL}/chat/stream"
    payload = json.dumps({"project_id": project_id, "message": message}).encode(
        "utf-8"
    )
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    try:
        with urllib.request.urlopen(req) as resp:
            assistant_text = ""
            event = None
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event = line.split("event:", 1)[1].strip()
                    continue
                if not line.startswith("data:") or not event:
                    continue
                data = json.loads(line.split("data:", 1)[1].strip())
                if event == "token":
                    assistant_text += data.get("delta", "")
                elif event == "done":
                    break
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise SystemExit(
            f"HTTP {exc.code} POST /chat/stream: {error_body}"
        ) from exc
    return assistant_text


def _fetch_runtime_snapshot(conn, project_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT current_question_bank_question_id,
                   next_question_bank_question_id,
                   runtime_version,
                   turn_state
              FROM project_runtime
             WHERE project_id = %s
               AND deleted_at IS NULL
             LIMIT 1
            """,
            (project_id,),
        )
        row = cur.fetchone()
    if not row:
        raise SystemExit("Runtime not found.")
    return {
        "current_question_id": row[0],
        "next_question_id": row[1],
        "runtime_version": row[2],
        "turn_state": row[3],
    }


def _fetch_instance_status(conn, project_id: str, question_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, validation_status
              FROM project_question_instances
             WHERE project_id = %s
               AND question_bank_question_id = %s
               AND deleted_at IS NULL
             LIMIT 1
            """,
            (project_id, question_id),
        )
        row = cur.fetchone()
    if not row:
        raise SystemExit("Question instance not found.")
    return {"status": row[0], "validation_status": row[1]}


def _count_background_jobs(conn, project_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
              FROM background_jobs
             WHERE project_id = %s
               AND job_type = 'extract_answer_v0'
               AND deleted_at IS NULL
            """,
            (project_id,),
        )
        row = cur.fetchone()
    return row[0] if row else 0


def _require(value: str | None, label: str) -> str:
    if not value:
        raise SystemExit(f"{label} is required.")
    return value


def main() -> None:
    dsn = _require(DATABASE_URL, "DATABASE_URL_ADMIN or DATABASE_URL")

    created = _request_json(
        "POST",
        "/projects",
        {"title": "Gate Flow Validation"},
    )
    project = created.get("project") or {}
    project_id = _require(project.get("id"), "project.id")

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        set_system_actor(conn)
        initial = _fetch_runtime_snapshot(conn, project_id)
        initial_jobs = _count_background_jobs(conn, project_id)

    _stream_chat(project_id, BAD_ANSWER)

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        set_system_actor(conn)
        after_bad = _fetch_runtime_snapshot(conn, project_id)
        if after_bad["current_question_id"] != initial["current_question_id"]:
            raise SystemExit("Bad answer advanced the runtime unexpectedly.")
        if after_bad["runtime_version"] != initial["runtime_version"]:
            raise SystemExit("Bad answer changed runtime_version unexpectedly.")
        if after_bad["turn_state"] != "needs_info":
            raise SystemExit("Bad answer did not set turn_state=needs_info.")

        status = _fetch_instance_status(
            conn, project_id, str(initial["current_question_id"])
        )
        if status["status"] != "needs_info":
            raise SystemExit("Bad answer did not set status=needs_info.")
        if status["validation_status"] != "needs_info":
            raise SystemExit("Bad answer did not set validation_status=needs_info.")

        jobs_after_bad = _count_background_jobs(conn, project_id)
        if jobs_after_bad != initial_jobs:
            raise SystemExit("Bad answer enqueued background jobs unexpectedly.")

    _stream_chat(project_id, GOOD_ANSWER)

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        set_system_actor(conn)
        after_good = _fetch_runtime_snapshot(conn, project_id)
        if after_good["current_question_id"] == initial["current_question_id"]:
            raise SystemExit("Good answer did not advance the runtime.")
        if after_good["runtime_version"] <= initial["runtime_version"]:
            raise SystemExit("Good answer did not increment runtime_version.")
        if after_good["turn_state"] != "updated":
            raise SystemExit("Good answer did not set turn_state=updated.")

    print("Gate flow validation complete.")


if __name__ == "__main__":
    main()
