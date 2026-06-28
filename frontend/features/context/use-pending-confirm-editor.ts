"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getPendingConfirmErrorDetails,
  PendingConfirmItem,
} from "./pending-confirm";

type PendingConfirmEditorOptions = {
  items: PendingConfirmItem[];
  onUpdate: (path: string, value: unknown) => Promise<void>;
  onEditStateChange?: (editing: boolean) => void;
  setIsSubmitting: (next: boolean) => void;
  messages: {
    invalidNumber: string;
    invalidBoolean: string;
    structuredValue: string;
  };
};

type PendingConfirmEditorState = {
  isEditing: boolean;
  editOpenState: Record<string, boolean>;
  editDraftState: Record<string, string>;
  editErrorState: Record<string, string>;
  handleEditToggle: (path: string, value: unknown) => void;
  handleEditCancel: (path: string) => void;
  handleEditChange: (path: string, value: string) => void;
  handleEditSave: (path: string, originalValue: unknown) => Promise<void>;
};

const formatDraftValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const parseDraftValue = (
  draft: string,
  originalValue: unknown,
  messages: PendingConfirmEditorOptions["messages"]
): { value: unknown; error: string | null } => {
  const trimmed = draft.trim();
  if (typeof originalValue === "number") {
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) {
      return { value: parsed, error: null };
    }
    return { value: originalValue, error: messages.invalidNumber };
  }
  if (typeof originalValue === "boolean") {
    const normalized = trimmed.toLowerCase();
    if (normalized === "true" || normalized === "false") {
      return { value: normalized === "true", error: null };
    }
    return { value: originalValue, error: messages.invalidBoolean };
  }
  if (originalValue && typeof originalValue === "object") {
    return {
      value: originalValue,
      error: messages.structuredValue,
    };
  }
  return { value: draft, error: null };
};

const isEditableValue = (value: unknown): boolean =>
  value === null ||
  value === undefined ||
  typeof value === "string" ||
  typeof value === "number" ||
  typeof value === "boolean";

export function usePendingConfirmEditor({
  items,
  onUpdate,
  onEditStateChange,
  setIsSubmitting,
  messages,
}: PendingConfirmEditorOptions): PendingConfirmEditorState {
  const [editOpenState, setEditOpenState] = useState<Record<string, boolean>>(
    {}
  );
  const [editDraftState, setEditDraftState] = useState<Record<string, string>>(
    {}
  );
  const [editErrorState, setEditErrorState] = useState<Record<string, string>>(
    {}
  );

  useEffect(() => {
    if (!items.length) {
      setEditOpenState({});
      setEditDraftState({});
      setEditErrorState({});
      return;
    }
    const pathSet = new Set(items.map((item) => item.path));
    setEditOpenState((prev) => {
      const next: Record<string, boolean> = {};
      for (const [key, value] of Object.entries(prev)) {
        if (pathSet.has(key)) {
          next[key] = value;
        }
      }
      return next;
    });
    setEditDraftState((prev) => {
      const next: Record<string, string> = {};
      for (const [key, value] of Object.entries(prev)) {
        if (pathSet.has(key)) {
          next[key] = value;
        }
      }
      return next;
    });
    setEditErrorState((prev) => {
      const next: Record<string, string> = {};
      for (const [key, value] of Object.entries(prev)) {
        if (pathSet.has(key)) {
          next[key] = value;
        }
      }
      return next;
    });
  }, [items]);

  const isEditing = useMemo(
    () => Object.values(editOpenState).some(Boolean),
    [editOpenState]
  );

  useEffect(() => {
    onEditStateChange?.(isEditing);
  }, [isEditing, onEditStateChange]);

  const handleEditToggle = (path: string, value: unknown) => {
    if (!isEditableValue(value)) {
      return;
    }
    setEditOpenState((prev) => {
      const next = !prev[path];
      return { ...prev, [path]: next };
    });
    setEditDraftState((prev) => ({
      ...prev,
      [path]: prev[path] ?? formatDraftValue(value),
    }));
    setEditErrorState((prev) => ({ ...prev, [path]: "" }));
  };

  const handleEditCancel = (path: string) => {
    setEditOpenState((prev) => ({ ...prev, [path]: false }));
    setEditDraftState((prev) => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    setEditErrorState((prev) => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
  };

  const handleEditChange = (path: string, value: string) => {
    setEditDraftState((prev) => ({ ...prev, [path]: value }));
    setEditErrorState((prev) => ({ ...prev, [path]: "" }));
  };

  const handleEditSave = async (path: string, originalValue: unknown) => {
    const draftValue = editDraftState[path] ?? formatDraftValue(originalValue);
    const parsed = parseDraftValue(draftValue, originalValue, messages);
    if (parsed.error) {
      setEditErrorState((prev) => ({ ...prev, [path]: parsed.error ?? "" }));
      return;
    }
    setIsSubmitting(true);
    setEditErrorState((prev) => ({ ...prev, [path]: "" }));
    try {
      await onUpdate(path, parsed.value);
      handleEditCancel(path);
    } catch (error) {
      const details = getPendingConfirmErrorDetails(error);
      setEditErrorState((prev) => ({ ...prev, [path]: details.message }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    isEditing,
    editOpenState,
    editDraftState,
    editErrorState,
    handleEditToggle,
    handleEditCancel,
    handleEditChange,
    handleEditSave,
  };
}
