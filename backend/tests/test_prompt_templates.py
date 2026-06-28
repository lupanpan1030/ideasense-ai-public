import asyncio
from datetime import datetime, timezone
from typing import Any

from app.services.prompt_templates import (
    PromptTemplateRevisionCreateError,
    PromptTemplateRevisionValidationError,
    create_prompt_template_revision,
    list_active_global_prompt_template_payloads,
    prompt_template_row_to_payload,
    resolve_unique_prompt_template_version,
)


class _VersionResult:
    def __init__(self, exists: bool) -> None:
        self._exists = exists

    def first(self) -> dict[str, int] | None:
        return {"?column?": 1} if self._exists else None


class _VersionSession:
    def __init__(self, collision_count: int) -> None:
        self._collision_count = collision_count
        self.statements: list[str] = []
        self.params: list[dict[str, str]] = []

    async def execute(self, statement, params=None) -> _VersionResult:
        self.statements.append(str(statement))
        self.params.append(dict(params or {}))
        return _VersionResult(len(self.params) <= self._collision_count)


_UNSET = object()


class _QueryResult:
    def __init__(
        self,
        *,
        mapping_first: dict[str, Any] | None = None,
        mapping_all: list[dict[str, Any]] | None = None,
        first_value: object = _UNSET,
        rowcount: int = 0,
    ) -> None:
        self._mapping_first = mapping_first
        self._mapping_all = mapping_all or []
        self._first_value = first_value
        self.rowcount = rowcount

    def mappings(self) -> "_QueryResult":
        return self

    def first(self) -> object:
        if self._first_value is _UNSET:
            return self._mapping_first
        return self._first_value

    def all(self) -> list[dict[str, Any]]:
        return self._mapping_all


class _CreateRevisionSession:
    def __init__(self, results: list[_QueryResult]) -> None:
        self._results = results
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, statement, params=None) -> _QueryResult:
        self.calls.append((str(statement), dict(params or {})))
        return self._results.pop(0)


def test_prompt_template_row_payload_normalizes_optional_org_id() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = prompt_template_row_to_payload(
        {
            "id": "template-1",
            "template_key": "stage.summary",
            "version": "20260101000000",
            "content": "Template body",
            "purpose": "report",
            "stage": "problem",
            "variant": "default",
            "org_id": "org-1",
            "is_active": 1,
            "created_at": created_at,
            "updated_at": None,
        },
        include_org_id=True,
    )

    assert payload == {
        "id": "template-1",
        "template_key": "stage.summary",
        "version": "20260101000000",
        "content": "Template body",
        "purpose": "report",
        "stage": "problem",
        "variant": "default",
        "org_id": "org-1",
        "is_active": True,
        "created_at": created_at,
        "updated_at": None,
    }


def test_prompt_template_row_payload_can_omit_org_id_for_platform_api() -> None:
    payload = prompt_template_row_to_payload(
        {
            "id": "template-1",
            "template_key": "stage.summary",
            "is_active": False,
            "org_id": "org-1",
        }
    )

    assert "org_id" not in payload
    assert payload["template_key"] == "stage.summary"
    assert payload["is_active"] is False


def test_list_active_global_prompt_template_payloads_uses_global_active_scope() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = _CreateRevisionSession(
        [
            _QueryResult(
                mapping_all=[
                    {
                        "id": "template-1",
                        "template_key": "stage.summary",
                        "version": "20260101000000",
                        "content": "Template body",
                        "purpose": "report",
                        "stage": "problem",
                        "variant": None,
                        "is_active": True,
                        "created_at": created_at,
                        "updated_at": None,
                    }
                ]
            )
        ]
    )

    payloads = asyncio.run(list_active_global_prompt_template_payloads(session))

    assert payloads == [
        {
            "id": "template-1",
            "template_key": "stage.summary",
            "version": "20260101000000",
            "content": "Template body",
            "purpose": "report",
            "stage": "problem",
            "variant": None,
            "is_active": True,
            "created_at": created_at,
            "updated_at": None,
        }
    ]
    statement = session.calls[0][0]
    assert "AND org_id IS NULL" in statement
    assert "AND is_active" in statement
    assert "ORDER BY template_key" in statement


def test_resolve_unique_prompt_template_version_uses_org_scope() -> None:
    session = _VersionSession(collision_count=2)

    version = asyncio.run(
        resolve_unique_prompt_template_version(
            session,
            "stage.summary",
            "20260101000000",
            scope="org",
        )
    )

    assert version == "20260101000000.2"
    assert [params["version"] for params in session.params] == [
        "20260101000000",
        "20260101000000.1",
        "20260101000000.2",
    ]
    assert all("org_id = app_org_id()" in statement for statement in session.statements)
    assert all("org_id IS NULL" not in statement for statement in session.statements)


def test_resolve_unique_prompt_template_version_uses_global_scope() -> None:
    session = _VersionSession(collision_count=1)

    version = asyncio.run(
        resolve_unique_prompt_template_version(
            session,
            "stage.summary",
            "20260101000000",
            scope="global",
        )
    )

    assert version == "20260101000000.1"
    assert [params["version"] for params in session.params] == [
        "20260101000000",
        "20260101000000.1",
    ]
    assert all("org_id IS NULL" in statement for statement in session.statements)
    assert all("org_id = app_org_id()" not in statement for statement in session.statements)


def test_create_prompt_template_revision_uses_org_scope_and_payload() -> None:
    session = _CreateRevisionSession(
        [
            _QueryResult(
                mapping_first={
                    "purpose": "assessment",
                    "stage": "problem",
                    "variant": "default",
                }
            ),
            _QueryResult(first_value=None),
            _QueryResult(rowcount=1),
            _QueryResult(
                mapping_first={
                    "id": "template-1",
                    "template_key": "stage.summary",
                    "version": "v1",
                    "content": "New body",
                    "purpose": "assessment",
                    "stage": "problem",
                    "variant": "default",
                    "org_id": "org-1",
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None,
                }
            ),
        ]
    )

    payload = asyncio.run(
        create_prompt_template_revision(
            session,
            template_key="Stage/Summary",
            content="  New body  ",
            version="v1",
            scope="org",
            include_org_id=True,
        )
    )

    assert payload == {
        "id": "template-1",
        "template_key": "stage.summary",
        "version": "v1",
        "content": "New body",
        "purpose": "assessment",
        "stage": "problem",
        "variant": "default",
        "org_id": "org-1",
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }
    assert [params.get("template_key") for _, params in session.calls] == [
        "stage.summary",
        "stage.summary",
        "stage.summary",
        "stage.summary",
    ]
    base_sql, version_sql, deactivate_sql, insert_sql = [
        statement for statement, _ in session.calls
    ]
    assert "AND (org_id = app_org_id() OR org_id IS NULL)" in base_sql
    assert "ORDER BY CASE WHEN org_id IS NULL THEN 1 ELSE 0 END" in base_sql
    assert "AND org_id = app_org_id()" in version_sql
    assert "UPDATE prompt_templates" in deactivate_sql
    assert "AND org_id = app_org_id()" in deactivate_sql
    assert "INSERT INTO prompt_templates" in insert_sql
    assert "app_org_id(), :template_key" in insert_sql
    assert session.calls[3][1]["content"] == "New body"
    assert session.calls[3][1]["purpose"] == "assessment"


def test_create_prompt_template_revision_uses_global_scope_and_version_collision() -> None:
    session = _CreateRevisionSession(
        [
            _QueryResult(
                mapping_first={
                    "purpose": "assessment",
                    "stage": None,
                    "variant": None,
                }
            ),
            _QueryResult(first_value={"?column?": 1}),
            _QueryResult(first_value=None),
            _QueryResult(rowcount=1),
            _QueryResult(
                mapping_first={
                    "id": "template-2",
                    "template_key": "stage.summary",
                    "version": "v1.1",
                    "content": "Global body",
                    "purpose": "assessment",
                    "stage": None,
                    "variant": None,
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None,
                }
            ),
        ]
    )

    payload = asyncio.run(
        create_prompt_template_revision(
            session,
            template_key="stage.summary",
            content="Global body",
            version="v1",
            scope="global",
        )
    )

    assert payload["version"] == "v1.1"
    assert "org_id" not in payload
    assert [params.get("version") for _, params in session.calls[1:3]] == [
        "v1",
        "v1.1",
    ]
    base_sql = session.calls[0][0]
    version_sql = session.calls[1][0]
    deactivate_sql = session.calls[3][0]
    insert_sql = session.calls[4][0]
    assert "AND org_id IS NULL" in base_sql
    assert "AND (org_id = app_org_id() OR org_id IS NULL)" not in base_sql
    assert "AND org_id IS NULL" in version_sql
    assert "UPDATE prompt_templates" in deactivate_sql
    assert "AND org_id IS NULL" in deactivate_sql
    assert "NULL, :template_key" in insert_sql


def test_create_prompt_template_revision_validates_required_fields() -> None:
    for kwargs, detail in (
        (
            {"template_key": " ", "content": "Body", "purpose": "assessment"},
            "template_key is required",
        ),
        (
            {"template_key": "stage.summary", "content": " ", "purpose": "assessment"},
            "content is required",
        ),
    ):
        session = _CreateRevisionSession([])
        try:
            asyncio.run(
                create_prompt_template_revision(
                    session,
                    scope="org",
                    **kwargs,
                )
            )
        except PromptTemplateRevisionValidationError as exc:
            assert exc.detail == detail
        else:
            raise AssertionError("Expected validation error")
        assert session.calls == []

    session = _CreateRevisionSession([_QueryResult(mapping_first=None)])
    try:
        asyncio.run(
            create_prompt_template_revision(
                session,
                template_key="stage.summary",
                content="Body",
                scope="org",
            )
        )
    except PromptTemplateRevisionValidationError as exc:
        assert exc.detail == "purpose is required"
    else:
        raise AssertionError("Expected validation error")

    session = _CreateRevisionSession([_QueryResult(mapping_first=None)])
    try:
        asyncio.run(
            create_prompt_template_revision(
                session,
                template_key="stage.summary",
                content="Body",
                purpose="assessment",
                variant="default",
                scope="global",
            )
        )
    except PromptTemplateRevisionValidationError as exc:
        assert exc.detail == "variant requires stage"
    else:
        raise AssertionError("Expected validation error")


def test_create_prompt_template_revision_raises_when_insert_returns_no_row() -> None:
    session = _CreateRevisionSession(
        [
            _QueryResult(mapping_first=None),
            _QueryResult(first_value=None),
            _QueryResult(rowcount=1),
            _QueryResult(mapping_first=None),
        ]
    )

    try:
        asyncio.run(
            create_prompt_template_revision(
                session,
                template_key="stage.summary",
                content="Body",
                purpose="assessment",
                version="v1",
                scope="global",
            )
        )
    except PromptTemplateRevisionCreateError as exc:
        assert str(exc) == "Unable to create prompt template."
    else:
        raise AssertionError("Expected create error")
