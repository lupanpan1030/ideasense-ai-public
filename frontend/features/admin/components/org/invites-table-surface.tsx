import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  formatInviteDate,
  interpolateInviteMessage,
  resolveIntlLocale,
  STATUS_VARIANTS,
  type AdminInvitesMessages,
  type AdminRoleLabels,
  type OrgInvite,
  type RoleFilter,
  type StatusFilter,
} from "@/features/admin/admin-invites-view-model";

type FilterOption<T extends string> = {
  value: T;
  label: string;
};

type InvitesTableSurfaceProps = {
  actionError: string | null;
  canGoBack: boolean;
  canGoForward: boolean;
  currentPage: number;
  invites: OrgInvite[];
  isLoading: boolean;
  loadError: string | null;
  locale: string;
  messages: AdminInvitesMessages;
  onOpenCreateModal: () => void;
  onPageChange: (page: number) => void;
  onQueryChange: (value: string) => void;
  onRequestRevoke: (invite: OrgInvite) => void;
  onRoleFilterChange: (value: RoleFilter) => void;
  onStatusFilterChange: (value: StatusFilter) => void;
  page: number;
  pageEnd: number;
  pageStart: number;
  query: string;
  roleFilter: RoleFilter;
  roleFilterOptions: Array<FilterOption<RoleFilter>>;
  roleLabels: AdminRoleLabels;
  statusFilter: StatusFilter;
  statusFilterOptions: Array<FilterOption<StatusFilter>>;
  toastMessage: string | null;
  total: number;
  totalPages: number;
};

export function InvitesTableSurface({
  actionError,
  canGoBack,
  canGoForward,
  currentPage,
  invites,
  isLoading,
  loadError,
  locale,
  messages,
  onOpenCreateModal,
  onPageChange,
  onQueryChange,
  onRequestRevoke,
  onRoleFilterChange,
  onStatusFilterChange,
  page,
  pageEnd,
  pageStart,
  query,
  roleFilter,
  roleFilterOptions,
  roleLabels,
  statusFilter,
  statusFilterOptions,
  toastMessage,
  total,
  totalPages,
}: InvitesTableSurfaceProps) {
  return (
    <>
      <Card className="admin-invites">
        <CardHeader className="admin-invites__toolbar">
          <div className="admin-invites__toolbar-left">
            <div className="admin-invites__search">
              <input
                id="invite-search"
                type="search"
                className="input input--sm"
                value={query}
                placeholder={messages.filters.searchPlaceholder}
                aria-label={messages.filters.searchAriaLabel}
                onChange={(event) => onQueryChange(event.target.value)}
              />
            </div>
            <div className="admin-invites__role-filter">
              <select
                id="invite-role-filter"
                className="input input--sm"
                value={roleFilter}
                aria-label={messages.filters.roleFilterAriaLabel}
                onChange={(event) =>
                  onRoleFilterChange(event.target.value as RoleFilter)
                }
              >
                {roleFilterOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="admin-invites__toolbar-right">
            <div className="admin-invites__status-filter">
              <select
                id="invite-status-filter"
                className="input input--sm"
                value={statusFilter}
                aria-label={messages.filters.statusFilterAriaLabel}
                onChange={(event) =>
                  onStatusFilterChange(event.target.value as StatusFilter)
                }
              >
                {statusFilterOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <span className="admin-invites__count-badge">
              {interpolateInviteMessage(messages.filters.countBadge, {
                count: total.toLocaleString(resolveIntlLocale(locale)),
              })}
            </span>
            <Button type="button" size="sm" onClick={onOpenCreateModal}>
              {messages.filters.createInvite}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="admin-invites__content stack">
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

          <div className="admin-invites__table">
            <table className="admin-invites-table">
              <thead>
                <tr>
                  <th scope="col">{messages.table.email}</th>
                  <th scope="col" className="admin-invites__col--role">
                    {messages.table.role}
                  </th>
                  <th scope="col">{messages.table.status}</th>
                  <th scope="col" className="admin-invites__col--expires">
                    {messages.table.expires}
                  </th>
                  <th scope="col" className="admin-invites__col--created">
                    {messages.table.created}
                  </th>
                  <th scope="col" className="admin-invites__col--actions">
                    {messages.table.actions}
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading && invites.length === 0
                  ? Array.from({ length: 5 }).map((_, index) => (
                      <tr key={`skeleton-${index}`}>
                        <td>
                          <div className="skeleton" style={{ width: 180 }} />
                        </td>
                        <td className="admin-invites__col--role">
                          <div className="skeleton" style={{ width: 80 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 90 }} />
                        </td>
                        <td className="admin-invites__col--expires">
                          <div className="skeleton" style={{ width: 90 }} />
                        </td>
                        <td className="admin-invites__col--created">
                          <div className="skeleton" style={{ width: 90 }} />
                        </td>
                        <td className="admin-invites__col--actions">
                          <div className="skeleton" style={{ width: 80 }} />
                        </td>
                      </tr>
                    ))
                  : invites.map((invite) => {
                      const isPending = invite.status === "pending";
                      return (
                        <tr key={invite.id}>
                          <td className="admin-invite__email">
                            {invite.invitee_email}
                          </td>
                          <td className="admin-invites__col--role">
                            {roleLabels[invite.invited_role] ?? invite.invited_role}
                          </td>
                          <td>
                            <Badge variant={STATUS_VARIANTS[invite.status]}>
                              {messages.statuses[invite.status]}
                            </Badge>
                          </td>
                          <td className="admin-invites__col--expires">
                            <span className="admin-invite__muted">
                              {formatInviteDate(invite.expires_at, locale)}
                            </span>
                          </td>
                          <td className="admin-invites__col--created">
                            <span className="admin-invite__muted">
                              {formatInviteDate(invite.created_at, locale)}
                            </span>
                          </td>
                          <td className="admin-invites__col--actions">
                            <div className="admin-invite__actions">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="admin-invite__revoke"
                                onClick={() => onRequestRevoke(invite)}
                                disabled={!isPending}
                              >
                                {messages.table.revoke}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {!isLoading && invites.length === 0 ? (
            <div className="admin-invites__empty">
              {messages.table.empty}
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="admin-invites__footer">
          <span className="text-muted">
            {interpolateInviteMessage(messages.pagination.showing, {
              start: pageStart,
              end: pageEnd,
              total: total.toLocaleString(resolveIntlLocale(locale)),
            })}
          </span>
          <div className="admin-invites__pagination">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onPageChange(Math.max(page - 1, 1))}
              disabled={!canGoBack}
            >
              {messages.pagination.previous}
            </Button>
            <span className="text-muted">
              {interpolateInviteMessage(messages.pagination.page, {
                current: currentPage,
                total: totalPages,
              })}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onPageChange(page + 1)}
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
