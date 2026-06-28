import type { useAppMessages } from "@/lib/i18n/provider";

export type InviteRole = "admin" | "mentor" | "student";
export type InviteStatus = "pending" | "accepted" | "expired" | "revoked";
export type RoleFilter = "all" | InviteRole;
export type StatusFilter = "pending" | "all";

export type OrgInvite = {
  id: string;
  invitee_email: string;
  invited_role: InviteRole;
  status: InviteStatus;
  token: string;
  invite_link: string;
  expires_at: string | null;
  created_at: string;
};

export type InviteUser = {
  id: string;
  email: string;
  display_name: string | null;
};

export type InvitesResponse = {
  invites: OrgInvite[];
  total: number;
  page: number;
  limit: number;
};

export type InviteCreateResponse = {
  status: "created" | "restored";
  invite_link?: string | null;
  token?: string | null;
  user?: InviteUser | null;
};

export type AdminInvitesMessages = ReturnType<
  typeof useAppMessages
>["adminInvites"];
export type AdminRoleLabels = ReturnType<typeof useAppMessages>["adminShell"]["roles"];

export const ROLE_FILTER_VALUES: RoleFilter[] = [
  "all",
  "admin",
  "mentor",
  "student",
];

export const ROLE_VALUES: InviteRole[] = ["admin", "mentor", "student"];

export const STATUS_FILTER_VALUES: StatusFilter[] = ["pending", "all"];

export const STATUS_VARIANTS: Record<
  InviteStatus,
  "default" | "success" | "warning" | "danger"
> = {
  pending: "warning",
  accepted: "success",
  expired: "default",
  revoked: "danger",
};

export const DEFAULT_INVITES_LIMIT = 20;

export const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const formatInviteDate = (
  value: string | null,
  locale: string
): string => {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(resolveIntlLocale(locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
};

export const interpolateInviteMessage = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export const buildInvitesQuery = (
  page: number,
  roleFilter: RoleFilter,
  statusFilter: StatusFilter,
  query: string
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_INVITES_LIMIT));
  if (roleFilter !== "all") {
    searchParams.set("role", roleFilter);
  }
  if (statusFilter !== "all") {
    searchParams.set("status", statusFilter);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return searchParams.toString();
};
