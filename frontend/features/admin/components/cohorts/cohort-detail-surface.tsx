import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button, buttonClassNames } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { buildLocalePath, type AppLocale } from "@/lib/i18n/config";
import type { useAppMessages } from "@/lib/i18n/provider";

import type {
  CohortMemberItem,
  CohortProjectItem,
  CohortSummary,
  DetailTab,
  MemberStatusFilter,
} from "./cohort-detail-types";

type CohortDetailMessages = ReturnType<typeof useAppMessages>["adminCohortDetail"];
type TimelineMessages = ReturnType<typeof useAppMessages>["adminShared"]["timeline"];

type StatusFilterOption = {
  value: MemberStatusFilter;
  label: string;
};

type CohortDetailSurfaceProps = {
  locale: AppLocale;
  messages: CohortDetailMessages;
  timelineMessages: TimelineMessages;
  intlLocale: string;
  cohort: CohortSummary | null;
  archiveLabel: string;
  archiveVariant: "success" | "warning";
  isArchiving: boolean;
  tab: DetailTab;
  tabLabel: string;
  query: string;
  searchPlaceholder: string;
  statusFilter: MemberStatusFilter;
  statusFilterOptions: StatusFilterOption[];
  isMemberTab: boolean;
  total: number;
  addLabel: string;
  items: Array<CohortMemberItem | CohortProjectItem>;
  isLoading: boolean;
  loadError: string | null;
  actionError: string | null;
  pageStart: number;
  pageEnd: number;
  page: number;
  totalPages: number;
  canGoBack: boolean;
  canGoForward: boolean;
  toastMessage: string | null;
  onArchiveToggle: () => void;
  onTabChange: (tab: DetailTab) => void;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: MemberStatusFilter) => void;
  onOpenAdd: () => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onRequestRemoveMember: (member: CohortMemberItem) => void;
};

const formatDate = (value: string | null, locale: AppLocale): string => {
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

export const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

const formatTimeline = (
  startAt: string | null,
  endAt: string | null,
  locale: AppLocale,
  timelineMessages: TimelineMessages
): string => {
  if (!startAt && !endAt) {
    return timelineMessages.datesTbd;
  }
  if (startAt && endAt) {
    return `${formatDate(startAt, locale)} - ${formatDate(endAt, locale)}`;
  }
  if (startAt) {
    return interpolate(timelineMessages.starts, {
      date: formatDate(startAt, locale),
    });
  }
  return interpolate(timelineMessages.ends, {
    date: formatDate(endAt, locale),
  });
};

const formatLabel = (value: string | null): string => {
  if (!value) {
    return "--";
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
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

function CohortDetailHeader({
  locale,
  messages,
  timelineMessages,
  cohort,
  archiveLabel,
  archiveVariant,
  isArchiving,
  onArchiveToggle,
}: Pick<
  CohortDetailSurfaceProps,
  | "locale"
  | "messages"
  | "timelineMessages"
  | "cohort"
  | "archiveLabel"
  | "archiveVariant"
  | "isArchiving"
  | "onArchiveToggle"
>) {
  return (
    <div className="page-header">
      <div className="stack-sm">
        <p className="eyebrow">{messages.page.eyebrow}</p>
        <div className="admin-cohort-detail__title">
          <h1 className="page-title">
            {cohort?.name ?? messages.page.fallbackTitle}
          </h1>
          {cohort ? <Badge variant={archiveVariant}>{archiveLabel}</Badge> : null}
        </div>
        <p className="page-subtitle">
          {cohort?.description || messages.page.fallbackDescription}
        </p>
        {cohort ? (
          <p className="text-muted">
            {formatTimeline(
              cohort.start_at,
              cohort.end_at,
              locale,
              timelineMessages
            )}
          </p>
        ) : null}
      </div>
      <div className="admin-cohort-detail__header-actions">
        <Link
          className={buttonClassNames({ variant: "secondary", size: "sm" })}
          href={buildLocalePath(locale, "/admin/cohorts")}
        >
          {messages.page.backToCohorts}
        </Link>
        {cohort ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="admin-cohort__archive"
            onClick={onArchiveToggle}
            disabled={isArchiving}
          >
            {cohort.is_archived ? messages.page.unarchive : messages.page.archive}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function CohortDetailTabs({
  messages,
  tab,
  onTabChange,
}: Pick<CohortDetailSurfaceProps, "messages" | "tab" | "onTabChange">) {
  return (
    <CardHeader className="admin-cohort-detail__tabs">
      <div
        className="admin-tabs"
        role="tablist"
        aria-label={messages.page.tabsAriaLabel}
      >
        {(["members", "mentors", "projects"] as DetailTab[]).map((entry) => (
          <button
            key={entry}
            type="button"
            role="tab"
            aria-selected={tab === entry}
            className={["admin-tab", tab === entry ? "admin-tab--active" : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onTabChange(entry)}
          >
            {entry === "members"
              ? messages.tabs.members
              : entry === "mentors"
                ? messages.tabs.mentors
                : messages.tabs.projects}
          </button>
        ))}
      </div>
    </CardHeader>
  );
}

function CohortDetailToolbar({
  messages,
  intlLocale,
  tabLabel,
  query,
  searchPlaceholder,
  statusFilter,
  statusFilterOptions,
  isMemberTab,
  total,
  addLabel,
  onQueryChange,
  onStatusFilterChange,
  onOpenAdd,
}: Pick<
  CohortDetailSurfaceProps,
  | "messages"
  | "intlLocale"
  | "tabLabel"
  | "query"
  | "searchPlaceholder"
  | "statusFilter"
  | "statusFilterOptions"
  | "isMemberTab"
  | "total"
  | "addLabel"
  | "onQueryChange"
  | "onStatusFilterChange"
  | "onOpenAdd"
>) {
  return (
    <div className="admin-cohort-detail__toolbar">
      <div className="admin-cohort-detail__toolbar-left">
        <div className="admin-cohort-detail__search">
          <input
            type="search"
            className="input input--sm"
            value={query}
            placeholder={searchPlaceholder}
            aria-label={messages.filters.searchAriaLabel}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
        {isMemberTab ? (
          <div className="admin-cohort-detail__status-filter">
            <select
              className="input input--sm"
              value={statusFilter}
              aria-label={messages.filters.memberStatusFilterAriaLabel}
              onChange={(event) =>
                onStatusFilterChange(event.target.value as MemberStatusFilter)
              }
            >
              {statusFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}
      </div>
      <div className="admin-cohort-detail__toolbar-right">
        <span className="admin-cohort-detail__count-badge">
          {interpolate(messages.filters.countBadge, {
            count: total.toLocaleString(intlLocale),
            label: tabLabel,
          })}
        </span>
        {isMemberTab ? (
          <Button type="button" size="sm" variant="secondary" onClick={onOpenAdd}>
            {addLabel}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function CohortProjectsTable({
  locale,
  messages,
  items,
  isLoading,
}: Pick<CohortDetailSurfaceProps, "locale" | "messages" | "items" | "isLoading">) {
  return (
    <table className="admin-cohort-projects-table">
      <thead>
        <tr>
          <th scope="col">{messages.projectTable.project}</th>
          <th scope="col" className="admin-cohort-projects__col--owner">
            {messages.projectTable.owner}
          </th>
          <th scope="col" className="admin-cohort-projects__col--stage">
            {messages.projectTable.stage}
          </th>
          <th scope="col">{messages.projectTable.status}</th>
        </tr>
      </thead>
      <tbody>
        {isLoading && items.length === 0
          ? Array.from({ length: 5 }).map((_, index) => (
              <tr key={`skeleton-${index}`}>
                <td>
                  <div className="skeleton" style={{ width: 180 }} />
                </td>
                <td className="admin-cohort-projects__col--owner">
                  <div className="skeleton" style={{ width: 140 }} />
                </td>
                <td className="admin-cohort-projects__col--stage">
                  <div className="skeleton" style={{ width: 90 }} />
                </td>
                <td>
                  <div className="skeleton" style={{ width: 90 }} />
                </td>
              </tr>
            ))
          : (items as CohortProjectItem[]).map((project, index) => {
              const ownerPrimary =
                project.owner_name ||
                project.owner_email ||
                messages.projectTable.unknownOwner;
              const ownerSecondary =
                project.owner_name && project.owner_email
                  ? project.owner_email
                  : null;
              const rowKey = project.id
                ? `${project.id}-${index}`
                : `project-${index}`;
              return (
                <tr
                  key={rowKey}
                  className={
                    project.is_archived
                      ? "admin-cohort-projects__row--archived"
                      : ""
                  }
                >
                  <td>
                    <div className="stack-sm">
                      <Link
                        href={buildLocalePath(
                          locale,
                          `/admin/projects/${project.id}`
                        )}
                        className="admin-cohort-project__link"
                      >
                        {project.title || messages.projectTable.untitledProject}
                      </Link>
                      {project.is_archived ? (
                        <span className="admin-cohort-project__muted">
                          {messages.projectTable.archived}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="admin-cohort-projects__col--owner">
                    <span className="admin-cohort-project__owner">
                      {ownerPrimary}
                    </span>
                    {ownerSecondary ? (
                      <span className="admin-cohort-project__muted">
                        {ownerSecondary}
                      </span>
                    ) : null}
                  </td>
                  <td className="admin-cohort-projects__col--stage">
                    <span className="admin-cohort-project__muted">
                      {messages.stageLabels[project.current_stage ?? ""] ||
                        formatLabel(project.current_stage)}
                    </span>
                  </td>
                  <td>
                    <Badge
                      variant={
                        project.stage_status === "passed"
                          ? "success"
                          : project.stage_status === "awaiting_confirm"
                            ? "info"
                            : "warning"
                      }
                    >
                      {messages.stageStatuses[project.stage_status ?? ""] ||
                        formatLabel(project.stage_status)}
                    </Badge>
                  </td>
                </tr>
              );
            })}
      </tbody>
    </table>
  );
}

function CohortMembersTable({
  locale,
  messages,
  items,
  isLoading,
  onRequestRemoveMember,
}: Pick<
  CohortDetailSurfaceProps,
  "locale" | "messages" | "items" | "isLoading" | "onRequestRemoveMember"
>) {
  return (
    <table className="admin-cohort-members-table">
      <thead>
        <tr>
          <th scope="col">{messages.memberTable.member}</th>
          <th scope="col" className="admin-cohort-members__col--email">
            {messages.memberTable.email}
          </th>
          <th scope="col">{messages.memberTable.status}</th>
          <th scope="col" className="admin-cohort-members__col--joined">
            {messages.memberTable.joined}
          </th>
          <th scope="col">{messages.memberTable.actions}</th>
        </tr>
      </thead>
      <tbody>
        {isLoading && items.length === 0
          ? Array.from({ length: 5 }).map((_, index) => (
              <tr key={`skeleton-${index}`}>
                <td>
                  <div className="admin-member__identity">
                    <div
                      className="skeleton"
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 999,
                      }}
                    />
                    <div className="stack-sm">
                      <div className="skeleton" style={{ width: 160 }} />
                      <div className="skeleton" style={{ width: 120 }} />
                    </div>
                  </div>
                </td>
                <td className="admin-cohort-members__col--email">
                  <div className="skeleton" style={{ width: 160 }} />
                </td>
                <td>
                  <div className="skeleton" style={{ width: 80 }} />
                </td>
                <td className="admin-cohort-members__col--joined">
                  <div className="skeleton" style={{ width: 100 }} />
                </td>
                <td>
                  <div className="skeleton" style={{ width: 70 }} />
                </td>
              </tr>
            ))
          : (items as CohortMemberItem[]).map((member) => {
              const displayName =
                member.display_name ||
                member.email ||
                messages.memberTable.fallbackMember;
              const initials = resolveInitials(displayName);
              const isRemoved = member.status === "removed";
              return (
                <tr
                  key={member.membership_id}
                  className={
                    isRemoved ? "admin-cohort-members__row--removed" : ""
                  }
                >
                  <td>
                    <div className="admin-member__identity">
                      <div className="admin-member__avatar">{initials}</div>
                      <div className="stack-sm">
                        <span className="admin-member__name">{displayName}</span>
                      </div>
                    </div>
                  </td>
                  <td className="admin-cohort-members__col--email">
                    <span className="admin-member__email">
                      {member.email || messages.memberTable.noEmail}
                    </span>
                  </td>
                  <td>
                    <Badge variant={isRemoved ? "danger" : "success"}>
                      {isRemoved
                        ? messages.memberTable.removed
                        : messages.memberTable.active}
                    </Badge>
                  </td>
                  <td className="admin-cohort-members__col--joined">
                    <span className="admin-member__muted">
                      {formatDate(member.joined_at, locale)}
                    </span>
                  </td>
                  <td>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="admin-cohort-member__remove"
                      onClick={() => onRequestRemoveMember(member)}
                      disabled={isRemoved}
                    >
                      {messages.memberTable.remove}
                    </Button>
                  </td>
                </tr>
              );
            })}
      </tbody>
    </table>
  );
}

function CohortDetailFooter({
  messages,
  intlLocale,
  pageStart,
  pageEnd,
  page,
  total,
  totalPages,
  canGoBack,
  canGoForward,
  onPreviousPage,
  onNextPage,
}: Pick<
  CohortDetailSurfaceProps,
  | "messages"
  | "intlLocale"
  | "pageStart"
  | "pageEnd"
  | "page"
  | "total"
  | "totalPages"
  | "canGoBack"
  | "canGoForward"
  | "onPreviousPage"
  | "onNextPage"
>) {
  return (
    <CardFooter className="admin-cohort-detail__footer">
      <span className="text-muted">
        {interpolate(messages.pagination.showing, {
          start: pageStart,
          end: pageEnd,
          total: total.toLocaleString(intlLocale),
        })}
      </span>
      <div className="admin-cohort-detail__pagination">
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
  );
}

export function CohortDetailSurface(props: CohortDetailSurfaceProps) {
  const {
    messages,
    tab,
    items,
    isLoading,
    loadError,
    actionError,
    toastMessage,
  } = props;

  return (
    <div className="page">
      <CohortDetailHeader {...props} />

      <Card className="admin-cohort-detail">
        <CohortDetailTabs {...props} />
        <CardContent className="admin-cohort-detail__content stack">
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

          <CohortDetailToolbar {...props} />

          <div className="admin-cohort-detail__table">
            {tab === "projects" ? (
              <CohortProjectsTable {...props} />
            ) : (
              <CohortMembersTable {...props} />
            )}
          </div>

          {!isLoading && items.length === 0 ? (
            <div className="admin-cohort-detail__empty">
              {tab === "projects"
                ? messages.projectTable.empty
                : messages.memberTable.empty}
            </div>
          ) : null}
        </CardContent>
        <CohortDetailFooter {...props} />
      </Card>

      {toastMessage ? (
        <div className="admin-toast" role="status" aria-live="polite">
          <span className="admin-toast__title">{toastMessage}</span>
        </div>
      ) : null}
    </div>
  );
}
