import asyncio
from pathlib import Path

from app.services.project_state_events import record_project_state_event

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class FakeAsyncSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params: dict) -> None:
        self.calls.append((str(statement), params))


def test_record_project_state_event_inserts_apply_patch_versions() -> None:
    session = FakeAsyncSession()

    asyncio.run(
        record_project_state_event(
            session,
            org_id="11111111-1111-1111-1111-111111111111",
            project_id="22222222-2222-2222-2222-222222222222",
            question_instance_id="33333333-3333-3333-3333-333333333333",
            event_type="apply_patch",
            patch_json={
                "source": "chat_sync_extraction",
                "paths": ["problem.one_line"],
            },
            actor_type="system",
            prev_state_version=4,
            next_state_version=5,
            request_id="44444444-4444-4444-4444-444444444444",
        )
    )

    assert len(session.calls) == 1
    statement, params = session.calls[0]
    assert "INSERT INTO project_state_events" in statement
    assert params["event_type"] == "apply_patch"
    assert params["patch_json"]["source"] == "chat_sync_extraction"
    assert params["prev_state_version"] == 4
    assert params["next_state_version"] == 5
    assert params["request_id"] == "44444444-4444-4444-4444-444444444444"


def test_versioned_project_state_mutations_record_state_events() -> None:
    expected_event_calls = {
        "app/services/chat_turn_commit.py": 2,
        "app/services/pending_confirms.py": 2,
        "app/services/project_creation.py": 1,
        "app/services/answer_extraction_worker_handler.py": 2,
    }

    for relative_path, expected_count in expected_event_calls.items():
        source = (BACKEND_ROOT / relative_path).read_text()
        assert source.count("await record_project_state_event(") >= expected_count
