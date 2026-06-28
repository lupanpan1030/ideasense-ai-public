import type { useAppMessages } from "@/lib/i18n/provider";

export type OrgRole = "owner" | "admin" | "mentor" | "student";
export type MutableOrgRole = "admin" | "mentor" | "student";
export type MemberRoleFilter = "all" | MutableOrgRole;
export type MemberStatus = "active" | "invited" | "removed";

export type MemberUser = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

export type OrgMember = {
  id: string;
  org_role: OrgRole;
  status: MemberStatus;
  created_at: string;
  user: MemberUser | null;
};

export type MembersResponse = {
  members: OrgMember[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminMembersMessages = ReturnType<
  typeof useAppMessages
>["adminMembers"];
export type AdminRoleLabels = ReturnType<typeof useAppMessages>["adminShell"]["roles"];

export const MEMBER_ROLE_FILTER_VALUES: MemberRoleFilter[] = [
  "all",
  "admin",
  "mentor",
  "student",
];

export const MEMBER_ROLE_VALUES: MutableOrgRole[] = [
  "admin",
  "mentor",
  "student",
];

export const MEMBER_STATUS_VARIANTS: Record<
  MemberStatus,
  "success" | "warning" | "danger"
> = {
  active: "success",
  invited: "warning",
  removed: "danger",
};

export const DEFAULT_MEMBERS_LIMIT = 20;

export const resolveMemberInitials = (value: string): string => {
  const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, " ").trim();
  if (!cleaned) {
    return "IS";
  }
  const parts = cleaned.split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "IS";
};

export const resolveMemberIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const formatMemberDate = (value: string, locale: string): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(resolveMemberIntlLocale(locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
};

export const interpolateMemberMessage = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export const buildMembersQuery = (
  offset: number,
  roleFilter: MemberRoleFilter,
  query: string
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(DEFAULT_MEMBERS_LIMIT));
  searchParams.set("offset", String(offset));
  if (roleFilter !== "all") {
    searchParams.set("role", roleFilter);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return searchParams.toString();
};
