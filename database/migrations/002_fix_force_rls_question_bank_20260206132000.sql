-- 002) Ensure question bank triggers can read under FORCE RLS
-- Keep RLS enabled, but allow security definer functions to bypass FORCE.
ALTER TABLE question_bank_questions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE projects NO FORCE ROW LEVEL SECURITY;
