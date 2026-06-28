# Roles

Role and grant definitions for runtime/worker connections.

- `rls_roles.sql`: creates roles and grants for self-hosted Postgres.
- Managed DBs may not allow `ALTER ROLE ... BYPASSRLS`; use `--managed-db` to skip.
