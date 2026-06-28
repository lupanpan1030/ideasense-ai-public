-- 053) Fix malformed projects.settings jsonb payloads and harden trigger function search_path

-- Normalize rows where settings was accidentally persisted as a JSON string.
UPDATE projects
SET settings = (settings #>> '{}')::jsonb
WHERE settings IS NOT NULL
  AND jsonb_typeof(settings) = 'string'
  AND left(ltrim(settings #>> '{}'), 1) IN ('{', '[');

-- SECURITY DEFINER functions should pin search_path to avoid function hijacking.
ALTER FUNCTION enforce_project_runtime_questions()
SET search_path = public, pg_temp;
