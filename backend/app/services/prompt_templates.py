"""Prompt template resolution with DB overrides and file fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompt_loader import load_prompt, render_text


PROMPT_SOURCE_ENV = "IDEASENSE_PROMPT_SOURCE"
PROMPT_SOURCE_VALUES = {"file", "database", "hybrid"}


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    template_key: str
    version: str
    content: str
    purpose: str
    stage: str | None
    variant: str | None
    org_id: str | None


PromptTemplateRevisionScope = Literal["org", "global"]


class PromptTemplateRevisionValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PromptTemplateRevisionCreateError(RuntimeError):
    pass


def prompt_source() -> str:
    raw = os.getenv(PROMPT_SOURCE_ENV, "hybrid").strip().lower()
    return raw if raw in PROMPT_SOURCE_VALUES else "hybrid"


def normalize_template_key(template_name: str) -> str:
    return template_name.strip().lower().replace("/", ".")


def extract_prompt_template_ids(project_settings: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(project_settings, dict):
        return {}
    mapping = project_settings.get("prompt_template_ids")
    if not isinstance(mapping, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str) and value.strip():
            result[key.strip().lower()] = value.strip()
    return result


def get_prompt_template_id(
    project_settings: dict[str, Any] | None, template_key: str
) -> str | None:
    mapping = extract_prompt_template_ids(project_settings)
    return mapping.get(template_key)


def prompt_template_row_to_payload(
    row: Mapping[str, Any], *, include_org_id: bool = False
) -> dict[str, Any]:
    payload = {
        "id": str(row.get("id")),
        "template_key": row.get("template_key") or "",
        "version": row.get("version") or "",
        "content": row.get("content") or "",
        "purpose": row.get("purpose") or "",
        "stage": row.get("stage"),
        "variant": row.get("variant"),
        "is_active": bool(row.get("is_active")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
    if include_org_id:
        payload["org_id"] = str(row.get("org_id")) if row.get("org_id") else None
    return payload


async def list_active_global_prompt_template_payloads(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT id, template_key, version, content, purpose, stage, variant, "
            "is_active, created_at, updated_at "
            "FROM prompt_templates "
            "WHERE deleted_at IS NULL "
            "AND org_id IS NULL "
            "AND is_active "
            "ORDER BY template_key"
        )
    )
    return [prompt_template_row_to_payload(row) for row in result.mappings().all()]


async def resolve_unique_prompt_template_version(
    session: AsyncSession,
    template_key: str,
    base_version: str,
    *,
    scope: PromptTemplateRevisionScope,
) -> str:
    if scope == "org":
        org_scope_clause = "AND org_id = app_org_id()"
    elif scope == "global":
        org_scope_clause = "AND org_id IS NULL"
    else:
        raise ValueError(f"Unsupported prompt template scope: {scope}")
    version = base_version
    suffix = 1
    while True:
        result = await session.execute(
            text(
                "SELECT 1 "
                "FROM prompt_templates "
                "WHERE template_key = :template_key "
                "AND version = :version "
                "AND deleted_at IS NULL "
                f"{org_scope_clause} "
                "LIMIT 1"
            ),
            {"template_key": template_key, "version": version},
        )
        if not result.first():
            return version
        version = f"{base_version}.{suffix}"
        suffix += 1


async def create_prompt_template_revision(
    session: AsyncSession,
    *,
    template_key: str,
    content: str,
    purpose: str | None = None,
    stage: str | None = None,
    variant: str | None = None,
    version: str | None = None,
    scope: PromptTemplateRevisionScope,
    include_org_id: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized_key = normalize_template_key(template_key)
    if not normalized_key:
        raise PromptTemplateRevisionValidationError("template_key is required")

    normalized_content = content.strip()
    if not normalized_content:
        raise PromptTemplateRevisionValidationError("content is required")

    if scope == "org":
        base_result = await session.execute(
            text(
                "SELECT purpose, stage, variant "
                "FROM prompt_templates "
                "WHERE template_key = :template_key "
                "AND deleted_at IS NULL "
                "AND is_active "
                "AND (org_id = app_org_id() OR org_id IS NULL) "
                "ORDER BY CASE WHEN org_id IS NULL THEN 1 ELSE 0 END "
                "LIMIT 1"
            ),
            {"template_key": normalized_key},
        )
    elif scope == "global":
        base_result = await session.execute(
            text(
                "SELECT purpose, stage, variant "
                "FROM prompt_templates "
                "WHERE template_key = :template_key "
                "AND deleted_at IS NULL "
                "AND is_active "
                "AND org_id IS NULL "
                "LIMIT 1"
            ),
            {"template_key": normalized_key},
        )
    else:
        raise ValueError(f"Unsupported prompt template scope: {scope}")
    base_row = base_result.mappings().first()

    resolved_purpose = purpose or (base_row.get("purpose") if base_row else None)
    if not resolved_purpose:
        raise PromptTemplateRevisionValidationError("purpose is required")
    resolved_stage = stage if stage is not None else (
        base_row.get("stage") if base_row else None
    )
    resolved_variant = variant if variant is not None else (
        base_row.get("variant") if base_row else None
    )
    if resolved_variant and not resolved_stage:
        raise PromptTemplateRevisionValidationError("variant requires stage")

    base_version = (
        version.strip()
        if version and version.strip()
        else (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
    )
    resolved_version = await resolve_unique_prompt_template_version(
        session,
        normalized_key,
        base_version,
        scope=scope,
    )

    if scope == "org":
        await session.execute(
            text(
                "UPDATE prompt_templates "
                "SET is_active = false, updated_at = now() "
                "WHERE template_key = :template_key "
                "AND org_id = app_org_id() "
                "AND deleted_at IS NULL "
                "AND is_active"
            ),
            {"template_key": normalized_key},
        )
        result = await session.execute(
            text(
                "INSERT INTO prompt_templates ("
                "org_id, template_key, purpose, stage, variant, version, content, "
                "params, is_active"
                ") VALUES ("
                "app_org_id(), :template_key, :purpose, :stage, :variant, "
                ":version, :content, :params, true"
                ") "
                "RETURNING id, template_key, version, content, purpose, stage, "
                "variant, org_id, is_active, created_at, updated_at"
            ),
            {
                "template_key": normalized_key,
                "purpose": resolved_purpose,
                "stage": resolved_stage,
                "variant": resolved_variant,
                "version": resolved_version,
                "content": normalized_content,
                "params": None,
            },
        )
    else:
        await session.execute(
            text(
                "UPDATE prompt_templates "
                "SET is_active = false, updated_at = now() "
                "WHERE template_key = :template_key "
                "AND org_id IS NULL "
                "AND deleted_at IS NULL "
                "AND is_active"
            ),
            {"template_key": normalized_key},
        )
        result = await session.execute(
            text(
                "INSERT INTO prompt_templates ("
                "org_id, template_key, purpose, stage, variant, version, content, "
                "params, is_active"
                ") VALUES ("
                "NULL, :template_key, :purpose, :stage, :variant, "
                ":version, :content, :params, true"
                ") "
                "RETURNING id, template_key, version, content, purpose, stage, "
                "variant, is_active, created_at, updated_at"
            ),
            {
                "template_key": normalized_key,
                "purpose": resolved_purpose,
                "stage": resolved_stage,
                "variant": resolved_variant,
                "version": resolved_version,
                "content": normalized_content,
                "params": None,
            },
        )

    row = result.mappings().first()
    if not row:
        raise PromptTemplateRevisionCreateError("Unable to create prompt template.")
    return prompt_template_row_to_payload(row, include_org_id=include_org_id)


async def fetch_active_prompt_templates(
    session: AsyncSession,
) -> dict[str, PromptTemplate]:
    result = await session.execute(
        text(
            "SELECT DISTINCT ON (template_key) "
            "id, template_key, version, content, purpose, stage, variant, org_id "
            "FROM prompt_templates "
            "WHERE is_active "
            "AND deleted_at IS NULL "
            "AND (org_id = app_org_id() OR org_id IS NULL) "
            "ORDER BY template_key, CASE WHEN org_id IS NULL THEN 1 ELSE 0 END"
        )
    )
    templates: dict[str, PromptTemplate] = {}
    for row in result.mappings().all():
        template_key = row.get("template_key")
        if not template_key:
            continue
        templates[template_key] = PromptTemplate(
            id=str(row.get("id")),
            template_key=template_key,
            version=row.get("version") or "",
            content=row.get("content") or "",
            purpose=row.get("purpose") or "",
            stage=row.get("stage"),
            variant=row.get("variant"),
            org_id=str(row.get("org_id")) if row.get("org_id") else None,
        )
    return templates


async def fetch_active_prompt_template_ids(
    session: AsyncSession,
) -> dict[str, str]:
    templates = await fetch_active_prompt_templates(session)
    return {key: template.id for key, template in templates.items()}


async def _fetch_prompt_template_by_id(
    session: AsyncSession, template_id: str
) -> PromptTemplate | None:
    result = await session.execute(
        text(
            "SELECT id, template_key, version, content, purpose, stage, variant, org_id "
            "FROM prompt_templates "
            "WHERE id = :template_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"template_id": template_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    return PromptTemplate(
        id=str(row.get("id")),
        template_key=row.get("template_key") or "",
        version=row.get("version") or "",
        content=row.get("content") or "",
        purpose=row.get("purpose") or "",
        stage=row.get("stage"),
        variant=row.get("variant"),
        org_id=str(row.get("org_id")) if row.get("org_id") else None,
    )


async def _fetch_active_prompt_template(
    session: AsyncSession, template_key: str
) -> PromptTemplate | None:
    result = await session.execute(
        text(
            "SELECT id, template_key, version, content, purpose, stage, variant, org_id "
            "FROM prompt_templates "
            "WHERE template_key = :template_key "
            "AND is_active "
            "AND deleted_at IS NULL "
            "AND (org_id = app_org_id() OR org_id IS NULL) "
            "ORDER BY CASE WHEN org_id IS NULL THEN 1 ELSE 0 END "
            "LIMIT 1"
        ),
        {"template_key": template_key},
    )
    row = result.mappings().first()
    if not row:
        return None
    return PromptTemplate(
        id=str(row.get("id")),
        template_key=row.get("template_key") or template_key,
        version=row.get("version") or "",
        content=row.get("content") or "",
        purpose=row.get("purpose") or "",
        stage=row.get("stage"),
        variant=row.get("variant"),
        org_id=str(row.get("org_id")) if row.get("org_id") else None,
    )


async def resolve_prompt_template(
    session: AsyncSession,
    template_name: str,
    *,
    project_settings: dict[str, Any] | None = None,
) -> PromptTemplate | None:
    template_key = normalize_template_key(template_name)
    template_id = get_prompt_template_id(project_settings, template_key)
    if template_id:
        resolved = await _fetch_prompt_template_by_id(session, template_id)
        if resolved:
            return resolved
    return await _fetch_active_prompt_template(session, template_key)


async def render_prompt_template(
    session: AsyncSession,
    template_name: str,
    *,
    project_settings: dict[str, Any] | None = None,
    allow_fallback: bool = True,
    **vars: Any,
) -> str:
    source = prompt_source()
    if source == "file":
        return render_text(load_prompt(template_name), **vars)

    template = await resolve_prompt_template(
        session, template_name, project_settings=project_settings
    )
    if template:
        return render_text(template.content, **vars)

    if source == "database":
        raise RuntimeError(f"Prompt template missing: {template_name}")

    if allow_fallback:
        return render_text(load_prompt(template_name), **vars)

    raise RuntimeError(f"Prompt template missing: {template_name}")


__all__ = [
    "PromptTemplate",
    "PromptTemplateRevisionCreateError",
    "PromptTemplateRevisionValidationError",
    "PromptTemplateRevisionScope",
    "create_prompt_template_revision",
    "extract_prompt_template_ids",
    "fetch_active_prompt_template_ids",
    "fetch_active_prompt_templates",
    "list_active_global_prompt_template_payloads",
    "normalize_template_key",
    "prompt_source",
    "prompt_template_row_to_payload",
    "render_prompt_template",
    "resolve_prompt_template",
    "resolve_unique_prompt_template_version",
]
