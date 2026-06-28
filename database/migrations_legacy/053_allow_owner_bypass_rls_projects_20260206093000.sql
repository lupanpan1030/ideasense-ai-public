-- 053) Allow owner to bypass RLS for internal trigger reads
ALTER TABLE projects NO FORCE ROW LEVEL SECURITY;
ALTER TABLE question_bank_questions NO FORCE ROW LEVEL SECURITY;
