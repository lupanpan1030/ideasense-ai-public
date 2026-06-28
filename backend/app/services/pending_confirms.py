from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.answer_meta import extract_answer_value_and_meta, set_answer_meta_entry
from app.services.context_paths import (
    infer_context_path_stage,
    pop_context_path_value,
    set_context_path_value,
)
from app.services.project_gate_sync import sync_runtime_gate_state
from app.services.project_state_events import record_project_state_event
from app.services.stage_payloads import normalize_user_edited_map


class PendingConfirmConflictError(RuntimeError):
    pass


class PendingConfirmNotFoundError(RuntimeError):
    pass


class PendingConfirmValidationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PendingConfirmConfigurationError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PendingConfirmForbiddenError(PermissionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


SetSystemActorFn = Callable[[AsyncSession], Awaitable[None]]
ResolveOrgMembershipFn = Callable[..., Awaitable[dict[str, Any]]]


def normalize_pending_confirm(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalize_pending_confirm_updates(updates: dict[str, Any] | None) -> dict[str, Any]:
    normalized = updates or {}
    if not isinstance(normalized, dict) or not normalized:
        raise PendingConfirmValidationError("Updates payload is required.")
    return normalized


def normalize_pending_confirm_resolve_paths(
    *,
    accept_paths: list[Any],
    reject_paths: list[Any],
) -> tuple[list[str], list[str]]:
    accepted = [
        path.strip()
        for path in accept_paths
        if isinstance(path, str) and path.strip()
    ]
    rejected = [
        path.strip()
        for path in reject_paths
        if isinstance(path, str) and path.strip()
    ]
    if accepted:
        accepted_set = set(accepted)
        rejected = [path for path in rejected if path not in accepted_set]
    return accepted, rejected


async def _set_pending_confirm_rls_context(
    session: AsyncSession,
    *,
    actor_user_id: Any,
    org_id: Any,
) -> None:
    await session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(actor_user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": str(org_id)},
    )
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )


async def _resolve_pending_confirm_org_id(
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
        raise PendingConfirmForbiddenError("No active organization membership.")
    return org_id


async def _run_pending_confirm_workflow(
    *,
    admin_session_factory: Any | None,
    set_system_actor_fn: SetSystemActorFn,
    resolve_org_membership_fn: ResolveOrgMembershipFn,
    actor_user_id: Any,
    explicit_org_id: str | None,
    operation: Callable[[AsyncSession, Any], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    if admin_session_factory is None:
        raise PendingConfirmConfigurationError(
            "DATABASE_URL_ADMIN is required for pending updates."
        )

    async with admin_session_factory() as session:
        async with session.begin():
            await set_system_actor_fn(session)
            org_id = await _resolve_pending_confirm_org_id(
                session,
                actor_user_id=actor_user_id,
                explicit_org_id=explicit_org_id,
                resolve_org_membership_fn=resolve_org_membership_fn,
            )
            await _set_pending_confirm_rls_context(
                session,
                actor_user_id=actor_user_id,
                org_id=org_id,
            )
            return await operation(session, org_id)


async def fetch_project_pending_confirm(
    session: AsyncSession,
    project_id: Any,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            "SELECT "
            "p.id AS project_id, "
            "p.updated_at AS project_updated_at, "
            "pr.updated_at AS runtime_updated_at, "
            "ps.state_version, "
            "ps.state_meta -> 'pending_confirm' AS pending_confirm, "
            "ps.updated_at AS state_updated_at "
            "FROM projects p "
            "LEFT JOIN project_runtime pr "
            "ON pr.project_id = p.id "
            "AND pr.org_id = p.org_id "
            "AND pr.deleted_at IS NULL "
            "LEFT JOIN project_states ps "
            "ON ps.project_id = p.id "
            "AND ps.org_id = p.org_id "
            "AND ps.deleted_at IS NULL "
            "WHERE p.id = :project_id "
            "AND p.org_id = app_org_id() "
            "AND p.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id)},
    )
    row = result.mappings().first()
    if not row:
        return None

    context_version = row.get("state_version")
    if context_version is None:
        context_version = 0
    return {
        "project_id": row.get("project_id"),
        "pending_confirm": normalize_pending_confirm(row.get("pending_confirm")),
        "context_version": context_version,
        "updated_at": row.get("state_updated_at")
        or row.get("project_updated_at")
        or row.get("runtime_updated_at"),
    }


def valid_pending_confirm_update_paths(updates: dict[str, Any]) -> list[str]:
    return sorted(
        path
        for path in updates.keys()
        if isinstance(path, str) and path.strip()
    )


def apply_pending_confirm_updates(
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    updates: dict[str, Any],
    current_stage: str,
) -> list[str]:
    pending_confirm = normalize_pending_confirm(state_meta.get("pending_confirm"))
    user_edited_map = normalize_user_edited_map(state_meta)

    for path, value in updates.items():
        if not isinstance(path, str) or not path.strip():
            continue
        resolved_value, answer_meta = extract_answer_value_and_meta(value)
        source = answer_meta.get("source")
        if source == "user":
            set_context_path_value(state_json, path, resolved_value)
            stage_key = infer_context_path_stage(path, current_stage)
            stage_paths = set(user_edited_map.get(stage_key, []))
            stage_paths.add(path)
            user_edited_map[stage_key] = sorted(stage_paths)
            set_answer_meta_entry(state_meta, path, **answer_meta)
            pop_context_path_value(pending_confirm, path)
            continue
        if value is None:
            pop_context_path_value(pending_confirm, path)
        else:
            set_context_path_value(pending_confirm, path, value)

    state_meta["pending_confirm"] = pending_confirm
    if user_edited_map:
        state_meta["user_edited_paths"] = user_edited_map
    return valid_pending_confirm_update_paths(updates)


def resolve_pending_confirm_paths(
    state_json: dict[str, Any],
    state_meta: dict[str, Any],
    accept_paths: list[str],
    reject_paths: list[str],
    current_stage: str,
) -> None:
    pending_confirm = normalize_pending_confirm(state_meta.get("pending_confirm"))
    user_edited_map = {
        stage: set(paths)
        for stage, paths in normalize_user_edited_map(state_meta).items()
    }

    for path in accept_paths:
        pending_value = pop_context_path_value(pending_confirm, path)
        if pending_value is None:
            continue
        resolved_value, answer_meta = extract_answer_value_and_meta(
            pending_value,
            default_source="mixed",
        )
        source = answer_meta.get("source")
        set_context_path_value(state_json, path, resolved_value)
        set_answer_meta_entry(state_meta, path, **answer_meta)
        if source == "user":
            stage_key = infer_context_path_stage(path, current_stage)
            user_edited_map.setdefault(stage_key, set()).add(path)

    for path in reject_paths:
        pop_context_path_value(pending_confirm, path)

    state_meta["pending_confirm"] = pending_confirm
    if user_edited_map:
        state_meta["user_edited_paths"] = {
            stage: sorted(paths)
            for stage, paths in user_edited_map.items()
        }


async def update_pending_confirm_context(
    session: AsyncSession,
    *,
    project_id: Any,
    org_id: Any,
    actor_user_id: Any,
    updates: dict[str, Any],
    client_context_version: int | None,
) -> dict[str, Any]:
    state_result = await session.execute(
        text(
            "SELECT "
            "ps.state_json, "
            "ps.state_meta, "
            "ps.state_version, "
            "p.current_stage "
            "FROM project_states ps "
            "JOIN projects p "
            "ON p.id = ps.project_id "
            "AND p.org_id = ps.org_id "
            "AND p.deleted_at IS NULL "
            "WHERE ps.project_id = :project_id "
            "AND ps.org_id = :org_id "
            "AND ps.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id), "org_id": str(org_id)},
    )
    state_row = state_result.mappings().first()
    if not state_row:
        raise PendingConfirmNotFoundError("Project context not found.")

    state_json = state_row.get("state_json") or {}
    if not isinstance(state_json, dict):
        state_json = {}
    state_meta = state_row.get("state_meta") or {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    current_stage = state_row.get("current_stage") or "problem"
    state_version = state_row.get("state_version") or 0

    if (
        client_context_version is not None
        and client_context_version != state_version
    ):
        raise PendingConfirmConflictError(
            "Context updated while you were away. Refresh and try again."
        )

    changed_paths = apply_pending_confirm_updates(
        state_json,
        state_meta,
        updates,
        current_stage,
    )
    pending_confirm = normalize_pending_confirm(state_meta.get("pending_confirm"))
    next_version = state_version + 1
    update_result = await session.execute(
        text(
            "UPDATE project_states "
            "SET state_json = :state_json, "
            "state_meta = :state_meta, "
            "state_version = :state_version "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "RETURNING state_meta, state_version, updated_at"
        ).bindparams(
            bindparam("state_json", type_=JSONB),
            bindparam("state_meta", type_=JSONB),
        ),
        {
            "project_id": str(project_id),
            "org_id": str(org_id),
            "state_json": state_json,
            "state_meta": state_meta,
            "state_version": next_version,
        },
    )
    await record_project_state_event(
        session,
        org_id=str(org_id),
        project_id=str(project_id),
        event_type="apply_patch",
        patch_json={
            "source": "pending_context_update",
            "stage": current_stage,
            "paths": changed_paths,
        },
        actor_type="user",
        actor_user_id=str(actor_user_id),
        prev_state_version=state_version,
        next_state_version=next_version,
    )
    await sync_runtime_gate_state(
        session,
        project_id=str(project_id),
        org_id=str(org_id),
        current_stage=current_stage,
        state_json=state_json,
        state_meta=state_meta,
    )
    updated_row = update_result.mappings().first()
    updated_meta = updated_row.get("state_meta") if updated_row else state_meta
    updated_pending = (
        updated_meta.get("pending_confirm")
        if isinstance(updated_meta, dict)
        else pending_confirm
    )
    if not isinstance(updated_pending, dict):
        updated_pending = pending_confirm
    updated_version = updated_row.get("state_version") if updated_row else next_version
    updated_at = (
        updated_row.get("updated_at")
        if updated_row
        else datetime.now(timezone.utc)
    )
    return {
        "project_id": project_id,
        "pending_confirm": updated_pending,
        "context_version": updated_version,
        "updated_at": updated_at,
    }


async def resolve_pending_confirm_context(
    session: AsyncSession,
    *,
    project_id: Any,
    org_id: Any,
    actor_user_id: Any,
    accept_paths: list[str],
    reject_paths: list[str],
    client_context_version: int | None,
) -> dict[str, Any]:
    project_result = await session.execute(
        text(
            "SELECT current_stage "
            "FROM projects "
            "WHERE id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id), "org_id": str(org_id)},
    )
    project_row = project_result.mappings().first()
    if not project_row:
        raise PendingConfirmNotFoundError("Project not found.")
    current_stage = project_row.get("current_stage") or "problem"

    state_result = await session.execute(
        text(
            "SELECT state_json, state_meta, state_version "
            "FROM project_states "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"project_id": str(project_id), "org_id": str(org_id)},
    )
    state_row = state_result.mappings().first()
    if not state_row:
        raise PendingConfirmNotFoundError("Project context not found.")

    state_json = state_row.get("state_json") or {}
    if not isinstance(state_json, dict):
        state_json = {}
    state_meta = state_row.get("state_meta") or {}
    if not isinstance(state_meta, dict):
        state_meta = {}
    state_version = state_row.get("state_version") or 0

    if (
        client_context_version is not None
        and client_context_version != state_version
    ):
        raise PendingConfirmConflictError(
            "Context updated while you were away. Refresh and try again."
        )

    resolve_pending_confirm_paths(
        state_json,
        state_meta,
        accept_paths,
        reject_paths,
        current_stage,
    )
    pending_confirm = normalize_pending_confirm(state_meta.get("pending_confirm"))

    next_version = state_version + 1
    update_result = await session.execute(
        text(
            "UPDATE project_states "
            "SET state_json = :state_json, "
            "state_meta = :state_meta, "
            "state_version = :state_version "
            "WHERE project_id = :project_id "
            "AND org_id = :org_id "
            "AND deleted_at IS NULL "
            "RETURNING state_meta, state_version, updated_at"
        ).bindparams(
            bindparam("state_json", type_=JSONB),
            bindparam("state_meta", type_=JSONB),
        ),
        {
            "project_id": str(project_id),
            "org_id": str(org_id),
            "state_json": state_json,
            "state_meta": state_meta,
            "state_version": next_version,
        },
    )
    await record_project_state_event(
        session,
        org_id=str(org_id),
        project_id=str(project_id),
        event_type="apply_patch",
        patch_json={
            "source": "pending_context_resolve",
            "stage": current_stage,
            "accepted_paths": accept_paths,
            "rejected_paths": reject_paths,
        },
        actor_type="user",
        actor_user_id=str(actor_user_id),
        prev_state_version=state_version,
        next_state_version=next_version,
    )
    await sync_runtime_gate_state(
        session,
        project_id=str(project_id),
        org_id=str(org_id),
        current_stage=current_stage,
        state_json=state_json,
        state_meta=state_meta,
    )
    updated_row = update_result.mappings().first()
    updated_meta = updated_row.get("state_meta") if updated_row else state_meta
    updated_pending = (
        updated_meta.get("pending_confirm")
        if isinstance(updated_meta, dict)
        else pending_confirm
    )
    if not isinstance(updated_pending, dict):
        updated_pending = pending_confirm
    updated_version = updated_row.get("state_version") if updated_row else next_version
    updated_at = (
        updated_row.get("updated_at")
        if updated_row
        else datetime.now(timezone.utc)
    )
    return {
        "project_id": project_id,
        "pending_confirm": updated_pending,
        "context_version": updated_version,
        "updated_at": updated_at,
    }


async def update_pending_confirm_workflow(
    *,
    admin_session_factory: Any | None,
    set_system_actor_fn: SetSystemActorFn,
    resolve_org_membership_fn: ResolveOrgMembershipFn,
    actor_user_id: Any,
    explicit_org_id: str | None,
    project_id: Any,
    updates: dict[str, Any] | None,
    client_context_version: int | None,
) -> dict[str, Any]:
    normalized_updates = normalize_pending_confirm_updates(updates)

    async def operation(session: AsyncSession, org_id: Any) -> dict[str, Any]:
        return await update_pending_confirm_context(
            session,
            project_id=project_id,
            org_id=org_id,
            actor_user_id=actor_user_id,
            updates=normalized_updates,
            client_context_version=client_context_version,
        )

    return await _run_pending_confirm_workflow(
        admin_session_factory=admin_session_factory,
        set_system_actor_fn=set_system_actor_fn,
        resolve_org_membership_fn=resolve_org_membership_fn,
        actor_user_id=actor_user_id,
        explicit_org_id=explicit_org_id,
        operation=operation,
    )


async def resolve_pending_confirm_workflow(
    *,
    admin_session_factory: Any | None,
    set_system_actor_fn: SetSystemActorFn,
    resolve_org_membership_fn: ResolveOrgMembershipFn,
    actor_user_id: Any,
    explicit_org_id: str | None,
    project_id: Any,
    accept_paths: list[Any],
    reject_paths: list[Any],
    client_context_version: int | None,
) -> dict[str, Any]:
    accepted, rejected = normalize_pending_confirm_resolve_paths(
        accept_paths=accept_paths,
        reject_paths=reject_paths,
    )

    async def operation(session: AsyncSession, org_id: Any) -> dict[str, Any]:
        return await resolve_pending_confirm_context(
            session,
            project_id=project_id,
            org_id=org_id,
            actor_user_id=actor_user_id,
            accept_paths=accepted,
            reject_paths=rejected,
            client_context_version=client_context_version,
        )

    return await _run_pending_confirm_workflow(
        admin_session_factory=admin_session_factory,
        set_system_actor_fn=set_system_actor_fn,
        resolve_org_membership_fn=resolve_org_membership_fn,
        actor_user_id=actor_user_id,
        explicit_org_id=explicit_org_id,
        operation=operation,
    )


__all__ = [
    "apply_pending_confirm_updates",
    "fetch_project_pending_confirm",
    "normalize_pending_confirm",
    "normalize_pending_confirm_resolve_paths",
    "normalize_pending_confirm_updates",
    "PendingConfirmConflictError",
    "PendingConfirmConfigurationError",
    "PendingConfirmForbiddenError",
    "PendingConfirmNotFoundError",
    "PendingConfirmValidationError",
    "resolve_pending_confirm_context",
    "resolve_pending_confirm_paths",
    "resolve_pending_confirm_workflow",
    "update_pending_confirm_context",
    "update_pending_confirm_workflow",
    "valid_pending_confirm_update_paths",
]
