from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str
    captcha_token: str | None = None


class DevLoginRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    captcha_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    status: str


class ResendVerificationResponse(BaseModel):
    status: str


class ResendVerificationRequest(BaseModel):
    captcha_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: str
    captcha_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    token: str
    password: str


class PasswordResetResponse(BaseModel):
    status: str
