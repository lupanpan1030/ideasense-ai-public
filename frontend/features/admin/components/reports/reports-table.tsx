"use client";

import { useEffect, useMemo, useState, type ChangeEvent, type MouseEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiClient, buildApiUrl } from "@/lib/api/client";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { orgStorage } from "@/lib/storage/org";
import { tokenStorage } from "@/lib/storage/token";
import {
  ReportsTableSurface,
  interpolate,
  resolveIntlLocale,
} from "./reports-table-surface";
import type {
  CohortSummary,
  CohortsResponse,
  ConfirmedFilter,
  ReportStatus,
  ReportSummary,
  ReportsResponse,
  UpdatedRange,
} from "./reports-table-types";

const DEFAULT_LIMIT = 20;

const getReportsErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminReports"]
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

const getReportActionErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminReports"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return messages.errors.updateNoAccess;
    }
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

const getCohortsErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminReports"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.cohortsNoAccess;
    }
    if (error.status >= 500) {
      return messages.errors.cohortsUnavailable;
    }
  }
  return messages.errors.cohortsLoadFailed;
};

const buildReportsQuery = (
  page: number,
  status: ReportStatus | "all",
  confirmed: ConfirmedFilter,
  query: string,
  includeArchived: boolean,
  cohortId: string,
  updatedSinceDays: number | null
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_LIMIT));
  searchParams.set("status", status);
  if (confirmed !== "all") {
    searchParams.set("confirmed", confirmed);
  }
  if (query) {
    searchParams.set("q", query);
  }
  if (cohortId) {
    searchParams.set("cohort_id", cohortId);
  }
  if (updatedSinceDays) {
    searchParams.set("updated_since_days", String(updatedSinceDays));
  }
  if (includeArchived) {
    searchParams.set("include_archived", "true");
  }
  return searchParams.toString();
};

const buildExportQuery = (
  status: ReportStatus | "all",
  confirmed: ConfirmedFilter,
  query: string,
  includeArchived: boolean,
  cohortId: string,
  updatedSinceDays: number | null
): string => {
  const searchParams = new URLSearchParams();
  if (status !== "all") {
    searchParams.set("status", status);
  }
  if (confirmed !== "all") {
    searchParams.set("confirmed", confirmed);
  }
  if (query) {
    searchParams.set("q", query);
  }
  if (cohortId) {
    searchParams.set("cohort_id", cohortId);
  }
  if (updatedSinceDays) {
    searchParams.set("updated_since_days", String(updatedSinceDays));
  }
  if (includeArchived) {
    searchParams.set("include_archived", "true");
  }
  return searchParams.toString();
};

const fetchReports = async (
  page: number,
  status: ReportStatus | "all",
  confirmed: ConfirmedFilter,
  query: string,
  includeArchived: boolean,
  cohortId: string,
  updatedSinceDays: number | null
): Promise<ReportsResponse> => {
  const queryString = buildReportsQuery(
    page,
    status,
    confirmed,
    query,
    includeArchived,
    cohortId,
    updatedSinceDays
  );
  const url = queryString ? `/admin-api/reports?${queryString}` : "/admin-api/reports";
  return apiClient.fetchJson<ReportsResponse>(url);
};

const fetchCohorts = async (): Promise<CohortsResponse> => {
  const query = new URLSearchParams({
    page: "1",
    limit: "100",
    status: "all",
  });
  return apiClient.fetchJson<CohortsResponse>(`/admin-api/cohorts?${query}`);
};

const getExportErrorMessage = async (
  response: Response,
  messages: ReturnType<typeof useAppMessages>["adminReports"]
): Promise<string> => {
  if (response.status === 401) {
    return messages.errors.expiredSession;
  }
  if (response.status === 403) {
    return messages.errors.noAccess;
  }
  if (response.status >= 500) {
    return messages.errors.unavailable;
  }
  return messages.errors.exportFailed;
};

const parseFilename = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const match = /filename="?([^"]+)"?/i.exec(value);
  if (!match) {
    return null;
  }
  return match[1];
};

const updateReport = async (
  reportId: string,
  confirmed: boolean
): Promise<ReportSummary> =>
  apiClient.postJson<ReportSummary>(
    `/admin-api/reports/${reportId}`,
    { confirmed },
    { method: "PATCH" }
  );

const updateReportsBatch = async (
  reportIds: string[],
  confirmed: boolean
): Promise<{ updated_count: number }> =>
  apiClient.postJson<{ updated_count: number }>(
    "/admin-api/reports/batch",
    { report_ids: reportIds, confirmed },
    { method: "POST" }
  );

export function ReportsTable() {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminReports;
  const archivedLabel = appMessages.adminCohorts.table.archived;
  const intlLocale = resolveIntlLocale(locale);
  const router = useRouter();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "all">("all");
  const [confirmedFilter, setConfirmedFilter] =
    useState<ConfirmedFilter>("all");
  const [updatedRange, setUpdatedRange] = useState<UpdatedRange>("all");
  const [cohortFilter, setCohortFilter] = useState("");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [updatingReportId, setUpdatingReportId] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBatchUpdating, setIsBatchUpdating] = useState(false);
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [cohortError, setCohortError] = useState<string | null>(null);

  const reportStatusOptions = useMemo(
    () => [
      { value: "all", label: messages.filters.statusOptions.all },
      { value: "draft", label: messages.filters.statusOptions.draft },
      { value: "final", label: messages.filters.statusOptions.final },
      { value: "archived", label: messages.filters.statusOptions.archived },
    ] satisfies Array<{ value: ReportStatus | "all"; label: string }>,
    [messages]
  );

  const confirmedOptions = useMemo(
    () => [
      { value: "all", label: messages.filters.confirmationOptions.all },
      {
        value: "confirmed",
        label: messages.filters.confirmationOptions.confirmed,
      },
      {
        value: "unconfirmed",
        label: messages.filters.confirmationOptions.unconfirmed,
      },
    ] satisfies Array<{ value: ConfirmedFilter; label: string }>,
    [messages]
  );

  const updatedRangeOptions = useMemo(
    () => [
      { value: "all", label: messages.filters.updatedRangeOptions.all },
      { value: "7", label: messages.filters.updatedRangeOptions["7"] },
      { value: "30", label: messages.filters.updatedRangeOptions["30"] },
      { value: "90", label: messages.filters.updatedRangeOptions["90"] },
    ] satisfies Array<{ value: UpdatedRange; label: string }>,
    [messages]
  );

  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_LIMIT));
  const pageStart = total === 0 ? 0 : (page - 1) * DEFAULT_LIMIT + 1;
  const pageEnd = Math.min(total, page * DEFAULT_LIMIT);
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;
  const allVisibleSelected = useMemo(() => {
    if (reports.length === 0) {
      return false;
    }
    return reports.every((report) => selectedIds.has(report.id));
  }, [reports, selectedIds]);
  const selectedCount = selectedIds.size;

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    setPage(1);
  }, [
    statusFilter,
    confirmedFilter,
    updatedRange,
    cohortFilter,
    debouncedQuery,
    includeArchived,
  ]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, statusFilter, confirmedFilter, updatedRange, cohortFilter, debouncedQuery, includeArchived]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchReports(
      page,
      statusFilter,
      confirmedFilter,
      debouncedQuery,
      includeArchived,
      cohortFilter,
      updatedRange === "all" ? null : Number(updatedRange)
    )
      .then((response) => {
        if (!isActive) {
          return;
        }
        setReports(response.reports ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getReportsErrorMessage(error, messages));
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
    statusFilter,
    confirmedFilter,
    updatedRange,
    cohortFilter,
    debouncedQuery,
    includeArchived,
    refreshToken,
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
        setCohortError(getCohortsErrorMessage(error, messages));
      });
    return () => {
      isActive = false;
    };
  }, [messages]);

  useEffect(() => {
    if (total === 0) {
      if (page !== 1) {
        setPage(1);
      }
      return;
    }
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, total, totalPages]);

  const handleRowClick = (projectId: string) => {
    router.push(buildLocalePath(locale, `/admin/projects/${projectId}`, "tab=reports"));
  };

  const handleSelectAll = (event: ChangeEvent<HTMLInputElement>) => {
    const checked = event.target.checked;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        reports.forEach((report) => next.add(report.id));
      } else {
        reports.forEach((report) => next.delete(report.id));
      }
      return next;
    });
  };

  const handleSelectRow =
    (reportId: string) => (event: ChangeEvent<HTMLInputElement>) => {
      const checked = event.target.checked;
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (checked) {
          next.add(reportId);
        } else {
          next.delete(reportId);
        }
        return next;
      });
    };

  const handleBatchUpdate = async (confirmed: boolean) => {
    if (isBatchUpdating || selectedIds.size === 0) {
      return;
    }
    setActionError(null);
    setIsBatchUpdating(true);
    try {
      const ids = Array.from(selectedIds);
      const response = await updateReportsBatch(ids, confirmed);
      if (response.updated_count === 0) {
        setToastMessage(messages.toasts.noneUpdated);
      } else {
        setToastMessage(
          confirmed
            ? interpolate(messages.toasts.confirmedBatch, {
                count: response.updated_count,
              })
            : interpolate(messages.toasts.unconfirmedBatch, {
                count: response.updated_count,
              })
        );
      }
      setSelectedIds(new Set());
      setRefreshToken((value) => value + 1);
    } catch (error) {
      setActionError(getReportActionErrorMessage(error, messages));
    } finally {
      setIsBatchUpdating(false);
    }
  };

  const handleExport = async () => {
    if (isExporting) {
      return;
    }
    setActionError(null);
    setIsExporting(true);
    try {
      const queryString = buildExportQuery(
        statusFilter,
        confirmedFilter,
        debouncedQuery,
        includeArchived,
        cohortFilter,
        updatedRange === "all" ? null : Number(updatedRange)
      );
      const url = buildApiUrl(
        queryString ? `/admin-api/reports/export?${queryString}` : "/admin-api/reports/export"
      );
      const headers = new Headers();
      const token = tokenStorage.getToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      const orgId = orgStorage.getOrgId();
      if (orgId) {
        headers.set("X-Org-ID", orgId);
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        const message = await getExportErrorMessage(response, messages);
        setActionError(message);
        return;
      }

      const blob = await response.blob();
      const filename =
        parseFilename(response.headers.get("content-disposition")) ??
        "reports_export.csv";
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
      setToastMessage(messages.toasts.exportReady);
    } catch (error) {
      setActionError(getReportActionErrorMessage(error, messages));
    } finally {
      setIsExporting(false);
    }
  };

  const handleToggleConfirm = async (
    event: MouseEvent<HTMLButtonElement>,
    report: ReportSummary
  ) => {
    event.stopPropagation();
    if (updatingReportId) {
      return;
    }
    setActionError(null);
    setUpdatingReportId(report.id);
    try {
      const updated = await updateReport(report.id, !report.confirmed);
      const shouldRemove =
        (confirmedFilter === "confirmed" && !updated.confirmed) ||
        (confirmedFilter === "unconfirmed" && updated.confirmed);
      setReports((prev) =>
        shouldRemove
          ? prev.filter((item) => item.id !== updated.id)
          : prev.map((item) => (item.id === updated.id ? updated : item))
      );
      setSelectedIds((prev) => {
        if (!prev.has(updated.id)) {
          return prev;
        }
        if (!shouldRemove) {
          return prev;
        }
        const next = new Set(prev);
        next.delete(updated.id);
        return next;
      });
      if (shouldRemove) {
        setTotal((value) => Math.max(0, value - 1));
      }
      setToastMessage(
        updated.confirmed
          ? messages.toasts.confirmedSingle
          : messages.toasts.unconfirmedSingle
      );
      setRefreshToken((value) => value + 1);
    } catch (error) {
      setActionError(getReportActionErrorMessage(error, messages));
    } finally {
      setUpdatingReportId(null);
    }
  };

  return (
    <ReportsTableSurface
      messages={messages}
      archivedLabel={archivedLabel}
      locale={locale}
      intlLocale={intlLocale}
      reports={reports}
      total={total}
      query={query}
      statusFilter={statusFilter}
      reportStatusOptions={reportStatusOptions}
      confirmedFilter={confirmedFilter}
      confirmedOptions={confirmedOptions}
      updatedRange={updatedRange}
      updatedRangeOptions={updatedRangeOptions}
      cohortFilter={cohortFilter}
      cohorts={cohorts}
      includeArchived={includeArchived}
      selectedIds={selectedIds}
      selectedCount={selectedCount}
      allVisibleSelected={allVisibleSelected}
      isLoading={isLoading}
      loadError={loadError}
      cohortError={cohortError}
      actionError={actionError}
      isBatchUpdating={isBatchUpdating}
      isExporting={isExporting}
      updatingReportId={updatingReportId}
      pageStart={pageStart}
      pageEnd={pageEnd}
      page={page}
      totalPages={totalPages}
      canGoBack={canGoBack}
      canGoForward={canGoForward}
      toastMessage={toastMessage}
      onQueryChange={setQuery}
      onStatusFilterChange={setStatusFilter}
      onConfirmedFilterChange={setConfirmedFilter}
      onCohortFilterChange={setCohortFilter}
      onUpdatedRangeChange={setUpdatedRange}
      onIncludeArchivedChange={setIncludeArchived}
      onBatchUpdate={handleBatchUpdate}
      onExport={handleExport}
      onSelectAll={handleSelectAll}
      onSelectRow={handleSelectRow}
      onRowClick={handleRowClick}
      onToggleConfirm={handleToggleConfirm}
      onPreviousPage={() => setPage(Math.max(page - 1, 1))}
      onNextPage={() => setPage(page + 1)}
    />
  );
}
