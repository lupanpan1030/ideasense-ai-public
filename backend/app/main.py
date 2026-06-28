import os

from app.core.env import load_backend_env, require_dev_flags_disabled_in_production

load_backend_env()
require_dev_flags_disabled_in_production()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.email_sender import log_email_diagnostics

app = FastAPI(title="IdeaSenseAI API")
raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
app_env = os.getenv("APP_ENV", "").strip().lower()
if not allowed_origins:
    if app_env == "production":
        raise RuntimeError(
            "CORS_ALLOW_ORIGINS must be set in production (comma-separated list)."
        )
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Auth-Token"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def _log_email_diagnostics() -> None:
    log_email_diagnostics()
