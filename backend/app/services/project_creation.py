from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.localization import DEFAULT_OUTPUT_LOCALE
from app.services.project_question_prompts import (
    QuestionPromptMissingError,
    fetch_question_detail,
)
from app.services.project_state_events import record_project_state_event
from app.services.prompt_templates import fetch_active_prompt_template_ids
from app.services.stage_gate_paths import resolve_stage_blocking_paths


class ProjectCreationQuestionSetupError(RuntimeError):
    pass


class ProjectCreationRecordsError(RuntimeError):
    pass


class ProjectCreationInputValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProjectCreationConfigurationError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProjectCreationForbiddenError(PermissionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProjectCreationConflictError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class ProjectCreationQuestionSetup:
    bank_id: Any
    current_question_id: Any
    next_question_id: Any | None
    missing_paths: list[str]
    question_detail: dict[str, Any]


@dataclass(frozen=True)
class ProjectCreationRecords:
    project: dict[str, Any]
    runtime: dict[str, Any]
    question_instance: dict[str, Any]


@dataclass(frozen=True)
class ProjectCreationInput:
    title: str
    description: str | None
    bank_key: str


SetSystemActorFn = Callable[[AsyncSession], Awaitable[None]]
ResolveOrgMembershipFn = Callable[..., Awaitable[dict[str, Any]]]


def normalize_project_creation_input(
    *,
    title: str | None,
    description: str | None,
    bank_key: str | None,
    allowed_bank_keys: set[str],
) -> ProjectCreationInput:
    normalized_title = title.strip() if title is not None else ""
    if not normalized_title:
        raise ProjectCreationInputValidationError("Title is required.")

    normalized_description = description.strip() if description else None
    if normalized_description is not None and not normalized_description:
        normalized_description = None

    normalized_bank_key = (bank_key or "default").strip().lower()
    if normalized_bank_key not in allowed_bank_keys:
        raise ProjectCreationInputValidationError(
            f"Unsupported bank_key: {bank_key!r}."
        )

    return ProjectCreationInput(
        title=normalized_title,
        description=normalized_description,
        bank_key=normalized_bank_key,
    )


async def _resolve_active_question_bank(
    session: AsyncSession,
    org_id: str,
    *,
    bank_key: str = "default",
) -> Any:
    # Select the active bank for this scope AND bank_key. Filtering by bank_key
    # is required: multiple bank_keys (e.g. "default" and "lite") can be active
    # in the same scope at once, so an unfiltered "newest active" query would
    # non-deterministically pick whichever bank was imported last.
    result = await session.execute(
        text(
            "SELECT id "
            "FROM question_bank_versions "
            "WHERE org_id = :org_id "
            "AND bank_key = :bank_key "
            "AND is_active "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {"org_id": org_id, "bank_key": bank_key},
    )
    row = result.mappings().first()
    if row and row.get("id"):
        return row.get("id")

    fallback = await session.execute(
        text(
            "SELECT id "
            "FROM question_bank_versions "
            "WHERE org_id IS NULL "
            "AND bank_key = :bank_key "
            "AND is_active "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {"bank_key": bank_key},
    )
    fallback_row = fallback.mappings().first()
    if fallback_row and fallback_row.get("id"):
        return fallback_row.get("id")

    raise ProjectCreationQuestionSetupError(
        f"No active question bank version available for bank_key={bank_key!r}."
    )


async def _resolve_initial_questions(
    session: AsyncSession,
    bank_id: Any,
    stage: str,
    variant: str,
) -> tuple[Any, Any | None]:
    result = await session.execute(
        text(
            "SELECT id "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "ORDER BY order_index ASC "
            "LIMIT 2"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    rows = [row.get("id") for row in result.mappings().all() if row.get("id")]
    if not rows:
        raise ProjectCreationQuestionSetupError(
            "Question bank has no starter questions."
        )
    current_id = rows[0]
    next_id = rows[1] if len(rows) > 1 else None
    return current_id, next_id


async def _resolve_missing_paths(
    session: AsyncSession,
    bank_id: Any,
    stage: str,
    variant: str,
) -> list[str]:
    result = await session.execute(
        text(
            "SELECT COALESCE(array_agg(DISTINCT path ORDER BY path), ARRAY[]::text[]) "
            "AS paths "
            "FROM ( "
            "SELECT unnest(COALESCE(schema_paths, ARRAY[]::text[])) AS path "
            "FROM question_bank_questions "
            "WHERE bank_version_id = :bank_id "
            "AND stage = :stage "
            "AND variant = :variant "
            "AND deleted_at IS NULL "
            "AND type_raw ILIKE 'Required%' "
            ") AS required_paths "
            "WHERE path IS NOT NULL "
            "AND btrim(path) <> ''"
        ),
        {"bank_id": str(bank_id), "stage": stage, "variant": variant},
    )
    row = result.mappings().first()
    paths = row.get("paths") if row else None
    if paths is None:
        return []
    return resolve_stage_blocking_paths(stage, list(paths))


async def resolve_project_creation_question_setup(
    session: AsyncSession,
    *,
    org_id: str,
    stage: str,
    variant: str,
    bank_key: str = "default",
) -> ProjectCreationQuestionSetup:
    bank_id = await _resolve_active_question_bank(
        session, org_id, bank_key=bank_key
    )
    current_question_id, next_question_id = await _resolve_initial_questions(
        session,
        bank_id,
        stage,
        variant,
    )
    missing_paths = await _resolve_missing_paths(
        session,
        bank_id,
        stage,
        variant,
    )
    try:
        question_detail = await fetch_question_detail(session, current_question_id)
    except QuestionPromptMissingError as exc:
        raise ProjectCreationQuestionSetupError(str(exc)) from exc

    return ProjectCreationQuestionSetup(
        bank_id=bank_id,
        current_question_id=current_question_id,
        next_question_id=next_question_id,
        missing_paths=missing_paths,
        question_detail=question_detail,
    )


async def create_project_records(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
    bank_id: Any,
    stage: str,
    variant: str,
    current_question_id: Any,
    next_question_id: Any | None,
    missing_paths: list[str],
    question_detail: dict[str, Any],
    actor_user_id: Any,
    project_settings: dict[str, Any] | None = None,
) -> ProjectCreationRecords:
    if not project_settings:
        prompt_template_ids = await fetch_active_prompt_template_ids(session)
        project_settings = {"prompt_template_ids": prompt_template_ids}

    project_result = await session.execute(
        text(
            "INSERT INTO projects ("
            "org_id, owner_user_id, title, description, question_bank_version_id, "
            "current_stage, current_variant, stage_status, settings"
            ") VALUES ("
            "app_org_id(), app_user_id(), :title, :description, :bank_id, "
            ":stage, :variant, 'in_progress', :settings"
            ") "
            "RETURNING "
            "id, org_id, owner_user_id, title, description, "
            "question_bank_version_id, current_stage, current_variant, "
            "stage_status, settings, is_archived, archived_at, created_at, updated_at"
        ).bindparams(bindparam("settings", type_=JSONB)),
        {
            "title": title,
            "description": description,
            "bank_id": str(bank_id),
            "stage": stage,
            "variant": variant,
            "settings": project_settings,
        },
    )
    project_row = project_result.mappings().first()
    if not project_row:
        raise ProjectCreationRecordsError("Unable to create project.")

    runtime_result = await session.execute(
        text(
            "INSERT INTO project_runtime ("
            "project_id, org_id, stage, variant, "
            "current_question_bank_question_id, next_question_bank_question_id, "
            "missing_paths"
            ") VALUES ("
            ":project_id, :org_id, :stage, :variant, :current_question_id, "
            ":next_question_id, :missing_paths"
            ") "
            "RETURNING "
            "project_id, org_id, stage, variant, "
            "current_question_bank_question_id, next_question_bank_question_id, "
            "missing_paths, turn_state, runtime_version, created_at, updated_at"
        ),
        {
            "project_id": project_row.get("id"),
            "org_id": project_row.get("org_id"),
            "stage": stage,
            "variant": variant,
            "current_question_id": current_question_id,
            "next_question_id": next_question_id,
            "missing_paths": missing_paths,
        },
    )
    runtime_row = runtime_result.mappings().first()
    if not runtime_row:
        raise ProjectCreationRecordsError("Unable to initialize project runtime.")

    await session.execute(
        text(
            "INSERT INTO project_states ("
            "project_id, org_id, bank_version_id, "
            "state_json, state_meta, state_version"
            ") VALUES ("
            ":project_id, :org_id, :bank_version_id, "
            ":state_json, :state_meta, :state_version"
            ")"
        ).bindparams(
            bindparam("state_json", type_=JSONB),
            bindparam("state_meta", type_=JSONB),
        ),
        {
            "project_id": project_row.get("id"),
            "org_id": project_row.get("org_id"),
            "bank_version_id": project_row.get("question_bank_version_id"),
            "state_json": {},
            "state_meta": {},
            "state_version": 0,
        },
    )
    await record_project_state_event(
        session,
        org_id=str(project_row.get("org_id")),
        project_id=str(project_row.get("id")),
        event_type="initialize_state",
        patch_json={"source": "project_create"},
        actor_type="system",
        actor_user_id=str(actor_user_id),
        next_state_version=0,
    )

    instance_result = await session.execute(
        text(
            "INSERT INTO project_question_instances ("
            "org_id, project_id, question_bank_question_id"
            ") VALUES ("
            ":org_id, :project_id, :question_id"
            ") "
            "RETURNING "
            "id, question_bank_question_id, status, asked_count, created_at, updated_at"
        ),
        {
            "org_id": project_row.get("org_id"),
            "project_id": project_row.get("id"),
            "question_id": current_question_id,
        },
    )
    instance_row = instance_result.mappings().first()
    if not instance_row:
        raise ProjectCreationRecordsError("Unable to initialize project questions.")

    assistant_prompt = question_detail.get("prompt")
    if not assistant_prompt:
        raise ProjectCreationRecordsError("Question prompt is missing.")

    prompt_meta = question_detail.get("prompt_meta")
    question_meta = None
    if isinstance(prompt_meta, dict):
        ui_meta = prompt_meta.get("ui")
        if isinstance(ui_meta, dict) and ui_meta:
            question_meta = {
                "question_id": question_detail.get("question_id"),
                "stage": question_detail.get("stage"),
                "variant": question_detail.get("variant"),
                "ui": ui_meta,
            }

    await session.execute(
        text(
            "INSERT INTO conversation_messages ("
            "org_id, project_id, role, stage, variant, "
            "question_instance_id, content, meta"
            ") VALUES ("
            "app_org_id(), :project_id, 'assistant', :stage, :variant, "
            ":question_instance_id, :content, :meta"
            ")"
        ).bindparams(bindparam("meta", type_=JSONB)),
        {
            "project_id": project_row.get("id"),
            "stage": stage,
            "variant": variant,
            "question_instance_id": instance_row.get("id"),
            "content": assistant_prompt,
            "meta": {
                "schema_version": "v1",
                "question_id": question_detail.get("question_id"),
                "content_locale": DEFAULT_OUTPUT_LOCALE,
                "question_meta": question_meta,
            },
        },
    )

    return ProjectCreationRecords(
        project=dict(project_row),
        runtime=dict(runtime_row),
        question_instance=dict(instance_row),
    )


async def _set_project_creation_rls_context(
    session: AsyncSession,
    *,
    actor_user_id: Any,
    org_id: Any,
    actor_type: str | None = None,
) -> None:
    await session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(actor_user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": str(org_id)},
    )
    if actor_type is not None:
        await session.execute(
            text("SELECT set_config('app.actor_type', :actor_type, true)"),
            {"actor_type": actor_type},
        )


async def _resolve_creation_org_id(
    session: AsyncSession,
    *,
    actor_user_id: Any,
    explicit_org_id: str | None,
    resolve_org_membership_fn: ResolveOrgMembershipFn,
) -> Any:
    membership = await resolve_org_membership_fn(
        session,
        user_id=str(actor_user_id),
        explicit_org_id=explicit_org_id,
    )
    org_id = membership.get("org_id")
    if not org_id:
        raise ProjectCreationForbiddenError("No active organization membership.")
    return org_id


async def create_project_workflow(
    *,
    admin_session_factory: Any | None,
    set_system_actor_fn: SetSystemActorFn,
    resolve_org_membership_fn: ResolveOrgMembershipFn,
    actor_user_id: Any,
    explicit_org_id: str | None,
    title: str | None,
    description: str | None,
    bank_key: str | None,
    allowed_bank_keys: set[str],
) -> ProjectCreationRecords:
    project_input = normalize_project_creation_input(
        title=title,
        description=description,
        bank_key=bank_key,
        allowed_bank_keys=allowed_bank_keys,
    )

    if admin_session_factory is None:
        raise ProjectCreationConfigurationError(
            "DATABASE_URL_ADMIN is required for project creation."
        )

    current_stage = "problem"
    current_variant = "default"
    org_id_value: str | None = None
    question_setup: ProjectCreationQuestionSetup | None = None

    async with admin_session_factory() as session:
        async with session.begin():
            await set_system_actor_fn(session)
            org_id = await _resolve_creation_org_id(
                session,
                actor_user_id=actor_user_id,
                explicit_org_id=explicit_org_id,
                resolve_org_membership_fn=resolve_org_membership_fn,
            )
            org_id_value = str(org_id)
            await _set_project_creation_rls_context(
                session,
                actor_user_id=actor_user_id,
                org_id=org_id_value,
            )
            question_setup = await resolve_project_creation_question_setup(
                session,
                org_id=org_id_value,
                stage=current_stage,
                variant=current_variant,
                bank_key=project_input.bank_key,
            )

    if question_setup is None or org_id_value is None:
        raise ProjectCreationConfigurationError(
            "Project initialization data is missing."
        )

    async with admin_session_factory() as session:
        async with session.begin():
            await set_system_actor_fn(session)
            org_id = await _resolve_creation_org_id(
                session,
                actor_user_id=actor_user_id,
                explicit_org_id=explicit_org_id,
                resolve_org_membership_fn=resolve_org_membership_fn,
            )
            if str(org_id) != org_id_value:
                raise ProjectCreationConflictError(
                    "Organization changed. Refresh and try again."
                )

            await _set_project_creation_rls_context(
                session,
                actor_user_id=actor_user_id,
                org_id=org_id,
                actor_type="system",
            )
            return await create_project_records(
                session,
                title=project_input.title,
                description=project_input.description,
                bank_id=question_setup.bank_id,
                stage=current_stage,
                variant=current_variant,
                current_question_id=question_setup.current_question_id,
                next_question_id=question_setup.next_question_id,
                missing_paths=question_setup.missing_paths,
                question_detail=question_setup.question_detail,
                actor_user_id=actor_user_id,
            )


__all__ = [
    "ProjectCreationConflictError",
    "ProjectCreationConfigurationError",
    "ProjectCreationForbiddenError",
    "ProjectCreationInput",
    "ProjectCreationInputValidationError",
    "ProjectCreationQuestionSetup",
    "ProjectCreationRecords",
    "ProjectCreationRecordsError",
    "ProjectCreationQuestionSetupError",
    "create_project_records",
    "create_project_workflow",
    "normalize_project_creation_input",
    "resolve_project_creation_question_setup",
]
