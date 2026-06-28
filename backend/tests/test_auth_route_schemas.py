from app.api.routes import auth
from app.schemas import auth as auth_schemas


def test_auth_route_reexports_schema_owned_dtos() -> None:
    assert auth.LoginRequest is auth_schemas.LoginRequest
    assert auth.DevLoginRequest is auth_schemas.DevLoginRequest
    assert auth.RegisterRequest is auth_schemas.RegisterRequest
    assert auth.TokenResponse is auth_schemas.TokenResponse
    assert auth.VerifyEmailRequest is auth_schemas.VerifyEmailRequest
    assert auth.PasswordResetRequest is auth_schemas.PasswordResetRequest
