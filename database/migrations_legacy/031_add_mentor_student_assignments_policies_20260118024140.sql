-- 031) mentor_student_assignments RLS policies and update rules
CREATE POLICY mentor_student_assignments_select ON mentor_student_assignments
    FOR SELECT USING (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_insert ON mentor_student_assignments
    FOR INSERT WITH CHECK (
        is_org_admin(org_id)
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_update ON mentor_student_assignments
    FOR UPDATE USING (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    )
    WITH CHECK (
        is_org_admin(org_id)
        OR mentor_user_id = app_user_id()
        OR student_user_id = app_user_id()
    );

CREATE POLICY mentor_student_assignments_delete ON mentor_student_assignments
    FOR DELETE USING (is_org_admin(org_id));

CREATE OR REPLACE FUNCTION enforce_assignment_write_rules()
RETURNS trigger AS $$
DECLARE
    actor_id UUID;
    actor_is_admin BOOLEAN;
BEGIN
    actor_id := app_user_id();
    IF actor_id IS NULL THEN
        RAISE EXCEPTION 'app.user_id is required for assignment writes'
            USING ERRCODE = '23514';
    END IF;

    actor_is_admin := is_org_admin(NEW.org_id);

    IF TG_OP = 'INSERT' THEN
        IF actor_is_admin THEN
            RETURN NEW;
        END IF;

        IF NEW.student_user_id <> actor_id THEN
            RAISE EXCEPTION 'only student can self-invite a mentor'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.status <> 'pending' THEN
            RAISE EXCEPTION 'student invitation must be pending'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.can_view_messages OR NEW.can_view_facts THEN
            RAISE EXCEPTION 'student invitation cannot grant view permissions'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.created_by IS NULL THEN
            NEW.created_by := actor_id;
        ELSIF NEW.created_by <> actor_id THEN
            RAISE EXCEPTION 'created_by must match actor for student invite'
                USING ERRCODE = '23514';
        END IF;

        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF actor_is_admin THEN
            RETURN NEW;
        END IF;

        IF NEW.org_id IS DISTINCT FROM OLD.org_id
            OR NEW.cohort_id IS DISTINCT FROM OLD.cohort_id
            OR NEW.mentor_user_id IS DISTINCT FROM OLD.mentor_user_id
            OR NEW.student_user_id IS DISTINCT FROM OLD.student_user_id
            OR NEW.created_by IS DISTINCT FROM OLD.created_by
            OR NEW.created_at IS DISTINCT FROM OLD.created_at
            OR NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
            RAISE EXCEPTION 'immutable assignment fields cannot be changed'
                USING ERRCODE = '23514';
        END IF;

        IF actor_id = NEW.mentor_user_id THEN
            IF NEW.can_view_messages IS DISTINCT FROM OLD.can_view_messages
                OR NEW.can_view_facts IS DISTINCT FROM OLD.can_view_facts
                OR NEW.can_comment IS DISTINCT FROM OLD.can_comment THEN
                RAISE EXCEPTION 'mentor cannot change permission flags'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT (
                    (OLD.status = 'pending' AND NEW.status IN ('active','revoked'))
                    OR (OLD.status = 'active' AND NEW.status = 'revoked')
                ) THEN
                    RAISE EXCEPTION 'invalid status transition for mentor'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            RETURN NEW;
        END IF;

        IF actor_id = NEW.student_user_id THEN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT (
                    (OLD.status = 'pending' AND NEW.status = 'revoked')
                    OR (OLD.status = 'active' AND NEW.status = 'revoked')
                ) THEN
                    RAISE EXCEPTION 'invalid status transition for student'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'actor not permitted to update assignment'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mentor_student_assignments_write_guard
    BEFORE INSERT OR UPDATE ON mentor_student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION enforce_assignment_write_rules();
