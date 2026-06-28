import type { FormEvent } from "react";
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
import type { AdminCohortsMessages } from "@/features/admin/admin-cohorts-view-model";

type CreateCohortModalProps = {
  descriptionInput: string;
  endAtInput: string;
  formError: string | null;
  isOpen: boolean;
  isSubmitting: boolean;
  messages: AdminCohortsMessages;
  nameInput: string;
  onClose: () => void;
  onDescriptionChange: (value: string) => void;
  onEndAtChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onStartAtChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  startAtInput: string;
  submitError: string | null;
};

export function CreateCohortModal({
  descriptionInput,
  endAtInput,
  formError,
  isOpen,
  isSubmitting,
  messages,
  nameInput,
  onClose,
  onDescriptionChange,
  onEndAtChange,
  onNameChange,
  onStartAtChange,
  onSubmit,
  startAtInput,
  submitError,
}: CreateCohortModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <AdminModal
      labelledBy="create-cohort-title"
      closeDisabled={isSubmitting}
      onClose={onClose}
    >
      <Card>
        <CardHeader className="stack-sm">
          <CardTitle id="create-cohort-title">
            {messages.createModal.title}
          </CardTitle>
          <CardDescription>{messages.createModal.description}</CardDescription>
        </CardHeader>
        <form className="stack" onSubmit={onSubmit}>
          <CardContent className="stack">
            <div className="field">
              <label className="field__label" htmlFor="cohort-name">
                {messages.createModal.nameLabel}
              </label>
              <input
                id="cohort-name"
                className="input"
                value={nameInput}
                onChange={(event) => onNameChange(event.target.value)}
                placeholder={messages.createModal.namePlaceholder}
                autoFocus
              />
              {formError ? (
                <span className="field__error">{formError}</span>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cohort-description">
                {messages.createModal.descriptionLabel}
              </label>
              <textarea
                id="cohort-description"
                className="textarea"
                rows={3}
                value={descriptionInput}
                onChange={(event) => onDescriptionChange(event.target.value)}
                placeholder={messages.createModal.descriptionPlaceholder}
              />
            </div>
            <div className="admin-cohort__dates">
              <div className="field">
                <label className="field__label" htmlFor="cohort-start">
                  {messages.createModal.startDateLabel}
                </label>
                <input
                  id="cohort-start"
                  type="date"
                  className="input"
                  value={startAtInput}
                  onChange={(event) => onStartAtChange(event.target.value)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="cohort-end">
                  {messages.createModal.endDateLabel}
                </label>
                <input
                  id="cohort-end"
                  type="date"
                  className="input"
                  value={endAtInput}
                  onChange={(event) => onEndAtChange(event.target.value)}
                />
              </div>
            </div>
            {submitError ? (
              <div className="alert" role="alert">
                <span>{submitError}</span>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="admin-modal__footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              {messages.createModal.cancel}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? messages.createModal.creating
                : messages.createModal.create}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </AdminModal>
  );
}
