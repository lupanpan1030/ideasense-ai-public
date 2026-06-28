-- 001) Add per-question verification claim metadata
ALTER TABLE project_stage_verification_claims
    ALTER COLUMN assessment_id DROP NOT NULL;

ALTER TABLE project_stage_verification_claims
    ADD COLUMN question_id TEXT NULL,
    ADD COLUMN question_bank_question_id UUID NULL REFERENCES question_bank_questions(id) ON DELETE SET NULL,
    ADD COLUMN source_message_id BIGINT NULL REFERENCES conversation_messages(id) ON DELETE SET NULL,
    ADD COLUMN priority TEXT NULL,
    ADD COLUMN batch_id UUID NULL;

ALTER TABLE project_stage_verification_claims
    ADD CONSTRAINT project_stage_verification_claims_priority_check
    CHECK (priority IS NULL OR priority IN ('high','medium','low','none'));

CREATE INDEX project_stage_verification_claims_project_stage_question_created_idx
    ON project_stage_verification_claims (project_id, stage, question_bank_question_id, created_at DESC)
    WHERE deleted_at IS NULL;
