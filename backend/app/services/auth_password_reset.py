import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email_sender import send_password_reset_email
from app.core.password_reset import (
    PasswordResetError,
    issue_password_reset_token,
    verify_password_reset_token,
)


logger = logging.getLogger(__name__)


class AuthPasswordResetError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthPasswordResetInvalidTokenError(AuthPasswordResetError):
    pass


class AuthPasswordResetUserNotFoundError(AuthPasswordResetError):
    pass


async def fetch_password_reset_user(
    session: AsyncSession, *, email: str
) -> dict | None:
    result = await session.execute(
        text(
            "SELECT u.id, u.email "
            "FROM user_identities ui "
            "JOIN users u ON u.id = ui.user_id "
            "WHERE ui.provider = 'local' "
            "AND ui.deleted_at IS NULL "
            "AND u.deleted_at IS NULL "
            "AND u.is_active IS TRUE "
            "AND ui.email = :email"
        ),
        {"email": email},
    )
    return result.mappings().first()


async def request_password_reset_workflow(
    session: AsyncSession, *, email: str
) -> str:
    user = await fetch_password_reset_user(session, email=email)
    if user:
        token_info = await issue_password_reset_token(
            session, user_id=str(user.get("id")), email=str(user.get("email"))
        )
        try:
            send_password_reset_email(
                to_email=str(user.get("email")), token=token_info.token
            )
        except RuntimeError:
            logger.exception("PASSWORD_RESET_EMAIL_FAILED")
            # Do not leak account existence; return sent status regardless.

    return "sent"


async def confirm_password_reset_workflow(
    session: AsyncSession, *, token: str, password: str
) -> str:
    try:
        record = await verify_password_reset_token(session, token=token)
    except PasswordResetError as exc:
        raise AuthPasswordResetInvalidTokenError(str(exc)) from exc

    result = await session.execute(
        text(
            "UPDATE user_identities ui "
            "SET password_hash = crypt(:password, gen_salt('bf')) "
            "FROM users u "
            "WHERE ui.user_id = u.id "
            "AND ui.user_id = :user_id "
            "AND ui.provider = 'local' "
            "AND ui.deleted_at IS NULL "
            "AND u.deleted_at IS NULL "
            "AND u.is_active IS TRUE"
        ),
        {"password": password, "user_id": record.user_id},
    )
    if not result.rowcount:
        raise AuthPasswordResetUserNotFoundError("User not found or inactive")

    await session.execute(
        text(
            "UPDATE password_reset_tokens "
            "SET consumed_at = now() "
            "WHERE id = :token_id"
        ),
        {"token_id": record.token_id},
    )
    return "reset"
