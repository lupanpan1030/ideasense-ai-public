import { useCallback, useRef, useState } from "react";
import { getPendingConfirmErrorDetails } from "./pending-confirm";
import {
  type EditMode,
  type LiveContextMessages,
  formatDraftValue,
  isEditableValue,
  isStringList,
  resolveEditMode,
} from "./live-context-formatters";

type UpdatePendingValue = (path: string, value: unknown) => Promise<void>;

type UseLiveContextEditingOptions = {
  messages: LiveContextMessages;
  updatePendingValue: UpdatePendingValue;
  onEditStateChange: (editing: boolean) => void;
};

export function useLiveContextEditing({
  messages,
  updatePendingValue,
  onEditStateChange,
}: UseLiveContextEditingOptions) {
  const editOriginalRef = useRef<unknown>(null);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<EditMode>("text");
  const [editDraft, setEditDraft] = useState("");
  const [editListDraft, setEditListDraft] = useState<string[]>([]);
  const [editListDraftInput, setEditListDraftInput] = useState("");
  const [editBooleanDraft, setEditBooleanDraft] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [isEditSaving, setIsEditSaving] = useState(false);

  const handleEditStart = useCallback(
    (path: string, value: unknown) => {
      if (!isEditableValue(value)) {
        return;
      }
      const nextMode = resolveEditMode(value);
      setEditingPath(path);
      setEditMode(nextMode);
      if (nextMode === "string_list") {
        setEditListDraft(
          (isStringList(value) ? value : []).map((item) => item.trim())
        );
        setEditListDraftInput("");
        setEditDraft("");
      } else if (nextMode === "boolean") {
        setEditBooleanDraft(Boolean(value));
        setEditDraft("");
      } else {
        setEditDraft(formatDraftValue(value));
        setEditListDraft([]);
        setEditListDraftInput("");
      }
      setEditError(null);
      editOriginalRef.current = value;
      onEditStateChange(true);
    },
    [onEditStateChange]
  );

  const handleEditCancel = useCallback(() => {
    setEditingPath(null);
    setEditMode("text");
    setEditDraft("");
    setEditListDraft([]);
    setEditListDraftInput("");
    setEditBooleanDraft(false);
    setEditError(null);
    setIsEditSaving(false);
    editOriginalRef.current = null;
    onEditStateChange(false);
  }, [onEditStateChange]);

  const handleEditChange = useCallback((value: string) => {
    setEditDraft(value);
    setEditError(null);
  }, []);

  const handleListItemChange = useCallback((index: number, value: string) => {
    setEditListDraft((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
    setEditError(null);
  }, []);

  const handleListItemRemove = useCallback((index: number) => {
    setEditListDraft((prev) => prev.filter((_, idx) => idx !== index));
    setEditError(null);
  }, []);

  const handleListDraftInputChange = useCallback((value: string) => {
    setEditListDraftInput(value);
    setEditError(null);
  }, []);

  const handleListAdd = useCallback(() => {
    const trimmed = editListDraftInput.trim();
    if (!trimmed) {
      return;
    }
    setEditListDraft((prev) => [...prev, trimmed]);
    setEditListDraftInput("");
    setEditError(null);
  }, [editListDraftInput]);

  const handleBooleanChange = useCallback((value: string) => {
    setEditBooleanDraft(value === "true");
    setEditError(null);
  }, []);

  const handleEditSave = useCallback(
    async (path: string, originalValue: unknown) => {
      const sourceValue = editOriginalRef.current ?? originalValue;
      let parsed: { value: unknown; error: string | null };
      if (editMode === "string_list") {
        const normalized = editListDraft
          .map((item) => item.trim())
          .filter(Boolean);
        parsed = { value: normalized, error: null };
      } else if (editMode === "boolean") {
        parsed = { value: editBooleanDraft, error: null };
      } else if (editMode === "number") {
        const trimmed = editDraft.trim();
        const numberValue = Number(trimmed);
        if (Number.isFinite(numberValue)) {
          parsed = { value: numberValue, error: null };
        } else {
          parsed = {
            value: sourceValue,
            error: messages.edit.invalidNumber,
          };
        }
      } else {
        parsed = { value: editDraft, error: null };
      }
      if (parsed.error) {
        setEditError(parsed.error);
        return;
      }
      setIsEditSaving(true);
      try {
        await updatePendingValue(path, {
          value: parsed.value,
          source: "user",
          created_at: new Date().toISOString(),
          current_value: sourceValue,
        });
        handleEditCancel();
      } catch (error) {
        const details = getPendingConfirmErrorDetails(error);
        setEditError(details.message);
      } finally {
        setIsEditSaving(false);
      }
    },
    [
      editBooleanDraft,
      editDraft,
      editListDraft,
      editMode,
      handleEditCancel,
      messages.edit.invalidNumber,
      updatePendingValue,
    ]
  );

  return {
    editingPath,
    editMode,
    editDraft,
    editListDraft,
    editListDraftInput,
    editBooleanDraft,
    editError,
    isEditSaving,
    handleEditStart,
    handleEditCancel,
    handleEditChange,
    handleListItemChange,
    handleListItemRemove,
    handleListDraftInputChange,
    handleListAdd,
    handleBooleanChange,
    handleEditSave,
  };
}
