# Conventions

## Status
- Applies to the rebuild in `backend/`.

## Layering and Ownership
- `backend/app/api`: FastAPI routers and HTTP boundary; keep route handlers thin.
- `backend/app/api/deps.py`: dependency injection for DB sessions and auth (JWT parsing stays here; JWT primitives live in `backend/app/core/security.py`).
- `backend/app/schemas`: request/response Pydantic models only.
- `backend/app/models`: SQLModel definitions and DB mapping only.
- `backend/app/crud`: data access helpers; no HTTP or FastAPI types.
- `backend/app/services`: business workflows and orchestration.
- `backend/app/core`: shared infrastructure (config, database engines).
- `docs/OWNERSHIP_MAP.md`: canonical owner map for split-prone routes, helpers, services, frontend modules, and database contracts; update it when ownership moves.
- Route modules should not own reusable background job enqueue rules, prompt
  task wrappers, context path transforms, or stream event formatting. Put those
  in `backend/app/services` and import the service owner.
- `backend/app/worker.py` should keep worker-loop concerns only. Job execution
  bodies belong in service-owned worker handler modules.
- Feature-specific frontend components belong under `frontend/features/*`.
  `frontend/components` is for shared UI primitives; do not recreate admin
  feature components under `frontend/components/admin`.

## Naming
- Use snake_case for Python modules and functions.
- Use `*_service.py` for service modules and `*_schema.py` only if a schema is shared across domains.
- Prefer `get_*` for reads and `create_*`/`update_*`/`delete_*` for mutations.

## Error Handling
- Route handlers raise `HTTPException` and map domain errors to HTTP status codes.
- Service and CRUD layers should raise typed/domain errors and avoid FastAPI imports.
- DB session scopes must always rollback on errors (use the provided context managers).

## Logging
- Prefer `logging.getLogger(__name__)` and structured messages.
- Avoid `print` in runtime code; allow in scripts.

## Dependency Constraints
- FastAPI runtime uses async DB session (`backend/app/core/database_async.py`).
- Scripts/migrations use script-local sync DB helpers under `database/scripts/`.
- Primary database schema/seed source: `database/migrations/` + `database/seeds/`.
- Contract surfaces must align with `docs/spec/MASTER_SPEC.md` in the private
  repository; public-safe exports use `docs/spec/PUBLIC_SPEC.md` as the
  available contract summary. Add or run a contract checker when changing API or
  data contracts.
