#!/usr/bin/env python3
"""Drop and recreate the database, then run migrations, roles, question bank, and seed."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from psycopg2 import errors, sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from bootstrap_db import (
    PRODUCTION_DB_ALLOW_ENV,
    REMOTE_DB_ALLOW_ENV,
    apply_rls_roles,
    assert_safe_database_target,
    build_dsn,
    default_question_bank_yaml,
    ensure_database,
    generate_schema_snapshot,
    _env_flag_enabled,
    import_question_bank,
    load_env_file,
    parse_admin_dsn,
    run_migrations,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SEED_PATH = BASE_DIR / "seeds" / "seed_dev.sql"
DEFAULT_ENV_PATHS = (
    BASE_DIR.parent / "backend" / ".env",
    BASE_DIR.parent / ".env",
)


def log_step(message: str) -> None:
    print(f"\n==> {message}")


def drop_database(admin_dsn: str, db_name: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            try:
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        sql.Identifier(db_name)
                    )
                )
            except errors.SyntaxError:
                conn.rollback()
                cur.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (db_name,),
                )
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(db_name)
                    )
                )
        print(f"Dropped database {db_name}.")
    finally:
        conn.close()


def resolve_seed_file(seed_file: Path) -> Path:
    seed_file = seed_file.expanduser()
    if not seed_file.is_absolute():
        seed_file = (Path.cwd() / seed_file).resolve()
    if not seed_file.exists():
        raise FileNotFoundError(seed_file)
    return seed_file


def run_seed_local(dsn: str, seed_file: Path) -> None:
    seed_file = resolve_seed_file(seed_file)
    try:
        subprocess.run(
            ["psql", "--dbname", dsn, "-f", str(seed_file)],
            check=True,
            cwd=str(seed_file.parent),
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "psql not found; install client tools or run seed manually."
        ) from exc


def main() -> None:
    managed_default = os.getenv("MANAGED_DB", "").lower() in (
        "1",
        "true",
        "yes",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-name", default="ideasense_ai_dev")
    parser.add_argument("--admin-dsn", default=os.getenv("DATABASE_URL_ADMIN"))
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--skip-roles", action="store_true")
    parser.add_argument("--skip-question-bank", action="store_true")
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--skip-schema", action="store_true")
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
        help="Allow this destructive reset to target a non-local database host.",
    )
    parser.add_argument(
        "--allow-production-db",
        action="store_true",
        default=_env_flag_enabled(PRODUCTION_DB_ALLOW_ENV),
        help="Allow this destructive reset in APP_ENV=production or against a production-like database name.",
    )
    parser.add_argument(
        "--question-bank-yaml",
        default=default_question_bank_yaml(),
    )
    parser.add_argument("--seed-file", default=str(DEFAULT_SEED_PATH))
    args = parser.parse_args()

    if args.env_file and not args.admin_dsn:
        log_step(f"Loading env file: {args.env_file}")
        load_env_file(Path(args.env_file))
        args.admin_dsn = os.getenv("DATABASE_URL_ADMIN")

    if not args.admin_dsn:
        for env_path in DEFAULT_ENV_PATHS:
            if env_path.exists():
                log_step(f"Loading env file: {env_path}")
                load_env_file(env_path)
                args.admin_dsn = os.getenv("DATABASE_URL_ADMIN")
                if args.admin_dsn:
                    break

    if not args.admin_dsn:
        raise SystemExit(
            "DATABASE_URL_ADMIN or --admin-dsn is required "
            "(or set --env-file to a file that defines it)."
        )

    db_name_explicit = "--db-name" in sys.argv
    admin_params = parse_admin_dsn(args.admin_dsn)
    if not db_name_explicit:
        admin_dbname = admin_params.get("dbname")
        if admin_dbname and admin_dbname not in ("postgres", "template1"):
            args.db_name = admin_dbname
            print(f"Using db name from admin DSN: {args.db_name}")
    assert_safe_database_target(
        admin_params,
        args.db_name,
        script_name=Path(__file__).name,
        destructive=True,
        allow_remote=args.allow_remote_db,
        allow_production=args.allow_production_db,
    )
    maintenance_params = dict(admin_params)
    if maintenance_params.get("dbname") in ("", args.db_name):
        maintenance_params["dbname"] = "postgres"
    maintenance_dsn = build_dsn(maintenance_params)

    target_params = dict(admin_params)
    target_params["dbname"] = args.db_name
    target_dsn = build_dsn(target_params)

    display_host = admin_params.get("host") or "localhost"
    display_port = admin_params.get("port") or "5432"
    display_user = admin_params.get("user") or "postgres"
    log_step(
        f"Reset starting for {args.db_name} "
        f"(host={display_host}, port={display_port}, user={display_user})"
    )

    log_step(f"Dropping database {args.db_name}")
    drop_database(maintenance_dsn, args.db_name)

    log_step(f"Creating database {args.db_name}")
    ensure_database(maintenance_dsn, args.db_name)

    log_step("Running migrations")
    run_migrations(target_dsn)

    if args.managed_db and not args.skip_roles:
        log_step("Managed DB detected: skipping role grants.")
        args.skip_roles = True

    if not args.skip_roles:
        log_step("Applying RLS roles")
        apply_rls_roles(target_dsn, args.db_name)
        print("RLS roles applied.")
    else:
        log_step("Skipping RLS roles")

    if not args.skip_question_bank:
        log_step(f"Importing question bank from {args.question_bank_yaml}")
        import_question_bank(
            target_dsn,
            args.question_bank_yaml,
            relax_rls=args.managed_db,
        )
        print("Question bank import complete.")

    if not args.skip_seed:
        log_step("Seeding data")
        print("Using local psql for seed.")
        print(f"Seed file: {args.seed_file}")
        run_seed_local(target_dsn, Path(args.seed_file))
        print("Seed data applied.")

    if not args.skip_schema:
        log_step("Generating schema snapshot")
        generate_schema_snapshot()
        print("Schema snapshot generated.")

    print("Reset complete.")


if __name__ == "__main__":
    main()
