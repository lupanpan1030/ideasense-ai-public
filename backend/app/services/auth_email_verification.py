from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email_sender import send_verification_email
from app.core.email_verification import (
    VerificationError,
    issue_email_verification_token,
    verify_email_token,
)


class AuthEmailVerificationError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthEmailVerificationTokenError(AuthEmailVerificationError):
    pass


class AuthEmailVerificationUserError(AuthEmailVerificationError):
    pass


class AuthEmailVerificationMissingEmailError(AuthEmailVerificationError):
    pass


class AuthEmailVerificationDeliveryError(AuthEmailVerificationError):
    pass


async def verify_email_workflow(
    session: AsyncSession, *, token: str
) -> str:
    try:
        await verify_email_token(session, token=token)
    except VerificationError as exc:
        raise AuthEmailVerificationTokenError(str(exc)) from exc
    return "verified"


async def fetch_email_verification_user(
    session: AsyncSession, *, user_id: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT id, email, email_verified_at "
            "FROM users "
            "WHERE id = :user_id "
            "AND deleted_at IS NULL "
            "AND is_active IS TRUE"
        ),
        {"user_id": user_id},
    )
    return result.mappings().first()


async def resend_email_verification_workflow(
    session: AsyncSession, *, user_id: str
) -> str:
    user = await fetch_email_verification_user(session, user_id=user_id)
    if not user:
        raise AuthEmailVerificationUserError("User not found or inactive")

    if user.get("email_verified_at"):
        return "already_verified"

    email = user.get("email")
    if not isinstance(email, str) or not email.strip():
        raise AuthEmailVerificationMissingEmailError("User email is missing.")

    token_info = await issue_email_verification_token(
        session, user_id=str(user.get("id")), email=email
    )
    try:
        send_verification_email(to_email=email, token=token_info.token)
    except RuntimeError as exc:
        raise AuthEmailVerificationDeliveryError(
            "Unable to send verification email."
        ) from exc
    return "sent"
