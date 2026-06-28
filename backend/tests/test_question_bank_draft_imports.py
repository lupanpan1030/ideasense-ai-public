import asyncio
import json
from typing import Any

import yaml

from app.services.question_bank_drafts import QUESTION_BANK_KEY_ERROR
from app.services.question_bank_draft_imports import (
    QuestionBankDraftImportNotFoundError,
    QuestionBankDraftImportValidationError,
    import_question_bank_draft_json,
    import_question_bank_draft_yaml,
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


class _ImportSession:
    def __init__(
        self,
        rows: list[dict[str, Any] | list[dict[str, Any]] | None],
    ) -> None:
        self._rows = rows
        self.calls: list[tuple[str, Any]] = []

    async def execute(self, statement, params=None) -> _QueryResult:
        if isinstance(params, list):
            captured_params: Any = [dict(item) for item in params]
        else:
            captured_params = dict(params or {})
        self.calls.append((str(statement), captured_params))
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


def _question_row(question_id: str = "problem-q1") -> dict[str, Any]:
    return {
        "id": f"{question_id}-row",
        "question_id": question_id,
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
        "meta": {"notes": "note"},
        "capture_intent": "problem",
        "capture_spec": {"path": "problem.summary"},
        "answer_examples": ["Example"],
        "expected_patch_example": {"problem": {"summary": "x"}},
        "display_if": {"stage": "problem"},
    }


def _import_data() -> dict[str, Any]:
    return {
        "version": "draft",
        "source": "manual",
        "stages": {
            "problem": {
                "questions": [
                    {
                        "id": "problem-q1",
                        "title": "Problem",
                        "type": "text",
                        "prompt": "What problem are you solving?",
                        "schema_paths": ["problem.summary"],
                        "expected_key_points": ["clear problem"],
                        "prompt_meta": {"tone": "plain"},
                        "notes": "note",
                        "capture_intent": "problem",
                        "capture_spec": {"path": "problem.summary"},
                        "answer_examples": ["Example"],
                        "expected_patch_example": {"problem": {"summary": "x"}},
                        "display_if": {"stage": "problem"},
                    }
                ]
            },
            "tech": {
                "software": [
                    {
                        "id": "tech-q1",
                        "title": "Tech",
                        "type": "text",
                        "prompt": "How will you build it?",
                    }
                ]
            },
        },
    }


def test_import_question_bank_draft_yaml_replace_updates_raw_payload() -> None:
    raw_yaml = yaml.safe_dump(_import_data(), sort_keys=False, allow_unicode=True)
    session = _ImportSession([_draft_row(), None, None, None, [_question_row()]])

    result = asyncio.run(
        import_question_bank_draft_yaml(
            session,
            bank_key=" Default ",
            raw_yaml=raw_yaml,
            mode=None,
        )
    )

    assert result["draft"]["id"] == "draft-1"
    assert result["questions"] == [_question_row()]
    assert len(session.calls) == 5
    fetch_sql, fetch_params = session.calls[0]
    delete_sql, delete_params = session.calls[1]
    insert_sql, insert_params = session.calls[2]
    update_sql, update_params = session.calls[3]
    refetch_sql, refetch_params = session.calls[4]

    assert "version = 'draft'" in fetch_sql
    assert fetch_params == {"bank_key": "default"}
    assert "UPDATE question_bank_questions" in delete_sql
    assert "SET deleted_at = now()" in delete_sql
    assert delete_params == {"bank_version_id": "draft-1"}
    assert "INSERT INTO question_bank_questions" in insert_sql
    assert isinstance(insert_params, list)
    assert len(insert_params) == 2
    assert insert_params[0]["bank_version_id"] == "draft-1"
    assert insert_params[0]["question_id"] == "problem-q1"
    assert insert_params[0]["prompt_meta"] == '{"tone": "plain"}'
    assert insert_params[0]["capture_spec"] == '{"path": "problem.summary"}'
    assert insert_params[0]["meta"] == '{"notes": "note"}'
    assert insert_params[1]["stage"] == "tech"
    assert insert_params[1]["variant"] == "software"
    assert "UPDATE question_bank_versions" in update_sql
    assert "raw_yaml = :raw_yaml" in update_sql
    assert update_params["raw_yaml"] == raw_yaml
    assert json.loads(update_params["raw_json"]) == _import_data()
    assert update_params["bank_version_id"] == "draft-1"
    assert "ORDER BY stage, variant, order_index" in refetch_sql
    assert refetch_params == {"bank_version_id": "draft-1"}


def test_import_question_bank_draft_json_replace_generates_yaml_payload() -> None:
    data = _import_data()
    raw_json = json.dumps(data)
    session = _ImportSession([_draft_row(), None, None, None, [_question_row()]])

    result = asyncio.run(
        import_question_bank_draft_json(
            session,
            bank_key="default",
            raw_json=raw_json,
            mode="replace",
        )
    )

    assert result["questions"] == [_question_row()]
    update_sql, update_params = session.calls[3]
    assert "UPDATE question_bank_versions" in update_sql
    assert update_params["raw_yaml"] == yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
    )
    assert json.loads(update_params["raw_json"]) == data


def test_import_question_bank_draft_merge_updates_and_appends_questions() -> None:
    data = {
        "version": "draft",
        "stages": {
            "problem": {
                "questions": [
                    {
                        "id": "problem-q1",
                        "title": "Problem",
                        "type": "text",
                        "prompt": "Updated prompt",
                    },
                    {
                        "id": "problem-q2",
                        "title": "Second",
                        "type": "text",
                        "prompt": "What else?",
                    },
                ]
            }
        },
    }
    existing_rows = [
        {"id": "existing-row", "stage": "problem", "variant": "default", "question_id": "problem-q1", "order_index": 2}
    ]
    session = _ImportSession(
        [_draft_row(), existing_rows, None, None, None, [_question_row("problem-q2")]]
    )

    result = asyncio.run(
        import_question_bank_draft_json(
            session,
            bank_key="default",
            raw_json=json.dumps(data),
            mode="merge",
        )
    )

    assert result["questions"] == [_question_row("problem-q2")]
    assert len(session.calls) == 6
    existing_sql, existing_params = session.calls[1]
    update_question_sql, update_question_params = session.calls[2]
    insert_question_sql, insert_question_params = session.calls[3]
    update_version_sql, update_version_params = session.calls[4]

    assert "FROM question_bank_questions" in existing_sql
    assert existing_params == {"bank_version_id": "draft-1"}
    assert "UPDATE question_bank_questions" in update_question_sql
    assert "WHERE id = :row_id" in update_question_sql
    assert update_question_params["row_id"] == "existing-row"
    assert update_question_params["question_id"] == "problem-q1"
    assert "INSERT INTO question_bank_questions" in insert_question_sql
    assert insert_question_params["question_id"] == "problem-q2"
    assert insert_question_params["order_index"] == 3
    assert "UPDATE question_bank_versions" in update_version_sql
    assert "SET updated_at = now()" in update_version_sql
    assert "raw_yaml" not in update_version_sql
    assert update_version_params == {"bank_version_id": "draft-1"}


def test_import_question_bank_draft_yaml_replace_allows_empty_question_set() -> None:
    raw_yaml = "version: draft\nstages: {}\n"
    session = _ImportSession([_draft_row(), None, None, []])

    result = asyncio.run(
        import_question_bank_draft_yaml(
            session,
            bank_key="default",
            raw_yaml=raw_yaml,
            mode="replace",
        )
    )

    assert result["questions"] == []
    assert len(session.calls) == 4
    assert "INSERT INTO question_bank_questions" not in session.calls[2][0]
    assert "UPDATE question_bank_versions" in session.calls[2][0]


def test_import_question_bank_draft_validates_bank_key_before_payload() -> None:
    session = _ImportSession([])

    try:
        asyncio.run(
            import_question_bank_draft_yaml(
                session,
                bank_key="Default Bank",
                raw_yaml="",
            )
        )
    except QuestionBankDraftImportValidationError as exc:
        assert exc.detail == QUESTION_BANK_KEY_ERROR
    else:
        raise AssertionError("Expected validation error")

    assert session.calls == []


def test_import_question_bank_draft_requires_existing_draft_before_payload() -> None:
    session = _ImportSession([None])

    try:
        asyncio.run(
            import_question_bank_draft_json(
                session,
                bank_key="default",
                raw_json="",
            )
        )
    except QuestionBankDraftImportNotFoundError as exc:
        assert str(exc) == "Draft not found"
    else:
        raise AssertionError("Expected not found error")

    assert len(session.calls) == 1


def test_import_question_bank_draft_validation_errors_preserve_details() -> None:
    cases = [
        ("", "yaml is required"),
        ("[1, 2]", "YAML root must be a mapping"),
        ("stages:\n  - x", "stages must be a mapping"),
        ("stages:\n  tech: []\n", "tech stage must map variants to question lists"),
        ("stages:\n  unknown: {}\n", "unsupported stage: unknown"),
    ]
    for raw_yaml, expected in cases:
        session = _ImportSession([_draft_row()])
        try:
            asyncio.run(
                import_question_bank_draft_yaml(
                    session,
                    bank_key="default",
                    raw_yaml=raw_yaml,
                )
            )
        except QuestionBankDraftImportValidationError as exc:
            assert exc.detail == expected
        else:
            raise AssertionError("Expected validation error")

    json_cases = [
        ("", "json is required"),
        ("{", "Invalid JSON"),
        ("[]", "JSON root must be an object"),
    ]
    for raw_json, expected in json_cases:
        session = _ImportSession([_draft_row()])
        try:
            asyncio.run(
                import_question_bank_draft_json(
                    session,
                    bank_key="default",
                    raw_json=raw_json,
                )
            )
        except QuestionBankDraftImportValidationError as exc:
            assert exc.detail == expected
        else:
            raise AssertionError("Expected validation error")

    session = _ImportSession([_draft_row()])
    try:
        asyncio.run(
            import_question_bank_draft_json(
                session,
                bank_key="default",
                raw_json=json.dumps(_import_data()),
                mode="invalid",
            )
        )
    except QuestionBankDraftImportValidationError as exc:
        assert exc.detail == "mode must be replace or merge"
    else:
        raise AssertionError("Expected validation error")
