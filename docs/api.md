# API Notes

The backend is a FastAPI app mounted under `/api/v1`.

## Runtime Documentation

During local development, FastAPI can expose generated API documentation from
the running backend:

- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

These routes describe the current backend code. Review examples before sharing
generated output publicly, because private schemas, admin routes, or internal
debug endpoints may be present.

## Source Ownership

- API router aggregation: `backend/app/main.py` and
  `backend/app/api/routes/__init__.py`
- HTTP route boundaries: `backend/app/api/routes/*`
- Business workflows: `backend/app/services/*`
- Shared infrastructure: `backend/app/core/*`
- Frontend API clients: `frontend/features/*` and `frontend/lib/api/*`

See `docs/OWNERSHIP_MAP.md` before moving route or client ownership.

## Public-Safe API Contract

A public-safe export may include generated OpenAPI output only after removing or
redacting:

- Private assessment examples.
- Production prompt or trace examples.
- Admin-only operational details that should remain private.
- Real user, project, report, or organization identifiers.
- Deployment-specific URLs or secrets.

If generated OpenAPI output depends on private prompt or question-bank content,
add synthetic examples instead of copying production examples.
