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
import type { useAppMessages } from "@/lib/i18n/provider";

import { interpolate } from "./cohort-detail-surface";
import type { CohortMemberItem, OrgMember } from "./cohort-detail-types";

type CohortDetailMessages = ReturnType<typeof useAppMessages>["adminCohortDetail"];

type SelectedMember = {
  id: string;
  name: string;
  email: string;
};

type RemoveCohortMemberModalProps = {
  messages: CohortDetailMessages;
  memberToRemove: CohortMemberItem;
  isRemoving: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

type AddCohortMembersModalProps = {
  messages: CohortDetailMessages;
  tab: "members" | "mentors";
  memberQuery: string;
  memberLoadError: string | null;
  isMembersLoading: boolean;
  availableMembers: OrgMember[];
  selectedMembers: Record<string, SelectedMember>;
  selection: Record<string, boolean>;
  hasSelection: boolean;
  hasSelectedMembers: boolean;
  memberActionError: string | null;
  isAdding: boolean;
  availablePage: number;
  availableTotalPages: number;
  canGoBackAvailable: boolean;
  canGoForwardAvailable: boolean;
  onClose: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onMemberQueryChange: (value: string) => void;
  onSelectionChange: (userId: string, checked: boolean) => void;
  onAddSelected: () => void;
  onAvailablePreviousPage: () => void;
  onAvailableNextPage: () => void;
  onRemoveSelected: (userId: string) => void;
};

export function RemoveCohortMemberModal({
  messages,
  memberToRemove,
  isRemoving,
  onClose,
  onConfirm,
}: RemoveCohortMemberModalProps) {
  return (
    <AdminModal
      labelledBy="remove-cohort-member-title"
      closeDisabled={isRemoving}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="remove-cohort-member-title">
            {messages.removeModal.title}
          </CardTitle>
          <CardDescription>
            {interpolate(messages.removeModal.description, {
              name:
                memberToRemove.display_name ||
                memberToRemove.email ||
                messages.removeModal.fallbackSubject,
            })}
          </CardDescription>
        </CardHeader>
        <CardFooter className="admin-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isRemoving}
          >
            {messages.removeModal.cancel}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={isRemoving}>
            {isRemoving
              ? messages.removeModal.removing
              : messages.removeModal.confirm}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}

export function AddCohortMembersModal({
  messages,
  tab,
  memberQuery,
  memberLoadError,
  isMembersLoading,
  availableMembers,
  selectedMembers,
  selection,
  hasSelection,
  hasSelectedMembers,
  memberActionError,
  isAdding,
  availablePage,
  availableTotalPages,
  canGoBackAvailable,
  canGoForwardAvailable,
  onClose,
  onSubmit,
  onMemberQueryChange,
  onSelectionChange,
  onAddSelected,
  onAvailablePreviousPage,
  onAvailableNextPage,
  onRemoveSelected,
}: AddCohortMembersModalProps) {
  return (
    <AdminModal
      labelledBy="add-cohort-members-title"
      panelClassName="admin-modal__panel--wide"
      closeDisabled={isAdding}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="add-cohort-members-title">
            {tab === "members"
              ? messages.addModal.titleStudents
              : messages.addModal.titleMentors}
          </CardTitle>
          <CardDescription>{messages.addModal.description}</CardDescription>
        </CardHeader>
        <form className="stack" onSubmit={onSubmit}>
          <CardContent className="stack">
            <div className="admin-transfer">
              <div className="admin-transfer__panel">
                <div className="admin-transfer__header">
                  {messages.addModal.availableMembers}
                </div>
                <input
                  type="search"
                  className="input input--sm"
                  placeholder={messages.addModal.searchPlaceholder}
                  value={memberQuery}
                  aria-label={messages.addModal.searchAriaLabel}
                  onChange={(event) => onMemberQueryChange(event.target.value)}
                />
                {memberLoadError ? (
                  <div className="alert" role="alert">
                    <span>{memberLoadError}</span>
                  </div>
                ) : null}
                <div className="admin-transfer__list">
                  {isMembersLoading ? (
                    <div className="admin-transfer__empty">
                      {messages.addModal.loading}
                    </div>
                  ) : availableMembers.length === 0 ? (
                    <div className="admin-transfer__empty">
                      {messages.addModal.noMembersFound}
                    </div>
                  ) : (
                    availableMembers.map((member) => {
                      const userId = member.user?.id;
                      if (!userId) {
                        return null;
                      }
                      const displayName =
                        member.user?.display_name ||
                        member.user?.email ||
                        messages.addModal.unknownMember;
                      const email = member.user?.email || messages.addModal.noEmail;
                      const isSelected = Boolean(selectedMembers[userId]);
                      return (
                        <label
                          key={userId}
                          className={[
                            "admin-transfer__item",
                            isSelected ? "admin-transfer__item--selected" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        >
                          <input
                            type="checkbox"
                            checked={Boolean(selection[userId])}
                            onChange={(event) =>
                              onSelectionChange(userId, event.target.checked)
                            }
                            disabled={isSelected}
                          />
                          <div className="admin-transfer__meta">
                            <span className="admin-transfer__name">
                              {displayName}
                            </span>
                            <span className="admin-transfer__email">{email}</span>
                          </div>
                          {isSelected ? (
                            <span className="admin-transfer__tag">
                              {messages.addModal.addedTag}
                            </span>
                          ) : null}
                        </label>
                      );
                    })
                  )}
                </div>
                <div className="admin-transfer__footer">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={onAddSelected}
                    disabled={isMembersLoading || !hasSelection}
                  >
                    {messages.addModal.addSelected}
                  </Button>
                  <div className="admin-transfer__pagination">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={onAvailablePreviousPage}
                      disabled={!canGoBackAvailable}
                    >
                      {messages.addModal.previous}
                    </Button>
                    <span className="text-muted">
                      {interpolate(messages.addModal.availablePage, {
                        current: availablePage,
                        total: availableTotalPages,
                      })}
                    </span>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={onAvailableNextPage}
                      disabled={!canGoForwardAvailable}
                    >
                      {messages.addModal.next}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="admin-transfer__panel admin-transfer__panel--selected">
                <div className="admin-transfer__header">
                  {messages.addModal.selected}
                </div>
                <div className="admin-transfer__list">
                  {Object.keys(selectedMembers).length === 0 ? (
                    <div className="admin-transfer__empty">
                      {messages.addModal.noneSelected}
                    </div>
                  ) : (
                    Object.values(selectedMembers).map((member) => (
                      <div key={member.id} className="admin-transfer__item">
                        <div className="admin-transfer__meta">
                          <span className="admin-transfer__name">
                            {member.name}
                          </span>
                          <span className="admin-transfer__email">
                            {member.email}
                          </span>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="admin-transfer__remove"
                          onKeyDown={(event) => event.stopPropagation()}
                          onClick={() => onRemoveSelected(member.id)}
                        >
                          {messages.addModal.remove}
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
            {memberActionError ? (
              <div className="alert" role="alert">
                <span>{memberActionError}</span>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="admin-modal__footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isAdding}
            >
              {messages.addModal.cancel}
            </Button>
            <Button type="submit" disabled={isAdding || !hasSelectedMembers}>
              {isAdding ? messages.addModal.adding : messages.addModal.confirm}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </AdminModal>
  );
}
