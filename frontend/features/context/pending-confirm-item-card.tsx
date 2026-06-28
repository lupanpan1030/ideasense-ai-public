"use client";

import { useId } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  getPendingConfirmPathValue,
  PendingConfirmItem,
} from "./pending-confirm";
import {
  formatCreatedAt,
  formatSource,
  formatValue,
} from "./pending-confirm-formatters";

type PendingConfirmItemCardProps = {
  item: PendingConfirmItem;
  mergedData: Record<string, unknown> | null;
  isSubmitting: boolean;
  isOverride: boolean;
  isNoteOpen: boolean;
  noteValue: string;
  isEditing: boolean;
  draftValue: string;
  draftError: string | null;
  showSeparator: boolean;
  onAccept: (path: string) => void;
  onReject: (path: string) => void;
  onEdit: (path: string) => void;
  onEditCancel: (path: string) => void;
  onEditChange: (path: string, value: string) => void;
  onEditSave: (path: string) => void;
  onNoteToggle: (path: string) => void;
  onNoteChange: (path: string, value: string) => void;
  messages: {
    pendingBadge: string;
    overridesBadge: string;
    sourcePrefix: string;
    suggestedPrefix: string;
    suggestedValue: string;
    editSuggestion: string;
    currentValue: string;
    currentValueUnavailable: string;
    saveEdit: string;
    cancel: string;
    accept: string;
    reject: string;
    edit: string;
    structuredValueHint: string;
    hideNote: string;
    addNote: string;
    decisionNote: string;
    sessionNoteHint: string;
    notSet: string;
    nullValue: string;
    modelInferred: string;
    userEdit: string;
    dateLocale: string;
  };
};

export function PendingConfirmItemCard({
  item,
  mergedData,
  isSubmitting,
  isOverride,
  isNoteOpen,
  noteValue,
  isEditing,
  draftValue,
  draftError,
  showSeparator,
  onAccept,
  onReject,
  onEdit,
  onEditCancel,
  onEditChange,
  onEditSave,
  onNoteToggle,
  onNoteChange,
  messages,
}: PendingConfirmItemCardProps) {
  const noteId = useId();
  const editId = useId();
  const createdAt = formatCreatedAt(item.createdAt, messages.dateLocale);
  const currentLookup = getPendingConfirmPathValue(mergedData, item.path);
  const hasCurrentValue =
    currentLookup.found || item.currentValue !== undefined;
  const currentValue = currentLookup.found
    ? currentLookup.value
    : item.currentValue;
  const canEdit =
    item.value === null ||
    item.value === undefined ||
    typeof item.value === "string" ||
    typeof item.value === "number" ||
    typeof item.value === "boolean";

  return (
    <div className="stack-sm">
      <div className="cluster-tight">
        <Badge variant="warning">{messages.pendingBadge}</Badge>
        {item.priority !== null ? (
          <Badge variant="info">P{item.priority}</Badge>
        ) : null}
        {isOverride ? (
          <Badge variant="danger">{messages.overridesBadge}</Badge>
        ) : null}
        <span className="text-muted">{item.path}</span>
      </div>
      <div className="cluster-tight">
        <span className="text-muted">
          {messages.sourcePrefix} {formatSource(item.source, messages)}
        </span>
        {createdAt ? (
          <span className="text-muted">
            {messages.suggestedPrefix} {createdAt}
          </span>
        ) : null}
      </div>
      <div className="stack-sm">
        <div className="stack-sm">
          <span className="text-muted">{messages.suggestedValue}</span>
          {isEditing ? (
            <div className="field">
              <label className="field__label" htmlFor={editId}>
                {messages.editSuggestion}
              </label>
              <textarea
                id={editId}
                className="textarea"
                rows={3}
                value={draftValue}
                onChange={(event) =>
                  onEditChange(item.path, event.target.value)
                }
                disabled={isSubmitting}
              />
              {draftError ? (
                <p className="field__error">{draftError}</p>
              ) : null}
            </div>
          ) : (
            <span>{formatValue(item.value, messages)}</span>
          )}
        </div>
        <div className="stack-sm">
          <span className="text-muted">{messages.currentValue}</span>
          {hasCurrentValue ? (
            <span>{formatValue(currentValue, messages)}</span>
          ) : (
            <span className="text-muted">{messages.currentValueUnavailable}</span>
          )}
        </div>
      </div>
      <div className="cluster">
        {isEditing ? (
          <>
            <Button
              size="sm"
              disabled={isSubmitting}
              onClick={() => onEditSave(item.path)}
            >
              {messages.saveEdit}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={isSubmitting}
              onClick={() => onEditCancel(item.path)}
            >
              {messages.cancel}
            </Button>
          </>
        ) : (
          <>
            <Button
              size="sm"
              disabled={isSubmitting}
              onClick={() => onAccept(item.path)}
            >
              {messages.accept}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={isSubmitting}
              onClick={() => onReject(item.path)}
            >
              {messages.reject}
            </Button>
            {canEdit ? (
              <Button
                size="sm"
                variant="ghost"
                disabled={isSubmitting}
                onClick={() => onEdit(item.path)}
              >
                {messages.edit}
              </Button>
            ) : (
              <span className="text-muted">{messages.structuredValueHint}</span>
            )}
          </>
        )}
        <Button
          size="sm"
          variant="ghost"
          disabled={isSubmitting}
          onClick={() => onNoteToggle(item.path)}
        >
          {isNoteOpen ? messages.hideNote : messages.addNote}
        </Button>
      </div>
      {isNoteOpen ? (
        <div className="field">
          <label className="field__label" htmlFor={noteId}>
            {messages.decisionNote}
          </label>
          <textarea
            id={noteId}
            className="textarea"
            rows={2}
            value={noteValue}
            onChange={(event) => onNoteChange(item.path, event.target.value)}
            disabled={isSubmitting}
          />
          <p className="field__hint">{messages.sessionNoteHint}</p>
        </div>
      ) : null}
      {showSeparator ? <Separator /> : null}
    </div>
  );
}
