-- 045) add prompt_meta to question_bank_questions
ALTER TABLE question_bank_questions
    ADD COLUMN prompt_meta JSONB NOT NULL DEFAULT '{}'::jsonb;
