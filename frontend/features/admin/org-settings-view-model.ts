import type { AdminSession } from "@/features/admin/admin-session";
import type { OrgSettings } from "@/features/admin/org-settings";

export type SelectOption = {
  value: string;
  label: string;
  description?: string;
};

export const DEFAULT_SETTINGS = {
  org_type: "institution",
  allow_cohorts: true,
  allow_mentor_assignments: true,
  default_mentor_visibility: "summaries_only",
};

export const MAX_LOGO_BYTES = 2 * 1024 * 1024;
export const LOGO_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/svg+xml",
]);

export const isPlainRecord = (
  value: unknown
): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const formatSettings = (settings: OrgSettings): string =>
  JSON.stringify(settings, null, 2);

export const formatTimestamp = (
  value: string | null,
  locale: "en" | "zh",
  unknownLabel: string
) => {
  if (!value) {
    return unknownLabel;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return unknownLabel;
  }
  return date.toLocaleString(locale === "zh" ? "zh-CN" : "en-US");
};

export const toBoolean = (value: unknown, fallback: boolean): boolean =>
  typeof value === "boolean" ? value : fallback;

export const toStringValue = (value: unknown, fallback: string): string => {
  if (typeof value !== "string") {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : fallback;
};

export const ensureOption = (
  options: SelectOption[],
  currentValue: string,
  currentPrefix: string
): SelectOption[] => {
  if (!currentValue) {
    return options;
  }
  if (options.some((option) => option.value === currentValue)) {
    return options;
  }
  return [
    ...options,
    {
      value: currentValue,
      label: `${currentPrefix}: ${currentValue}`,
    },
  ];
};

export const resolveOrgSlug = (session: AdminSession | null): string => {
  if (!session) {
    return "";
  }
  const settings = session.org.settings;
  if (typeof settings !== "object" || settings === null) {
    return "";
  }
  const record = settings as Record<string, unknown>;
  const slug = record.slug ?? record.org_slug;
  if (typeof slug !== "string") {
    return "";
  }
  return slug.trim();
};
