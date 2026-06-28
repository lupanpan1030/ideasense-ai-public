#!/usr/bin/env python3
"""Bootstrap the database: create DB, run migrations, apply roles, import question bank."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2 import errors, sql
from psycopg2.extensions import (
    ISOLATION_LEVEL_AUTOCOMMIT,
    parse_dsn,
)


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
RLS_ROLES_PATH = BASE_DIR / "roles" / "rls_roles.sql"
IMPORT_QB_PATH = BASE_DIR / "scripts" / "import_question_bank.py"
SCHEMA_SNAPSHOT_PATH = BASE_DIR / "scripts" / "generate_schema_snapshot.py"
PRIVATE_QUESTION_BANK_DIR = Path("resources") / "question_bank"
PUBLIC_QUESTION_BANK_EXAMPLE_PATH = "resources/question_bank.example.yaml"
DEFAULT_ENV_PATHS = (
    REPO_ROOT / "backend" / ".env",
    REPO_ROOT / ".env",
)
QUESTION_BANK_TABLES = (
    "question_bank_versions",
    "question_bank_stage_variants",
    "question_bank_questions",
)
LOCAL_DB_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
PRODUCTION_DB_NAME_MARKERS = ("prod", "production")
REMOTE_DB_ALLOW_ENV = "IDEASENSE_ALLOW_REMOTE_DB_MUTATION"
PRODUCTION_DB_ALLOW_ENV = "IDEASENSE_ALLOW_PRODUCTION_DB_MUTATION"


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def default_question_bank_yaml(repo_root: Path = REPO_ROOT) -> str:
    private_dir = repo_root / PRIVATE_QUESTION_BANK_DIR
    private_candidates = sorted(private_dir.glob("*.yaml")) if private_dir.exists() else []
    for candidate in private_candidates:
        name = candidate.name.lower()
        if "final" in name and "lite" not in name:
            return str(candidate.relative_to(repo_root))
    if private_candidates:
        return str(private_candidates[0].relative_to(repo_root))
    public_example_path = repo_root / PUBLIC_QUESTION_BANK_EXAMPLE_PATH
    if public_example_path.exists():
        return PUBLIC_QUESTION_BANK_EXAMPLE_PATH
    return PUBLIC_QUESTION_BANK_EXAMPLE_PATH


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


def parse_admin_dsn(dsn: str) -> dict:
    if "://" in dsn:
        parsed = urlparse(dsn)
        return {
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "host": parsed.hostname or "",
            "port": str(parsed.port) if parsed.port else "",
            "dbname": parsed.path.lstrip("/") or "",
        }
    return parse_dsn(dsn)


def _db_host(params: dict) -> str:
    return str(params.get("host") or params.get("hostaddr") or "")


def _is_local_db_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized.startswith("/"):
        return True
    return normalized in LOCAL_DB_HOSTS


def _production_target_detected(params: dict, db_name: str) -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env == "production":
        return True
    normalized_db_name = db_name.strip().lower()
    db_name_parts = re.split(r"[^a-z0-9]+", normalized_db_name)
    return any(marker in db_name_parts for marker in PRODUCTION_DB_NAME_MARKERS)


def assert_safe_database_target(
    params: dict,
    db_name: str,
    *,
    script_name: str,
    destructive: bool = False,
    allow_remote: bool = False,
    allow_production: bool = False,
) -> None:
    """Fail closed for scripts that mutate or destroy database state."""
    host = _db_host(params)
    host_display = host or "local socket/default host"
    problems = []

    if not _is_local_db_host(host) and not allow_remote:
        problems.append(
            "remote database host detected "
            f"({host_display}); pass --allow-remote-db or set "
            f"{REMOTE_DB_ALLOW_ENV}=1"
        )

    if _production_target_detected(params, db_name) and not allow_production:
        problems.append(
            "production environment or production-like database name detected; "
            f"pass --allow-production-db or set {PRODUCTION_DB_ALLOW_ENV}=1"
        )

    if problems:
        action = "destructive" if destructive else "mutating"
        raise SystemExit(
            f"Refusing to run {action} database script {script_name} for "
            f"database {db_name!r} on {host_display}: " + "; ".join(problems)
        )


def build_dsn(params: dict) -> str:
    return " ".join(
        f"{key}={value}"
        for key, value in params.items()
        if value is not None and value != ""
    )


def ensure_database(admin_dsn: str, db_name: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
            )
            if cur.fetchone():
                print(f"Database {db_name} already exists.")
                return
            cur.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            print(f"Created database {db_name}.")
    finally:
        conn.close()


def ensure_schema_migrations(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, "
            "applied_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
    conn.commit()


def _fetch_applied_migrations(
    conn: psycopg2.extensions.connection,
) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM schema_migrations")
        rows = cur.fetchall()
    return {row[0] for row in rows}


def _has_public_tables(conn: psycopg2.extensions.connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name <> 'schema_migrations'"
            ")"
        )
        return bool(cur.fetchone()[0])


def run_migrations(dsn: str, *, mark_existing: bool = False) -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with psycopg2.connect(dsn) as conn:
        ensure_schema_migrations(conn)
        applied = _fetch_applied_migrations(conn)

        if mark_existing:
            if not _has_public_tables(conn):
                raise RuntimeError(
                    "No existing tables found; refusing to mark migrations. "
                    "Run without --mark-existing to apply migrations."
                )
            with conn.cursor() as cur:
                for path in migration_files:
                    if path.name in applied:
                        continue
                    cur.execute(
                        "INSERT INTO schema_migrations (name) "
                        "VALUES (%s) "
                        "ON CONFLICT DO NOTHING",
                        (path.name,),
                    )
            conn.commit()
            print(f"Marked {len(migration_files)} migrations as applied.")
            return

        if not applied and _has_public_tables(conn):
            raise RuntimeError(
                "Database already has tables but schema_migrations is empty. "
                "Re-run with --mark-existing to sync migrations."
            )

        with conn.cursor() as cur:
            for path in migration_files:
                if path.name in applied:
                    print(f"Skipping {path.name} (already applied)")
                    continue
                sql_text = path.read_text()
                try:
                    cur.execute(sql_text)
                    cur.execute(
                        "INSERT INTO schema_migrations (name) VALUES (%s)",
                        (path.name,),
                    )
                    conn.commit()
                    applied.add(path.name)
                    print(f"Applied {path.name}")
                except Exception:
                    conn.rollback()
                    raise


def apply_rls_roles(dsn: str, db_name: str) -> None:
    sql_text = RLS_ROLES_PATH.read_text().replace("your_db_name", db_name)
    statements = [stmt.strip() for stmt in sql_text.split(";") if stmt.strip()]
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for stmt in statements:
                try:
                    cur.execute(stmt)
                except errors.DuplicateObject:
                    conn.rollback()
                    continue
                except Exception as exc:
                    conn.rollback()
                    raise RuntimeError(
                        f"Failed to apply roles statement: {stmt}"
                    ) from exc


def set_question_bank_force_rls(dsn: str, force: bool) -> None:
    action = "FORCE" if force else "NO FORCE"
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for table in QUESTION_BANK_TABLES:
                cur.execute(
                    sql.SQL("ALTER TABLE {} {} ROW LEVEL SECURITY").format(
                        sql.Identifier(table),
                        sql.SQL(action),
                    )
                )


def import_question_bank(
    dsn: str, yaml_path: str, relax_rls: bool = False
) -> None:
    if relax_rls:
        print("Temporarily disabling FORCE RLS on question bank tables.")
        set_question_bank_force_rls(dsn, force=False)
    try:
        subprocess.run(
            [
                sys.executable,
                str(IMPORT_QB_PATH),
                "--dsn",
                dsn,
                "--yaml",
                yaml_path,
            ],
            check=True,
        )
    finally:
        if relax_rls:
            print("Re-enabling FORCE RLS on question bank tables.")
            set_question_bank_force_rls(dsn, force=True)


def generate_schema_snapshot() -> None:
    subprocess.run(
        [sys.executable, str(SCHEMA_SNAPSHOT_PATH)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    managed_default = os.getenv("MANAGED_DB", "").lower() in (
        "1",
        "true",
        "yes",
    )
    parser.add_argument("--db-name", default="ideasense_ai_dev")
    parser.add_argument("--admin-dsn", default=os.getenv("DATABASE_URL_ADMIN"))
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--skip-roles", action="store_true")
    parser.add_argument("--skip-migrations", action="store_true")
    parser.add_argument("--skip-question-bank", action="store_true")
    parser.add_argument("--skip-schema", action="store_true")
    parser.add_argument(
        "--mark-existing",
        action="store_true",
        help="Mark all migrations as applied without executing them. "
        "Use when the database already has the schema.",
    )
    parser.add_argument(
        "--managed-db",
        action="store_true",
        default=managed_default,
        help="Skip role grants and relax FORCE RLS for question bank imports.",
    )
    parser.add_argument(
        "--allow-remote-db",
        action="store_true",
        default=_env_flag_enabled(REMOTE_DB_ALLOW_ENV),
        help="Allow this mutating script to target a non-local database host.",
    )
    parser.add_argument(
        "--allow-production-db",
        action="store_true",
        default=_env_flag_enabled(PRODUCTION_DB_ALLOW_ENV),
        help="Allow this mutating script in APP_ENV=production or against a production-like database name.",
    )
    parser.add_argument(
        "--question-bank-yaml",
        default=default_question_bank_yaml(),
    )
    args = parser.parse_args()

    if args.env_file and not args.admin_dsn:
        load_env_file(Path(args.env_file))
        args.admin_dsn = os.getenv("DATABASE_URL_ADMIN")

    if not args.admin_dsn:
        for env_path in DEFAULT_ENV_PATHS:
            if env_path.exists():
                load_env_file(env_path)
                args.admin_dsn = os.getenv("DATABASE_URL_ADMIN")
                if args.admin_dsn:
                    break

    if not args.admin_dsn:
        raise SystemExit("DATABASE_URL_ADMIN or --admin-dsn is required")

    db_name_explicit = "--db-name" in sys.argv
    admin_params = parse_admin_dsn(args.admin_dsn)
    if not db_name_explicit:
        admin_dbname = admin_params.get("dbname")
        if admin_dbname and admin_dbname not in ("postgres", "template1"):
            args.db_name = admin_dbname
    assert_safe_database_target(
        admin_params,
        args.db_name,
        script_name=Path(__file__).name,
        allow_remote=args.allow_remote_db,
        allow_production=args.allow_production_db,
    )
    target_params = dict(admin_params)
    target_params["dbname"] = args.db_name
    target_dsn = build_dsn(target_params)

    ensure_database(args.admin_dsn, args.db_name)

    if not args.skip_migrations:
        run_migrations(target_dsn, mark_existing=args.mark_existing)

    if args.managed_db and not args.skip_roles:
        print("Managed DB detected: skipping role grants.")
        args.skip_roles = True

    if not args.skip_roles:
        apply_rls_roles(target_dsn, args.db_name)

    if not args.skip_question_bank:
        import_question_bank(
            target_dsn,
            args.question_bank_yaml,
            relax_rls=args.managed_db,
        )

    if not args.skip_schema:
        generate_schema_snapshot()

    print("Bootstrap complete.")


if __name__ == "__main__":
    main()
