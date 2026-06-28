"use client";

import { useId } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useModalFocusTrap } from "@/components/ui/modal-focus";
import { Separator } from "@/components/ui/separator";

export type PendingConfirmBulkAction = {
  type: "accept" | "reject";
  paths: string[];
  overrides: string[];
};

type PendingConfirmBulkActionModalProps = {
  action: PendingConfirmBulkAction;
  isSubmitting: boolean;
  messages: {
    acceptTitle: string;
    rejectTitle: string;
    acceptDescription: string;
    rejectDescription: string;
    overrideMessage: string;
    itemCount: string;
    overwriteWarningTitle: string;
    irreversibleNote: string;
    cancel: string;
    submitting: string;
    confirm: string;
  };
  onConfirm: () => void;
  onClose: () => void;
};

export function PendingConfirmBulkActionModal({
  action,
  isSubmitting,
  messages,
  onConfirm,
  onClose,
}: PendingConfirmBulkActionModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogId = useId();
  const handleFocusTrapKeyDown = useModalFocusTrap(dialogId);
  const isAccept = action.type === "accept";
  const title = isAccept ? messages.acceptTitle : messages.rejectTitle;
  const description = isAccept
    ? messages.acceptDescription
    : messages.rejectDescription;
  const overrideMessage = action.overrides.length
    ? messages.overrideMessage
    : null;

  const isBrowser = typeof document !== "undefined";

  if (!isBrowser) {
    return null;
  }

  const handleClose = () => {
    if (isSubmitting) {
      return;
    }
    onClose();
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      if (!isSubmitting) {
        event.preventDefault();
        handleClose();
      }
      return;
    }
    handleFocusTrapKeyDown(event);
  };

  return createPortal(
    <div className="modal-overlay" role="presentation" onClick={handleClose}>
      <Card
        id={dialogId}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <CardTitle id={titleId}>{title}</CardTitle>
            <CardDescription id={descriptionId}>{description}</CardDescription>
          </div>
          <Badge variant={isAccept ? "warning" : "danger"}>
            {messages.itemCount.replace("{count}", String(action.paths.length))}
          </Badge>
        </CardHeader>
        <CardContent className="modal-body">
          {overrideMessage ? (
            <Card variant="alert" role="alert">
              <CardHeader className="stack-sm">
                <CardTitle>{messages.overwriteWarningTitle}</CardTitle>
                <CardDescription>{overrideMessage}</CardDescription>
              </CardHeader>
            </Card>
          ) : null}
          <p className="text-muted">{messages.irreversibleNote}</p>
        </CardContent>
        <Separator />
        <CardFooter className="modal-footer">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
            data-modal-action="cancel"
          >
            {messages.cancel}
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            data-modal-action="confirm"
          >
            {isSubmitting ? messages.submitting : messages.confirm}
          </Button>
        </CardFooter>
      </Card>
    </div>,
    document.body
  );
}
