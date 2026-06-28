"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { ApiError, apiClient } from "@/lib/api/client";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type Stage = "problem" | "market" | "tech" | "report";
type StageStatus = "in_progress" | "awaiting_confirm" | "passed";

type ProjectOwner = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

type ProjectCohort = {
  id: string;
  name: string;
  is_archived: boolean;
};

type ProjectSummary = {
  id: string;
  title: string;
  description: string | null;
  current_stage: string | null;
  stage_status: string | null;
  is_archived: boolean;
  updated_at: string;
  created_at: string;
  owner: ProjectOwner;
  cohort: ProjectCohort | null;
};

type ProjectsResponse = {
  projects: ProjectSummary[];
  total: number;
  page: number;
  limit: number;
};

type CohortSummary = {
  id: string;
  name: string;
  is_archived: boolean;
};

type CohortsResponse = {
  cohorts: CohortSummary[];
  total: number;
  page: number;
  limit: number;
};

const DEFAULT_LIMIT = 20;

const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

const STATUS_VARIANTS: Record<
  StageStatus,
  "warning" | "success" | "info"
> = {
  in_progress: "warning",
  awaiting_confirm: "info",
  passed: "success",
};

const resolveInitials = (value: string): string => {
  const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, " ").trim();
  if (!cleaned) {
    return "IS";
  }
  const parts = cleaned.split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "IS";
};

const formatDate = (value: string, locale: string): string => {
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

const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

const getProjectsErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminProjects"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status >= 500) {
      return messages.errors.unavailable;
    }
  }
  return messages.errors.loadFailed;
};

const buildProjectsQuery = (
  page: number,
  stage: Stage | "all",
  status: StageStatus | "all",
  cohortId: string,
  ownerQuery: string,
  includeArchived: boolean
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_LIMIT));
  searchParams.set("stage", stage);
  searchParams.set("status", status);
  if (cohortId) {
    searchParams.set("cohort_id", cohortId);
  }
  if (ownerQuery) {
    searchParams.set("owner", ownerQuery);
  }
  if (includeArchived) {
    searchParams.set("include_archived", "true");
  }
  return searchParams.toString();
};

const fetchProjects = async (
  page: number,
  stage: Stage | "all",
  status: StageStatus | "all",
  cohortId: string,
  ownerQuery: string,
  includeArchived: boolean
): Promise<ProjectsResponse> => {
  const queryString = buildProjectsQuery(
    page,
    stage,
    status,
    cohortId,
    ownerQuery,
    includeArchived
  );
  const url = queryString ? `/admin-api/projects?${queryString}` : "/admin-api/projects";
  return apiClient.fetchJson<ProjectsResponse>(url);
};

const fetchCohorts = async (): Promise<CohortsResponse> => {
  const query = new URLSearchParams({
    page: "1",
    limit: "100",
    status: "all",
  });
  return apiClient.fetchJson<CohortsResponse>(`/admin-api/cohorts?${query}`);
};

type ProjectsTableProps = {
  initialStage?: Stage | "all";
  initialStatus?: StageStatus | "all";
  initialIncludeArchived?: boolean;
  stageFilterLocked?: boolean;
  statusFilterLocked?: boolean;
};

export function ProjectsTable({
  initialStage = "all",
  initialStatus = "all",
  initialIncludeArchived = false,
  stageFilterLocked = false,
  statusFilterLocked = false,
}: ProjectsTableProps = {}) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminProjects;
  const archivedLabel = appMessages.adminCohorts.table.archived;
  const intlLocale = resolveIntlLocale(locale);
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [stageFilter, setStageFilter] = useState<Stage | "all">(initialStage);
  const [statusFilter, setStatusFilter] =
    useState<StageStatus | "all">(initialStatus);
  const [cohortFilter, setCohortFilter] = useState("");
  const [ownerQuery, setOwnerQuery] = useState("");
  const [debouncedOwnerQuery, setDebouncedOwnerQuery] = useState("");
  const [includeArchived, setIncludeArchived] = useState(
    initialIncludeArchived
  );
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [cohortError, setCohortError] = useState<string | null>(null);

  const stageOptions = useMemo(
    () => [
      { value: "all", label: messages.filters.stageOptions.all },
      { value: "problem", label: messages.filters.stageOptions.problem },
      { value: "market", label: messages.filters.stageOptions.market },
      { value: "tech", label: messages.filters.stageOptions.tech },
      { value: "report", label: messages.filters.stageOptions.report },
    ] satisfies Array<{ value: Stage | "all"; label: string }>,
    [messages]
  );

  const statusOptions = useMemo(
    () => [
      { value: "all", label: messages.filters.statusOptions.all },
      {
        value: "in_progress",
        label: messages.filters.statusOptions.in_progress,
      },
      {
        value: "awaiting_confirm",
        label: messages.filters.statusOptions.awaiting_confirm,
      },
      { value: "passed", label: messages.filters.statusOptions.passed },
    ] satisfies Array<{ value: StageStatus | "all"; label: string }>,
    [messages]
  );

  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_LIMIT));
  const pageStart = total === 0 ? 0 : (page - 1) * DEFAULT_LIMIT + 1;
  const pageEnd = Math.min(total, page * DEFAULT_LIMIT);
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedOwnerQuery(ownerQuery.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [ownerQuery]);

  useEffect(() => {
    setPage(1);
  }, [stageFilter, statusFilter, cohortFilter, debouncedOwnerQuery, includeArchived]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchProjects(
      page,
      stageFilter,
      statusFilter,
      cohortFilter,
      debouncedOwnerQuery,
      includeArchived
    )
      .then((response) => {
        if (!isActive) {
          return;
        }
        setProjects(response.projects ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getProjectsErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [
    page,
    stageFilter,
    statusFilter,
    cohortFilter,
    debouncedOwnerQuery,
    includeArchived,
    messages,
  ]);

  useEffect(() => {
    let isActive = true;
    setCohortError(null);
    fetchCohorts()
      .then((response) => {
        if (!isActive) {
          return;
        }
        setCohorts(response.cohorts ?? []);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setCohortError(getProjectsErrorMessage(error, messages));
      });
    return () => {
      isActive = false;
    };
  }, [messages]);

  const cohortOptions = useMemo(
    () =>
      cohorts.map((cohort) => ({
        id: cohort.id,
        label: cohort.is_archived ? `${cohort.name} (${archivedLabel})` : cohort.name,
      })),
    [cohorts, archivedLabel]
  );

  const handleRowClick = (projectId: string) => {
    router.push(buildLocalePath(locale, `/admin/projects/${projectId}`));
  };

  return (
    <Card className="admin-projects">
      <CardHeader className="admin-projects__toolbar">
        <div className="admin-projects__toolbar-left">
          <div className="admin-projects__owner-search">
            <input
              type="search"
              className="input input--sm"
              placeholder={messages.filters.ownerSearchPlaceholder}
              value={ownerQuery}
              aria-label={messages.filters.ownerSearchAriaLabel}
              onChange={(event) => setOwnerQuery(event.target.value)}
            />
          </div>
          <div className="admin-projects__stage-filter">
            <select
              className="input input--sm"
              value={stageFilter}
              aria-label={messages.filters.stageFilterAriaLabel}
              disabled={stageFilterLocked}
              onChange={(event) =>
                setStageFilter(event.target.value as Stage | "all")
              }
            >
              {stageOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="admin-projects__status-filter">
            <select
              className="input input--sm"
              value={statusFilter}
              aria-label={messages.filters.statusFilterAriaLabel}
              disabled={statusFilterLocked}
              onChange={(event) =>
                setStatusFilter(event.target.value as StageStatus | "all")
              }
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="admin-projects__cohort-filter">
            <select
              className="input input--sm"
              value={cohortFilter}
              aria-label={messages.filters.cohortFilterAriaLabel}
              onChange={(event) => setCohortFilter(event.target.value)}
            >
              <option value="">{messages.filters.allCohorts}</option>
              {cohortOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <label className="admin-projects__archived-toggle">
            <span className="admin-projects__archived-label">
              {messages.filters.showArchived}
            </span>
            <span className="admin-switch">
              <input
                type="checkbox"
                checked={includeArchived}
                onChange={(event) => setIncludeArchived(event.target.checked)}
                aria-label={messages.filters.showArchivedAriaLabel}
              />
              <span className="admin-switch__track">
                <span className="admin-switch__thumb" />
              </span>
            </span>
          </label>
        </div>
        <div className="admin-projects__toolbar-right">
          <span className="admin-projects__count-badge">
            {interpolate(messages.filters.countBadge, {
              count: total.toLocaleString(intlLocale),
            })}
          </span>
        </div>
      </CardHeader>
      <CardContent className="admin-projects__content stack">
        {loadError ? (
          <div className="alert" role="alert">
            <span>{loadError}</span>
          </div>
        ) : null}
        {cohortError ? (
          <div className="alert" role="alert">
            <span>{cohortError}</span>
          </div>
        ) : null}

        <div className="admin-projects__table">
          <table className="admin-projects-table">
            <thead>
              <tr>
                <th scope="col">{messages.table.project}</th>
                <th scope="col" className="admin-projects__col--owner">
                  {messages.table.owner}
                </th>
                <th scope="col" className="admin-projects__col--cohort">
                  {messages.table.cohort}
                </th>
                <th scope="col">{messages.table.stage}</th>
                <th scope="col">{messages.table.status}</th>
                <th scope="col" className="admin-projects__col--updated">
                  {messages.table.updated}
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && projects.length === 0
                ? Array.from({ length: 5 }).map((_, index) => (
                    <tr key={`skeleton-${index}`}>
                      <td>
                        <div className="stack-sm">
                          <div className="skeleton" style={{ width: 180 }} />
                          <div className="skeleton" style={{ width: 220 }} />
                        </div>
                      </td>
                      <td className="admin-projects__col--owner">
                        <div className="admin-member__identity">
                          <div
                            className="skeleton"
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: 999,
                            }}
                          />
                          <div className="stack-sm">
                            <div className="skeleton" style={{ width: 140 }} />
                            <div className="skeleton" style={{ width: 120 }} />
                          </div>
                        </div>
                      </td>
                      <td className="admin-projects__col--cohort">
                        <div className="skeleton" style={{ width: 120 }} />
                      </td>
                      <td>
                        <div className="skeleton" style={{ width: 110 }} />
                      </td>
                      <td>
                        <div className="skeleton" style={{ width: 90 }} />
                      </td>
                      <td className="admin-projects__col--updated">
                        <div className="skeleton" style={{ width: 110 }} />
                      </td>
                    </tr>
                  ))
                : projects.map((project) => {
                    const ownerLabel =
                      project.owner.display_name ||
                      project.owner.email ||
                      messages.table.unknownOwner;
                    const ownerEmail = project.owner.email || messages.table.noEmail;
                    const ownerInitials = resolveInitials(ownerLabel);
                    const stageValue = project.current_stage as Stage | null;
                    const statusValue = project.stage_status as StageStatus | null;
                    const stageLabel = stageValue
                      ? messages.stageLabels[stageValue] ?? stageValue
                      : "--";
                    const statusLabel = statusValue
                      ? messages.stageStatuses[statusValue] ?? statusValue
                      : "--";
                    const statusVariant = statusValue
                      ? STATUS_VARIANTS[statusValue] ?? "warning"
                      : "warning";
                    return (
                      <tr
                        key={project.id}
                        className="admin-projects-table__row--clickable"
                        role="button"
                        tabIndex={0}
                        aria-label={interpolate(messages.table.openProjectAria, {
                          title: project.title || messages.table.untitledProject,
                        })}
                        onClick={() => handleRowClick(project.id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            handleRowClick(project.id);
                          }
                        }}
                      >
                        <td>
                          <div className="stack-sm">
                            <span className="admin-project__title">
                              {project.title || messages.table.untitledProject}
                            </span>
                            <span className="admin-project__subtitle">
                              {project.description || messages.table.noDescription}
                            </span>
                            {project.is_archived ? (
                              <span className="admin-project__muted">
                                {messages.table.archived}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td className="admin-projects__col--owner">
                          <div className="admin-member__identity">
                            <div className="admin-member__avatar">
                              {ownerInitials}
                            </div>
                            <div className="stack-sm">
                              <span className="admin-member__name">
                                {ownerLabel}
                              </span>
                              <span className="admin-member__email">
                                {ownerEmail}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="admin-projects__col--cohort">
                          <span className="admin-project__muted">
                            {project.cohort?.name || messages.table.global}
                          </span>
                        </td>
                        <td>
                          <span className="admin-project__muted">
                            {stageLabel}
                          </span>
                        </td>
                        <td>
                          <Badge variant={statusVariant}>{statusLabel}</Badge>
                        </td>
                        <td className="admin-projects__col--updated">
                          <span className="admin-project__muted">
                            {formatDate(project.updated_at, locale)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>

        {!isLoading && projects.length === 0 ? (
          <div className="admin-projects__empty">
            {messages.table.empty}
          </div>
        ) : null}
      </CardContent>
      <CardFooter className="admin-projects__footer">
        <span className="text-muted">
          {interpolate(messages.pagination.showing, {
            start: pageStart,
            end: pageEnd,
            total: total.toLocaleString(intlLocale),
          })}
        </span>
        <div className="admin-projects__pagination">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setPage(Math.max(page - 1, 1))}
            disabled={!canGoBack}
          >
            {messages.pagination.previous}
          </Button>
          <span className="text-muted">
            {interpolate(messages.pagination.page, {
              current: page,
              total: totalPages,
            })}
          </span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setPage(page + 1)}
            disabled={!canGoForward}
          >
            {messages.pagination.next}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
