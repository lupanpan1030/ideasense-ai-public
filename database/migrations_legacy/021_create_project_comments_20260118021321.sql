-- 021) project_comments
CREATE TABLE project_comments (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                    UUID NOT NULL,
    project_id                UUID NOT NULL,
    author_user_id            UUID NOT NULL REFERENCES users(id),
    visibility                TEXT NOT NULL DEFAULT 'student_and_mentors',
    status                    TEXT NOT NULL DEFAULT 'open',
    content                   TEXT NOT NULL,
    content_format            TEXT NOT NULL DEFAULT 'markdown',
    target_stage              TEXT NULL,
    target_question_instance_id UUID NULL REFERENCES project_question_instances(id),
    target_message_id         BIGINT NULL REFERENCES conversation_messages(id),
    target_report_id          UUID NULL REFERENCES project_reports(id),
    target_section_key        TEXT NULL,
    parent_comment_id         UUID NULL REFERENCES project_comments(id),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                TIMESTAMPTZ,
    CHECK (visibility IN ('student_and_mentors','mentors_only','private')),
    CHECK (status IN ('open','resolved','archived')),
    CHECK (content_format IN ('markdown','text')),
    CHECK (target_stage IS NULL OR target_stage IN ('problem','market','tech','report')),
    CHECK (
        num_nonnulls(
            target_stage,
            target_question_instance_id,
            target_message_id,
            target_report_id,
            target_section_key
        ) <= 1
    ),
    FOREIGN KEY (org_id, project_id)
        REFERENCES projects (org_id, id) ON DELETE CASCADE
);

CREATE INDEX project_comments_project_created_idx
    ON project_comments (project_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX project_comments_project_status_idx
    ON project_comments (project_id, status)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_project_comment_author_membership()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM organization_memberships om
        WHERE om.org_id = NEW.org_id
          AND om.user_id = NEW.author_user_id
          AND om.status = 'active'
          AND om.deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'author_user_id % is not an active member of org %',
            NEW.author_user_id, NEW.org_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_comments_author_guard
    BEFORE INSERT OR UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_comment_author_membership();

CREATE OR REPLACE FUNCTION enforce_project_comment_targets()
RETURNS trigger AS $$
DECLARE
    target_project_id UUID;
    target_org_id UUID;
BEGIN
    IF NEW.target_question_instance_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM project_question_instances
         WHERE id = NEW.target_question_instance_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'question_instance % not found or deleted',
                NEW.target_question_instance_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'question_instance % does not belong to project %',
                NEW.target_question_instance_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.target_message_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM conversation_messages
         WHERE id = NEW.target_message_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'message % not found or deleted',
                NEW.target_message_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'message % does not belong to project %',
                NEW.target_message_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.target_report_id IS NOT NULL THEN
        SELECT project_id, org_id
          INTO target_project_id, target_org_id
          FROM project_reports
         WHERE id = NEW.target_report_id
           AND deleted_at IS NULL;

        IF target_project_id IS NULL THEN
            RAISE EXCEPTION 'report % not found or deleted',
                NEW.target_report_id
                USING ERRCODE = '23514';
        END IF;

        IF target_project_id <> NEW.project_id
            OR target_org_id <> NEW.org_id THEN
            RAISE EXCEPTION 'report % does not belong to project %',
                NEW.target_report_id, NEW.project_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_comments_targets_guard
    BEFORE INSERT OR UPDATE ON project_comments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_project_comment_targets();
