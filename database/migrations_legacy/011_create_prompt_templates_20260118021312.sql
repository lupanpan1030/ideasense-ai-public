-- 011) prompt_templates
CREATE TABLE prompt_templates (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scope_org_id UUID GENERATED ALWAYS AS (
        COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid)
    ) STORED NOT NULL,
    template_key TEXT NOT NULL,
    purpose      TEXT NOT NULL,
    stage        TEXT NULL,
    variant      TEXT NULL,
    version      TEXT NOT NULL,
    content      TEXT NOT NULL,
    params       JSONB NULL,
    is_active    BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    CHECK (purpose IN ('chat','extract','summary','score','evaluate','report')),
    CHECK (
        template_key = lower(btrim(template_key))
        AND template_key <> ''
        AND template_key ~ '^[a-z0-9_.-]+$'
    ),
    CHECK (variant IS NULL OR stage IS NOT NULL),
    CHECK (stage IS NULL OR stage IN ('problem','market','tech','report'))
);

CREATE UNIQUE INDEX prompt_templates_scope_unique
    ON prompt_templates (scope_org_id, template_key, version)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX prompt_templates_scope_active_unique
    ON prompt_templates (scope_org_id, template_key)
    WHERE is_active AND deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_prompt_template_stage_variant()
RETURNS trigger AS $$
BEGIN
    IF NEW.variant IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM question_bank_stage_variants
            WHERE stage = NEW.stage
              AND variant = NEW.variant
        ) THEN
            RAISE EXCEPTION 'invalid stage/variant for prompt template: %/%',
                NEW.stage, NEW.variant
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prompt_templates_stage_variant_guard
    BEFORE INSERT OR UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION enforce_prompt_template_stage_variant();
