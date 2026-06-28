#!/usr/bin/env python3
"""Import a question bank YAML into the database."""

import argparse
import hashlib
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values
import yaml

from db_context import set_system_actor
BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
PRIVATE_QUESTION_BANK_DIR = Path("resources") / "question_bank"
PUBLIC_QUESTION_BANK_EXAMPLE_PATH = "resources/question_bank.example.yaml"
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


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


def load_yaml(path: Path) -> tuple[str, dict]:
    raw_yaml = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_yaml)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return raw_yaml, data


def resolve_yaml_path(path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate.resolve()
    return path


def iter_questions(data: dict) -> list[dict]:
    stages = data.get("stages") or {}
    if not isinstance(stages, dict):
        raise ValueError("stages must be a mapping")

    rows = []
    for stage, block in stages.items():
        if stage in {"problem", "market", "report"}:
            questions = (block or {}).get("questions", [])
            if questions is None:
                questions = []
            for index, question in enumerate(questions, 1):
                rows.append(
                    {
                        "stage": stage,
                        "variant": "default",
                        "order_index": index,
                        "question": question or {},
                    }
                )
        elif stage == "tech":
            if not isinstance(block, dict):
                raise ValueError("tech stage must map variants to question lists")
            for variant, questions in block.items():
                if questions is None:
                    questions = []
                for index, question in enumerate(questions, 1):
                    rows.append(
                        {
                            "stage": stage,
                            "variant": variant,
                            "order_index": index,
                            "question": question or {},
                        }
                    )
        else:
            raise ValueError(f"unsupported stage: {stage}")
    return rows


def build_question_row(bank_version_id: str, row: dict) -> tuple:
    question = row["question"]
    notes = question.get("notes")
    meta = {}
    if notes:
        meta["notes"] = notes

    return (
        bank_version_id,
        row["stage"],
        row["variant"],
        question.get("id"),
        row["order_index"],
        question.get("title"),
        question.get("type"),
        question.get("prompt"),
        question.get("standard_question"),
        question.get("consultant_tactic"),
        question.get("instruction"),
        question.get("validation_rule"),
        question.get("schema_paths") or [],
        question.get("expected_key_points") or [],
        Json(question.get("prompt_meta") or {}),
        None,  # capture_intent
        Json({}),  # capture_spec
        [],  # answer_examples
        None,  # expected_patch_example
        None,  # display_if
        Json(meta),
    )


def _resolve_version_suffix(
    cur, scope_org_id: str, bank_key: str, base_version: str
) -> str:
    suffix = 1
    while True:
        candidate = f"{base_version}.{suffix}"
        cur.execute(
            """
            SELECT 1
            FROM question_bank_versions
            WHERE scope_org_id = %s
              AND bank_key = %s
              AND version = %s
              AND deleted_at IS NULL
            """,
            (scope_org_id, bank_key, candidate),
        )
        if not cur.fetchone():
            return candidate
        suffix += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yaml",
        default=default_question_bank_yaml(),
        help="Path to question bank YAML",
    )
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--org-id", default=None)
    parser.add_argument("--bank-key", default="default")
    parser.add_argument("--inactive", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dsn:
        raise SystemExit("DATABASE_URL or --dsn is required")

    bank_key = args.bank_key.strip().lower()
    if not bank_key or any(ch.isspace() for ch in bank_key):
        raise SystemExit("bank_key must be lowercase, trimmed, and contain no spaces")

    yaml_path = resolve_yaml_path(Path(args.yaml))
    raw_yaml, data = load_yaml(yaml_path)

    version = str(data.get("version") or "").strip()
    source = data.get("source")
    if not version:
        raise SystemExit("YAML is missing version")

    content_hash = hashlib.sha256(raw_yaml.encode("utf-8")).hexdigest()
    question_rows = iter_questions(data)

    if args.dry_run:
        print(f"YAML: {yaml_path}")
        print(f"Version: {version}")
        print(f"Questions: {len(question_rows)}")
        return

    with psycopg2.connect(args.dsn) as conn:
        conn.autocommit = True
        set_system_actor(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stage, variant FROM question_bank_stage_variants"
            )
            allowed = {(row[0], row[1]) for row in cur.fetchall()}

            for row in question_rows:
                if (row["stage"], row["variant"]) not in allowed:
                    raise SystemExit(
                        f"invalid stage/variant: {row['stage']}/{row['variant']}"
                    )

            scope_org_id = args.org_id or ZERO_UUID
            base_version = version

            cur.execute(
                """
                SELECT id, content_hash
                FROM question_bank_versions
                WHERE scope_org_id = %s
                  AND bank_key = %s
                  AND version = %s
                  AND deleted_at IS NULL
                """,
                (scope_org_id, bank_key, base_version),
            )
            existing = cur.fetchone()
            if existing and not args.replace:
                existing_id, existing_hash = existing
                if existing_hash == content_hash:
                    if not args.inactive:
                        cur.execute(
                            """
                            UPDATE question_bank_versions
                               SET is_active = false
                             WHERE scope_org_id = %s
                               AND bank_key = %s
                               AND is_active
                               AND deleted_at IS NULL
                            """,
                            (scope_org_id, bank_key),
                        )
                        cur.execute(
                            """
                            UPDATE question_bank_versions
                               SET is_active = true
                             WHERE id = %s
                            """,
                            (existing_id,),
                        )
                    print("Version already exists with identical content; activated.")
                    return

                version = _resolve_version_suffix(
                    cur, scope_org_id, bank_key, base_version
                )
                print(
                    f"Version {base_version} exists with different content; "
                    f"using {version}."
                )

            if existing and args.replace:
                existing_id = existing[0]
                cur.execute(
                    """
                    UPDATE question_bank_questions
                       SET deleted_at = now()
                     WHERE bank_version_id = %s
                       AND deleted_at IS NULL
                    """,
                    (existing_id,),
                )
                cur.execute(
                    """
                    UPDATE question_bank_versions
                       SET deleted_at = now(),
                           is_active = false
                     WHERE id = %s
                    """,
                    (existing_id,),
                )

            cur.execute(
                """
                SELECT id, version
                FROM question_bank_versions
                WHERE scope_org_id = %s
                  AND content_hash = %s
                  AND deleted_at IS NULL
                LIMIT 1
                """,
                (scope_org_id, content_hash),
            )
            existing_hash = cur.fetchone()
            if existing_hash and not args.replace:
                existing_id, existing_version = existing_hash
                if not args.inactive:
                    cur.execute(
                        """
                        UPDATE question_bank_versions
                           SET is_active = false
                         WHERE scope_org_id = %s
                           AND bank_key = %s
                           AND is_active
                           AND deleted_at IS NULL
                        """,
                        (scope_org_id, bank_key),
                    )
                    cur.execute(
                        """
                        UPDATE question_bank_versions
                           SET is_active = true
                         WHERE id = %s
                        """,
                        (existing_id,),
                    )
                print(
                    f"Content already exists as version {existing_version}; "
                    "activated."
                )
                return

            if not args.inactive:
                cur.execute(
                    """
                    UPDATE question_bank_versions
                       SET is_active = false
                     WHERE scope_org_id = %s
                       AND bank_key = %s
                       AND is_active
                       AND deleted_at IS NULL
                    """,
                    (scope_org_id, bank_key),
                )

            cur.execute(
                """
                INSERT INTO question_bank_versions (
                    org_id,
                    bank_key,
                    version,
                    source,
                    raw_yaml,
                    raw_json,
                    content_hash,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    args.org_id,
                    bank_key,
                    version,
                    source,
                    raw_yaml,
                    Json(data),
                    content_hash,
                    not args.inactive,
                ),
            )
            bank_version_id = cur.fetchone()[0]

            columns = (
                "bank_version_id",
                "stage",
                "variant",
                "question_id",
                "order_index",
                "title",
                "type_raw",
                "prompt",
                "standard_question",
                "consultant_tactic",
                "instruction",
                "validation_rule",
                "schema_paths",
                "expected_key_points",
                "prompt_meta",
                "capture_intent",
                "capture_spec",
                "answer_examples",
                "expected_patch_example",
                "display_if",
                "meta",
            )

            values = [
                build_question_row(bank_version_id, row) for row in question_rows
            ]

            execute_values(
                cur,
                f"""
                INSERT INTO question_bank_questions ({", ".join(columns)})
                VALUES %s
                """,
                values,
            )

    print(
        f"Imported question bank {bank_key} v{version} "
        f"({len(question_rows)} questions)"
    )


if __name__ == "__main__":
    main()
