import os
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_async import AdminAsyncSessionLocal, AsyncSessionLocal
from app.core.email_verification import is_email_verified
from app.core.security import decode_access_token, maybe_refresh_access_token


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    org_id: str | None
    actor_type: str


@dataclass(frozen=True)
class VerifiedOrgContext:
    org_id: str
    email_verified: bool = True


DEV_AUTH_BYPASS = os.getenv("DEV_AUTH_BYPASS", "0") == "1"
DEV_USER_ID = os.getenv("DEV_USER_ID")
DEV_ORG_ID = os.getenv("DEV_ORG_ID")
DEV_ACTOR_TYPE = os.getenv("DEV_ACTOR_TYPE", "user")


def _require_env(value: str | None, name: str) -> str:
    if not value or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{name} is required when DEV_AUTH_BYPASS=1",
        )
    return value.strip()


async def get_actor_context(
    response: Response,
    authorization: str | None = Header(default=None),
) -> ActorContext:
    if DEV_AUTH_BYPASS:
        user_id = _require_env(DEV_USER_ID, "DEV_USER_ID")
        org_id = _require_env(DEV_ORG_ID, "DEV_ORG_ID")
        actor_type = (DEV_ACTOR_TYPE or "user").strip() or "user"
        return ActorContext(user_id=user_id, org_id=org_id, actor_type=actor_type)

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth token",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    try:
        payload = decode_access_token(token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    refreshed = maybe_refresh_access_token(payload)
    if refreshed:
        response.headers["X-Auth-Token"] = refreshed

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    actor_type_value = payload.get("actor_type")
    actor_type = (
        actor_type_value.strip()
        if isinstance(actor_type_value, str) and actor_type_value.strip()
        else "user"
    )
    return ActorContext(user_id=user_id, org_id=None, actor_type=actor_type)


def normalize_org_header(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid organization context",
        )
    try:
        UUID(cleaned)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid organization context",
        ) from exc
    return cleaned


async def set_system_actor(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )


async def require_verified_system_actor(
    session: AsyncSession,
    *,
    user_id: str,
    detail: str,
) -> bool:
    await set_system_actor(session)
    if not await is_email_verified(session, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
    return True


async def resolve_verified_org_context(
    session: AsyncSession,
    *,
    user_id: str,
    explicit_org_id: str | None,
    email_detail: str,
    no_org_detail: str,
) -> VerifiedOrgContext:
    email_verified = await require_verified_system_actor(
        session,
        user_id=user_id,
        detail=email_detail,
    )
    membership = await resolve_org_membership(
        session,
        user_id=user_id,
        explicit_org_id=explicit_org_id,
    )
    org_id = membership.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=no_org_detail,
        )
    return VerifiedOrgContext(org_id=str(org_id), email_verified=email_verified)


async def set_system_rls_context(
    session: AsyncSession,
    *,
    user_id: str,
    org_id: str,
) -> None:
    await session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": user_id},
    )
    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": org_id},
    )
    await session.execute(
        text("SELECT set_config('app.actor_type', :actor_type, true)"),
        {"actor_type": "system"},
    )


async def _fetch_active_membership(
    session: AsyncSession, *, user_id: str, org_id: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT om.id, om.org_id, om.org_role, om.status "
            "FROM organization_memberships om "
            "JOIN organizations o ON o.id = om.org_id AND o.deleted_at IS NULL "
            "WHERE om.user_id = :user_id "
            "AND om.org_id = :org_id "
            "AND om.status = 'active' "
            "AND om.deleted_at IS NULL "
            "LIMIT 1"
        ),
        {"user_id": user_id, "org_id": org_id},
    )
    return result.mappings().first()


async def _fetch_latest_active_membership(
    session: AsyncSession, *, user_id: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT om.id, om.org_id, om.org_role, om.status "
            "FROM organization_memberships om "
            "JOIN organizations o ON o.id = om.org_id AND o.deleted_at IS NULL "
            "WHERE om.user_id = :user_id "
            "AND om.status = 'active' "
            "AND om.deleted_at IS NULL "
            "ORDER BY om.created_at DESC "
            "LIMIT 1"
        ),
        {"user_id": user_id},
    )
    return result.mappings().first()


async def resolve_org_membership(
    session: AsyncSession, *, user_id: str, explicit_org_id: str | None
) -> dict:
    if explicit_org_id:
        membership = await _fetch_active_membership(
            session, user_id=user_id, org_id=explicit_org_id
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization access denied",
            )
        return membership

    membership = await _fetch_latest_active_membership(
        session, user_id=user_id
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active org membership",
        )
    return membership


async def _resolve_active_org_id(
    user_id: str, explicit_org_id: str | None
) -> str:
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required to resolve org membership",
        )

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )
            membership = await resolve_org_membership(
                session, user_id=user_id, explicit_org_id=explicit_org_id
            )
            org_id = membership.get("org_id")
            if not org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No active org membership",
                )
            return str(org_id)


async def get_db_session(
    actor: ActorContext = Depends(get_actor_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> AsyncSession:
    org_id = actor.org_id if DEV_AUTH_BYPASS else None
    if not org_id:
        explicit_org_id = None
        if not DEV_AUTH_BYPASS:
            explicit_org_id = normalize_org_header(x_org_id)
        org_id = await _resolve_active_org_id(actor.user_id, explicit_org_id)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.user_id', :user_id, true)"),
                {"user_id": actor.user_id},
            )
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": actor.actor_type},
            )
            await session.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": org_id},
            )
            yield session


async def get_admin_db_session() -> AsyncSession:
    if AdminAsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL_ADMIN is required for auth",
        )

    async with AdminAsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.actor_type', :actor_type, true)"),
                {"actor_type": "system"},
            )
            yield session
