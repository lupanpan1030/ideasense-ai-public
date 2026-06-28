-- 043) add expected_key_points to question_bank_questions
ALTER TABLE question_bank_questions
    ADD COLUMN expected_key_points TEXT[];
