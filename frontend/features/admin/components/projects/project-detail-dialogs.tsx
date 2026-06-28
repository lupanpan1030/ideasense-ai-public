import type { FormEventHandler } from "react";

import { AdminModal } from "@/features/admin/components/shared/admin-modal";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { useAppMessages } from "@/lib/i18n/provider";

import type { Stage, StageStatus } from "./project-detail-types";

type AdminProjectDetailMessages = ReturnType<
  typeof useAppMessages
>["adminProjectDetail"];

type ProjectDetailOption<T extends string> = {
  value: T;
  label: string;
};

type ProjectEditDraft = {
  title: string;
  description: string;
  current_stage: Stage;
  stage_status: StageStatus;
};

type EditProjectModalProps = {
  messages: AdminProjectDetailMessages;
  editDraft: ProjectEditDraft;
  stageOptions: Array<ProjectDetailOption<Stage>>;
  statusOptions: Array<ProjectDetailOption<StageStatus>>;
  editError: string | null;
  isSaving: boolean;
  onClose: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onDraftChange: (draft: ProjectEditDraft) => void;
};

type DeleteProjectCommentModalProps = {
  messages: AdminProjectDetailMessages;
  isDeletingComment: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function EditProjectModal({
  messages,
  editDraft,
  stageOptions,
  statusOptions,
  editError,
  isSaving,
  onClose,
  onSubmit,
  onDraftChange,
}: EditProjectModalProps) {
  return (
    <AdminModal
      labelledBy="edit-project-title"
      closeDisabled={isSaving}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="edit-project-title">
            {messages.editModal.title}
          </CardTitle>
          <CardDescription>{messages.editModal.description}</CardDescription>
        </CardHeader>
        <form className="stack" onSubmit={onSubmit}>
          <CardContent className="stack">
            <div className="field">
              <label className="field__label" htmlFor="project-title">
                {messages.editModal.titleLabel}
              </label>
              <input
                id="project-title"
                className="input"
                value={editDraft.title}
                onChange={(event) =>
                  onDraftChange({
                    ...editDraft,
                    title: event.target.value,
                  })
                }
                required
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="project-description">
                {messages.editModal.descriptionLabel}
              </label>
              <textarea
                id="project-description"
                className="textarea"
                rows={4}
                value={editDraft.description}
                onChange={(event) =>
                  onDraftChange({
                    ...editDraft,
                    description: event.target.value,
                  })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="project-stage">
                {messages.editModal.stageLabel}
              </label>
              <select
                id="project-stage"
                className="input"
                value={editDraft.current_stage}
                onChange={(event) =>
                  onDraftChange({
                    ...editDraft,
                    current_stage: event.target.value as Stage,
                  })
                }
              >
                {stageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="project-status">
                {messages.editModal.statusLabel}
              </label>
              <select
                id="project-status"
                className="input"
                value={editDraft.stage_status}
                onChange={(event) =>
                  onDraftChange({
                    ...editDraft,
                    stage_status: event.target.value as StageStatus,
                  })
                }
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            {editError ? (
              <div className="alert" role="alert">
                <span>{editError}</span>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="admin-modal__footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              {messages.editModal.cancel}
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving
                ? messages.editModal.saving
                : messages.editModal.saveChanges}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </AdminModal>
  );
}

export function DeleteProjectCommentModal({
  messages,
  isDeletingComment,
  onClose,
  onConfirm,
}: DeleteProjectCommentModalProps) {
  return (
    <AdminModal
      labelledBy="delete-comment-title"
      closeDisabled={isDeletingComment}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="delete-comment-title">
            {messages.deleteCommentModal.title}
          </CardTitle>
          <CardDescription>
            {messages.deleteCommentModal.description}
          </CardDescription>
        </CardHeader>
        <CardFooter className="admin-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isDeletingComment}
          >
            {messages.deleteCommentModal.cancel}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={isDeletingComment}>
            {isDeletingComment
              ? messages.deleteCommentModal.deleting
              : messages.deleteCommentModal.confirm}
          </Button>
        </CardFooter>
      </Card>
    </AdminModal>
  );
}
