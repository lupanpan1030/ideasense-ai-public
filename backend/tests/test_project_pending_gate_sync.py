import unittest
from app.services.project_gate_sync import sync_runtime_gate_state


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, *, stage: str = "problem", variant: str = "default") -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self.stage = stage
        self.variant = variant

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append((sql, params))
        if "SELECT stage, variant, missing_paths" in sql:
            return _FakeResult(
                {
                    "stage": self.stage,
                    "variant": self.variant,
                    "missing_paths": (
                        ["tech_execution.product_scope.mvp_definition"]
                        if self.stage == "tech"
                        else ["problem.one_line"]
                    ),
                }
            )
        return _FakeResult(None)


class SyncRuntimeGateStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_runtime_gate_state_updates_runtime_and_stage_status(self) -> None:
        session = _FakeSession()

        await sync_runtime_gate_state(
            session,
            project_id="project-1",
            org_id="org-1",
            current_stage="problem",
            state_json={"problem": {"one_line": "Manual reporting is slow."}},
            state_meta={},
        )

        runtime_update = next(
            params
            for sql, params in session.calls
            if "UPDATE project_runtime" in sql and isinstance(params, dict)
        )
        project_update = next(
            params
            for sql, params in session.calls
            if "UPDATE projects" in sql and isinstance(params, dict)
        )

        self.assertEqual(runtime_update["missing_paths"], [])
        self.assertEqual(project_update["stage_status"], "awaiting_confirm")

    async def test_sync_runtime_gate_state_keeps_router_stage_in_progress(self) -> None:
        session = _FakeSession(stage="tech", variant="router")

        await sync_runtime_gate_state(
            session,
            project_id="project-1",
            org_id="org-1",
            current_stage="tech",
            state_json={
                "tech_execution": {
                    "product_scope": {
                        "mvp_definition": "Pilot dashboard for finance ops."
                    }
                }
            },
            state_meta={},
        )

        runtime_update = next(
            params
            for sql, params in session.calls
            if "UPDATE project_runtime" in sql and isinstance(params, dict)
        )
        project_update = next(
            params
            for sql, params in session.calls
            if "UPDATE projects" in sql and isinstance(params, dict)
        )

        self.assertEqual(runtime_update["missing_paths"], [])
        self.assertEqual(project_update["stage_status"], "in_progress")


if __name__ == "__main__":
    unittest.main()
