import asyncio
from typing import Any

from app.services.question_bank_drafts import (
    QUESTION_BANK_KEY_ERROR,
    QuestionBankDraftConflictError,
    QuestionBankDraftCreateError,
    QuestionBankDraftNotFoundError,
    QuestionBankDraftValidationError,
    create_question_bank_draft,
    normalize_question_bank_key,
)


class _QueryResult:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self._row = row

    def mappings(self) -> "_QueryResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._row


class _DraftSession:
    def __init__(self, rows: list[dict[str, Any] | None]) -> None:
        self._rows = rows
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, statement, params=None) -> _QueryResult:
        self.calls.append((str(statement), dict(params or {})))
        row = self._rows.pop(0) if self._rows else None
        return _QueryResult(row)


def test_normalize_question_bank_key_rejects_empty_or_spaced_values() -> None:
    for value in ("", " ", "default bank"):
        try:
            normalize_question_bank_key(value)
        except QuestionBankDraftValidationError as exc:
            assert exc.detail == QUESTION_BANK_KEY_ERROR
        else:
            raise AssertionError("Expected validation error")


def test_normalize_question_bank_key_strips_and_lowercases() -> None:
    assert normalize_question_bank_key(" Default ") == "default"


def test_create_question_bank_draft_copies_active_bank_questions() -> None:
    session = _DraftSession(
        [
            None,
            {
                "id": "active-1",
                "version": "20260601000000",
                "raw_yaml": "version: 20260601000000",
                "raw_json": {"version": "20260601000000"},
            },
            {
                "id": "draft-1",
                "org_id": "org-1",
                "bank_key": "default",
                "version": "draft",
                "source": "draft_from:20260601000000",
                "is_active": False,
                "created_at": None,
                "activated_at": None,
            },
            None,
        ]
    )

    draft = asyncio.run(
        create_question_bank_draft(session, bank_key=" Default ")
    )

    assert draft["id"] == "draft-1"
    assert draft["bank_key"] == "default"
    assert draft["source"] == "draft_from:20260601000000"
    assert len(session.calls) == 4

    existing_sql, existing_params = session.calls[0]
    active_sql, active_params = session.calls[1]
    insert_sql, insert_params = session.calls[2]
    copy_sql, copy_params = session.calls[3]

    assert "version = 'draft'" in existing_sql
    assert "AND org_id = app_org_id()" in existing_sql
    assert existing_params == {"bank_key": "default"}
    assert "AND (org_id = app_org_id() OR org_id IS NULL)" in active_sql
    assert "ORDER BY (org_id IS NULL) ASC, activated_at DESC" in active_sql
    assert active_params == {"bank_key": "default"}
    assert "INSERT INTO question_bank_versions" in insert_sql
    assert "app_org_id(), :bank_key, 'draft'" in insert_sql
    assert insert_params["raw_json"] == '{"version": "20260601000000"}'
    assert insert_params["source"] == "draft_from:20260601000000"
    assert "INSERT INTO question_bank_questions" in copy_sql
    assert "FROM question_bank_questions" in copy_sql
    assert copy_params == {"draft_id": "draft-1", "active_id": "active-1"}


def test_create_question_bank_draft_rejects_existing_draft() -> None:
    session = _DraftSession([{"id": "draft-1"}])

    try:
        asyncio.run(create_question_bank_draft(session, bank_key="default"))
    except QuestionBankDraftConflictError as exc:
        assert str(exc) == "Draft already exists"
    else:
        raise AssertionError("Expected conflict error")

    assert len(session.calls) == 1


def test_create_question_bank_draft_requires_active_bank() -> None:
    session = _DraftSession([None, None])

    try:
        asyncio.run(create_question_bank_draft(session, bank_key="default"))
    except QuestionBankDraftNotFoundError as exc:
        assert str(exc) == "Active question bank not found"
    else:
        raise AssertionError("Expected not found error")

    assert len(session.calls) == 2


def test_create_question_bank_draft_raises_when_insert_returns_no_row() -> None:
    session = _DraftSession(
        [
            None,
            {"id": "active-1", "version": "20260601000000", "raw_json": {}},
            None,
        ]
    )

    try:
        asyncio.run(create_question_bank_draft(session, bank_key="default"))
    except QuestionBankDraftCreateError as exc:
        assert str(exc) == "Unable to create draft"
    else:
        raise AssertionError("Expected create error")

    assert len(session.calls) == 3
