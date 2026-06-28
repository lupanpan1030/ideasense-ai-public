import { apiClient } from "@/lib/api/client";
import { orgStorage } from "@/lib/storage/org";

export type AdminSession = {
  user: {
    id: string;
    email: string | null;
    display_name: string | null;
  };
  org: {
    id: string;
    name: string;
    settings: Record<string, unknown>;
  };
  membership: {
    id: string;
    org_role: string;
    status: string;
  };
  capabilities: {
    is_org_admin: boolean;
    can_manage_org_settings: boolean;
    can_manage_prompts: boolean;
    can_manage_members: boolean;
    can_manage_invites: boolean;
    can_manage_cohorts: boolean;
    can_manage_assignments: boolean;
    can_manage_projects: boolean;
    can_manage_reports: boolean;
    can_manage_question_bank: boolean;
    can_transfer_ownership: boolean;
  };
  orgs: Array<{
    id: string;
    name: string;
    org_role: string;
    status: string;
  }>;
  actor_type: string;
  is_platform_admin: boolean;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const requireString = (value: unknown, label: string): string => {
  const resolved = toTrimmedString(value);
  if (!resolved) {
    throw new Error(`Invalid ${label}`);
  }
  return resolved;
};

const toOptionalString = (value: unknown): string | null =>
  toTrimmedString(value);

const toBoolean = (value: unknown, fallback: boolean): boolean =>
  typeof value === "boolean" ? value : fallback;

const normalizeSession = (payload: unknown): AdminSession => {
  if (!isRecord(payload)) {
    throw new Error("Invalid session payload");
  }

  const user = isRecord(payload.user) ? payload.user : null;
  const org = isRecord(payload.org) ? payload.org : null;
  const membership = isRecord(payload.membership) ? payload.membership : null;

  if (!user || !org || !membership) {
    throw new Error("Session payload is incomplete");
  }

  const orgRole = requireString(membership.org_role, "membership.org_role");
  const isOrgAdmin = orgRole === "owner" || orgRole === "admin";

  const capabilitiesSource = isRecord(payload.capabilities)
    ? payload.capabilities
    : {};

  const capabilities = {
    is_org_admin: toBoolean(capabilitiesSource.is_org_admin, isOrgAdmin),
    can_manage_org_settings: toBoolean(
      capabilitiesSource.can_manage_org_settings,
      isOrgAdmin
    ),
    can_manage_prompts: toBoolean(
      capabilitiesSource.can_manage_prompts,
      isOrgAdmin
    ),
    can_manage_members: toBoolean(
      capabilitiesSource.can_manage_members,
      isOrgAdmin
    ),
    can_manage_invites: toBoolean(
      capabilitiesSource.can_manage_invites,
      isOrgAdmin
    ),
    can_manage_cohorts: toBoolean(
      capabilitiesSource.can_manage_cohorts,
      isOrgAdmin
    ),
    can_manage_assignments: toBoolean(
      capabilitiesSource.can_manage_assignments,
      isOrgAdmin
    ),
    can_manage_projects: toBoolean(
      capabilitiesSource.can_manage_projects,
      isOrgAdmin
    ),
    can_manage_reports: toBoolean(
      capabilitiesSource.can_manage_reports,
      isOrgAdmin
    ),
    can_manage_question_bank: toBoolean(
      capabilitiesSource.can_manage_question_bank,
      isOrgAdmin
    ),
    can_transfer_ownership: toBoolean(
      capabilitiesSource.can_transfer_ownership,
      orgRole === "owner"
    ),
  };

  const orgs = Array.isArray(payload.orgs)
    ? payload.orgs
        .map((item) => {
          if (!isRecord(item)) {
            return null;
          }
          const id = toTrimmedString(item.id);
          const name = toTrimmedString(item.name);
          if (!id || !name) {
            return null;
          }
          return {
            id,
            name,
            org_role: toOptionalString(item.org_role) ?? orgRole,
            status: toOptionalString(item.status) ?? "active",
          };
        })
        .filter(
          (item): item is AdminSession["orgs"][number] => Boolean(item)
        )
    : [];

  return {
    user: {
      id: requireString(user.id, "user.id"),
      email: toOptionalString(user.email),
      display_name: toOptionalString(user.display_name),
    },
    org: {
      id: requireString(org.id, "org.id"),
      name: requireString(org.name, "org.name"),
      settings: isRecord(org.settings) ? org.settings : {},
    },
    membership: {
      id: requireString(membership.id, "membership.id"),
      org_role: orgRole,
      status: requireString(membership.status, "membership.status"),
    },
    capabilities,
    orgs,
    actor_type: toOptionalString(payload.actor_type) ?? "user",
    is_platform_admin: toBoolean(payload.is_platform_admin, false),
  };
};

export const isOrgAdmin = (session: AdminSession): boolean =>
  session.capabilities.is_org_admin ||
  session.membership.org_role === "owner" ||
  session.membership.org_role === "admin";

export const fetchAdminSession = async (): Promise<AdminSession> => {
  const response = await apiClient.fetchJson<unknown>("/session");
  const session = normalizeSession(response);
  orgStorage.setOrgId(session.org.id);
  return session;
};
