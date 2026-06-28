import type { useAppMessages } from "@/lib/i18n/provider";

export type CohortStatusFilter = "active" | "archived" | "all";

export type CohortSummary = {
  id: string;
  name: string;
  description: string | null;
  start_at: string | null;
  end_at: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  students_count: number;
  mentors_count: number;
  projects_count: number;
};

export type CohortsResponse = {
  cohorts: CohortSummary[];
  total: number;
  page: number;
  limit: number;
};

export type CohortCreatePayload = {
  name: string;
  description?: string | null;
  start_at?: string | null;
  end_at?: string | null;
};

export type AdminCohortsMessages = ReturnType<typeof useAppMessages>["adminCohorts"];
export type AdminTimelineMessages = ReturnType<
  typeof useAppMessages
>["adminShared"]["timeline"];

export type CohortStatusFilterOption = {
  value: CohortStatusFilter;
  label: string;
};

export const DEFAULT_COHORTS_LIMIT = 20;

export const resolveCohortIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const formatCohortDate = (
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
  return new Intl.DateTimeFormat(resolveCohortIntlLocale(locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
};

export const interpolateCohortMessage = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export const formatCohortTimeline = (
  startAt: string | null,
  endAt: string | null,
  locale: string,
  timelineMessages: AdminTimelineMessages
): string => {
  if (!startAt && !endAt) {
    return timelineMessages.datesTbd;
  }
  if (startAt && endAt) {
    return `${formatCohortDate(startAt, locale)} - ${formatCohortDate(
      endAt,
      locale
    )}`;
  }
  if (startAt) {
    return interpolateCohortMessage(timelineMessages.starts, {
      date: formatCohortDate(startAt, locale),
    });
  }
  return interpolateCohortMessage(timelineMessages.ends, {
    date: formatCohortDate(endAt, locale),
  });
};

export const buildCohortsQuery = (
  page: number,
  statusFilter: CohortStatusFilter,
  query: string
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_COHORTS_LIMIT));
  if (statusFilter !== "active") {
    searchParams.set("status", statusFilter);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return searchParams.toString();
};
