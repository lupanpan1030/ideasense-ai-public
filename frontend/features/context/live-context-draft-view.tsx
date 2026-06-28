import type { MutableRefObject } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnswerMetaEntry } from "./project-context";
import type { PendingConfirmItem } from "./pending-confirm-types";
import {
  type ContextSection,
  type EditMode,
  type LiveContextMessages,
  isEditableValue,
  isUnresolvedAnswer,
  ListeningIndicator,
  renderAnswerMetaBadges,
  renderValue,
  resolveConfirmedDisplayValue,
  resolveStageLabel,
} from "./live-context-formatters";

type LiveDraftViewProps = {
  context: {
    stage: string;
    contextVersion: number;
    answerMeta: Record<string, AnswerMetaEntry>;
  } | null;
  sections: ContextSection[];
  pendingItemMap: Map<string, PendingConfirmItem>;
  userEditedPaths: Set<string>;
  highlightedKeys: Set<string>;
  fieldRefs: MutableRefObject<Map<string, HTMLDivElement | null>>;
  isLoading: boolean;
  isReviewing: boolean;
  isReviewSubmitting: boolean;
  editingPath: string | null;
  editMode: EditMode;
  editDraft: string;
  editListDraft: string[];
  editListDraftInput: string;
  editBooleanDraft: boolean;
  editError: string | null;
  isEditSaving: boolean;
  onEditStart: (path: string, value: unknown) => void;
  onEditCancel: () => void;
  onEditChange: (value: string) => void;
  onListItemChange: (index: number, value: string) => void;
  onListItemRemove: (index: number) => void;
  onListDraftInputChange: (value: string) => void;
  onListAdd: () => void;
  onBooleanChange: (value: string) => void;
  onEditSave: (path: string, originalValue: unknown) => void;
  messages: LiveContextMessages;
};

export function LiveDraftView({
  context,
  sections,
  pendingItemMap,
  userEditedPaths,
  highlightedKeys,
  fieldRefs,
  isLoading,
  isReviewing,
  isReviewSubmitting,
  editingPath,
  editMode,
  editDraft,
  editListDraft,
  editListDraftInput,
  editBooleanDraft,
  editError,
  isEditSaving,
  onEditStart,
  onEditCancel,
  onEditChange,
  onListItemChange,
  onListItemRemove,
  onListDraftInputChange,
  onListAdd,
  onBooleanChange,
  onEditSave,
  messages,
}: LiveDraftViewProps) {
  const hasSections = sections.length > 0;
  const stageLabel = context?.stage
    ? resolveStageLabel(context.stage, messages)
    : messages.tabs.unknownStage;
  const answerMeta = context?.answerMeta ?? {};

  return (
    <div className="context-panel__section">
      <div className="context-panel__section-header">
        <p className="sidebar-label">{messages.sectionLabels.liveContext}</p>
        <span className="context-panel__meta">
          {stageLabel} - v{context?.contextVersion ?? 0}
        </span>
      </div>

      {isLoading && !hasSections ? (
        <div className="context-panel__skeleton">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      ) : null}

      {hasSections ? (
        <div className="context-panel__sections">
          {sections.map((section) => (
            <section key={section.key} className="context-panel__section">
              <div className="context-panel__section-header">
                <p className="sidebar-label">{section.label}</p>
              </div>
              {section.fields.length ? (
                <div className="context-list">
                  {section.fields.map((field) => {
                    const pendingItem = pendingItemMap.get(field.path);
                    const confirmedValue =
                      pendingItem?.currentValue !== undefined
                        ? pendingItem.currentValue
                        : field.value;
                    const showDraft = Boolean(pendingItem);
                    const isUserEdited =
                      userEditedPaths.has(field.path) ||
                      pendingItem?.source === "user";
                    const canReviewEdit = isReviewing && !isReviewSubmitting;
                    const isEditing = canReviewEdit && editingPath === field.path;
                    const canEdit = isEditableValue(confirmedValue);
                    const answerMetaEntry = answerMeta[field.path];
                    const confirmedDisplayValue = resolveConfirmedDisplayValue(
                      confirmedValue,
                      answerMetaEntry
                    );
                    const isUnresolved = isUnresolvedAnswer(answerMetaEntry);

                    return (
                      <div
                        key={field.path}
                        ref={(node) => {
                          if (node) {
                            fieldRefs.current.set(field.path, node);
                          } else {
                            fieldRefs.current.delete(field.path);
                          }
                        }}
                        className={[
                          "context-list__row",
                          isEditing ? "context-list__row--editing" : "",
                          isUnresolved ? "context-list__row--unresolved" : "",
                          highlightedKeys.has(field.path)
                            ? "context-list__row--highlight"
                            : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                      >
                        <div className="context-list__label">{field.label}</div>
                        <div className="context-list__value">
                          {showDraft ? (
                            <div className="context-list__value-stack">
                              <div>
                                <div className="context-list__meta">
                                  {messages.labels.confirmed}
                                  {isUserEdited && pendingItem?.source !== "user" ? (
                                    <span className="context-list__badge">
                                      {messages.labels.userEdit}
                                    </span>
                                  ) : null}
                                </div>
                                {renderValue(
                                  confirmedDisplayValue,
                                  "confirmed",
                                  isUnresolved
                                    ? messages.noConfirmedValue
                                    : messages.listening
                                )}
                                {renderAnswerMetaBadges(answerMetaEntry, messages)}
                              </div>
                              <div>
                                <div className="context-list__meta context-list__meta--accent">
                                  {messages.labels.draft}
                                  {pendingItem?.source === "user" ? (
                                    <span className="context-list__badge context-list__badge--accent">
                                      {messages.labels.userEdit}
                                    </span>
                                  ) : null}
                                </div>
                                {renderValue(pendingItem?.value, "draft", messages.listening)}
                              </div>
                            </div>
                          ) : (
                            <>
                              {isUserEdited ? (
                                <div className="context-list__meta context-list__meta--accent">
                                  {messages.labels.userEdit}
                                </div>
                              ) : null}
                              {renderValue(
                                confirmedDisplayValue,
                                "confirmed",
                                isUnresolved
                                  ? messages.noConfirmedValue
                                  : messages.listening
                              )}
                              {renderAnswerMetaBadges(answerMetaEntry, messages)}
                            </>
                          )}

                          {canReviewEdit ? (
                            <div className="context-list__actions">
                              {isEditing && canEdit ? (
                                <div className="context-list__edit">
                                  {editMode === "string_list" ? (
                                    <>
                                      <label
                                        className="field__label"
                                        htmlFor={`${field.path}-edit-list`}
                                      >
                                        {messages.edit.editItems}
                                      </label>
                                      <div
                                        className="context-list__edit-list"
                                        id={`${field.path}-edit-list`}
                                      >
                                        {editListDraft.map((item, index) => (
                                          <div
                                            key={`${field.path}-item-${index}`}
                                            className="context-list__edit-row"
                                          >
                                            <input
                                              className="input input--sm"
                                              value={item}
                                              onChange={(event) =>
                                                onListItemChange(index, event.target.value)
                                              }
                                              disabled={isEditSaving}
                                            />
                                            <Button
                                              type="button"
                                              size="sm"
                                              variant="ghost"
                                              onClick={() => onListItemRemove(index)}
                                              disabled={isEditSaving}
                                            >
                                              {messages.edit.remove}
                                            </Button>
                                          </div>
                                        ))}
                                        <div className="context-list__edit-add">
                                          <input
                                            className="input input--sm"
                                            placeholder={messages.edit.addItemPlaceholder}
                                            value={editListDraftInput}
                                            onChange={(event) =>
                                              onListDraftInputChange(event.target.value)
                                            }
                                            disabled={isEditSaving}
                                          />
                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="secondary"
                                            onClick={onListAdd}
                                            disabled={isEditSaving || !editListDraftInput.trim()}
                                          >
                                            {messages.edit.add}
                                          </Button>
                                        </div>
                                      </div>
                                      <p className="field__hint">
                                        {messages.edit.listHint}
                                      </p>
                                    </>
                                  ) : editMode === "boolean" ? (
                                    <>
                                      <label
                                        className="field__label"
                                        htmlFor={`${field.path}-edit-boolean`}
                                      >
                                        {messages.edit.editValue}
                                      </label>
                                      <select
                                        id={`${field.path}-edit-boolean`}
                                        className="input input--sm"
                                        value={editBooleanDraft ? "true" : "false"}
                                        onChange={(event) =>
                                          onBooleanChange(event.target.value)
                                        }
                                        disabled={isEditSaving}
                                      >
                                        <option value="true">{messages.edit.trueLabel}</option>
                                        <option value="false">{messages.edit.falseLabel}</option>
                                      </select>
                                    </>
                                  ) : editMode === "number" ? (
                                    <>
                                      <label
                                        className="field__label"
                                        htmlFor={`${field.path}-edit-number`}
                                      >
                                        {messages.edit.editValue}
                                      </label>
                                      <input
                                        id={`${field.path}-edit-number`}
                                        className="input input--sm"
                                        type="number"
                                        value={editDraft}
                                        onChange={(event) =>
                                          onEditChange(event.target.value)
                                        }
                                        disabled={isEditSaving}
                                      />
                                    </>
                                  ) : (
                                    <>
                                      <label
                                        className="field__label"
                                        htmlFor={`${field.path}-edit`}
                                      >
                                        {messages.edit.editValue}
                                      </label>
                                      <textarea
                                        id={`${field.path}-edit`}
                                        className="textarea"
                                        rows={3}
                                        value={editDraft}
                                        onChange={(event) =>
                                          onEditChange(event.target.value)
                                        }
                                        disabled={isEditSaving}
                                      />
                                    </>
                                  )}
                                  {editError ? (
                                    <p className="field__error">{editError}</p>
                                  ) : null}
                                  <div className="context-list__actions-row">
                                    <Button
                                      size="sm"
                                      disabled={isEditSaving}
                                      onClick={() => onEditSave(field.path, confirmedValue)}
                                    >
                                      {messages.edit.saveEdit}
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="secondary"
                                      disabled={isEditSaving}
                                      onClick={onEditCancel}
                                    >
                                      {messages.edit.cancel}
                                    </Button>
                                  </div>
                                </div>
                              ) : canEdit ? (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => onEditStart(field.path, confirmedValue)}
                                >
                                  {messages.edit.edit}
                                </Button>
                              ) : (
                                <p className="text-muted">
                                  {messages.edit.structuredValueDisabled}
                                </p>
                              )}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <ListeningIndicator label={messages.listening} />
              )}
            </section>
          ))}
        </div>
      ) : !isLoading ? (
        <ListeningIndicator label={messages.listening} />
      ) : null}
    </div>
  );
}
