import { type FormEvent, type KeyboardEvent as ReactKeyboardEvent, useEffect, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useModalFocusTrap } from "@/components/ui/modal-focus";
import { Separator } from "@/components/ui/separator";
import {
  getProjectDeleteErrorMessage,
  getProjectUpdateErrorMessage,
  type ProjectSummary,
} from "@/features/projects/projects";
import { useAppMessages } from "@/lib/i18n/provider";

type RenameProjectModalProps = {
  project: ProjectSummary;
  onClose: () => void;
  onSubmit: (projectId: string, title: string) => Promise<void>;
};

export function RenameProjectModal({
  project,
  onClose,
  onSubmit,
}: RenameProjectModalProps) {
  const messages = useAppMessages().projectsWorkspace;
  const commonMessages = messages.common;
  const renameMessages = messages.renameModal;
  const titleId = useId();
  const descriptionId = useId();
  const dialogId = useId();
  const handleModalFocusKeyDown = useModalFocusTrap(dialogId);
  const [title, setTitle] = useState(project.title);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const handleClose = () => {
    if (isSubmitting) {
      return;
    }
    onClose();
  };

  const handleDialogKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      if (!isSubmitting) {
        event.preventDefault();
        onClose();
      }
      return;
    }
    handleModalFocusKeyDown(event);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setFieldError(renameMessages.fieldRequired);
      setSubmitError(null);
      return;
    }

    setFieldError(null);
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      await onSubmit(project.id, trimmedTitle);
      onClose();
    } catch (error) {
      setSubmitError(getProjectUpdateErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" role="presentation" onClick={handleClose}>
      <Card
        id={dialogId}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleDialogKeyDown}
        tabIndex={-1}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <CardTitle id={titleId}>{renameMessages.title}</CardTitle>
            <CardDescription id={descriptionId}>
              {renameMessages.description}
            </CardDescription>
          </div>
        </CardHeader>
        <Separator />
        <form className="stack" onSubmit={handleSubmit}>
          <CardContent className="modal-body">
            <Input
              id="rename-project-title"
              label={renameMessages.titleLabel}
              placeholder={renameMessages.titlePlaceholder}
              value={title}
              maxLength={255}
              onChange={(event) => {
                setTitle(event.target.value);
                if (fieldError) {
                  setFieldError(null);
                }
              }}
              error={fieldError ?? undefined}
              required
              autoFocus
              disabled={isSubmitting}
            />
            {submitError ? (
              <div className="alert" role="alert">
                <span>{submitError}</span>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="modal-footer">
            <Button
              type="button"
              variant="secondary"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              {commonMessages.cancel}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? renameMessages.submitBusy : renameMessages.submitIdle}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

type DeleteProjectModalProps = {
  project: ProjectSummary;
  onClose: () => void;
  onConfirm: (projectId: string) => Promise<void>;
};

export function DeleteProjectModal({
  project,
  onClose,
  onConfirm,
}: DeleteProjectModalProps) {
  const messages = useAppMessages().projectsWorkspace;
  const commonMessages = messages.common;
  const deleteMessages = messages.deleteModal;
  const titleId = useId();
  const descriptionId = useId();
  const dialogId = useId();
  const handleModalFocusKeyDown = useModalFocusTrap(dialogId);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const handleClose = () => {
    if (isSubmitting) {
      return;
    }
    onClose();
  };

  const handleDialogKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      if (!isSubmitting) {
        event.preventDefault();
        onClose();
      }
      return;
    }
    handleModalFocusKeyDown(event);
  };

  const handleConfirm = async () => {
    if (isSubmitting) {
      return;
    }
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await onConfirm(project.id);
      onClose();
    } catch (error) {
      setSubmitError(getProjectDeleteErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" role="presentation" onClick={handleClose}>
      <Card
        id={dialogId}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleDialogKeyDown}
        tabIndex={-1}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <CardTitle id={titleId}>{deleteMessages.title}</CardTitle>
            <CardDescription id={descriptionId}>
              {deleteMessages.description}
            </CardDescription>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="modal-body">
          <p className="text-muted">
            {deleteMessages.confirmPrefix} <strong>{project.title}</strong>.
          </p>
          {submitError ? (
            <div className="alert" role="alert">
              <span>{submitError}</span>
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="modal-footer">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {commonMessages.cancel}
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={isSubmitting}>
            {isSubmitting ? deleteMessages.submitBusy : deleteMessages.submitIdle}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
