import type { ChangeEvent, MouseEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import type { useAppMessages } from "@/lib/i18n/provider";

import type {
  CohortSummary,
  ConfirmedFilter,
  ReportStatus,
  ReportSummary,
  UpdatedRange,
} from "./reports-table-types";

type AdminReportsMessages = ReturnType<typeof useAppMessages>["adminReports"];

type ReportsTableOption<T extends string> = {
  value: T;
  label: string;
};

type ReportsTableSurfaceProps = {
  messages: AdminReportsMessages;
  archivedLabel: string;
  locale: string;
  intlLocale: string;
  reports: ReportSummary[];
  total: number;
  query: string;
  statusFilter: ReportStatus | "all";
  reportStatusOptions: Array<ReportsTableOption<ReportStatus | "all">>;
  confirmedFilter: ConfirmedFilter;
  confirmedOptions: Array<ReportsTableOption<ConfirmedFilter>>;
  updatedRange: UpdatedRange;
  updatedRangeOptions: Array<ReportsTableOption<UpdatedRange>>;
  cohortFilter: string;
  cohorts: CohortSummary[];
  includeArchived: boolean;
  selectedIds: Set<string>;
  selectedCount: number;
  allVisibleSelected: boolean;
  isLoading: boolean;
  loadError: string | null;
  cohortError: string | null;
  actionError: string | null;
  isBatchUpdating: boolean;
  isExporting: boolean;
  updatingReportId: string | null;
  pageStart: number;
  pageEnd: number;
  page: number;
  totalPages: number;
  canGoBack: boolean;
  canGoForward: boolean;
  toastMessage: string | null;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: ReportStatus | "all") => void;
  onConfirmedFilterChange: (value: ConfirmedFilter) => void;
  onCohortFilterChange: (value: string) => void;
  onUpdatedRangeChange: (value: UpdatedRange) => void;
  onIncludeArchivedChange: (checked: boolean) => void;
  onBatchUpdate: (confirmed: boolean) => void;
  onExport: () => void;
  onSelectAll: (event: ChangeEvent<HTMLInputElement>) => void;
  onSelectRow: (
    reportId: string
  ) => (event: ChangeEvent<HTMLInputElement>) => void;
  onRowClick: (projectId: string) => void;
  onToggleConfirm: (
    event: MouseEvent<HTMLButtonElement>,
    report: ReportSummary
  ) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
};

const REPORT_STATUS_VARIANTS: Record<
  ReportStatus,
  "warning" | "success" | "default"
> = {
  draft: "warning",
  final: "success",
  archived: "default",
};

export const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

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

export const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export function ReportsTableSurface({
  messages,
  archivedLabel,
  locale,
  intlLocale,
  reports,
  total,
  query,
  statusFilter,
  reportStatusOptions,
  confirmedFilter,
  confirmedOptions,
  updatedRange,
  updatedRangeOptions,
  cohortFilter,
  cohorts,
  includeArchived,
  selectedIds,
  selectedCount,
  allVisibleSelected,
  isLoading,
  loadError,
  cohortError,
  actionError,
  isBatchUpdating,
  isExporting,
  updatingReportId,
  pageStart,
  pageEnd,
  page,
  totalPages,
  canGoBack,
  canGoForward,
  toastMessage,
  onQueryChange,
  onStatusFilterChange,
  onConfirmedFilterChange,
  onCohortFilterChange,
  onUpdatedRangeChange,
  onIncludeArchivedChange,
  onBatchUpdate,
  onExport,
  onSelectAll,
  onSelectRow,
  onRowClick,
  onToggleConfirm,
  onPreviousPage,
  onNextPage,
}: ReportsTableSurfaceProps) {
  return (
    <>
      <Card className="admin-projects admin-reports">
        <CardHeader className="admin-projects__toolbar">
          <div className="admin-projects__toolbar-left">
            <div className="admin-projects__owner-search">
              <input
                type="search"
                className="input input--sm"
                placeholder={messages.filters.searchPlaceholder}
                value={query}
                aria-label={messages.filters.searchAriaLabel}
                onChange={(event) => onQueryChange(event.target.value)}
              />
            </div>
            <div className="admin-projects__status-filter">
              <select
                className="input input--sm"
                value={statusFilter}
                aria-label={messages.filters.statusFilterAriaLabel}
                onChange={(event) =>
                  onStatusFilterChange(event.target.value as ReportStatus | "all")
                }
              >
                {reportStatusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="admin-projects__cohort-filter">
              <select
                className="input input--sm"
                value={confirmedFilter}
                aria-label={messages.filters.confirmationFilterAriaLabel}
                onChange={(event) =>
                  onConfirmedFilterChange(event.target.value as ConfirmedFilter)
                }
              >
                {confirmedOptions.map((option) => (
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
                onChange={(event) => onCohortFilterChange(event.target.value)}
              >
                <option value="">{messages.filters.allCohorts}</option>
                {cohorts.map((cohort) => (
                  <option key={cohort.id} value={cohort.id}>
                    {cohort.is_archived
                      ? `${cohort.name} (${archivedLabel})`
                      : cohort.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="admin-projects__stage-filter">
              <select
                className="input input--sm"
                value={updatedRange}
                aria-label={messages.filters.updatedRangeAriaLabel}
                onChange={(event) =>
                  onUpdatedRangeChange(event.target.value as UpdatedRange)
                }
              >
                {updatedRangeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="admin-projects__toolbar-right">
            <label className="admin-projects__archived-toggle">
              <span className="admin-projects__archived-label">
                {messages.filters.includeArchived}
              </span>
              <span className="admin-switch">
                <input
                  type="checkbox"
                  checked={includeArchived}
                  onChange={(event) => onIncludeArchivedChange(event.target.checked)}
                  aria-label={messages.filters.includeArchived}
                />
                <span className="admin-switch__track">
                  <span className="admin-switch__thumb" />
                </span>
              </span>
            </label>
            <span className="admin-projects__count-badge">
              {interpolate(messages.filters.countBadge, {
                count: total.toLocaleString(intlLocale),
              })}
            </span>
            {selectedCount > 0 ? (
              <div className="admin-projects__batch">
                <span className="text-muted">
                  {interpolate(messages.batch.selectedCount, {
                    count: selectedCount.toLocaleString(intlLocale),
                  })}
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => onBatchUpdate(true)}
                  disabled={isBatchUpdating}
                >
                  {isBatchUpdating
                    ? messages.batch.updating
                    : messages.batch.confirmSelected}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onBatchUpdate(false)}
                  disabled={isBatchUpdating}
                >
                  {isBatchUpdating
                    ? messages.batch.updating
                    : messages.batch.unconfirmSelected}
                </Button>
              </div>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onExport}
              disabled={isExporting}
            >
              {isExporting ? messages.batch.exporting : messages.batch.exportCsv}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="admin-projects__content stack">
          {loadError ? (
            <div className="alert" role="alert">
              {loadError}
            </div>
          ) : null}
          {cohortError ? (
            <div className="alert" role="alert">
              {cohortError}
            </div>
          ) : null}
          {actionError ? (
            <div className="alert" role="alert">
              {actionError}
            </div>
          ) : null}

          <div className="admin-projects__table">
            <table className="admin-projects-table">
              <thead>
                <tr>
                  <th scope="col" className="admin-projects__col--select">
                    <label className="admin-checkbox-target">
                      <input
                        type="checkbox"
                        aria-label={messages.table.selectAllAria}
                        checked={allVisibleSelected}
                        onChange={onSelectAll}
                      />
                    </label>
                  </th>
                  <th scope="col">{messages.table.project}</th>
                  <th scope="col" className="admin-projects__col--owner">
                    {messages.table.owner}
                  </th>
                  <th scope="col">{messages.table.report}</th>
                  <th scope="col">{messages.table.confirmation}</th>
                  <th scope="col" className="admin-projects__col--updated">
                    {messages.table.updated}
                  </th>
                  <th scope="col" className="admin-projects__col--actions">
                    {messages.table.actions}
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading && reports.length === 0
                  ? Array.from({ length: 5 }).map((_, index) => (
                      <tr key={`skeleton-${index}`}>
                        <td className="admin-projects__col--select">
                          <div
                            className="skeleton"
                            style={{ width: 16, height: 16 }}
                          />
                        </td>
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
                        <td>
                          <div className="skeleton" style={{ width: 100 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 120 }} />
                        </td>
                        <td className="admin-projects__col--updated">
                          <div className="skeleton" style={{ width: 110 }} />
                        </td>
                        <td className="admin-projects__col--actions">
                          <div className="skeleton" style={{ width: 90 }} />
                        </td>
                      </tr>
                    ))
                  : reports.map((report) => {
                      const ownerLabel =
                        report.project.owner.display_name ||
                        report.project.owner.email ||
                        messages.table.unknownOwner;
                      const ownerEmail =
                        report.project.owner.email || messages.table.noEmail;
                      const ownerInitials = resolveInitials(ownerLabel);
                      const statusLabel =
                        messages.reportStatuses[report.status] ?? report.status;
                      const statusVariant =
                        REPORT_STATUS_VARIANTS[report.status] ?? "default";
                      const confirmationLabel = report.confirmed
                        ? messages.table.confirmed
                        : messages.table.unconfirmed;
                      const confirmationVariant = report.confirmed
                        ? "success"
                        : "warning";
                      return (
                        <tr
                          key={report.id}
                          className="admin-projects-table__row--clickable"
                          role="button"
                          tabIndex={0}
                          aria-label={interpolate(messages.table.openReportsAria, {
                            title:
                              report.project.title ||
                              messages.table.untitledProject,
                          })}
                          onClick={() => onRowClick(report.project.id)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onRowClick(report.project.id);
                            }
                          }}
                        >
                          <td
                            className="admin-projects__col--select"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <label className="admin-checkbox-target">
                              <input
                                type="checkbox"
                                aria-label={interpolate(
                                  messages.table.selectReportAria,
                                  {
                                    version: report.report_version,
                                  }
                                )}
                                checked={selectedIds.has(report.id)}
                                onChange={onSelectRow(report.id)}
                                onClick={(event) => event.stopPropagation()}
                              />
                            </label>
                          </td>
                          <td>
                            <div className="stack-sm">
                              <span className="admin-project__title">
                                {report.project.title ||
                                  messages.table.untitledProject}
                              </span>
                              <span className="admin-project__subtitle">
                                {interpolate(messages.table.reportVersion, {
                                  version: report.report_version,
                                })}
                                {report.project.is_archived
                                  ? ` · ${messages.table.archivedProjectSuffix}`
                                  : ""}
                              </span>
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
                          <td>
                            <div className="stack-sm">
                              <Badge variant={statusVariant}>{statusLabel}</Badge>
                              <span className="admin-project__muted">
                                {report.project.cohort?.name ||
                                  messages.table.globalCohort}
                              </span>
                            </div>
                          </td>
                          <td>
                            <Badge variant={confirmationVariant}>
                              {confirmationLabel}
                            </Badge>
                          </td>
                          <td className="admin-projects__col--updated">
                            <span className="admin-project__muted">
                              {formatDate(report.updated_at, locale)}
                            </span>
                          </td>
                          <td className="admin-projects__col--actions">
                            <div className="admin-projects__actions">
                              <Button
                                type="button"
                                variant={report.confirmed ? "secondary" : "primary"}
                                size="sm"
                                onClick={(event) => onToggleConfirm(event, report)}
                                onKeyDown={(event) => event.stopPropagation()}
                                disabled={updatingReportId === report.id}
                                aria-label={
                                  report.confirmed
                                    ? messages.table.unconfirmButtonAria
                                    : messages.table.confirmButtonAria
                                }
                              >
                                {updatingReportId === report.id
                                  ? messages.table.updating
                                  : report.confirmed
                                    ? messages.table.unconfirm
                                    : messages.table.confirm}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {!isLoading && reports.length === 0 ? (
            <div className="admin-projects__empty">{messages.table.empty}</div>
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
              onClick={onPreviousPage}
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
              onClick={onNextPage}
              disabled={!canGoForward}
            >
              {messages.pagination.next}
            </Button>
          </div>
        </CardFooter>
      </Card>
      {toastMessage ? (
        <div className="admin-toast" role="status" aria-live="polite">
          <span className="admin-toast__title">{toastMessage}</span>
        </div>
      ) : null}
    </>
  );
}
