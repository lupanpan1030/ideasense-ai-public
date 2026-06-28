import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services.context_paths import get_context_path_value
from app.services.pending_confirms import (
    PendingConfirmConflictError,
    PendingConfirmValidationError,
    apply_pending_confirm_updates,
    fetch_project_pending_confirm,
    normalize_pending_confirm,
    normalize_pending_confirm_resolve_paths,
    normalize_pending_confirm_updates,
    resolve_pending_confirm_context,
    resolve_pending_confirm_paths,
    resolve_pending_confirm_workflow,
    update_pending_confirm_context,
    update_pending_confirm_workflow,
)


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _FakeSession:
    def __init__(self, row: dict | None) -> None:
        self.row = row
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return _FakeResult(self.row)


class _SequenceSession:
    def __init__(self, rows: list[dict | None]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return _FakeResult(self.rows.pop(0))


class _WorkflowSessionFactory:
    def __init__(self) -> None:
        self.created: list[_WorkflowSession] = []

    def __call__(self) -> "_WorkflowSession":
        session = _WorkflowSession()
        self.created.append(session)
        return session


class _WorkflowSession:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def __aenter__(self) -> "_WorkflowSession":
        self.events.append("enter_session")
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        self.events.append("exit_session")

    def begin(self) -> "_WorkflowTransaction":
        return _WorkflowTransaction(self)

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.events.append(("execute", params or {}))
        return _FakeResult(None)


class _WorkflowTransaction:
    def __init__(self, session: _WorkflowSession) -> None:
        self.session = session

    async def __aenter__(self) -> "_WorkflowTransaction":
        self.session.events.append("enter_transaction")
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        self.session.events.append("exit_transaction")


class PendingConfirmServiceTests(unittest.TestCase):
    def test_normalize_pending_confirm_drops_invalid_values(self) -> None:
        self.assertEqual(normalize_pending_confirm(None), {})
        self.assertEqual(normalize_pending_confirm(["not", "a", "map"]), {})
        self.assertEqual(normalize_pending_confirm({"path": "value"}), {"path": "value"})

    def test_apply_pending_confirm_updates_splits_user_and_pending_values(self) -> None:
        state_json: dict = {}
        state_meta = {
            "pending_confirm": {
                "market_strategy": {"stale": {"value": "old"}},
            },
            "user_edited_paths": {
                "market": ["market_strategy.existing"],
            },
        }

        changed_paths = apply_pending_confirm_updates(
            state_json,
            state_meta,
            {
                "market_strategy.uvp.one_line": {
                    "value": "Cuts finance ops time in half.",
                    "source": "user",
                },
                "market_strategy.unit_economics.cac_hypothesis": {
                    "value": "Partner-led acquisition.",
                    "source": "ai",
                },
                "market_strategy.stale": None,
                "": "ignored",
            },
            "market",
        )

        self.assertEqual(
            changed_paths,
            [
                "market_strategy.stale",
                "market_strategy.unit_economics.cac_hypothesis",
                "market_strategy.uvp.one_line",
            ],
        )
        self.assertEqual(
            get_context_path_value(state_json, "market_strategy.uvp.one_line"),
            "Cuts finance ops time in half.",
        )
        self.assertIsNone(
            get_context_path_value(
                state_meta["pending_confirm"],
                "market_strategy.stale",
            )
        )
        self.assertEqual(
            get_context_path_value(
                state_meta["pending_confirm"],
                "market_strategy.unit_economics.cac_hypothesis.value",
            ),
            "Partner-led acquisition.",
        )
        self.assertEqual(
            state_meta["user_edited_paths"]["market"],
            [
                "market_strategy.existing",
                "market_strategy.stale",
                "market_strategy.uvp.one_line",
            ],
        )
        self.assertEqual(
            state_meta["answer_meta"]["market_strategy.uvp.one_line"]["source"],
            "user",
        )

    def test_normalize_pending_confirm_updates_requires_non_empty_mapping(self) -> None:
        with self.assertRaisesRegex(
            PendingConfirmValidationError,
            "Updates payload is required.",
        ):
            normalize_pending_confirm_updates({})

        self.assertEqual(
            normalize_pending_confirm_updates({"market.path": "Draft"}),
            {"market.path": "Draft"},
        )

    def test_normalize_pending_confirm_resolve_paths_removes_accepted_rejects(
        self,
    ) -> None:
        accepted, rejected = normalize_pending_confirm_resolve_paths(
            accept_paths=[" market.path ", "", 123, "duplicate.path"],
            reject_paths=["market.path", "other.path", " duplicate.path "],
        )

        self.assertEqual(accepted, ["market.path", "duplicate.path"])
        self.assertEqual(rejected, ["other.path"])

    def test_resolve_pending_confirm_accepts_and_rejects_paths(self) -> None:
        state_json: dict = {}
        state_meta = {
            "pending_confirm": {
                "market_strategy": {
                    "uvp": {
                        "one_line": {
                            "value": "Save founders four hours a week.",
                            "source": "user",
                        },
                    },
                    "unit_economics": {
                        "cac_hypothesis": {
                            "value": "AI-generated CAC draft.",
                            "source": "ai",
                        },
                    },
                },
            },
        }

        resolve_pending_confirm_paths(
            state_json,
            state_meta,
            ["market_strategy.uvp.one_line"],
            ["market_strategy.unit_economics.cac_hypothesis"],
            "market",
        )

        self.assertEqual(
            get_context_path_value(state_json, "market_strategy.uvp.one_line"),
            "Save founders four hours a week.",
        )
        self.assertEqual(state_meta["pending_confirm"], {})
        self.assertEqual(
            state_meta["user_edited_paths"],
            {"market": ["market_strategy.uvp.one_line"]},
        )
        self.assertEqual(
            state_meta["answer_meta"]["market_strategy.uvp.one_line"]["source"],
            "user",
        )


class PendingConfirmReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_pending_confirm_workflow_sets_rls_and_returns_payload(
        self,
    ) -> None:
        sessions = _WorkflowSessionFactory()

        async def set_system_actor_fn(session):  # type: ignore[no-untyped-def]
            session.events.append("set_system_actor")

        async def resolve_org_membership_fn(session, **kwargs):  # type: ignore[no-untyped-def]
            session.events.append(("resolve_org_membership", kwargs))
            return {"org_id": "org-1"}

        expected_payload = {
            "project_id": "project-1",
            "pending_confirm": {},
            "context_version": 2,
            "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
        with patch(
            "app.services.pending_confirms.update_pending_confirm_context",
            AsyncMock(return_value=expected_payload),
        ) as update_context:
            payload = await update_pending_confirm_workflow(
                admin_session_factory=sessions,
                set_system_actor_fn=set_system_actor_fn,
                resolve_org_membership_fn=resolve_org_membership_fn,
                actor_user_id="user-1",
                explicit_org_id="org-1",
                project_id="project-1",
                updates={"market.path": "Draft"},
                client_context_version=1,
            )

        self.assertEqual(payload, expected_payload)
        update_context.assert_awaited_once()
        self.assertEqual(update_context.await_args.kwargs["org_id"], "org-1")
        self.assertIn(
            ("execute", {"user_id": "user-1"}),
            sessions.created[0].events,
        )
        self.assertIn(
            ("execute", {"org_id": "org-1"}),
            sessions.created[0].events,
        )
        self.assertIn(
            ("execute", {"actor_type": "system"}),
            sessions.created[0].events,
        )

    async def test_resolve_pending_confirm_workflow_normalizes_paths(self) -> None:
        sessions = _WorkflowSessionFactory()

        async def set_system_actor_fn(session):  # type: ignore[no-untyped-def]
            session.events.append("set_system_actor")

        async def resolve_org_membership_fn(session, **kwargs):  # type: ignore[no-untyped-def]
            session.events.append(("resolve_org_membership", kwargs))
            return {"org_id": "org-1"}

        expected_payload = {
            "project_id": "project-1",
            "pending_confirm": {},
            "context_version": 2,
            "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
        with patch(
            "app.services.pending_confirms.resolve_pending_confirm_context",
            AsyncMock(return_value=expected_payload),
        ) as resolve_context:
            payload = await resolve_pending_confirm_workflow(
                admin_session_factory=sessions,
                set_system_actor_fn=set_system_actor_fn,
                resolve_org_membership_fn=resolve_org_membership_fn,
                actor_user_id="user-1",
                explicit_org_id=None,
                project_id="project-1",
                accept_paths=[" market.path "],
                reject_paths=["market.path", "other.path"],
                client_context_version=1,
            )

        self.assertEqual(payload, expected_payload)
        resolve_context.assert_awaited_once()
        self.assertEqual(resolve_context.await_args.kwargs["accept_paths"], ["market.path"])
        self.assertEqual(resolve_context.await_args.kwargs["reject_paths"], ["other.path"])

    async def test_update_pending_confirm_context_records_state_event(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        state_json: dict = {}
        state_meta = {"pending_confirm": {}}
        session = _SequenceSession(
            [
                {
                    "state_json": state_json,
                    "state_meta": state_meta,
                    "state_version": 4,
                    "current_stage": "market",
                },
                {
                    "state_meta": state_meta,
                    "state_version": 5,
                    "updated_at": updated_at,
                },
                None,
            ]
        )

        with patch(
            "app.services.pending_confirms.sync_runtime_gate_state",
            AsyncMock(),
        ) as sync_gate:
            payload = await update_pending_confirm_context(
                session,
                project_id="project-1",
                org_id="org-1",
                actor_user_id="user-1",
                updates={
                    "market_strategy.uvp.one_line": {
                        "value": "Save founders four hours a week.",
                        "source": "user",
                    },
                },
                client_context_version=4,
            )

        self.assertEqual(payload["context_version"], 5)
        self.assertEqual(payload["updated_at"], updated_at)
        self.assertEqual(payload["pending_confirm"], {})
        event_params = next(
            params
            for sql, params in session.calls
            if "INSERT INTO project_state_events" in sql and isinstance(params, dict)
        )
        self.assertEqual(event_params["patch_json"]["source"], "pending_context_update")
        self.assertEqual(
            event_params["patch_json"]["paths"],
            ["market_strategy.uvp.one_line"],
        )
        sync_gate.assert_awaited_once()

    async def test_update_pending_confirm_context_rejects_stale_version(self) -> None:
        session = _SequenceSession(
            [
                {
                    "state_json": {},
                    "state_meta": {},
                    "state_version": 4,
                    "current_stage": "market",
                }
            ]
        )

        with self.assertRaisesRegex(
            PendingConfirmConflictError,
            "Context updated while you were away.",
        ):
            await update_pending_confirm_context(
                session,
                project_id="project-1",
                org_id="org-1",
                actor_user_id="user-1",
                updates={"market_strategy.uvp.one_line": "Draft"},
                client_context_version=3,
            )

        self.assertEqual(len(session.calls), 1)

    async def test_resolve_pending_confirm_context_records_state_event(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        state_json: dict = {}
        state_meta = {
            "pending_confirm": {
                "market_strategy": {
                    "uvp": {
                        "one_line": {
                            "value": "Save founders four hours a week.",
                            "source": "user",
                        },
                    },
                    "unit_economics": {
                        "cac_hypothesis": "AI draft",
                    },
                },
            }
        }
        session = _SequenceSession(
            [
                {"current_stage": "market"},
                {
                    "state_json": state_json,
                    "state_meta": state_meta,
                    "state_version": 7,
                },
                {
                    "state_meta": state_meta,
                    "state_version": 8,
                    "updated_at": updated_at,
                },
                None,
            ]
        )

        with patch(
            "app.services.pending_confirms.sync_runtime_gate_state",
            AsyncMock(),
        ) as sync_gate:
            payload = await resolve_pending_confirm_context(
                session,
                project_id="project-1",
                org_id="org-1",
                actor_user_id="user-1",
                accept_paths=["market_strategy.uvp.one_line"],
                reject_paths=["market_strategy.unit_economics.cac_hypothesis"],
                client_context_version=7,
            )

        self.assertEqual(payload["context_version"], 8)
        self.assertEqual(payload["pending_confirm"], {})
        update_params = next(
            params
            for sql, params in session.calls
            if "UPDATE project_states" in sql and isinstance(params, dict)
        )
        self.assertEqual(
            get_context_path_value(
                update_params["state_json"],
                "market_strategy.uvp.one_line",
            ),
            "Save founders four hours a week.",
        )
        event_params = next(
            params
            for sql, params in session.calls
            if "INSERT INTO project_state_events" in sql and isinstance(params, dict)
        )
        self.assertEqual(event_params["patch_json"]["source"], "pending_context_resolve")
        self.assertEqual(
            event_params["patch_json"]["accepted_paths"],
            ["market_strategy.uvp.one_line"],
        )
        self.assertEqual(
            event_params["patch_json"]["rejected_paths"],
            ["market_strategy.unit_economics.cac_hypothesis"],
        )
        sync_gate.assert_awaited_once()

    async def test_fetch_project_pending_confirm_normalizes_response(self) -> None:
        updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        session = _FakeSession(
            {
                "project_id": "project-1",
                "project_updated_at": updated_at,
                "runtime_updated_at": None,
                "state_version": None,
                "pending_confirm": ["invalid"],
                "state_updated_at": None,
            }
        )

        payload = await fetch_project_pending_confirm(session, "project-1")

        self.assertEqual(
            session.calls[0][1],
            {"project_id": "project-1"},
        )
        self.assertEqual(
            payload,
            {
                "project_id": "project-1",
                "pending_confirm": {},
                "context_version": 0,
                "updated_at": updated_at,
            },
        )

    async def test_fetch_project_pending_confirm_returns_none_when_missing(self) -> None:
        payload = await fetch_project_pending_confirm(_FakeSession(None), "missing")

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
