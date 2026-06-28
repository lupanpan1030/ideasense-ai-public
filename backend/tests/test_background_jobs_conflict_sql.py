import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CONFLICT_TARGET = "ON CONFLICT (org_id, job_type, idempotency_key)"
PARTIAL_INDEX_PREDICATE = (
    "WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL"
)


def _runtime_sources() -> list[Path]:
    return [
        BACKEND_ROOT / "app/services/answer_extraction_jobs.py",
        BACKEND_ROOT / "app/services/background_jobs.py",
        BACKEND_ROOT / "app/services/stage_summary_jobs.py",
        BACKEND_ROOT / "app/services/verification_jobs.py",
    ]


def test_background_job_idempotency_conflicts_match_partial_index() -> None:
    for source_path in _runtime_sources():
        source = " ".join(source_path.read_text().split())
        conflict_count = source.count(CONFLICT_TARGET)
        assert conflict_count > 0, f"no background job conflicts found in {source_path}"

        matches = list(re.finditer(re.escape(CONFLICT_TARGET), source))
        assert len(matches) == conflict_count

        for match in matches:
            clause = source[match.start() : match.start() + 260]
            assert PARTIAL_INDEX_PREDICATE in clause
            assert re.search(r"DO (NOTHING|UPDATE)", clause)
