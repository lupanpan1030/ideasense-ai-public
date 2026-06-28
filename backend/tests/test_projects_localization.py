import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4


stub_db = types.ModuleType("app.core.database_async")
stub_db.AdminAsyncSessionLocal = None
stub_db.AsyncSessionLocal = None
sys.modules.setdefault("app.core.database_async", stub_db)
sys.modules.setdefault("resend", types.ModuleType("resend"))

from app.api.routes import projects  # noqa: E402
from app.services import (  # noqa: E402
    project_conversations,
    project_creation,
    project_question_prompts,
)
from app.services.project_creation import ProjectCreationQuestionSetup  # noqa: E402
from app.services.project_question_prompts import QuestionPromptMissingError  # noqa: E402


class _FakeResult:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict | None:
        return self._row


class _LocalizeSession:
    def __init__(self, latest_message: dict | None, *, has_user_after: bool = False) -> None:
        self.latest_message = latest_message
        self.has_user_after = has_user_after
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append((sql, params))
        if "FROM conversation_messages cm " in sql and "JOIN project_question_instances" in sql:
            return _FakeResult(self.latest_message)
        if "FROM question_bank_questions" in sql:
            return _FakeResult(self.latest_message)
        if "AND cm.role = 'user'" in sql:
            return _FakeResult({"found": 1} if self.has_user_after else None)
        return _FakeResult(None)


class _AsyncContext:
    def __init__(self, value=None) -> None:
        self.value = value

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self.value

    async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return False


class _CreateProjectSession:
    def __init__(self, *, project_id, org_id, user_id, question_id, instance_id) -> None:
        self.project_id = project_id
        self.org_id = org_id
        self.user_id = user_id
        self.question_id = question_id
        self.instance_id = instance_id
        self.calls: list[tuple[str, dict | None]] = []
        self.now = datetime.now(timezone.utc)

    def begin(self) -> _AsyncContext:
        return _AsyncContext()

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        sql = str(statement)
        self.calls.append((sql, params))
        if "INSERT INTO projects (" in sql:
            return _FakeResult(
                {
                    "id": self.project_id,
                    "org_id": self.org_id,
                    "owner_user_id": self.user_id,
                    "title": params["title"],
                    "description": params["description"],
                    "question_bank_version_id": params["bank_id"],
                    "current_stage": params["stage"],
                    "current_variant": params["variant"],
                    "stage_status": "in_progress",
                    "settings": params["settings"],
                    "is_archived": False,
                    "archived_at": None,
                    "created_at": self.now,
                    "updated_at": self.now,
                }
            )
        if "INSERT INTO project_runtime (" in sql:
            return _FakeResult(
                {
                    "project_id": self.project_id,
                    "org_id": self.org_id,
                    "stage": params["stage"],
                    "variant": params["variant"],
                    "current_question_bank_question_id": params["current_question_id"],
                    "next_question_bank_question_id": params["next_question_id"],
                    "missing_paths": params["missing_paths"],
                    "turn_state": "asking",
                    "runtime_version": 1,
                    "created_at": self.now,
                    "updated_at": self.now,
                }
            )
        if "INSERT INTO project_question_instances (" in sql:
            return _FakeResult(
                {
                    "id": self.instance_id,
                    "question_bank_question_id": params["question_id"],
                    "status": "asked",
                    "asked_count": 0,
                    "created_at": self.now,
                    "updated_at": self.now,
                }
            )
        return _FakeResult(None)


class ProjectLocalizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_question_detail_returns_prompt_row(self) -> None:
        question_id = uuid4()
        session = _LocalizeSession(None)
        session.latest_message = {
            "id": question_id,
            "question_id": "S1Q1",
            "prompt": "Describe your idea.",
        }

        detail = await project_question_prompts.fetch_question_detail(
            session,
            question_id,
        )

        self.assertEqual(detail["prompt"], "Describe your idea.")

    async def test_fetch_question_detail_rejects_missing_prompt(self) -> None:
        with self.assertRaisesRegex(
            QuestionPromptMissingError,
            "Question prompt not found.",
        ):
            await project_question_prompts.fetch_question_detail(
                _LocalizeSession(None),
                uuid4(),
            )

    async def test_build_question_rewrite_prompt_uses_requested_locale_label(self) -> None:
        renderer = AsyncMock(
            return_value=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ]
        )
        question_detail = {
            "question_id": "q_problem_one_line",
            "stage": "problem",
            "variant": "default",
            "type_raw": "short_text",
            "prompt": "What is the core problem?",
            "instruction": "Keep it concise.",
            "validation_rule": "non_empty",
            "standard_question": "Describe the main problem.",
            "schema_paths": ["problem.one_line"],
        }

        with patch.object(project_question_prompts, "render_prompt_messages", renderer):
            prompt = await project_question_prompts.build_question_rewrite_prompt(
                session=object(),
                question_detail=question_detail,
                output_locale="zh",
                project_settings={"prompt_template_ids": []},
            )

        self.assertEqual(
            prompt,
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
        )
        self.assertEqual(len(renderer.await_args_list), 1)
        context = renderer.await_args.args[1]
        self.assertEqual(
            context.variables["output_language"],
            "Simplified Chinese",
        )
        self.assertEqual(context.task_key, "question_rewrite_basic")

    async def test_maybe_localize_latest_question_prompt_rewrites_unanswered_message(self) -> None:
        project_id = uuid4()
        question_bank_question_id = uuid4()
        latest_message = {
            "id": 42,
            "created_at": "2026-04-06T00:00:00+00:00",
            "meta": {"question_id": "S1Q1"},
            "settings": {"prompt_template_ids": []},
            "question_bank_question_id": question_bank_question_id,
        }
        session = _LocalizeSession(latest_message)

        with patch.object(
            project_conversations,
            "fetch_question_detail",
            AsyncMock(
                return_value={
                    "id": question_bank_question_id,
                    "question_id": "S1Q1",
                    "prompt": "In 2-3 sentences, describe your idea.",
                }
            ),
        ):
            with patch.object(
                project_conversations,
                "run_question_rewrite",
                AsyncMock(return_value="请用两三句话概述你的想法。"),
            ):
                set_system_actor = AsyncMock()
                await project_conversations.maybe_localize_latest_question_prompt(
                    session,
                    project_id=project_id,
                    output_locale="zh",
                    set_system_actor_fn=set_system_actor,
                )

        update_params = next(
            params
            for sql, params in session.calls
            if "UPDATE conversation_messages " in sql and isinstance(params, dict)
        )
        self.assertEqual(update_params["content"], "请用两三句话概述你的想法。")
        self.assertEqual(update_params["meta"]["content_locale"], "zh")

    async def test_maybe_localize_latest_question_prompt_skips_answered_message(self) -> None:
        project_id = uuid4()
        question_bank_question_id = uuid4()
        session = _LocalizeSession(
            {
                "id": 42,
                "created_at": "2026-04-06T00:00:00+00:00",
                "meta": {"question_id": "S1Q1"},
                "settings": {"prompt_template_ids": []},
                "question_bank_question_id": question_bank_question_id,
            },
            has_user_after=True,
        )

        with patch.object(
            project_conversations,
            "fetch_question_detail",
            AsyncMock(),
        ) as fetch_detail:
            with patch.object(
                project_conversations,
                "run_question_rewrite",
                AsyncMock(),
            ) as rewrite:
                await project_conversations.maybe_localize_latest_question_prompt(
                    session,
                    project_id=project_id,
                    output_locale="zh",
                    set_system_actor_fn=AsyncMock(),
                )

        fetch_detail.assert_not_awaited()
        rewrite.assert_not_awaited()

    async def test_maybe_localize_latest_question_prompt_preserves_user_answer_locale(self) -> None:
        project_id = uuid4()
        question_bank_question_id = uuid4()
        session = _LocalizeSession(
            {
                "id": 42,
                "created_at": "2026-04-06T00:00:00+00:00",
                "meta": {
                    "question_id": "S1Q2",
                    "content_locale": "zh",
                    "requested_output_locale": "en",
                    "locale_source": "latest_user_answer",
                },
                "settings": {"prompt_template_ids": []},
                "question_bank_question_id": question_bank_question_id,
            },
        )

        with patch.object(
            project_conversations,
            "fetch_question_detail",
            AsyncMock(),
        ) as fetch_detail:
            with patch.object(
                project_conversations,
                "run_question_rewrite",
                AsyncMock(),
            ) as rewrite:
                await project_conversations.maybe_localize_latest_question_prompt(
                    session,
                    project_id=project_id,
                    output_locale="en",
                    set_system_actor_fn=AsyncMock(),
                )

        fetch_detail.assert_not_awaited()
        rewrite.assert_not_awaited()

    async def test_create_project_does_not_block_on_question_rewrite(self) -> None:
        project_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()
        bank_id = uuid4()
        question_id = uuid4()
        next_question_id = uuid4()
        instance_id = uuid4()
        session = _CreateProjectSession(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            question_id=question_id,
            instance_id=instance_id,
        )

        def session_factory() -> _AsyncContext:
            return _AsyncContext(session)

        question_setup = ProjectCreationQuestionSetup(
            bank_id=bank_id,
            current_question_id=question_id,
            next_question_id=next_question_id,
            missing_paths=["problem.initial_idea"],
            question_detail={
                "question_id": "S1Q1",
                "prompt": "Tell us briefly about your idea.",
                "prompt_meta": {},
                "stage": "problem",
                "variant": "default",
            },
        )

        with patch.object(projects, "AdminAsyncSessionLocal", session_factory):
            with patch.object(
                projects,
                "resolve_org_membership",
                AsyncMock(return_value={"org_id": org_id}),
            ):
                with patch.object(projects, "set_system_actor", AsyncMock()):
                    with patch.object(
                        project_creation,
                        "resolve_project_creation_question_setup",
                        AsyncMock(return_value=question_setup),
                    ):
                        with patch.object(
                            project_creation,
                            "fetch_active_prompt_template_ids",
                            AsyncMock(return_value=[]),
                        ):
                            response = await projects.create_project(
                                projects.ProjectCreateRequest(
                                    title="Fast project",
                                    output_locale="zh",
                                ),
                                actor=projects.ActorContext(
                                    user_id=str(user_id),
                                    org_id=None,
                                    actor_type="user",
                                ),
                                x_org_id=None,
                            )

        self.assertEqual(response.project.id, project_id)
        self.assertEqual(response.runtime.project_id, project_id)
        message_params = next(
            params
            for sql, params in session.calls
            if "INSERT INTO conversation_messages (" in sql and isinstance(params, dict)
        )
        self.assertEqual(message_params["content"], "Tell us briefly about your idea.")
        self.assertEqual(message_params["meta"]["content_locale"], "en")


if __name__ == "__main__":
    unittest.main()
