-- Helper for manual debugging in psql.
-- Loads a system actor context so RLS doesn't hide rows.
SELECT set_config('app.actor_type', 'system', true);
