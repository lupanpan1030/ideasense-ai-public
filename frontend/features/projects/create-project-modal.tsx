"use client";

import { useEffect, useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { useModalFocusTrap } from "@/components/ui/modal-focus";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  createProject,
  getProjectCreateErrorMessage,
  type ProjectCreateResult,
} from "@/features/projects/projects";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type CreateProjectModalProps = {
  onClose: () => void;
  onCreate: (result: ProjectCreateResult) => void;
};

export function CreateProjectModal({
  onClose,
  onCreate,
}: CreateProjectModalProps) {
  const locale = useAppLocale();
  const messages = useAppMessages().projectsWorkspace;
  const createModalMessages = messages.createModal;
  const commonMessages = messages.common;
  const titleId = useId();
  const descriptionId = useId();
  const dialogId = useId();
  const handleModalKeyDown = useModalFocusTrap(dialogId);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (!isSubmitting) {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isSubmitting, onClose]);

  const handleClose = () => {
    if (isSubmitting) {
      return;
    }
    onClose();
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setFieldError(createModalMessages.fieldRequired);
      setSubmitError(null);
      return;
    }

    setFieldError(null);
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const result = await createProject({
        title: trimmedTitle,
        description,
        outputLocale: locale,
      });
      onCreate(result);
    } catch (err) {
      setSubmitError(getProjectCreateErrorMessage(err));
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
        onKeyDown={handleModalKeyDown}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <CardTitle id={titleId}>{createModalMessages.title}</CardTitle>
            <CardDescription id={descriptionId}>
              {createModalMessages.description}
            </CardDescription>
          </div>
        </CardHeader>
        <Separator />
        <form className="stack" onSubmit={handleSubmit}>
          <CardContent className="modal-body">
            <Input
              id="project-title"
              label={createModalMessages.titleLabel}
              placeholder={createModalMessages.titlePlaceholder}
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
            <div className="field">
              <label className="field__label" htmlFor="project-description">
                {createModalMessages.descriptionLabel}
              </label>
              <textarea
                id="project-description"
                className="textarea"
                rows={4}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder={createModalMessages.descriptionPlaceholder}
                disabled={isSubmitting}
              />
              <p className="field__hint">
                {createModalMessages.descriptionHint}
              </p>
            </div>
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
              {isSubmitting
                ? createModalMessages.submitBusy
                : createModalMessages.submitIdle}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
