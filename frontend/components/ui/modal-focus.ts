"use client";

import { useCallback, useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export const getModalFocusableElements = (dialog: HTMLElement): HTMLElement[] =>
  Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (element) =>
      !element.hasAttribute("disabled") &&
      element.getAttribute("aria-hidden") !== "true"
  );

export function useModalFocusTrap(
  dialogId: string,
  { enabled = true }: { enabled?: boolean } = {}
) {
  const focusReturnRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!enabled || typeof document === "undefined") {
      return;
    }

    const dialog = document.getElementById(dialogId);
    const activeElement = document.activeElement;
    focusReturnRef.current =
      activeElement instanceof HTMLElement ? activeElement : null;
    window.requestAnimationFrame(() => {
      const initialFocus = dialog
        ? getModalFocusableElements(dialog)[0] ?? dialog
        : null;
      initialFocus?.focus();
    });

    return () => {
      const previousFocus = focusReturnRef.current;
      if (previousFocus && document.contains(previousFocus)) {
        previousFocus.focus();
      }
    };
  }, [dialogId, enabled]);

  return useCallback(
    (event: ReactKeyboardEvent<HTMLElement>) => {
      if (!enabled || event.key !== "Tab") {
        return;
      }

      const dialog = document.getElementById(dialogId);
      if (!dialog) {
        return;
      }

      const focusTargets = getModalFocusableElements(dialog);
      if (!focusTargets.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const activeElement = document.activeElement as HTMLElement | null;
      const first = focusTargets[0];
      const last = focusTargets[focusTargets.length - 1];
      const isWithin = activeElement
        ? focusTargets.includes(activeElement)
        : false;

      if (event.shiftKey) {
        if (!isWithin || activeElement === first) {
          event.preventDefault();
          last.focus();
        }
        return;
      }

      if (!isWithin || activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    },
    [dialogId, enabled]
  );
}
