#!/usr/bin/env python3
"""Backfill projects.settings.prompt_template_ids for an org."""

from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2.extras import Json

from db_context import set_actor_context


def _load_prompt_template_ids(cur, org_id: str) -> dict[str, str]:
    cur.execute(
        """
        SELECT DISTINCT ON (template_key) id, template_key
        FROM prompt_templates
        WHERE is_active
          AND deleted_at IS NULL
          AND (org_id = %s OR org_id IS NULL)
        ORDER BY template_key, CASE WHEN org_id IS NULL THEN 1 ELSE 0 END
        """,
        (org_id,),
    )
    mapping: dict[str, str] = {}
    for row in cur.fetchall():
        mapping[row[1]] = str(row[0])
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dsn:
        raise SystemExit("DATABASE_URL or --dsn is required")

    with psycopg2.connect(args.dsn) as conn:
        conn.autocommit = True
        set_actor_context(
            conn,
            actor_type="user",
            user_id=args.user_id,
            org_id=args.org_id,
        )
        with conn.cursor() as cur:
            prompt_template_ids = _load_prompt_template_ids(cur, args.org_id)
            if not prompt_template_ids:
                raise SystemExit("No active prompt templates found for org.")

            settings_patch = {"prompt_template_ids": prompt_template_ids}
            if args.dry_run:
                print(f"Org: {args.org_id}")
                print(f"Templates: {len(prompt_template_ids)}")
                return

            if args.force:
                condition = "TRUE"
            else:
                condition = "settings->'prompt_template_ids' IS NULL"

            cur.execute(
                f"""
                UPDATE projects
                SET settings = COALESCE(settings, '{{}}'::jsonb)
                    || %s::jsonb,
                    updated_at = now()
                WHERE org_id = %s
                  AND deleted_at IS NULL
                  AND {condition}
                """,
                (Json(settings_patch), args.org_id),
            )
            print(f"Updated projects: {cur.rowcount}")


if __name__ == "__main__":
    main()
