#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import psycopg2


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATHS = (
    BASE_DIR.parent / "backend" / ".env",
    BASE_DIR.parent / ".env",
)

API_BASE_URL = None
API_TOKEN = None
DATABASE_URL = None
ROUTER_ANSWER = None


def _log_api(method: str, path: str, status: int) -> None:
    print(f"[API] {method} {path} -> {status}")


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _request_json(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    try:
        with urllib.request.urlopen(req) as resp:
            _log_api(method, path, resp.status)
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise SystemExit(
            f"HTTP {exc.code} {method} {path}: {error_body}"
        ) from exc
    if not body:
        return {}
    return json.loads(body)


def _set_actor_context(cur, user_id: str, org_id: str, actor_type: str) -> None:
    cur.execute("SELECT set_config('app.user_id', %s, false)", (user_id,))
    cur.execute("SELECT set_config('app.org_id', %s, false)", (org_id,))
    cur.execute("SELECT set_config('app.actor_type', %s, false)", (actor_type,))


def _stream_chat(project_id: str, message: str) -> tuple[str, dict | None]:
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
            _log_api("POST", "/chat/stream", resp.status)
            event = None
            assistant_text = ""
            stage_gate = None
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
                elif event == "stage_gate_ready":
                    stage_gate = data
                elif event == "done":
                    break
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise SystemExit(
            f"HTTP {exc.code} POST /chat/stream: {error_body}"
        ) from exc
    return assistant_text, stage_gate


def _set_stage_status(
    conn,
    project_id: str,
    org_id: str,
    user_id: str,
    stage_status: str,
) -> None:
    with conn.cursor() as cur:
        _set_actor_context(cur, user_id, org_id, "user")
        cur.execute(
            """
            UPDATE projects
               SET stage_status = %s
             WHERE id = %s
               AND org_id = %s
               AND deleted_at IS NULL
            """,
            (stage_status, project_id, org_id),
        )
        if cur.rowcount == 0:
            raise SystemExit(
                "Failed to update stage_status; check DATABASE_URL_ADMIN "
                "matches the API database and RLS context."
            )


def _fetch_runtime_question_id(
    conn, project_id: str, org_id: str, user_id: str
) -> str | None:
    with conn.cursor() as cur:
        _set_actor_context(cur, user_id, org_id, "user")
        cur.execute(
            """
            SELECT current_question_bank_question_id
              FROM project_runtime
             WHERE project_id = %s
               AND deleted_at IS NULL
             LIMIT 1
            """,
            (project_id,),
        )
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def _fetch_question_code(
    conn, question_id: str, org_id: str, user_id: str
) -> str | None:
    with conn.cursor() as cur:
        _set_actor_context(cur, user_id, org_id, "user")
        cur.execute(
            """
            SELECT question_id
              FROM question_bank_questions
             WHERE id = %s
               AND deleted_at IS NULL
             LIMIT 1
            """,
            (question_id,),
        )
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def _format_question_id(
    conn, question_id: str | None, org_id: str, user_id: str
) -> str:
    if not question_id:
        return "None"
    code = _fetch_question_code(conn, question_id, org_id, user_id)
    if code:
        return f"{question_id} ({code})"
    return str(question_id)


def _log_project_state(
    label: str,
    project: dict,
    runtime: dict,
    dsn: str,
    org_id: str,
    user_id: str,
) -> None:
    stage = project.get("current_stage")
    variant = project.get("current_variant")
    current_q = runtime.get("current_question_bank_question_id")
    next_q = runtime.get("next_question_bank_question_id")
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        current_display = _format_question_id(conn, current_q, org_id, user_id)
        next_display = _format_question_id(conn, next_q, org_id, user_id)
    print(
        "[STATE] "
        f"{label}: stage={stage} variant={variant} "
        f"current_question_id={current_display} "
        f"next_question_id={next_display}"
    )


def _require(value: str | None, label: str) -> str:
    if not value:
        raise SystemExit(f"{label} is required.")
    return value


def _coerce_psycopg2_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg2://"):
        return f"postgresql://{dsn[len('postgresql+psycopg2://'):]}"
    if dsn.startswith("postgresql+asyncpg://"):
        return f"postgresql://{dsn[len('postgresql+asyncpg://'):]}"
    return dsn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args()

    if args.env_file:
        load_env_file(Path(args.env_file))
    else:
        for env_path in DEFAULT_ENV_PATHS:
            if env_path.exists():
                load_env_file(env_path)
                break

    global API_BASE_URL, API_TOKEN, DATABASE_URL, ROUTER_ANSWER
    API_BASE_URL = os.getenv(
        "IDEASENSE_API_BASE_URL", "http://localhost:8000/api/v1"
    )
    API_TOKEN = os.getenv("IDEASENSE_API_TOKEN", "").strip()
    DATABASE_URL = os.getenv("DATABASE_URL_ADMIN") or os.getenv("DATABASE_URL")
    ROUTER_ANSWER = os.getenv(
        "IDEASENSE_ROUTER_ANSWER",
        "I'm non-technical and prefer simple, fast explanations.",
    )

    dsn = _require(DATABASE_URL, "DATABASE_URL_ADMIN or DATABASE_URL")
    dsn = _coerce_psycopg2_dsn(dsn)

    created = _request_json(
        "POST",
        "/projects",
        {"title": "Stage Flow Validation"},
    )
    project = created.get("project") or {}
    runtime = created.get("runtime") or {}
    project_id = _require(project.get("id"), "project.id")
    org_id = _require(project.get("org_id"), "project.org_id")
    user_id = _require(project.get("owner_user_id"), "project.owner_user_id")
    _log_project_state("project_created", project, runtime, dsn, org_id, user_id)

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        _set_stage_status(conn, project_id, org_id, user_id, "awaiting_confirm")

    _request_json("POST", "/assessments/problem/confirm", {"project_id": project_id})
    detail = _request_json("GET", f"/projects/{project_id}")
    if (detail.get("project") or {}).get("current_stage") != "market":
        raise SystemExit("Expected stage to be market after problem confirm.")
    _log_project_state(
        "after_problem_confirm",
        detail.get("project") or {},
        detail.get("runtime") or {},
        dsn,
        org_id,
        user_id,
    )

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        _set_stage_status(conn, project_id, org_id, user_id, "awaiting_confirm")

    _request_json("POST", "/assessments/market/confirm", {"project_id": project_id})
    detail = _request_json("GET", f"/projects/{project_id}")
    project = detail.get("project") or {}
    runtime = detail.get("runtime") or {}
    if project.get("current_stage") != "tech":
        raise SystemExit("Expected stage to be tech after market confirm.")
    if project.get("current_variant") != "router":
        raise SystemExit("Expected variant to be router after market confirm.")
    _log_project_state(
        "after_market_confirm",
        project,
        runtime,
        dsn,
        org_id,
        user_id,
    )

    runtime_question = _require(
        runtime.get("current_question_bank_question_id"),
        "runtime.current_question_bank_question_id",
    )
    with psycopg2.connect(dsn) as conn:
        question_id = _fetch_question_code(
            conn, runtime_question, org_id, user_id
        )
    if question_id != "S3Q0":
        raise SystemExit(f"Expected router question S3Q0, got {question_id}.")

    assistant_text, stage_gate_ready = _stream_chat(project_id, ROUTER_ANSWER)
    if stage_gate_ready:
        raise SystemExit("Unexpected stage gate ready after router answer.")
    if not assistant_text:
        raise SystemExit("Expected assistant to return first pro/lite question.")

    detail = _request_json("GET", f"/projects/{project_id}")
    project = detail.get("project") or {}
    runtime = detail.get("runtime") or {}
    mode = project.get("current_variant")
    if mode not in {"pro", "lite"}:
        raise SystemExit(f"Expected variant to switch to pro/lite, got {mode}.")
    _log_project_state(
        "after_router_answer",
        project,
        runtime,
        dsn,
        org_id,
        user_id,
    )
    expected_question = "S3Q1" if mode == "pro" else "L3Q1"
    runtime_question = _require(
        runtime.get("current_question_bank_question_id"),
        "runtime.current_question_bank_question_id",
    )
    with psycopg2.connect(dsn) as conn:
        question_id = _fetch_question_code(
            conn, runtime_question, org_id, user_id
        )
    if question_id != expected_question:
        raise SystemExit(
            f"Expected {expected_question} after router, got {question_id}."
        )

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        _set_stage_status(conn, project_id, org_id, user_id, "awaiting_confirm")

    _request_json("POST", "/assessments/tech/confirm", {"project_id": project_id})
    detail = _request_json("GET", f"/projects/{project_id}")
    project = detail.get("project") or {}
    if project.get("current_stage") != "report":
        raise SystemExit("Expected stage to be report after tech confirm.")
    if project.get("current_variant") != "default":
        raise SystemExit("Expected variant default after tech confirm.")
    _log_project_state(
        "after_tech_confirm",
        project,
        detail.get("runtime") or {},
        dsn,
        org_id,
        user_id,
    )

    print("Stage flow validation complete.")


if __name__ == "__main__":
    main()
