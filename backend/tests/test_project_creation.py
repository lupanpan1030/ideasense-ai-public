import unittest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.services.project_creation import (
    ProjectCreationConflictError,
    ProjectCreationInputValidationError,
    ProjectCreationQuestionSetupError,
    ProjectCreationQuestionSetup,
    ProjectCreationRecords,
    create_project_records,
    create_project_workflow,
    normalize_project_creation_input,
    resolve_project_creation_question_setup,
)


class _FakeResult:
    def __init__(
        self,
        *,
        row: dict | None = None,
        rows: list[dict] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or []

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    def __init__(self, results: list[_FakeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.calls.append((str(statement), params))
        return self.results.pop(0)


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
        return _FakeResult(row=None)


class _WorkflowTransaction:
    def __init__(self, session: _WorkflowSession) -> None:
        self.session = session

    async def __aenter__(self) -> "_WorkflowTransaction":
        self.session.events.append("enter_transaction")
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        self.session.events.append("exit_transaction")


class ProjectCreationQuestionSetupTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_project_creation_input_validates_title_and_bank_key(self) -> None:
        with self.assertRaisesRegex(
            ProjectCreationInputValidationError,
            "Title is required.",
        ):
            normalize_project_creation_input(
                title="  ",
                description=None,
                bank_key=None,
                allowed_bank_keys={"default", "lite"},
            )

        with self.assertRaisesRegex(
            ProjectCreationInputValidationError,
            "Unsupported bank_key: 'unknown'.",
        ):
            normalize_project_creation_input(
                title="Idea",
                description="  ",
                bank_key="unknown",
                allowed_bank_keys={"default", "lite"},
            )

        normalized = normalize_project_creation_input(
            title=" Idea ",
            description="  ",
            bank_key=" Lite ",
            allowed_bank_keys={"default", "lite"},
        )
        self.assertEqual(normalized.title, "Idea")
        self.assertIsNone(normalized.description)
        self.assertEqual(normalized.bank_key, "lite")

    async def test_create_project_workflow_detects_org_change(self) -> None:
        sessions = _WorkflowSessionFactory()
        user_id = uuid4()
        question_setup = ProjectCreationQuestionSetup(
            bank_id=uuid4(),
            current_question_id=uuid4(),
            next_question_id=None,
            missing_paths=[],
            question_detail={"prompt": "Tell us briefly about your idea."},
        )
        memberships = [{"org_id": "org-1"}, {"org_id": "org-2"}]

        async def set_system_actor_fn(session):  # type: ignore[no-untyped-def]
            session.events.append("set_system_actor")

        async def resolve_org_membership_fn(session, **kwargs):  # type: ignore[no-untyped-def]
            session.events.append(("resolve_org_membership", kwargs))
            return memberships.pop(0)

        with patch(
            "app.services.project_creation.resolve_project_creation_question_setup",
            AsyncMock(return_value=question_setup),
        ) as resolve_setup:
            with patch(
                "app.services.project_creation.create_project_records",
                AsyncMock(),
            ) as create_records:
                with self.assertRaisesRegex(
                    ProjectCreationConflictError,
                    "Organization changed. Refresh and try again.",
                ):
                    await create_project_workflow(
                        admin_session_factory=sessions,
                        set_system_actor_fn=set_system_actor_fn,
                        resolve_org_membership_fn=resolve_org_membership_fn,
                        actor_user_id=user_id,
                        explicit_org_id=None,
                        title="Idea",
                        description=None,
                        bank_key=None,
                        allowed_bank_keys={"default", "lite"},
                    )

        resolve_setup.assert_awaited_once()
        create_records.assert_not_awaited()
        self.assertEqual(len(sessions.created), 2)
        self.assertNotIn(
            ("execute", {"actor_type": "system"}),
            sessions.created[1].events,
        )

    async def test_create_project_workflow_returns_created_records(self) -> None:
        sessions = _WorkflowSessionFactory()
        user_id = uuid4()
        project_id = uuid4()
        question_setup = ProjectCreationQuestionSetup(
            bank_id=uuid4(),
            current_question_id=uuid4(),
            next_question_id=uuid4(),
            missing_paths=["problem.initial_idea"],
            question_detail={"prompt": "Tell us briefly about your idea."},
        )
        records = ProjectCreationRecords(
            project={"id": project_id, "title": "Idea"},
            runtime={"project_id": project_id},
            question_instance={"id": uuid4()},
        )

        async def set_system_actor_fn(session):  # type: ignore[no-untyped-def]
            session.events.append("set_system_actor")

        async def resolve_org_membership_fn(session, **kwargs):  # type: ignore[no-untyped-def]
            session.events.append(("resolve_org_membership", kwargs))
            return {"org_id": "org-1"}

        with patch(
            "app.services.project_creation.resolve_project_creation_question_setup",
            AsyncMock(return_value=question_setup),
        ) as resolve_setup:
            with patch(
                "app.services.project_creation.create_project_records",
                AsyncMock(return_value=records),
            ) as create_records:
                result = await create_project_workflow(
                    admin_session_factory=sessions,
                    set_system_actor_fn=set_system_actor_fn,
                    resolve_org_membership_fn=resolve_org_membership_fn,
                    actor_user_id=user_id,
                    explicit_org_id="org-1",
                    title=" Idea ",
                    description="  ",
                    bank_key="lite",
                    allowed_bank_keys={"default", "lite"},
                )

        self.assertEqual(result.project["id"], project_id)
        resolve_setup.assert_awaited_once()
        self.assertEqual(resolve_setup.await_args.kwargs["bank_key"], "lite")
        create_records.assert_awaited_once()
        self.assertEqual(create_records.await_args.kwargs["title"], "Idea")
        self.assertIsNone(create_records.await_args.kwargs["description"])
        self.assertIn(
            ("execute", {"actor_type": "system"}),
            sessions.created[1].events,
        )

    async def test_create_project_records_inserts_project_runtime_and_message(
        self,
    ) -> None:
        now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        project_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()
        bank_id = uuid4()
        current_question_id = uuid4()
        next_question_id = uuid4()
        instance_id = uuid4()
        session = _FakeSession(
            [
                _FakeResult(
                    row={
                        "id": project_id,
                        "org_id": org_id,
                        "owner_user_id": user_id,
                        "title": "IdeaSense",
                        "description": None,
                        "question_bank_version_id": bank_id,
                        "current_stage": "problem",
                        "current_variant": "default",
                        "stage_status": "in_progress",
                        "settings": {"prompt_template_ids": []},
                        "is_archived": False,
                        "archived_at": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                ),
                _FakeResult(
                    row={
                        "project_id": project_id,
                        "org_id": org_id,
                        "stage": "problem",
                        "variant": "default",
                        "current_question_bank_question_id": current_question_id,
                        "next_question_bank_question_id": next_question_id,
                        "missing_paths": ["problem.initial_idea"],
                        "turn_state": "asking",
                        "runtime_version": 1,
                        "created_at": now,
                        "updated_at": now,
                    }
                ),
                _FakeResult(row=None),
                _FakeResult(row=None),
                _FakeResult(
                    row={
                        "id": instance_id,
                        "question_bank_question_id": current_question_id,
                        "status": "asked",
                        "asked_count": 0,
                        "created_at": now,
                        "updated_at": now,
                    }
                ),
                _FakeResult(row=None),
            ]
        )

        records = await create_project_records(
            session,
            title="IdeaSense",
            description=None,
            bank_id=bank_id,
            stage="problem",
            variant="default",
            current_question_id=current_question_id,
            next_question_id=next_question_id,
            missing_paths=["problem.initial_idea"],
            question_detail={
                "question_id": "S1Q1",
                "prompt": "Tell us briefly about your idea.",
                "prompt_meta": {
                    "ui": {"placeholder": "Short description"},
                },
                "stage": "problem",
                "variant": "default",
            },
            actor_user_id=user_id,
            project_settings={"prompt_template_ids": []},
        )

        self.assertEqual(records.project["id"], project_id)
        self.assertEqual(records.runtime["project_id"], project_id)
        self.assertEqual(records.question_instance["id"], instance_id)
        message_call = next(
            params
            for sql, params in session.calls
            if "INSERT INTO conversation_messages (" in sql and isinstance(params, dict)
        )
        self.assertEqual(message_call["content"], "Tell us briefly about your idea.")
        self.assertEqual(message_call["meta"]["content_locale"], "en")
        self.assertEqual(
            message_call["meta"]["question_meta"]["ui"],
            {"placeholder": "Short description"},
        )

    async def test_resolve_project_creation_question_setup_uses_org_bank(self) -> None:
        bank_id = uuid4()
        current_question_id = uuid4()
        next_question_id = uuid4()
        session = _FakeSession(
            [
                _FakeResult(row={"id": bank_id}),
                _FakeResult(
                    rows=[
                        {"id": current_question_id},
                        {"id": next_question_id},
                    ]
                ),
                _FakeResult(row={"paths": ["problem.initial_idea"]}),
                _FakeResult(
                    row={
                        "id": current_question_id,
                        "question_id": "S1Q1",
                        "prompt": "Describe your idea.",
                    }
                ),
            ]
        )

        setup = await resolve_project_creation_question_setup(
            session,
            org_id="org-1",
            stage="problem",
            variant="default",
        )

        self.assertEqual(setup.bank_id, bank_id)
        self.assertEqual(setup.current_question_id, current_question_id)
        self.assertEqual(setup.next_question_id, next_question_id)
        self.assertEqual(setup.missing_paths, ["problem.initial_idea"])
        self.assertEqual(setup.question_detail["prompt"], "Describe your idea.")
        self.assertEqual(
            session.calls[0][1], {"org_id": "org-1", "bank_key": "default"}
        )
        self.assertIn("AND bank_key = :bank_key", session.calls[0][0])

    async def test_resolve_project_creation_question_setup_selects_requested_bank(
        self,
    ) -> None:
        bank_id = uuid4()
        current_question_id = uuid4()
        session = _FakeSession(
            [
                _FakeResult(row={"id": bank_id}),
                _FakeResult(rows=[{"id": current_question_id}]),
                _FakeResult(row={"paths": None}),
                _FakeResult(
                    row={
                        "id": current_question_id,
                        "question_id": "S1Q1",
                        "prompt": "Describe your idea.",
                    }
                ),
            ]
        )

        setup = await resolve_project_creation_question_setup(
            session,
            org_id="org-1",
            stage="problem",
            variant="default",
            bank_key="lite",
        )

        self.assertEqual(setup.bank_id, bank_id)
        self.assertEqual(
            session.calls[0][1], {"org_id": "org-1", "bank_key": "lite"}
        )

    async def test_resolve_project_creation_question_setup_uses_fallback_bank(
        self,
    ) -> None:
        bank_id = uuid4()
        current_question_id = uuid4()
        session = _FakeSession(
            [
                _FakeResult(row=None),
                _FakeResult(row={"id": bank_id}),
                _FakeResult(rows=[{"id": current_question_id}]),
                _FakeResult(row={"paths": None}),
                _FakeResult(
                    row={
                        "id": current_question_id,
                        "question_id": "S1Q1",
                        "prompt": "Describe your idea.",
                    }
                ),
            ]
        )

        setup = await resolve_project_creation_question_setup(
            session,
            org_id="org-1",
            stage="problem",
            variant="default",
        )

        self.assertEqual(setup.bank_id, bank_id)
        self.assertIsNone(setup.next_question_id)
        self.assertEqual(setup.missing_paths, [])
        self.assertIn("WHERE org_id IS NULL", session.calls[1][0])

    async def test_resolve_project_creation_question_setup_requires_active_bank(
        self,
    ) -> None:
        session = _FakeSession([_FakeResult(row=None), _FakeResult(row=None)])

        with self.assertRaisesRegex(
            ProjectCreationQuestionSetupError,
            "No active question bank version available.",
        ):
            await resolve_project_creation_question_setup(
                session,
                org_id="org-1",
                stage="problem",
                variant="default",
            )

    async def test_resolve_project_creation_question_setup_requires_starter_question(
        self,
    ) -> None:
        session = _FakeSession([_FakeResult(row={"id": uuid4()}), _FakeResult(rows=[])])

        with self.assertRaisesRegex(
            ProjectCreationQuestionSetupError,
            "Question bank has no starter questions.",
        ):
            await resolve_project_creation_question_setup(
                session,
                org_id="org-1",
                stage="problem",
                variant="default",
            )


if __name__ == "__main__":
    unittest.main()
