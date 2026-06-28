import type { FormEventHandler } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  ASSIGNMENT_STATUS_VARIANTS,
  interpolateMentorAssignmentMessage,
  resolveMentorAssignmentInitials,
  type AdminMentorAssignmentsMessages,
  type AssignmentFlags,
  type AssignmentStatusFilter,
  type CohortOption,
  type MemberOption,
  type MentorAssignment,
  type StatusFilterOption,
} from "@/features/admin/admin-mentor-assignments-view-model";

import {
  AssignmentFormModal,
  AssignmentToast,
  RevokeAssignmentModal,
} from "./mentor-assignments-modals";
type MentorAssignmentsSurfaceProps = {
  messages: AdminMentorAssignmentsMessages;
  intlLocale: string;
  assignments: MentorAssignment[];
  total: number;
  query: string;
  statusFilter: AssignmentStatusFilter;
  statusFilterOptions: StatusFilterOption[];
  cohortFilter: string;
  cohortOptions: CohortOption[];
  isLoading: boolean;
  loadError: string | null;
  cohortError: string | null;
  actionError: string | null;
  pageStart: number;
  pageEnd: number;
  page: number;
  totalPages: number;
  canGoBack: boolean;
  canGoForward: boolean;
  isModalOpen: boolean;
  modalMode: "create" | "restore" | "edit";
  selectedCohortId: string;
  studentId: string;
  mentorId: string;
  flags: AssignmentFlags;
  memberOptions: {
    students: MemberOption[];
    mentors: MemberOption[];
  };
  memberOptionsLoading: boolean;
  memberOptionsError: string | null;
  formError: string | null;
  isSubmitting: boolean;
  factsLocked: boolean;
  isLockedMode: boolean;
  assignmentToRevoke: MentorAssignment | null;
  isRevoking: boolean;
  toastMessage: string | null;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: AssignmentStatusFilter) => void;
  onCohortFilterChange: (value: string) => void;
  onCreateAssignment: () => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onEditAssignment: (assignment: MentorAssignment) => void;
  onRestoreAssignment: (assignment: MentorAssignment) => void;
  onRequestRevoke: (assignment: MentorAssignment) => void;
  onCloseModal: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onSelectedCohortChange: (value: string) => void;
  onStudentIdChange: (value: string) => void;
  onMentorIdChange: (value: string) => void;
  onMessagesToggle: (checked: boolean) => void;
  onFactsToggle: (checked: boolean) => void;
  onCommentToggle: (checked: boolean) => void;
  onCloseRevoke: () => void;
  onConfirmRevoke: () => void;
};

function MentorAssignmentsToolbar({
  messages,
  intlLocale,
  total,
  query,
  statusFilter,
  statusFilterOptions,
  cohortFilter,
  cohortOptions,
  onQueryChange,
  onStatusFilterChange,
  onCohortFilterChange,
  onCreateAssignment,
}: Pick<
  MentorAssignmentsSurfaceProps,
  | "messages"
  | "intlLocale"
  | "total"
  | "query"
  | "statusFilter"
  | "statusFilterOptions"
  | "cohortFilter"
  | "cohortOptions"
  | "onQueryChange"
  | "onStatusFilterChange"
  | "onCohortFilterChange"
  | "onCreateAssignment"
>) {
  return (
    <CardHeader className="admin-assignments__toolbar">
      <div className="admin-assignments__toolbar-left">
        <div className="admin-assignments__search">
          <input
            type="search"
            className="input input--sm"
            placeholder={messages.filters.searchPlaceholder}
            value={query}
            aria-label={messages.filters.searchAriaLabel}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
        <div className="admin-assignments__status-filter">
          <select
            className="input input--sm"
            value={statusFilter}
            aria-label={messages.filters.statusFilterAriaLabel}
            onChange={(event) =>
              onStatusFilterChange(event.target.value as AssignmentStatusFilter)
            }
          >
            {statusFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="admin-assignments__cohort-filter">
          <select
            className="input input--sm"
            value={cohortFilter}
            aria-label={messages.filters.cohortFilterAriaLabel}
            onChange={(event) => onCohortFilterChange(event.target.value)}
          >
            <option value="">{messages.filters.allCohorts}</option>
            {cohortOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="admin-assignments__toolbar-right">
        <span className="admin-assignments__count-badge">
          {interpolateMentorAssignmentMessage(messages.filters.countBadge, {
            count: total.toLocaleString(intlLocale),
          })}
        </span>
        <Button type="button" size="sm" onClick={onCreateAssignment}>
          {messages.filters.createAssignment}
        </Button>
      </div>
    </CardHeader>
  );
}

function AssignmentIdentity({
  name,
  email,
}: {
  name: string;
  email: string | null | undefined;
}) {
  return (
    <div className="admin-member__identity">
      <div className="admin-member__avatar">
        {resolveMentorAssignmentInitials(name)}
      </div>
      <div className="stack-sm">
        <span className="admin-member__name">{name}</span>
        {email ? <span className="admin-member__email">{email}</span> : null}
      </div>
    </div>
  );
}

function AssignmentSkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, index) => (
        <tr key={`skeleton-${index}`}>
          <td>
            <div className="admin-member__identity">
              <div
                className="skeleton"
                style={{ width: 36, height: 36, borderRadius: 999 }}
              />
              <div className="stack-sm">
                <div className="skeleton" style={{ width: 140 }} />
                <div className="skeleton" style={{ width: 110 }} />
              </div>
            </div>
          </td>
          <td>
            <div className="admin-member__identity">
              <div
                className="skeleton"
                style={{ width: 36, height: 36, borderRadius: 999 }}
              />
              <div className="stack-sm">
                <div className="skeleton" style={{ width: 140 }} />
                <div className="skeleton" style={{ width: 110 }} />
              </div>
            </div>
          </td>
          <td className="admin-assignments__col--cohort">
            <div className="skeleton" style={{ width: 140 }} />
          </td>
          <td>
            <div className="skeleton" style={{ width: 90 }} />
          </td>
          <td className="admin-assignments__col--permissions">
            <div className="skeleton" style={{ width: 110 }} />
          </td>
          <td>
            <div className="skeleton" style={{ width: 80 }} />
          </td>
        </tr>
      ))}
    </>
  );
}

function AssignmentPermissions({
  assignment,
  messages,
}: {
  assignment: MentorAssignment;
  messages: AdminMentorAssignmentsMessages;
}) {
  const permissions = [
    {
      active: assignment.can_view_messages,
      label: messages.permissions.viewMessages,
      text: "M",
    },
    {
      active: assignment.can_view_facts,
      label: messages.permissions.viewFacts,
      text: "F",
    },
    {
      active: assignment.can_comment,
      label: messages.permissions.comment,
      text: "C",
    },
  ];

  return (
    <div className="admin-assignment__permissions">
      {permissions.map((permission) => (
        <span
          key={permission.text}
          className={[
            "admin-assignment__permission",
            permission.active
              ? "admin-assignment__permission--active"
              : "admin-assignment__permission--inactive",
          ]
            .filter(Boolean)
            .join(" ")}
          title={permission.label}
          aria-label={permission.label}
        >
          {permission.text}
        </span>
      ))}
    </div>
  );
}

function AssignmentRow({
  assignment,
  messages,
  onEditAssignment,
  onRestoreAssignment,
  onRequestRevoke,
}: {
  assignment: MentorAssignment;
  messages: AdminMentorAssignmentsMessages;
  onEditAssignment: (assignment: MentorAssignment) => void;
  onRestoreAssignment: (assignment: MentorAssignment) => void;
  onRequestRevoke: (assignment: MentorAssignment) => void;
}) {
  const studentName =
    assignment.student?.display_name ||
    assignment.student?.email ||
    messages.table.unknownStudent;
  const mentorName =
    assignment.mentor?.display_name ||
    assignment.mentor?.email ||
    messages.table.unknownMentor;
  const statusLabel = messages.statuses[assignment.status];
  const statusVariant = ASSIGNMENT_STATUS_VARIANTS[assignment.status];

  return (
    <tr
      className="admin-assignments__row--clickable"
      role="button"
      tabIndex={0}
      aria-label={interpolateMentorAssignmentMessage(messages.table.editAriaLabel, {
        student: studentName,
        mentor: mentorName,
      })}
      onClick={() => onEditAssignment(assignment)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onEditAssignment(assignment);
        }
      }}
    >
      <td>
        <AssignmentIdentity
          name={studentName}
          email={assignment.student?.email}
        />
      </td>
      <td>
        <AssignmentIdentity name={mentorName} email={assignment.mentor?.email} />
      </td>
      <td className="admin-assignments__col--cohort">
        <span className="admin-member__muted">
          {assignment.cohort?.name || messages.table.global}
        </span>
      </td>
      <td>
        <Badge variant={statusVariant}>{statusLabel}</Badge>
      </td>
      <td className="admin-assignments__col--permissions">
        <AssignmentPermissions assignment={assignment} messages={messages} />
      </td>
      <td>
        <div className="admin-assignment__actions">
          {assignment.status === "revoked" ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={(event) => {
                event.stopPropagation();
                onRestoreAssignment(assignment);
              }}
            >
              {messages.table.restore}
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="admin-assignment__revoke"
              onClick={(event) => {
                event.stopPropagation();
                onRequestRevoke(assignment);
              }}
            >
              {messages.table.revoke}
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

function MentorAssignmentsTablePanel({
  messages,
  assignments,
  isLoading,
  loadError,
  cohortError,
  actionError,
  onEditAssignment,
  onRestoreAssignment,
  onRequestRevoke,
}: Pick<
  MentorAssignmentsSurfaceProps,
  | "messages"
  | "assignments"
  | "isLoading"
  | "loadError"
  | "cohortError"
  | "actionError"
  | "onEditAssignment"
  | "onRestoreAssignment"
  | "onRequestRevoke"
>) {
  return (
    <CardContent className="admin-assignments__content stack">
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
      {actionError ? (
        <div className="alert" role="alert">
          <span>{actionError}</span>
        </div>
      ) : null}

      <div className="admin-assignments__table">
        <table className="admin-assignments-table">
          <thead>
            <tr>
              <th scope="col">{messages.table.student}</th>
              <th scope="col">{messages.table.mentor}</th>
              <th scope="col" className="admin-assignments__col--cohort">
                {messages.table.cohort}
              </th>
              <th scope="col">{messages.table.status}</th>
              <th scope="col" className="admin-assignments__col--permissions">
                {messages.table.permissions}
              </th>
              <th scope="col">{messages.table.actions}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && assignments.length === 0 ? (
              <AssignmentSkeletonRows />
            ) : (
              assignments.map((assignment) => (
                <AssignmentRow
                  key={assignment.id}
                  assignment={assignment}
                  messages={messages}
                  onEditAssignment={onEditAssignment}
                  onRestoreAssignment={onRestoreAssignment}
                  onRequestRevoke={onRequestRevoke}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {!isLoading && assignments.length === 0 ? (
        <div className="admin-assignments__empty">{messages.table.empty}</div>
      ) : null}
    </CardContent>
  );
}

function MentorAssignmentsPagination({
  messages,
  intlLocale,
  pageStart,
  pageEnd,
  total,
  page,
  totalPages,
  canGoBack,
  canGoForward,
  onPreviousPage,
  onNextPage,
}: Pick<
  MentorAssignmentsSurfaceProps,
  | "messages"
  | "intlLocale"
  | "pageStart"
  | "pageEnd"
  | "total"
  | "page"
  | "totalPages"
  | "canGoBack"
  | "canGoForward"
  | "onPreviousPage"
  | "onNextPage"
>) {
  return (
    <CardFooter className="admin-assignments__footer">
      <span className="text-muted">
        {interpolateMentorAssignmentMessage(messages.pagination.showing, {
          start: pageStart,
          end: pageEnd,
          total: total.toLocaleString(intlLocale),
        })}
      </span>
      <div className="admin-assignments__pagination">
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
          {interpolateMentorAssignmentMessage(messages.pagination.page, {
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

export function MentorAssignmentsSurface({
  messages,
  intlLocale,
  assignments,
  total,
  query,
  statusFilter,
  statusFilterOptions,
  cohortFilter,
  cohortOptions,
  isLoading,
  loadError,
  cohortError,
  actionError,
  pageStart,
  pageEnd,
  page,
  totalPages,
  canGoBack,
  canGoForward,
  isModalOpen,
  modalMode,
  selectedCohortId,
  studentId,
  mentorId,
  flags,
  memberOptions,
  memberOptionsLoading,
  memberOptionsError,
  formError,
  isSubmitting,
  factsLocked,
  isLockedMode,
  assignmentToRevoke,
  isRevoking,
  toastMessage,
  onQueryChange,
  onStatusFilterChange,
  onCohortFilterChange,
  onCreateAssignment,
  onPreviousPage,
  onNextPage,
  onEditAssignment,
  onRestoreAssignment,
  onRequestRevoke,
  onCloseModal,
  onSubmit,
  onSelectedCohortChange,
  onStudentIdChange,
  onMentorIdChange,
  onMessagesToggle,
  onFactsToggle,
  onCommentToggle,
  onCloseRevoke,
  onConfirmRevoke,
}: MentorAssignmentsSurfaceProps) {
  return (
    <>
      <Card className="admin-assignments">
        <MentorAssignmentsToolbar
          messages={messages}
          intlLocale={intlLocale}
          total={total}
          query={query}
          statusFilter={statusFilter}
          statusFilterOptions={statusFilterOptions}
          cohortFilter={cohortFilter}
          cohortOptions={cohortOptions}
          onQueryChange={onQueryChange}
          onStatusFilterChange={onStatusFilterChange}
          onCohortFilterChange={onCohortFilterChange}
          onCreateAssignment={onCreateAssignment}
        />
        <MentorAssignmentsTablePanel
          messages={messages}
          assignments={assignments}
          isLoading={isLoading}
          loadError={loadError}
          cohortError={cohortError}
          actionError={actionError}
          onEditAssignment={onEditAssignment}
          onRestoreAssignment={onRestoreAssignment}
          onRequestRevoke={onRequestRevoke}
        />
        <MentorAssignmentsPagination
          messages={messages}
          intlLocale={intlLocale}
          pageStart={pageStart}
          pageEnd={pageEnd}
          total={total}
          page={page}
          totalPages={totalPages}
          canGoBack={canGoBack}
          canGoForward={canGoForward}
          onPreviousPage={onPreviousPage}
          onNextPage={onNextPage}
        />
      </Card>

      {isModalOpen ? (
        <AssignmentFormModal
          messages={messages}
          modalMode={modalMode}
          isSubmitting={isSubmitting}
          selectedCohortId={selectedCohortId}
          cohortOptions={cohortOptions}
          studentId={studentId}
          mentorId={mentorId}
          flags={flags}
          memberOptions={memberOptions}
          memberOptionsLoading={memberOptionsLoading}
          memberOptionsError={memberOptionsError}
          formError={formError}
          factsLocked={factsLocked}
          isLockedMode={isLockedMode}
          onCloseModal={onCloseModal}
          onSubmit={onSubmit}
          onSelectedCohortChange={onSelectedCohortChange}
          onStudentIdChange={onStudentIdChange}
          onMentorIdChange={onMentorIdChange}
          onMessagesToggle={onMessagesToggle}
          onFactsToggle={onFactsToggle}
          onCommentToggle={onCommentToggle}
        />
      ) : null}

      {assignmentToRevoke ? (
        <RevokeAssignmentModal
          messages={messages}
          isRevoking={isRevoking}
          onCloseRevoke={onCloseRevoke}
          onConfirmRevoke={onConfirmRevoke}
        />
      ) : null}

      <AssignmentToast message={toastMessage} />
    </>
  );
}
