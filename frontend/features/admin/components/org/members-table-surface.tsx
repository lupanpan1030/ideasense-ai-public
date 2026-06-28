import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { buildLocalePath, type AppLocale } from "@/lib/i18n/config";
import {
  DEFAULT_MEMBERS_LIMIT,
  formatMemberDate,
  interpolateMemberMessage,
  MEMBER_STATUS_VARIANTS,
  resolveMemberInitials,
  resolveMemberIntlLocale,
  type AdminMembersMessages,
  type MemberRoleFilter,
  type MutableOrgRole,
  type OrgMember,
} from "@/features/admin/admin-members-view-model";

type FilterOption<T extends string> = {
  value: T;
  label: string;
};

type MembersTableSurfaceProps = {
  actionError: string | null;
  canGoBack: boolean;
  canGoForward: boolean;
  currentPage: number;
  isLoading: boolean;
  loadError: string | null;
  locale: AppLocale;
  members: OrgMember[];
  messages: AdminMembersMessages;
  offset: number;
  onOffsetChange: (offset: number) => void;
  onQueryChange: (value: string) => void;
  onRemoveRequest: (member: OrgMember) => void;
  onRoleChange: (member: OrgMember, nextRole: MutableOrgRole) => void;
  onRoleFilterChange: (value: MemberRoleFilter) => void;
  pageEnd: number;
  pageStart: number;
  pendingRoles: Record<string, boolean>;
  query: string;
  roleFilter: MemberRoleFilter;
  roleFilterOptions: Array<FilterOption<MemberRoleFilter>>;
  roleOptions: Array<FilterOption<MutableOrgRole>>;
  toastMessage: string | null;
  total: number;
  totalPages: number;
};

export function MembersTableSurface({
  actionError,
  canGoBack,
  canGoForward,
  currentPage,
  isLoading,
  loadError,
  locale,
  members,
  messages,
  offset,
  onOffsetChange,
  onQueryChange,
  onRemoveRequest,
  onRoleChange,
  onRoleFilterChange,
  pageEnd,
  pageStart,
  pendingRoles,
  query,
  roleFilter,
  roleFilterOptions,
  roleOptions,
  toastMessage,
  total,
  totalPages,
}: MembersTableSurfaceProps) {
  return (
    <>
      <Card className="admin-members">
        <CardHeader className="admin-members__toolbar">
          <div className="admin-members__toolbar-left">
            <div className="admin-members__search">
              <input
                id="member-search"
                type="search"
                className="input input--sm"
                value={query}
                placeholder={messages.filters.searchPlaceholder}
                aria-label={messages.filters.searchAriaLabel}
                onChange={(event) => onQueryChange(event.target.value)}
              />
            </div>
            <div className="admin-members__role-filter">
              <select
                id="member-role-filter"
                className="input input--sm"
                value={roleFilter}
                aria-label={messages.filters.roleFilterAriaLabel}
                onChange={(event) =>
                  onRoleFilterChange(event.target.value as MemberRoleFilter)
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
          <div className="admin-members__toolbar-right">
            <span className="admin-members__count-badge">
              {interpolateMemberMessage(messages.filters.countBadge, {
                count: total.toLocaleString(resolveMemberIntlLocale(locale)),
              })}
            </span>
            <Link
              className={buttonClassNames({ variant: "secondary", size: "sm" })}
              href={buildLocalePath(locale, "/admin/org/invites")}
            >
              {messages.filters.invite}
            </Link>
          </div>
        </CardHeader>
        <CardContent className="admin-members__content stack">
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

          <div className="admin-members__table">
            <table className="admin-members-table">
              <thead>
                <tr>
                  <th scope="col">{messages.table.user}</th>
                  <th scope="col" className="admin-members__col--email">
                    {messages.table.email}
                  </th>
                  <th scope="col">{messages.table.role}</th>
                  <th scope="col">{messages.table.status}</th>
                  <th scope="col" className="admin-members__col--joined">
                    {messages.table.joined}
                  </th>
                  <th scope="col">{messages.table.actions}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && members.length === 0
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
                        <td className="admin-members__col--email">
                          <div className="skeleton" style={{ width: 180 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 120 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 90 }} />
                        </td>
                        <td className="admin-members__col--joined">
                          <div className="skeleton" style={{ width: 110 }} />
                        </td>
                        <td>
                          <div className="skeleton" style={{ width: 80 }} />
                        </td>
                      </tr>
                    ))
                  : members.map((member) => {
                      const displayName =
                        member.user?.display_name ||
                        member.user?.email ||
                        messages.table.removedMember;
                      const email =
                        member.user?.email || messages.table.emailUnavailable;
                      const initials = resolveMemberInitials(displayName);
                      const isOwner = member.org_role === "owner";
                      const isRemoved = member.status === "removed";
                      const isUpdating = Boolean(pendingRoles[member.id]);
                      const disableActions = isOwner || isRemoved || isUpdating;
                      const actionHint = isOwner
                        ? messages.table.ownerCannotBeModified
                        : isRemoved
                          ? messages.table.removedCannotBeEdited
                          : undefined;
                      return (
                        <tr
                          key={member.id}
                          className={
                            isRemoved ? "admin-members-table__row--removed" : ""
                          }
                        >
                          <td>
                            <div className="admin-member__identity">
                              <div className="admin-member__avatar">
                                {initials}
                              </div>
                              <div className="stack-sm">
                                <div className="admin-member__name-row">
                                  <span className="admin-member__name">
                                    {displayName}
                                  </span>
                                  {isOwner ? (
                                    <Badge
                                      variant="info"
                                      className="admin-member__owner-badge"
                                    >
                                      {messages.table.owner}
                                    </Badge>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="admin-members__col--email">
                            <span className="admin-member__email">{email}</span>
                          </td>
                          <td>
                            {isOwner ? (
                              <span className="admin-member__role-static">
                                {messages.table.owner}
                              </span>
                            ) : (
                              <select
                                className="input input--sm admin-member__role-select"
                                value={member.org_role}
                                onChange={(event) =>
                                  onRoleChange(
                                    member,
                                    event.target.value as MutableOrgRole
                                  )
                                }
                                disabled={disableActions}
                                aria-label={interpolateMemberMessage(
                                  messages.table.roleFor,
                                  { name: displayName }
                                )}
                                title={actionHint}
                              >
                                {roleOptions.map((option) => (
                                  <option
                                    key={option.value}
                                    value={option.value}
                                  >
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            )}
                            {isUpdating ? (
                              <span className="admin-member__muted">
                                {messages.table.saving}
                              </span>
                            ) : null}
                          </td>
                          <td>
                            <Badge variant={MEMBER_STATUS_VARIANTS[member.status]}>
                              {messages.statuses[member.status]}
                            </Badge>
                          </td>
                          <td className="admin-members__col--joined">
                            <span className="admin-member__muted">
                              {formatMemberDate(member.created_at, locale)}
                            </span>
                          </td>
                          <td>
                            <div className="admin-member__actions">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="admin-member__remove"
                                onClick={() => onRemoveRequest(member)}
                                disabled={disableActions}
                                title={actionHint}
                              >
                                {messages.table.remove}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {!isLoading && members.length === 0 ? (
            <div className="admin-members__empty">
              {messages.table.empty}
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="admin-members__footer">
          <span className="text-muted">
            {interpolateMemberMessage(messages.pagination.showing, {
              start: pageStart,
              end: pageEnd,
              total: total.toLocaleString(resolveMemberIntlLocale(locale)),
            })}
          </span>
          <div className="admin-members__pagination">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() =>
                onOffsetChange(Math.max(offset - DEFAULT_MEMBERS_LIMIT, 0))
              }
              disabled={!canGoBack}
            >
              {messages.pagination.previous}
            </Button>
            <span className="text-muted">
              {interpolateMemberMessage(messages.pagination.page, {
                current: currentPage,
                total: totalPages,
              })}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onOffsetChange(offset + DEFAULT_MEMBERS_LIMIT)}
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
