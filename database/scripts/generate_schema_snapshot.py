#!/usr/bin/env python3
"""Generate database/schema/schema.sql by concatenating migrations."""

from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    migrations_dir = base_dir / "migrations"
    schema_dir = base_dir / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    output_path = schema_dir / "schema.sql"

    migration_files = sorted(migrations_dir.glob("*.sql"))

    header = [
        "-- Generated from database/migrations. Do not edit by hand.",
        "-- Source order:",
    ]
    header.extend([f"--   {path.name}" for path in migration_files])
    header.append("")

    parts = ["\n".join(header)]
    for path in migration_files:
        parts.append(f"-- ------------------------------------------------------------------")
        parts.append(f"-- Source: {path.name}")
        parts.append(path.read_text().rstrip())
        parts.append("")

    output_path.write_text("\n".join(parts))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
