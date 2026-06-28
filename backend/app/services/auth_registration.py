import json
import re
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email_sender import send_verification_email
from app.core.email_verification import issue_email_verification_token


@dataclass(frozen=True)
class AuthRegistrationResult:
    user_id: str
    email: str


class AuthRegistrationError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthRegistrationDuplicateEmailError(AuthRegistrationError):
    pass


class AuthRegistrationSlugError(AuthRegistrationError):
    pass


class AuthRegistrationEmailDeliveryError(AuthRegistrationError):
    pass


def normalize_registration_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def derive_registration_org_name(display_name: str | None) -> str:
    if display_name:
        return f"{display_name}'s Workspace"
    return "Personal Workspace"


def slugify_registration_workspace(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "workspace"


async def fetch_registration_user_by_email(
    session: AsyncSession, *, email: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, email, display_name "
            "FROM users "
            "WHERE email = :email "
            "AND deleted_at IS NULL"
        ),
        {"email": email},
    )
    return result.mappings().first()


async def generate_unique_registration_slug(
    session: AsyncSession, base_slug: str
) -> str:
    slug = base_slug
    for _ in range(8):
        result = await session.execute(
            text(
                "SELECT 1 "
                "FROM organizations "
                "WHERE slug = :slug "
                "AND deleted_at IS NULL"
            ),
            {"slug": slug},
        )
        if not result.first():
            return slug
        slug = f"{base_slug}-{secrets.token_hex(3)}"
    raise AuthRegistrationSlugError(
        "Unable to generate a unique organization slug."
    )


async def register_local_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None,
) -> AuthRegistrationResult:
    display_name = normalize_registration_display_name(full_name)
    existing_user = await fetch_registration_user_by_email(
        session, email=email
    )
    if existing_user:
        raise AuthRegistrationDuplicateEmailError("Email is already registered")

    org_name = derive_registration_org_name(display_name)
    base_slug = slugify_registration_workspace(
        email.split("@", 1)[0] or "workspace"
    )
    org_slug = await generate_unique_registration_slug(session, base_slug)
    org_settings = {
        "org_type": "private",
        "allow_cohorts": False,
        "allow_mentor_assignments": False,
        "default_mentor_visibility": "summaries_only",
        "allow_admin_transfer_ownership": False,
    }

    org_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO organizations (id, name, slug, settings) "
            "VALUES (:id, :name, :slug, CAST(:settings AS jsonb))"
        ),
        {
            "id": org_id,
            "name": org_name,
            "slug": org_slug,
            "settings": json.dumps(org_settings),
        },
    )

    user_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO users (id, email, display_name, primary_org_id) "
            "VALUES (:id, :email, :display_name, :primary_org_id)"
        ),
        {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "primary_org_id": org_id,
        },
    )

    await session.execute(
        text(
            "INSERT INTO users_public_profiles (user_id, display_name) "
            "VALUES (:user_id, :display_name)"
        ),
        {"user_id": user_id, "display_name": display_name},
    )

    await session.execute(
        text(
            "INSERT INTO user_identities "
            "(user_id, provider, email, password_hash, status) "
            "VALUES (:user_id, 'local', :email, "
            "crypt(:password, gen_salt('bf')), 'active')"
        ),
        {"user_id": user_id, "email": email, "password": password},
    )

    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": org_id},
    )
    await session.execute(
        text(
            "INSERT INTO organization_memberships "
            "(org_id, user_id, org_role, status, created_by) "
            "VALUES (:org_id, :user_id, 'owner', 'active', NULL)"
        ),
        {"org_id": org_id, "user_id": user_id},
    )

    token_info = await issue_email_verification_token(
        session, user_id=user_id, email=email
    )
    try:
        send_verification_email(to_email=email, token=token_info.token)
    except RuntimeError as exc:
        raise AuthRegistrationEmailDeliveryError(
            "Unable to send verification email."
        ) from exc

    return AuthRegistrationResult(user_id=user_id, email=email)
