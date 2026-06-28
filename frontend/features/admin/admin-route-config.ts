import { stripLocalePrefix } from "@/lib/i18n/config";
import type { AdminSession } from "./admin-session";

export type AdminNavGroupKey =
  | "overview"
  | "organization"
  | "assessmentOps"
  | "methodology"
  | "platform";

export type AdminNavItemKey =
  | "overview"
  | "organization"
  | "members"
  | "invites"
  | "cohorts"
  | "mentorAssignments"
  | "projects"
  | "reports"
  | "reportQuality"
  | "prompts"
  | "questionBanks"
  | "platformSettings";

export type AdminCapability = keyof AdminSession["capabilities"];

export type AdminNavItemConfig = {
  key: AdminNavItemKey;
  href: string;
  group: AdminNavGroupKey;
  requiredCapability?: AdminCapability;
  requiresPlatformAdmin?: boolean;
};

export type AdminNavGroupConfig = {
  key: AdminNavGroupKey;
  itemKeys: AdminNavItemKey[];
};

export type AdminRouteRule = {
  prefix: string;
  matchChildren?: boolean;
  requiredCapability?: AdminCapability;
  requiresPlatformAdmin?: boolean;
};

const matchesRouteRule = (pathname: string, rule: AdminRouteRule): boolean =>
  pathname === rule.prefix ||
  Boolean(rule.matchChildren && pathname.startsWith(`${rule.prefix}/`));

export const ADMIN_NAV_GROUPS: AdminNavGroupConfig[] = [
  {
    key: "overview",
    itemKeys: ["overview"],
  },
  {
    key: "organization",
    itemKeys: ["organization", "members", "invites"],
  },
  {
    key: "assessmentOps",
    itemKeys: ["cohorts", "mentorAssignments", "projects", "reports"],
  },
  {
    key: "methodology",
    itemKeys: ["prompts", "questionBanks"],
  },
  {
    key: "platform",
    itemKeys: ["reportQuality", "platformSettings"],
  },
];

export const ADMIN_NAV_ITEMS: AdminNavItemConfig[] = [
  {
    key: "overview",
    href: "/admin",
    group: "overview",
  },
  {
    key: "organization",
    href: "/admin/org",
    group: "organization",
    requiredCapability: "can_manage_org_settings",
  },
  {
    key: "members",
    href: "/admin/org/members",
    group: "organization",
    requiredCapability: "can_manage_members",
  },
  {
    key: "invites",
    href: "/admin/org/invites",
    group: "organization",
    requiredCapability: "can_manage_invites",
  },
  {
    key: "cohorts",
    href: "/admin/cohorts",
    group: "assessmentOps",
    requiredCapability: "can_manage_cohorts",
  },
  {
    key: "mentorAssignments",
    href: "/admin/org/mentor-assignments",
    group: "assessmentOps",
    requiredCapability: "can_manage_assignments",
  },
  {
    key: "projects",
    href: "/admin/projects",
    group: "assessmentOps",
    requiredCapability: "can_manage_projects",
  },
  {
    key: "reports",
    href: "/admin/reports",
    group: "assessmentOps",
    requiredCapability: "can_manage_reports",
  },
  {
    key: "reportQuality",
    href: "/admin/platform/report-quality",
    group: "platform",
    requiresPlatformAdmin: true,
  },
  {
    key: "prompts",
    href: "/admin/org/prompts",
    group: "methodology",
    requiredCapability: "can_manage_prompts",
  },
  {
    key: "questionBanks",
    href: "/admin/org/question-banks",
    group: "methodology",
    requiredCapability: "can_manage_question_bank",
  },
  {
    key: "platformSettings",
    href: "/admin/platform/settings",
    group: "platform",
    requiresPlatformAdmin: true,
  },
];

export const ADMIN_ROUTE_RULES: AdminRouteRule[] = [
  ...ADMIN_NAV_ITEMS.filter((item) => item.key !== "overview").map((item) => ({
    prefix: item.href,
    matchChildren: item.key === "cohorts" || item.key === "projects",
    requiredCapability: item.requiredCapability,
    requiresPlatformAdmin: item.requiresPlatformAdmin,
  })),
  {
    prefix: "/admin/assignments",
    requiredCapability: "can_manage_assignments",
  },
  {
    prefix: "/admin/memberships",
    requiredCapability: "can_manage_members",
  },
];

export const ADMIN_QUICK_ACTION_KEYS: AdminNavItemKey[] = [
  "organization",
  "members",
  "cohorts",
  "mentorAssignments",
  "reports",
  "prompts",
  "questionBanks",
  "reportQuality",
  "platformSettings",
];

export const getAdminNavItem = (
  key: AdminNavItemKey
): AdminNavItemConfig => {
  const item = ADMIN_NAV_ITEMS.find((candidate) => candidate.key === key);
  if (!item) {
    throw new Error(`Unknown admin nav item: ${key}`);
  }
  return item;
};

export const canAccessAdminNavItem = (
  item: AdminNavItemConfig,
  session: Pick<AdminSession, "capabilities" | "is_platform_admin">
): boolean => {
  if (item.requiresPlatformAdmin && !session.is_platform_admin) {
    return false;
  }
  if (item.requiredCapability && !session.capabilities[item.requiredCapability]) {
    return false;
  }
  return true;
};

export const getVisibleAdminNavGroups = (
  session: Pick<AdminSession, "capabilities" | "is_platform_admin">
) =>
  ADMIN_NAV_GROUPS.map((group) => ({
    ...group,
    items: group.itemKeys
      .map(getAdminNavItem)
      .filter((item) => canAccessAdminNavItem(item, session)),
  })).filter((group) => group.items.length > 0);

export const getVisibleAdminQuickActions = (
  session: Pick<AdminSession, "capabilities" | "is_platform_admin">
) =>
  ADMIN_QUICK_ACTION_KEYS.map(getAdminNavItem).filter((item) =>
    canAccessAdminNavItem(item, session)
  );

export const isAdminNavItemActive = (
  routePathname: string,
  item: Pick<AdminNavItemConfig, "href">
): boolean => {
  if (item.href === "/admin") {
    return routePathname === "/admin";
  }
  if (item.href === "/admin/org") {
    return routePathname === "/admin/org";
  }
  return routePathname === item.href || routePathname.startsWith(`${item.href}/`);
};

export const findAdminRouteRule = (pathname: string): AdminRouteRule | null => {
  const normalizedPathname = stripLocalePrefix(pathname);
  const matches = ADMIN_ROUTE_RULES.filter((item) =>
    matchesRouteRule(normalizedPathname, item)
  ).sort((a, b) => b.prefix.length - a.prefix.length);
  return matches[0] ?? null;
};

export const hasAdminRouteAccess = (
  pathname: string,
  session: Pick<AdminSession, "capabilities" | "is_platform_admin">
): boolean => {
  const normalizedPathname = stripLocalePrefix(pathname);
  const rule = findAdminRouteRule(normalizedPathname);
  if (!rule) {
    return normalizedPathname === "/admin" || normalizedPathname === "/admin/";
  }
  if (rule.requiresPlatformAdmin && !session.is_platform_admin) {
    return false;
  }
  if (
    rule.requiredCapability &&
    !session.capabilities[rule.requiredCapability]
  ) {
    return false;
  }
  return true;
};
