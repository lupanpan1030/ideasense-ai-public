"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  flattenPendingConfirm,
  findPendingConfirmOverrides,
  getPendingConfirmErrorDetails,
  PendingConfirmResolveOptions,
  PendingConfirmSnapshot,
  shouldRequirePendingOverrideConfirmation,
} from "./pending-confirm";
import {
  PendingConfirmBulkAction,
  PendingConfirmBulkActionModal,
} from "./pending-confirm-bulk-modal";
import { PendingConfirmItemCard } from "./pending-confirm-item-card";
import { usePendingConfirmEditor } from "./use-pending-confirm-editor";
import { useAppMessages } from "@/lib/i18n/provider";

type PendingConfirmPanelProps = {
  pending: PendingConfirmSnapshot | null;
  mergedData: Record<string, unknown> | null;
  isLoading: boolean;
  errorMessage: string | null;
  onAccept: (paths: string[]) => Promise<void>;
  onReject: (paths: string[]) => Promise<void>;
  onUpdate: (path: string, value: unknown) => Promise<void>;
  onRequestRefresh: () => void | Promise<void>;
  onEditStateChange?: (editing: boolean) => void;
};

type PendingOverrideState = {
  paths: string[];
};

type PendingConfirmAction = {
  type: "accept" | "reject";
  paths: string[];
};

type ActionErrorState = {
  details: ReturnType<typeof getPendingConfirmErrorDetails>;
  action: PendingConfirmAction | null;
};

export function PendingConfirmPanel({
  pending,
  mergedData,
  isLoading,
  errorMessage,
  onAccept,
  onReject,
  onUpdate,
  onRequestRefresh,
  onEditStateChange,
}: PendingConfirmPanelProps) {
  const messages = useAppMessages().liveContext.pendingConfirm;
  const items = useMemo(
    () => flattenPendingConfirm(pending?.pendingConfirm ?? {}),
    [pending]
  );
  const pendingData = useMemo(
    () => pending?.pendingConfirm ?? {},
    [pending]
  );

  const [overrideState, setOverrideState] =
    useState<PendingOverrideState | null>(null);
  const [bulkAction, setBulkAction] =
    useState<PendingConfirmBulkAction | null>(null);
  const [actionError, setActionError] = useState<ActionErrorState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [noteState, setNoteState] = useState<Record<string, string>>({});
  const [noteOpenState, setNoteOpenState] = useState<Record<string, boolean>>({});

  const overridePaths = useMemo(() => {
    if (!items.length || !mergedData) {
      return [];
    }
    return findPendingConfirmOverrides(
      pendingData,
      mergedData,
      items.map((item) => item.path)
    );
  }, [items, mergedData, pendingData]);

  const overridePathSet = useMemo(
    () => new Set(overridePaths),
    [overridePaths]
  );

  const findOverrides = (paths: string[]): string[] => {
    if (!paths.length || !overridePathSet.size) {
      return [];
    }
    return paths.filter((path) => overridePathSet.has(path));
  };

  const resolveAction = async (
    type: "accept" | "reject",
    paths: string[],
    options: PendingConfirmResolveOptions = {}
  ) => {
    if (!paths.length) {
      return;
    }
    const overrides = findOverrides(paths);
    if (shouldRequirePendingOverrideConfirmation(type, overrides, options)) {
      setOverrideState({ paths });
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      if (type === "accept") {
        await onAccept(paths);
      } else {
        await onReject(paths);
      }
      setActionError(null);
    } catch (error) {
      setActionError({
        details: getPendingConfirmErrorDetails(error),
        action: { type, paths },
      });
    } finally {
      setIsSubmitting(false);
      setOverrideState(null);
      setBulkAction(null);
    }
  };

  const handleAccept = (paths: string[]) => {
    void resolveAction("accept", paths);
  };

  const handleReject = (paths: string[]) => {
    void resolveAction("reject", paths);
  };

  const handleBulkAction = (type: "accept" | "reject") => {
    if (!items.length) {
      return;
    }
    const paths = items.map((item) => item.path);
    setBulkAction({ type, paths, overrides: findOverrides(paths) });
  };

  const handleRetry = () => {
    if (!actionError?.action) {
      return;
    }
    void resolveAction(actionError.action.type, actionError.action.paths);
  };

  const handleRefreshAndRetry = async () => {
    if (!actionError?.action) {
      return;
    }
    setActionError(null);
    await Promise.resolve(onRequestRefresh());
    void resolveAction(actionError.action.type, actionError.action.paths);
  };

  const handleRefresh = async () => {
    await Promise.resolve(onRequestRefresh());
  };

  const handleNoteToggle = (path: string) => {
    setNoteOpenState((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const handleNoteChange = (path: string, value: string) => {
    setNoteState((prev) => ({ ...prev, [path]: value }));
  };

  const {
    isEditing,
    editOpenState,
    editDraftState,
    editErrorState,
    handleEditToggle,
    handleEditCancel,
    handleEditChange,
    handleEditSave,
  } = usePendingConfirmEditor({
    items,
    onUpdate,
    onEditStateChange,
    setIsSubmitting,
    messages: messages.editor,
  });

  const hasPending = items.length > 0;
  if (!hasPending && !isLoading && !errorMessage) {
    return null;
  }
  const panelError: ActionErrorState | null = actionError
    ? actionError
    : errorMessage
      ? {
          details: { type: "error", message: errorMessage },
          action: null,
        }
      : null;

  return (
    <Card variant="soft" className="pending-confirm-card">
      <CardHeader className="stack-sm">
        <div className="cluster-tight">
          <CardTitle>{messages.title}</CardTitle>
          <Badge variant={hasPending ? "warning" : "default"}>
            {items.length}
          </Badge>
        </div>
        <CardDescription>{messages.description}</CardDescription>
        {isEditing ? (
          <CardDescription>{messages.editingPaused}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="stack-sm">
        {panelError ? (
          <Card variant="alert" role="alert" aria-live="polite">
            <CardHeader className="stack-sm">
              <CardTitle>
                {panelError.details.type === "conflict"
                  ? messages.conflictTitle
                  : messages.attentionTitle}
              </CardTitle>
              <CardDescription>{panelError.details.message}</CardDescription>
            </CardHeader>
            <CardContent className="cluster">
              {panelError.details.type === "conflict" &&
              panelError.action ? (
                <Button
                  size="sm"
                  disabled={isSubmitting}
                  onClick={handleRefreshAndRetry}
                >
                  {messages.refreshRetry}
                </Button>
              ) : null}
              {panelError.details.type !== "conflict" &&
              panelError.action ? (
                <Button size="sm" disabled={isSubmitting} onClick={handleRetry}>
                  {messages.retry}
                </Button>
              ) : null}
              {!panelError.action ? (
                <Button size="sm" disabled={isSubmitting} onClick={handleRefresh}>
                  {messages.retry}
                </Button>
              ) : null}
              {panelError.action ? (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={isSubmitting}
                  onClick={() => setActionError(null)}
                >
                  {messages.dismiss}
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ) : null}
        {overrideState ? (
          <Card variant="alert" role="alert" aria-live="polite">
            <CardHeader className="stack-sm">
              <CardTitle>{messages.overwriteTitle}</CardTitle>
              <CardDescription>{messages.overwriteDescription}</CardDescription>
            </CardHeader>
            <CardContent className="cluster">
              <Button
                size="sm"
                disabled={isSubmitting}
                onClick={() =>
                  resolveAction("accept", overrideState.paths, {
                    overridesAcknowledged: true,
                  })
                }
              >
                {messages.confirmAccept}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={isSubmitting}
                onClick={() => setOverrideState(null)}
              >
                {messages.cancel}
              </Button>
            </CardContent>
          </Card>
        ) : null}
        <div className="cluster">
          <Button
            size="sm"
            disabled={!hasPending || isSubmitting || isEditing}
            onClick={() => handleBulkAction("accept")}
          >
            {messages.acceptAll}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={!hasPending || isSubmitting || isEditing}
            onClick={() => handleBulkAction("reject")}
          >
            {messages.rejectAll}
          </Button>
        </div>
        {isLoading ? (
          <div className="stack-sm">
            <Skeleton className="skeleton--line" />
            <Skeleton className="skeleton--line" />
          </div>
        ) : null}
        {!isLoading && hasPending ? (
          <div className="stack-sm">
            {items.map((item, index) => {
              const isNoteOpen =
                noteOpenState[item.path] ?? Boolean(noteState[item.path]);
              const noteValue = noteState[item.path] ?? "";
              const isEditingItem = editOpenState[item.path] ?? false;
              const draftValue = editDraftState[item.path] ?? "";
              const draftError = editErrorState[item.path] ?? "";
              return (
                <PendingConfirmItemCard
                  key={item.path}
                  item={item}
                  mergedData={mergedData}
                  isSubmitting={isSubmitting}
                  isOverride={overridePathSet.has(item.path)}
                  isNoteOpen={isNoteOpen}
                  noteValue={noteValue}
                  isEditing={isEditingItem}
                  draftValue={draftValue}
                  draftError={draftError || null}
                  showSeparator={index < items.length - 1}
                  onAccept={(path) => handleAccept([path])}
                  onReject={(path) => handleReject([path])}
                  onEdit={(path) => handleEditToggle(path, item.value)}
                  onEditCancel={handleEditCancel}
                  onEditChange={handleEditChange}
                  onEditSave={(path) => handleEditSave(path, item.value)}
                  onNoteToggle={handleNoteToggle}
                  onNoteChange={handleNoteChange}
                  messages={messages.item}
                />
              );
            })}
          </div>
        ) : null}
        <p className="text-muted">{messages.timestampNote}</p>
      </CardContent>
      {bulkAction ? (
        <PendingConfirmBulkActionModal
          action={bulkAction}
          isSubmitting={isSubmitting}
          messages={messages.bulk}
          onClose={() => setBulkAction(null)}
          onConfirm={() =>
            resolveAction(bulkAction.type, bulkAction.paths, {
              overridesAcknowledged: true,
            })
          }
        />
      ) : null}
    </Card>
  );
}
