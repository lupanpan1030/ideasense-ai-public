import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ActorContext, get_actor_context, get_admin_db_session
from app.core.captcha import CaptchaError, verify_captcha
from app.core.rate_limits import (
    RateLimitError,
    RateLimitSettings,
    enforce_rate_limit,
    get_rate_limit_count,
    load_rate_limit_settings,
)
from app.core.security import create_access_token
from app.schemas.auth import (
    DevLoginRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.auth_email_verification import (
    AuthEmailVerificationDeliveryError,
    AuthEmailVerificationMissingEmailError,
    AuthEmailVerificationTokenError,
    AuthEmailVerificationUserError,
    resend_email_verification_workflow,
    verify_email_workflow,
)
from app.services.auth_login import (
    AuthLoginInvalidCredentialsError,
    AuthLoginNoActiveMembershipError,
    dev_login_local_user,
    login_local_user,
)
from app.services.auth_password_reset import (
    AuthPasswordResetInvalidTokenError,
    AuthPasswordResetUserNotFoundError,
    confirm_password_reset_workflow,
    request_password_reset_workflow,
)
from app.services.auth_registration import (
    AuthRegistrationDuplicateEmailError,
    AuthRegistrationEmailDeliveryError,
    AuthRegistrationSlugError,
    register_local_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("ideasense")

DEV_LOGIN_ENABLED = os.getenv("DEV_LOGIN_ENABLED", "0") == "1"
GENERIC_REGISTRATION_FAILURE_DETAIL = "Unable to create account."


REGISTER_IP_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_REGISTER_IP",
    default_window_seconds=3600,
    default_max_count=10,
)
REGISTER_EMAIL_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_REGISTER_EMAIL",
    default_window_seconds=3600,
    default_max_count=3,
)
LOGIN_IP_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_LOGIN_IP",
    default_window_seconds=3600,
    default_max_count=30,
)
LOGIN_EMAIL_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_LOGIN_EMAIL",
    default_window_seconds=600,
    default_max_count=5,
)
VERIFY_RESEND_IP_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_VERIFY_RESEND_IP",
    default_window_seconds=3600,
    default_max_count=5,
)
VERIFY_RESEND_USER_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_VERIFY_RESEND_USER",
    default_window_seconds=3600,
    default_max_count=3,
)
PASSWORD_RESET_IP_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_PASSWORD_RESET_IP",
    default_window_seconds=3600,
    default_max_count=10,
)
PASSWORD_RESET_EMAIL_LIMIT = load_rate_limit_settings(
    "RATE_LIMIT_PASSWORD_RESET_EMAIL",
    default_window_seconds=3600,
    default_max_count=3,
)
LOGIN_FAIL_LIMIT = load_rate_limit_settings(
    "CAPTCHA_LOGIN_FAIL",
    default_window_seconds=900,
    default_max_count=3,
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip().lower()
    if not cleaned:
        return default
    return cleaned in {"1", "true", "yes", "on"}


CAPTCHA_LOGIN_REQUIRED = _env_bool("CAPTCHA_LOGIN_REQUIRED", False)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _resolve_client_ip(request: Request) -> str | None:
    if os.getenv("TRUST_PROXY_HEADERS", "0").strip() == "1":
        forwarded = request.headers.get("x-forwarded-for") or request.headers.get(
            "x-real-ip"
        )
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            if ip:
                return ip
    client = request.client
    return client.host if client else None


async def _require_captcha(token: str | None, client_ip: str | None) -> None:
    try:
        await verify_captcha(token, remote_ip=client_ip)
    except CaptchaError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


async def _apply_rate_limit(
    session: AsyncSession,
    *,
    scope: str,
    key: str | None,
    settings: RateLimitSettings,
) -> None:
    if not key:
        return
    try:
        await enforce_rate_limit(
            session,
            scope=scope,
            key=key,
            window_seconds=settings.window_seconds,
            max_count=settings.max_count,
        )
    except RateLimitError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds
            else None
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers,
        ) from exc


async def _should_require_login_captcha(
    session: AsyncSession,
    *,
    client_ip: str | None,
    email: str,
) -> bool:
    if CAPTCHA_LOGIN_REQUIRED:
        return True
    threshold = LOGIN_FAIL_LIMIT.max_count
    if threshold <= 0:
        return False
    counts: list[int] = []
    if client_ip:
        counts.append(
            await get_rate_limit_count(
                session,
                scope="login_fail:ip",
                key=client_ip,
                window_seconds=LOGIN_FAIL_LIMIT.window_seconds,
            )
        )
    counts.append(
        await get_rate_limit_count(
            session,
            scope="login_fail:email",
            key=email,
            window_seconds=LOGIN_FAIL_LIMIT.window_seconds,
        )
    )
    return max(counts) >= threshold if counts else False


@router.post("/login", response_model=TokenResponse)
async def login_with_email(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_admin_db_session),
) -> TokenResponse:
    email = _normalize_email(payload.email)
    password = payload.password.strip()
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )

    client_ip = _resolve_client_ip(request)
    await _apply_rate_limit(
        session,
        scope="login:ip",
        key=client_ip,
        settings=LOGIN_IP_LIMIT,
    )
    await _apply_rate_limit(
        session,
        scope="login:email",
        key=email,
        settings=LOGIN_EMAIL_LIMIT,
    )
    if await _should_require_login_captcha(
        session, client_ip=client_ip, email=email
    ):
        await _require_captcha(payload.captcha_token, client_ip)

    try:
        authenticated = await login_local_user(
            session,
            email=email,
            password=password,
            client_ip=client_ip,
            fail_limit=LOGIN_FAIL_LIMIT,
        )
    except AuthLoginInvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
        ) from exc
    except AuthLoginNoActiveMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc

    token = create_access_token(
        user_id=authenticated.user_id,
        actor_type="user",
        email=authenticated.email,
    )
    return TokenResponse(access_token=token)


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_admin_db_session),
) -> VerifyEmailResponse:
    try:
        verification_status = await verify_email_workflow(
            session, token=payload.token
        )
    except AuthEmailVerificationTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    return VerifyEmailResponse(status=verification_status)


@router.post("/verify-email/resend", response_model=ResendVerificationResponse)
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest | None = None,
    actor: ActorContext = Depends(get_actor_context),
    session: AsyncSession = Depends(get_admin_db_session),
) -> ResendVerificationResponse:
    client_ip = _resolve_client_ip(request)
    await _apply_rate_limit(
        session,
        scope="verify_resend:ip",
        key=client_ip,
        settings=VERIFY_RESEND_IP_LIMIT,
    )
    await _apply_rate_limit(
        session,
        scope="verify_resend:user",
        key=str(actor.user_id),
        settings=VERIFY_RESEND_USER_LIMIT,
    )
    await _require_captcha(
        payload.captcha_token if payload else None, client_ip
    )

    try:
        verification_status = await resend_email_verification_workflow(
            session, user_id=str(actor.user_id)
        )
    except AuthEmailVerificationUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc
    except AuthEmailVerificationMissingEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except AuthEmailVerificationDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.detail,
        ) from exc
    return ResendVerificationResponse(status=verification_status)


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_admin_db_session),
) -> PasswordResetResponse:
    email = _normalize_email(payload.email)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required",
        )
    if any(ch.isspace() for ch in email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email must not contain spaces",
        )

    client_ip = _resolve_client_ip(request)
    await _apply_rate_limit(
        session,
        scope="password_reset:ip",
        key=client_ip,
        settings=PASSWORD_RESET_IP_LIMIT,
    )
    await _apply_rate_limit(
        session,
        scope="password_reset:email",
        key=email,
        settings=PASSWORD_RESET_EMAIL_LIMIT,
    )
    await _require_captcha(payload.captcha_token, client_ip)

    reset_status = await request_password_reset_workflow(
        session, email=email
    )
    return PasswordResetResponse(status=reset_status)


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_admin_db_session),
) -> PasswordResetResponse:
    password = payload.password.strip()
    if not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password is required",
        )
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be between 8 and 128 characters",
        )

    try:
        reset_status = await confirm_password_reset_workflow(
            session, token=payload.token, password=password
        )
    except AuthPasswordResetInvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except AuthPasswordResetUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
    return PasswordResetResponse(status=reset_status)


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login_with_email(
    payload: DevLoginRequest,
    session: AsyncSession = Depends(get_admin_db_session),
) -> TokenResponse:
    if not DEV_LOGIN_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is disabled",
        )

    email = _normalize_email(payload.email)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required",
        )

    try:
        authenticated = await dev_login_local_user(session, email=email)
    except AuthLoginInvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
        ) from exc
    except AuthLoginNoActiveMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc

    token = create_access_token(
        user_id=authenticated.user_id,
        actor_type="user",
        email=authenticated.email,
    )
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse)
async def register_with_email(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_admin_db_session),
) -> TokenResponse:
    try:
        email = _normalize_email(payload.email)
        password = payload.password.strip()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email is required",
            )
        if any(ch.isspace() for ch in email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email must not contain spaces",
            )
        if not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password is required",
            )
        if len(password) < 8 or len(password) > 128:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be between 8 and 128 characters",
            )

        client_ip = _resolve_client_ip(request)
        await _apply_rate_limit(
            session,
            scope="register:ip",
            key=client_ip,
            settings=REGISTER_IP_LIMIT,
        )
        await _apply_rate_limit(
            session,
            scope="register:email",
            key=email,
            settings=REGISTER_EMAIL_LIMIT,
        )
        await _require_captcha(payload.captcha_token, client_ip)

        try:
            registration = await register_local_user(
                session,
                email=email,
                password=password,
                full_name=payload.full_name,
            )
        except AuthRegistrationDuplicateEmailError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=GENERIC_REGISTRATION_FAILURE_DETAIL,
            ) from exc
        except AuthRegistrationSlugError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=exc.detail,
            ) from exc
        except AuthRegistrationEmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=exc.detail,
            ) from exc

        token = create_access_token(
            user_id=registration.user_id,
            actor_type="user",
            email=registration.email,
        )
        return TokenResponse(access_token=token)
    except Exception:
        logger.exception("REGISTER_FAILED")
        raise
