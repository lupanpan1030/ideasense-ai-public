#!/usr/bin/env python3
"""Import prompt templates from backend/app/prompts into prompt_templates."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

from db_context import set_actor_context

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent


@dataclass(frozen=True)
class PromptTemplateRow:
    template_key: str
    template_name: str
    content: str
    purpose: str
    stage: str | None
    variant: str | None
    version: str


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def parse_front_matter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, content
    meta_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    meta: dict[str, str] = {}
    for raw in meta_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = _strip_quotes(value.strip())
        if key:
            meta[key] = value
    return meta, body


def _normalize_optional_meta(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or trimmed.lower() in {"null", "none", "nil"}:
        return None
    return trimmed


def normalize_stage_list(value: str | None) -> str | None:
    trimmed = _normalize_optional_meta(value)
    if not trimmed:
        return None
    parts = [
        part.strip().lower()
        for part in re.split(r"[,\|/]+", trimmed)
        if part.strip()
    ]
    if not parts:
        return None
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        ordered.append(part)
    return ", ".join(ordered)


def resolve_prompts_dir(path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate.resolve()
    return path


def normalize_template_key(template_name: str) -> str:
    return template_name.strip().lower().replace("/", ".")


def resolve_purpose(template_name: str, rel_parts: tuple[str, ...]) -> str:
    if rel_parts and rel_parts[0] == "chat":
        return "chat"
    if rel_parts and rel_parts[0] == "report":
        if "dvf_scoring" in template_name:
            return "score"
        if "stage_summary" in template_name or "project_description" in template_name:
            return "summary"
        return "report"
    if rel_parts and rel_parts[0] == "shared":
        if "extraction" in template_name:
            return "extract"
        if "qa_digest_summary" in template_name:
            return "summary"
        if "question_rewrite" in template_name:
            return "evaluate"
    return "chat"


def iter_prompt_templates(prompts_dir: Path) -> list[PromptTemplateRow]:
    rows: list[PromptTemplateRow] = []
    for path in sorted(prompts_dir.rglob("*.md")):
        rel_path = path.relative_to(prompts_dir)
        template_name = rel_path.with_suffix("").as_posix()
        template_key = normalize_template_key(template_name)
        raw_content = path.read_text(encoding="utf-8")
        meta, content = parse_front_matter(raw_content)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        version = content_hash[:12]
        purpose = meta.get("purpose") or resolve_purpose(template_name, rel_path.parts)
        stage = normalize_stage_list(meta.get("stage") or meta.get("stages"))
        variant = _normalize_optional_meta(meta.get("variant"))
        rows.append(
            PromptTemplateRow(
                template_key=template_key,
                template_name=template_name,
                content=content,
                purpose=purpose,
                stage=stage,
                variant=variant,
                version=version,
            )
        )
    return rows


def _resolve_unique_version(cur, org_id: str | None, template_key: str, base: str) -> str:
    version = base
    suffix = 1
    while True:
        cur.execute(
            """
            SELECT 1
            FROM prompt_templates
            WHERE template_key = %s
              AND version = %s
              AND deleted_at IS NULL
              AND org_id IS NOT DISTINCT FROM %s
            """,
            (template_key, version, org_id),
        )
        if not cur.fetchone():
            return version
        version = f"{base}.{suffix}"
        suffix += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompts-dir",
        default="backend/app/prompts",
        help="Path to prompt templates directory",
    )
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--org-id", default=None)
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--inactive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dsn:
        raise SystemExit("DATABASE_URL or --dsn is required")

    prompts_dir = resolve_prompts_dir(Path(args.prompts_dir))
    if not prompts_dir.exists():
        raise SystemExit(f"prompts dir not found: {prompts_dir}")

    rows = iter_prompt_templates(prompts_dir)
    if args.dry_run:
        print(f"Prompts: {prompts_dir}")
        print(f"Templates: {len(rows)}")
        for row in rows:
            print(f"- {row.template_key} ({row.purpose}) v{row.version}")
        return

    actor_type = "user" if args.user_id else "system"
    with psycopg2.connect(args.dsn) as conn:
        conn.autocommit = True
        set_actor_context(
            conn,
            actor_type=actor_type,
            user_id=args.user_id,
            org_id=args.org_id,
        )
        with conn.cursor() as cur:
            inserted = 0
            activated = 0
            for row in rows:
                base_version = row.version
                version = _resolve_unique_version(
                    cur, args.org_id, row.template_key, base_version
                )

                cur.execute(
                    """
                    SELECT id, content
                    FROM prompt_templates
                    WHERE template_key = %s
                      AND version = %s
                      AND deleted_at IS NULL
                      AND org_id IS NOT DISTINCT FROM %s
                    """,
                    (row.template_key, version, args.org_id),
                )
                existing = cur.fetchone()

                if existing:
                    template_id = existing[0]
                    if not args.inactive:
                        cur.execute(
                            """
                            UPDATE prompt_templates
                            SET is_active = false, updated_at = now()
                            WHERE template_key = %s
                              AND deleted_at IS NULL
                              AND is_active
                              AND org_id IS NOT DISTINCT FROM %s
                            """,
                            (row.template_key, args.org_id),
                        )
                        cur.execute(
                            """
                            UPDATE prompt_templates
                            SET is_active = true, updated_at = now()
                            WHERE id = %s
                            """,
                            (template_id,),
                        )
                        activated += 1
                    continue

                if not args.inactive:
                    cur.execute(
                        """
                        UPDATE prompt_templates
                        SET is_active = false, updated_at = now()
                        WHERE template_key = %s
                          AND deleted_at IS NULL
                          AND is_active
                          AND org_id IS NOT DISTINCT FROM %s
                        """,
                        (row.template_key, args.org_id),
                    )

                cur.execute(
                    """
                    INSERT INTO prompt_templates (
                        org_id, template_key, purpose, stage, variant,
                        version, content, params, is_active
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        args.org_id,
                        row.template_key,
                        row.purpose,
                        row.stage,
                        row.variant,
                        version,
                        row.content,
                        Json(None),
                        not args.inactive,
                    ),
                )
                inserted += 1
                if not args.inactive:
                    activated += 1

            print(f"Inserted: {inserted}")
            print(f"Activated: {activated}")


if __name__ == "__main__":
    main()
