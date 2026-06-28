-- 003) organization_memberships
CREATE TABLE organization_memberships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_role    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    created_by  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CHECK (org_role IN ('owner','admin','mentor','student')),
    CHECK (status IN ('invited','active','removed'))
);

CREATE UNIQUE INDEX organization_memberships_org_user_unique
    ON organization_memberships (org_id, user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX organization_memberships_user_id_idx
    ON organization_memberships (user_id)
    WHERE deleted_at IS NULL;

-- 003) organization_invitations
CREATE TABLE organization_invitations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invitee_email    CITEXT NOT NULL,
    invited_role     TEXT NOT NULL,
    invited_by       UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    token            TEXT NOT NULL,
    expires_at       TIMESTAMPTZ NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    accepted_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ,
    CHECK (invited_role IN ('mentor','student','admin')),
    CHECK (status IN ('pending','accepted','expired','revoked')),
    CHECK (invitee_email = btrim(invitee_email)),
    CHECK (invitee_email !~ '\s')
);

CREATE UNIQUE INDEX organization_invitations_org_token_unique
    ON organization_invitations (org_id, token)
    WHERE deleted_at IS NULL;
