import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  formatCohortTimeline,
  interpolateCohortMessage,
  type AdminCohortsMessages,
  type AdminTimelineMessages,
  type CohortStatusFilter,
  type CohortStatusFilterOption,
  type CohortSummary,
} from "@/features/admin/admin-cohorts-view-model";

type CohortsTableSurfaceProps = {
  actionError: string | null;
  canGoBack: boolean;
  canGoForward: boolean;
  cohorts: CohortSummary[];
  intlLocale: string;
  isLoading: boolean;
  loadError: string | null;
  locale: string;
  messages: AdminCohortsMessages;
  onArchiveToggle: (cohort: CohortSummary) => void;
  onCreateOpen: () => void;
  onNextPage: () => void;
  onPreviousPage: () => void;
  onQueryChange: (value: string) => void;
  onRowClick: (cohortId: string) => void;
  onStatusFilterChange: (value: CohortStatusFilter) => void;
  page: number;
  pageEnd: number;
  pageStart: number;
  pendingArchive: Record<string, boolean>;
  query: string;
  statusFilter: CohortStatusFilter;
  statusFilterOptions: CohortStatusFilterOption[];
  timelineMessages: AdminTimelineMessages;
  toastMessage: string | null;
  total: number;
  totalPages: number;
};

export function CohortsTableSurface({
  actionError,
  canGoBack,
  canGoForward,
  cohorts,
  intlLocale,
  isLoading,
  loadError,
  locale,
  messages,
  onArchiveToggle,
  onCreateOpen,
  onNextPage,
  onPreviousPage,
  onQueryChange,
  onRowClick,
  onStatusFilterChange,
  page,
  pageEnd,
  pageStart,
  pendingArchive,
  query,
  statusFilter,
  statusFilterOptions,
  timelineMessages,
  toastMessage,
  total,
  totalPages,
}: CohortsTableSurfaceProps) {
  return (
    <>
      <Card className="admin-cohorts">
        <CardHeader className="admin-cohorts__toolbar">
          <div className="admin-cohorts__toolbar-left">
            <div className="admin-cohorts__search">
              <input
                type="search"
                className="input input--sm"
                value={query}
                placeholder={messages.filters.searchPlaceholder}
                aria-label={messages.filters.searchAriaLabel}
                onChange={(event) => onQueryChange(event.target.value)}
              />
            </div>
            <div className="admin-cohorts__status-filter">
              <select
                className="input input--sm"
                value={statusFilter}
                aria-label={messages.filters.statusFilterAriaLabel}
                onChange={(event) =>
                  onStatusFilterChange(event.target.value as CohortStatusFilter)
                }
              >
                {statusFilterOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="admin-cohorts__toolbar-right">
            <span className="admin-cohorts__count-badge">
              {interpolateCohortMessage(messages.filters.countBadge, {
                count: total.toLocaleString(intlLocale),
              })}
            </span>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={onCreateOpen}
            >
              {messages.filters.newCohort}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="admin-cohorts__content stack">
          {loadError ? (
            <div className="alert" role="alert">
              <span>{loadError}</span>
            </div>
          ) : null}
          {actionError ? (
            <div className="alert" role="alert">
              <span>{actionError}</span>
            </div>
          ) : null}

          <div className="admin-cohorts__table">
            <table className="admin-cohorts-table">
              <thead>
                <tr>
                  <th scope="col">{messages.table.cohort}</th>
                  <th scope="col" className="admin-cohorts__col--timeline">
                    {messages.table.timeline}
                  </th>
                  <th scope="col">{messages.table.students}</th>
                  <th scope="col" className="admin-cohorts__col--mentors">
                    {messages.table.mentors}
                  </th>
                  <th scope="col" className="admin-cohorts__col--projects">
                    {messages.table.projects}
                  </th>
                  <th scope="col">{messages.table.status}</th>
                  <th scope="col">{messages.table.actions}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && cohorts.length === 0
                  ? Array.from({ length: 5 }).map((_, index) => (
                      <tr key={`skeleton-${index}`}>
                        <td>
                          <div className="stack-sm">
                            <div className="skeleton" style={{ width: 180 }} />
                            <div className="skeleton" style={{ width: 140 }} />
                          </div>
                        </td>
                        <td className="admin-cohorts__col--timeline">
                          <div className="skeleton" style={{ width: 160 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 70 }} />
                        </td>
                        <td className="admin-cohorts__col--mentors">
                          <div className="skeleton" style={{ width: 70 }} />
                        </td>
                        <td className="admin-cohorts__col--projects">
                          <div className="skeleton" style={{ width: 70 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 80 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 120 }} />
                        </td>
                      </tr>
                    ))
                  : cohorts.map((cohort) => {
                      const isArchived = cohort.is_archived;
                      const isUpdating = Boolean(pendingArchive[cohort.id]);
                      return (
                        <tr
                          key={cohort.id}
                          className={[
                            "admin-cohorts-table__row--clickable",
                            isArchived ? "admin-cohorts-table__row--archived" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                          onClick={() => onRowClick(cohort.id)}
                          role="link"
                          tabIndex={0}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onRowClick(cohort.id);
                            }
                          }}
                        >
                          <td>
                            <div className="stack-sm">
                              <div className="admin-cohort__name">
                                {cohort.name}
                              </div>
                              <span className="admin-cohort__muted">
                                {cohort.description || messages.table.noDescription}
                              </span>
                            </div>
                          </td>
                          <td className="admin-cohorts__col--timeline">
                            <span className="admin-cohort__muted">
                              {formatCohortTimeline(
                                cohort.start_at,
                                cohort.end_at,
                                locale,
                                timelineMessages
                              )}
                            </span>
                          </td>
                          <td>
                            <span className="admin-cohort__metric">
                              {cohort.students_count.toLocaleString(intlLocale)}
                            </span>
                          </td>
                          <td className="admin-cohorts__col--mentors">
                            <span className="admin-cohort__metric">
                              {cohort.mentors_count.toLocaleString(intlLocale)}
                            </span>
                          </td>
                          <td className="admin-cohorts__col--projects">
                            <span className="admin-cohort__metric">
                              {cohort.projects_count.toLocaleString(intlLocale)}
                            </span>
                          </td>
                          <td>
                            <Badge variant={isArchived ? "warning" : "success"}>
                              {isArchived
                                ? messages.table.archived
                                : messages.table.active}
                            </Badge>
                          </td>
                          <td>
                            <div className="admin-cohort__actions">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="admin-cohort__archive"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  onArchiveToggle(cohort);
                                }}
                                onKeyDown={(event) => event.stopPropagation()}
                                disabled={isUpdating}
                              >
                                {isArchived
                                  ? messages.table.unarchive
                                  : messages.table.archive}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {!isLoading && cohorts.length === 0 ? (
            <div className="admin-cohorts__empty">{messages.table.empty}</div>
          ) : null}
        </CardContent>
        <CardFooter className="admin-cohorts__footer">
          <span className="text-muted">
            {interpolateCohortMessage(messages.pagination.showing, {
              start: pageStart,
              end: pageEnd,
              total: total.toLocaleString(intlLocale),
            })}
          </span>
          <div className="admin-cohorts__pagination">
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
              {interpolateCohortMessage(messages.pagination.page, {
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
