import type { FormEventHandler } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AdminModal } from "@/features/admin/components/shared/admin-modal";
import type {
  AdminMentorAssignmentsMessages,
  AssignmentFlags,
  CohortOption,
  MemberOption,
} from "@/features/admin/admin-mentor-assignments-view-model";

type AssignmentFormModalProps = {
  messages: AdminMentorAssignmentsMessages;
  modalMode: "create" | "restore" | "edit";
  isSubmitting: boolean;
  selectedCohortId: string;
  cohortOptions: CohortOption[];
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
  factsLocked: boolean;
  isLockedMode: boolean;
  onCloseModal: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onSelectedCohortChange: (value: string) => void;
  onStudentIdChange: (value: string) => void;
  onMentorIdChange: (value: string) => void;
  onMessagesToggle: (checked: boolean) => void;
  onFactsToggle: (checked: boolean) => void;
  onCommentToggle: (checked: boolean) => void;
};

type RevokeAssignmentModalProps = {
  messages: AdminMentorAssignmentsMessages;
  isRevoking: boolean;
  onCloseRevoke: () => void;
  onConfirmRevoke: () => void;
};

function PermissionToggle({
  label,
  hint,
  ariaLabel,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  ariaLabel: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="admin-toggle">
      <div className="admin-toggle__text">
        <span className="admin-toggle__label">{label}</span>
        <span className="admin-toggle__hint">{hint}</span>
      </div>
      <label className="admin-switch">
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          disabled={disabled}
          aria-label={ariaLabel}
        />
        <span className="admin-switch__track">
          <span className="admin-switch__thumb" />
        </span>
      </label>
    </div>
  );
}

export function AssignmentFormModal({
  messages,
  modalMode,
  isSubmitting,
  selectedCohortId,
  cohortOptions,
  studentId,
  mentorId,
  flags,
  memberOptions,
  memberOptionsLoading,
  memberOptionsError,
  formError,
  factsLocked,
  isLockedMode,
  onCloseModal,
  onSubmit,
  onSelectedCohortChange,
  onStudentIdChange,
  onMentorIdChange,
  onMessagesToggle,
  onFactsToggle,
  onCommentToggle,
}: AssignmentFormModalProps) {
  return (
    <AdminModal
      labelledBy="assignment-modal-title"
      closeDisabled={isSubmitting}
      onClose={onCloseModal}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="assignment-modal-title">
            {modalMode === "restore"
              ? messages.modal.titles.restore
              : modalMode === "edit"
                ? messages.modal.titles.edit
                : messages.modal.titles.create}
          </CardTitle>
          <CardDescription>
            {modalMode === "restore"
              ? messages.modal.descriptions.restore
              : modalMode === "edit"
                ? messages.modal.descriptions.edit
                : messages.modal.descriptions.create}
          </CardDescription>
        </CardHeader>
        <form className="stack" onSubmit={onSubmit}>
          <CardContent className="stack">
            <div className="field">
              <label className="field__label" htmlFor="assignment-cohort">
                {messages.modal.cohortLabel}
              </label>
              <select
                id="assignment-cohort"
                className="input"
                value={selectedCohortId}
                onChange={(event) => onSelectedCohortChange(event.target.value)}
                disabled={isSubmitting || isLockedMode}
              >
                <option value="">{messages.modal.noCohort}</option>
                {cohortOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span className="field__hint">{messages.modal.cohortHint}</span>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="assignment-student">
                {messages.modal.studentLabel}
              </label>
              <select
                id="assignment-student"
                className="input"
                value={studentId}
                onChange={(event) => onStudentIdChange(event.target.value)}
                disabled={isSubmitting || isLockedMode || memberOptionsLoading}
                required
              >
                <option value="" disabled>
                  {memberOptionsLoading
                    ? messages.modal.loadingStudents
                    : messages.modal.selectStudent}
                </option>
                {memberOptions.students.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="assignment-mentor">
                {messages.modal.mentorLabel}
              </label>
              <select
                id="assignment-mentor"
                className="input"
                value={mentorId}
                onChange={(event) => onMentorIdChange(event.target.value)}
                disabled={isSubmitting || isLockedMode || memberOptionsLoading}
                required
              >
                <option value="" disabled>
                  {memberOptionsLoading
                    ? messages.modal.loadingMentors
                    : messages.modal.selectMentor}
                </option>
                {memberOptions.mentors.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {memberOptionsError ? (
              <div className="alert" role="alert">
                <span>{memberOptionsError}</span>
              </div>
            ) : null}

            <div className="admin-toggle-list">
              <PermissionToggle
                label={messages.modal.toggles.viewMessagesLabel}
                hint={messages.modal.toggles.viewMessagesHint}
                ariaLabel={messages.modal.toggles.viewMessagesAria}
                checked={flags.can_view_messages}
                disabled={isSubmitting}
                onChange={onMessagesToggle}
              />
              <PermissionToggle
                label={messages.modal.toggles.viewFactsLabel}
                hint={messages.modal.toggles.viewFactsHint}
                ariaLabel={messages.modal.toggles.viewFactsAria}
                checked={flags.can_view_facts}
                disabled={isSubmitting || factsLocked}
                onChange={onFactsToggle}
              />
              <PermissionToggle
                label={messages.modal.toggles.commentLabel}
                hint={messages.modal.toggles.commentHint}
                ariaLabel={messages.modal.toggles.commentAria}
                checked={flags.can_comment}
                disabled={isSubmitting}
                onChange={onCommentToggle}
              />
            </div>

            {formError ? (
              <div className="alert" role="alert">
                <span>{formError}</span>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="admin-modal__footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onCloseModal}
              disabled={isSubmitting}
            >
              {messages.modal.cancel}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? messages.modal.saving
                : modalMode === "restore"
                  ? messages.modal.restore
                  : modalMode === "edit"
                    ? messages.modal.saveChanges
                    : messages.modal.create}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </AdminModal>
  );
}

export function RevokeAssignmentModal({
  messages,
  isRevoking,
  onCloseRevoke,
  onConfirmRevoke,
}: RevokeAssignmentModalProps) {
  return (
    <AdminModal
      labelledBy="revoke-assignment-title"
      closeDisabled={isRevoking}
      onClose={onCloseRevoke}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="revoke-assignment-title">
            {messages.revokeModal.title}
          </CardTitle>
          <CardDescription>{messages.revokeModal.description}</CardDescription>
        </CardHeader>
        <CardFooter className="admin-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onCloseRevoke}
            disabled={isRevoking}
          >
            {messages.revokeModal.cancel}
          </Button>
          <Button type="button" onClick={onConfirmRevoke} disabled={isRevoking}>
            {isRevoking
              ? messages.revokeModal.revoking
              : messages.revokeModal.confirm}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}

export function AssignmentToast({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }

  return (
    <div className="admin-toast" role="status" aria-live="polite">
      <span className="admin-toast__title">{message}</span>
    </div>
  );
}
