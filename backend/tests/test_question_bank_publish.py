import asyncio
import hashlib
import json
from typing import Any

import yaml

from app.services.question_bank_drafts import QUESTION_BANK_KEY_ERROR
from app.services.question_bank_publish import (
    QuestionBankPublishCreateError,
    QuestionBankPublishNotFoundError,
    QuestionBankPublishValidationError,
    publish_question_bank_draft,
)


class _QueryResult:
    def __init__(
        self,
        row: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows

    def mappings(self) -> "_QueryResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._row

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows or [])


class _PublishSession:
    def __init__(
        self,
        rows: list[dict[str, Any] | list[dict[str, Any]] | None],
    ) -> None:
        self._rows = rows
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, statement, params=None) -> _QueryResult:
        self.calls.append((str(statement), dict(params or {})))
        row = self._rows.pop(0) if self._rows else None
        if isinstance(row, list):
            return _QueryResult(rows=row)
        return _QueryResult(row=row)


def _draft_row() -> dict[str, Any]:
    return {
        "id": "draft-1",
        "org_id": "org-1",
        "bank_key": "default",
        "version": "draft",
        "source": "draft_source",
        "is_active": False,
        "created_at": None,
        "activated_at": None,
    }


def _question_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "question-row-1",
            "question_id": "problem-q1",
            "stage": "problem",
            "variant": "default",
            "order_index": 1,
            "title": "Problem",
            "type_raw": "text",
            "prompt": "What problem are you solving?",
            "standard_question": None,
            "consultant_tactic": None,
            "instruction": None,
            "validation_rule": None,
            "schema_paths": ["problem.summary"],
            "expected_key_points": ["clear problem"],
            "prompt_meta": {"tone": "plain"},
            "meta": {"notes": "Founder-visible note"},
            "capture_intent": "problem",
            "capture_spec": {"path": "problem.summary"},
            "answer_examples": ["Example"],
            "expected_patch_example": {"problem": {"summary": "x"}},
            "display_if": {"stage": "problem"},
        },
        {
            "id": "question-row-2",
            "question_id": "tech-q1",
            "stage": "tech",
            "variant": "software",
            "order_index": 1,
            "title": "Tech",
            "type_raw": "text",
            "prompt": "How will you build it?",
            "standard_question": None,
            "consultant_tactic": None,
            "instruction": None,
            "validation_rule": None,
            "schema_paths": [],
            "expected_key_points": [],
            "prompt_meta": {},
            "meta": {},
            "capture_intent": None,
            "capture_spec": {},
            "answer_examples": [],
            "expected_patch_example": None,
            "display_if": None,
        },
    ]


def test_publish_question_bank_draft_inserts_new_active_version() -> None:
    new_version = {
        "id": "version-1",
        "org_id": "org-1",
        "bank_key": "default",
        "version": "20260606010101.1",
        "source": " Manual Source ",
        "is_active": True,
        "created_at": None,
        "activated_at": None,
    }
    session = _PublishSession(
        [
            _draft_row(),
            {"?column?": 1},
            None,
            _question_rows(),
            None,
            None,
            new_version,
            None,
            None,
            None,
        ]
    )

    published = asyncio.run(
        publish_question_bank_draft(
            session,
            bank_key=" Default ",
            version="20260606010101",
            source=" Manual Source ",
        )
    )

    assert published == new_version
    assert len(session.calls) == 10

    draft_sql, draft_params = session.calls[0]
    collision_sql, collision_params = session.calls[1]
    collision_retry_sql, collision_retry_params = session.calls[2]
    questions_sql, questions_params = session.calls[3]
    hash_sql, hash_params = session.calls[4]
    deactivate_sql, deactivate_params = session.calls[5]
    insert_sql, insert_params = session.calls[6]
    copy_sql, copy_params = session.calls[7]
    delete_draft_sql, delete_draft_params = session.calls[8]
    delete_questions_sql, delete_questions_params = session.calls[9]

    assert "version = 'draft'" in draft_sql
    assert draft_params == {"bank_key": "default"}
    assert "AND version = :version" in collision_sql
    assert collision_params == {
        "bank_key": "default",
        "version": "20260606010101",
    }
    assert collision_retry_params == {
        "bank_key": "default",
        "version": "20260606010101.1",
    }
    assert "SELECT id, question_id, stage, variant, order_index" in questions_sql
    assert "ORDER BY stage, variant, order_index" in questions_sql
    assert questions_params == {"bank_version_id": "draft-1"}
    assert "AND content_hash = :content_hash" in hash_sql
    assert hash_params["bank_key"] == "default"
    assert "UPDATE question_bank_versions" in deactivate_sql
    assert "SET is_active = false" in deactivate_sql
    assert deactivate_params == {"bank_key": "default"}
    assert "INSERT INTO question_bank_versions" in insert_sql
    assert insert_params["bank_key"] == "default"
    assert insert_params["version"] == "20260606010101.1"
    assert insert_params["source"] == " Manual Source "

    raw_json = json.loads(insert_params["raw_json"])
    assert raw_json["version"] == "20260606010101.1"
    assert raw_json["source"] == " Manual Source "
    assert raw_json["stages"]["problem"]["questions"][0]["notes"] == (
        "Founder-visible note"
    )
    assert raw_json["stages"]["tech"]["software"][0]["id"] == "tech-q1"
    raw_yaml = yaml.safe_dump(raw_json, sort_keys=False, allow_unicode=True)
    assert insert_params["raw_yaml"] == raw_yaml
    assert insert_params["content_hash"] == hashlib.sha256(
        raw_yaml.encode("utf-8")
    ).hexdigest()
    assert hash_params["content_hash"] == insert_params["content_hash"]
    assert "INSERT INTO question_bank_questions" in copy_sql
    assert copy_params == {"new_id": "version-1", "draft_id": "draft-1"}
    assert "UPDATE question_bank_versions" in delete_draft_sql
    assert "SET deleted_at = now()" in delete_draft_sql
    assert delete_draft_params == {"draft_id": "draft-1"}
    assert "UPDATE question_bank_questions" in delete_questions_sql
    assert delete_questions_params == {"draft_id": "draft-1"}


def test_publish_question_bank_draft_reactivates_existing_content_hash() -> None:
    existing_version = {
        "id": "version-existing",
        "org_id": "org-1",
        "bank_key": "default",
        "version": "20260606010101",
        "source": "draft_source",
        "is_active": True,
        "created_at": None,
        "activated_at": None,
    }
    session = _PublishSession(
        [
            _draft_row(),
            None,
            _question_rows(),
            {"id": "version-existing"},
            None,
            None,
            None,
            existing_version,
        ]
    )

    published = asyncio.run(
        publish_question_bank_draft(
            session,
            bank_key="default",
            version="20260606010101",
            source=None,
        )
    )

    assert published == existing_version
    assert len(session.calls) == 8
    statements = [call[0] for call in session.calls]
    assert not any("INSERT INTO question_bank_versions" in sql for sql in statements)
    assert not any("INSERT INTO question_bank_questions" in sql for sql in statements)
    assert not any("UPDATE question_bank_questions" in sql for sql in statements)
    assert "SET is_active = false" in statements[4]
    assert "SET is_active = true" in statements[5]
    assert "SET deleted_at = now()" in statements[6]
    assert session.calls[5][1] == {"version_id": "version-existing"}
    assert session.calls[6][1] == {"draft_id": "draft-1"}
    assert session.calls[7][1] == {"version_id": "version-existing"}


def test_publish_question_bank_draft_requires_valid_bank_key() -> None:
    session = _PublishSession([])

    try:
        asyncio.run(publish_question_bank_draft(session, bank_key="Default Bank"))
    except QuestionBankPublishValidationError as exc:
        assert exc.detail == QUESTION_BANK_KEY_ERROR
    else:
        raise AssertionError("Expected validation error")

    assert session.calls == []


def test_publish_question_bank_draft_requires_existing_draft() -> None:
    session = _PublishSession([None])

    try:
        asyncio.run(publish_question_bank_draft(session, bank_key="default"))
    except QuestionBankPublishNotFoundError as exc:
        assert str(exc) == "Draft not found"
    else:
        raise AssertionError("Expected not found error")

    assert len(session.calls) == 1


def test_publish_question_bank_draft_raises_when_insert_returns_no_row() -> None:
    session = _PublishSession(
        [
            _draft_row(),
            None,
            _question_rows(),
            None,
            None,
            None,
        ]
    )

    try:
        asyncio.run(
            publish_question_bank_draft(
                session,
                bank_key="default",
                version="20260606010101",
            )
        )
    except QuestionBankPublishCreateError as exc:
        assert str(exc) == "Unable to publish question bank"
    else:
        raise AssertionError("Expected create error")

    assert len(session.calls) == 6
    assert "INSERT INTO question_bank_versions" in session.calls[5][0]
