from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_report_runtime_allows_null_current_question_in_schema_contract() -> None:
    schema_sql = (ROOT / "database" / "schema" / "schema.sql").read_text()

    assert "Source: 055_allow_report_runtime_without_current_question" in schema_sql
    assert "IF NEW.stage = 'report' AND NEW.current_question_bank_question_id IS NULL" in schema_sql
    assert "NEW.next_question_bank_question_id := NULL;" in schema_sql


def test_report_runtime_fix_migration_is_present() -> None:
    migration_sql = (
        ROOT
        / "database"
        / "migrations"
        / "055_allow_report_runtime_without_current_question_20260521123000.sql"
    ).read_text()

    assert "ALTER COLUMN current_question_bank_question_id DROP NOT NULL" in migration_sql
    assert "SET row_security = off" in migration_sql
    assert "IF NEW.stage = 'report' AND NEW.current_question_bank_question_id IS NULL" in migration_sql
