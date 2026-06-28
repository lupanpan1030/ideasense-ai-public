"""Shared helpers for setting RLS session context in scripts."""

from __future__ import annotations

from psycopg2.extensions import connection


def set_actor_context(
    conn: connection,
    *,
    actor_type: str | None = "system",
    user_id: str | None = None,
    org_id: str | None = None,
) -> None:
    """Set RLS session variables for the current connection."""
    with conn.cursor() as cur:
        if actor_type:
            cur.execute(
                "SELECT set_config('app.actor_type', %s, true)",
                (actor_type,),
            )
        if user_id:
            cur.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (user_id,),
            )
        if org_id:
            cur.execute(
                "SELECT set_config('app.org_id', %s, true)",
                (org_id,),
            )


def set_system_actor(conn: connection) -> None:
    """Convenience for setting app.actor_type=system."""
    set_actor_context(conn, actor_type="system")
