"use client";

import {
  useEffect,
  useId,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { useModalFocusTrap } from "@/components/ui/modal-focus";

type AdminModalProps = {
  labelledBy: string;
  children: ReactNode;
  closeDisabled?: boolean;
  describedBy?: string;
  onClose?: () => void;
  onOverlayClick?: () => void;
  panelClassName?: string;
};

let modalScrollLockCount = 0;
let modalPreviousBodyOverflow: string | null = null;

const acquireBodyScrollLock = () => {
  if (typeof document === "undefined") {
    return () => {};
  }

  if (modalScrollLockCount === 0) {
    modalPreviousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  modalScrollLockCount += 1;

  return () => {
    modalScrollLockCount = Math.max(0, modalScrollLockCount - 1);
    if (modalScrollLockCount === 0) {
      document.body.style.overflow = modalPreviousBodyOverflow ?? "";
      modalPreviousBodyOverflow = null;
    }
  };
};

export function AdminModal({
  labelledBy,
  children,
  closeDisabled = false,
  describedBy,
  onClose,
  onOverlayClick,
  panelClassName,
}: AdminModalProps) {
  const dialogId = useId();
  const handleFocusTrapKeyDown = useModalFocusTrap(dialogId);
  const resolvedPanelClassName = panelClassName
    ? `admin-modal__panel ${panelClassName}`
    : "admin-modal__panel";

  useEffect(() => acquireBodyScrollLock(), []);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      if (!closeDisabled && onClose) {
        event.preventDefault();
        onClose();
      }
      return;
    }
    handleFocusTrapKeyDown(event);
  };

  const handleOverlayClick = () => {
    if (closeDisabled) {
      return;
    }
    if (onOverlayClick) {
      onOverlayClick();
      return;
    }
    onClose?.();
  };

  return (
    <div
      id={dialogId}
      className="admin-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className="admin-modal__overlay" onClick={handleOverlayClick} />
      <div className={resolvedPanelClassName}>{children}</div>
    </div>
  );
}
