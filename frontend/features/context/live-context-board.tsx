"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { subscribeToChatControl } from "@/features/chat/control-channel";
import { formatUpdatedAt } from "@/features/assessments/components/stage-gate-utils";
import {
  confirmStage,
  getStageDraft,
  getStageGateErrorMessage,
  type StageConfirmResult,
} from "@/features/assessments/api";
import { useUserSession } from "@/features/auth/user-session";
import { resolvePendingConfirm } from "./pending-confirm";
import { fetchProjectContext } from "./project-context";
import { useLiveContextBoardState } from "./use-live-context-board";
import { useLiveContextEditing } from "./use-live-context-editing";
import { LiveContextBoardSurface } from "./live-context-board-surface";
import {
  type ReviewSummaryStatus,
  type StageKey,
  type ViewMode,
  STAGE_ORDER,
  STAGES,
  buildContextSections,
  inferStageForPath,
  isReportStage,
  normalizeStageKey,
  resolveLatestContextVersion,
  resolveStageDraftUserError,
  resolveStageKey,
  resolveStageLabel,
  stableStringify,
} from "./live-context-formatters";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type LiveContextBoardProps = {
  projectId: string;
  lastMessageAt?: string | null;
  onSummaryVisibilityChange?: (isVisible: boolean) => void;
};

export function LiveContextBoard({
  projectId,
  lastMessageAt = null,
  onSummaryVisibilityChange,
}: LiveContextBoardProps) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const liveMessages = appMessages.liveContext;
  const { session } = useUserSession();
  const emailVerified = session?.user.emailVerified;
  const requiresVerification = emailVerified === false;
  const router = useRouter();
  const [highlightedKeys, setHighlightedKeys] = useState<Set<string>>(
    () => new Set()
  );
  const [viewMode, setViewMode] = useState<ViewMode>("draft");
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [isReviewHighlight, setIsReviewHighlight] = useState(false);
  const highlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reviewHighlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const previousValuesRef = useRef<Map<string, string>>(new Map());
  const previousStageRef = useRef<StageKey | null>(null);
  const fieldRefs = useRef<Map<string, HTMLDivElement | null>>(new Map());
  const contextPanelRef = useRef<HTMLDivElement | null>(null);
  const contextBodyRef = useRef<HTMLDivElement | null>(null);
  const userSelectedRef = useRef(false);
  const [reviewStage, setReviewStage] = useState<StageKey | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSummaryStatus, setReviewSummaryStatus] =
    useState<ReviewSummaryStatus>("idle");
  const [reviewSummaryError, setReviewSummaryError] = useState<string | null>(
    null
  );
  const [reviewSummaryRetryNonce, setReviewSummaryRetryNonce] = useState(0);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);

  const {
    context,
    pendingConfirm,
    projectDetail,
    stageSummaries,
    stageVerification,
    errorMessage,
    pendingErrorMessage,
    stageSummariesError,
    stageVerificationError,
    isLoading,
    isPendingLoading,
    isVerificationLoading,
    stageGateState,
    pendingItems,
    showPendingOverrideHint,
    pendingPanelRef,
    handleStageGateOpen,
    handleStageGateClose,
    handleStageGateConfirmed,
    resolvePending,
    updatePendingValue,
    refreshPendingPanelForce,
    refreshStageVerificationData,
    requestStageVerificationRefresh,
    handlePendingEditState,
    handleReviewPending,
  } = useLiveContextBoardState({ projectId });

  const {
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
  } = useLiveContextEditing({
    messages: liveMessages,
    updatePendingValue,
    onEditStateChange: handlePendingEditState,
  });

  const updatedLabel = useMemo(() => {
    if (!lastMessageAt) {
      return liveMessages.updatedFallback;
    }
    return formatUpdatedAt(lastMessageAt);
  }, [lastMessageAt, liveMessages.updatedFallback]);

  const stageValue = useMemo(() => {
    const gateStage = stageGateState?.stage ?? null;
    const contextStage = context?.stage ?? projectDetail?.currentStage ?? null;
    if (!gateStage) {
      return contextStage;
    }
    if (!contextStage) {
      return gateStage;
    }
    const gateKey = resolveStageKey(gateStage);
    const contextKey = resolveStageKey(contextStage);
    const gateIndex = STAGE_ORDER.get(gateKey) ?? 0;
    const contextIndex = STAGE_ORDER.get(contextKey) ?? 0;
    if (contextIndex > gateIndex) {
      return contextStage;
    }
    return gateStage;
  }, [stageGateState?.stage, context?.stage, projectDetail?.currentStage]);
  const currentStageKey = useMemo(
    () => resolveStageKey(stageValue),
    [stageValue]
  );
  const progressIndex = useMemo(() => {
    if (isReportStage(stageValue)) {
      return STAGES.length;
    }
    return STAGE_ORDER.get(currentStageKey) ?? 0;
  }, [currentStageKey, stageValue]);

  const [activeTab, setActiveTab] = useState<StageKey>(currentStageKey);
  const lastResolvedStageRef = useRef<StageKey>(currentStageKey);

  useEffect(() => {
    userSelectedRef.current = false;
  }, [projectId]);

  useEffect(() => {
    if (lastResolvedStageRef.current !== currentStageKey) {
      userSelectedRef.current = false;
      setActiveTab(currentStageKey);
      lastResolvedStageRef.current = currentStageKey;
      return;
    }
    if (!userSelectedRef.current) {
      setActiveTab(currentStageKey);
    }
  }, [currentStageKey]);

  useEffect(() => {
    setViewMode("draft");
  }, [projectId]);

  useEffect(() => {
    if (viewMode !== "insight") {
      return;
    }
    void requestStageVerificationRefresh(activeTab);
    void refreshStageVerificationData();
  }, [activeTab, refreshStageVerificationData, requestStageVerificationRefresh, viewMode]);

  useEffect(() => {
    setReviewStage(null);
    setReviewError(null);
    setReportModalOpen(false);
    setIsReviewHighlight(false);
    handleEditCancel();
  }, [projectId, handleEditCancel]);

  const triggerReviewHighlight = useCallback(() => {
    if (reviewHighlightTimeoutRef.current) {
      clearTimeout(reviewHighlightTimeoutRef.current);
    }
    setIsReviewHighlight(true);
    reviewHighlightTimeoutRef.current = setTimeout(() => {
      setIsReviewHighlight(false);
      reviewHighlightTimeoutRef.current = null;
    }, 5200);
  }, []);

  useEffect(
    () => () => {
      if (reviewHighlightTimeoutRef.current) {
        clearTimeout(reviewHighlightTimeoutRef.current);
        reviewHighlightTimeoutRef.current = null;
      }
    },
    []
  );

  const handleReportModalOpen = useCallback(() => {
    setReportModalOpen(true);
    handleStageGateOpen();
  }, [handleStageGateOpen]);

  const handleReportModalClose = useCallback(() => {
    setReportModalOpen(false);
    handleStageGateClose();
  }, [handleStageGateClose]);

  const handleReportConfirmed = useCallback(async (result?: StageConfirmResult) => {
    await handleStageGateConfirmed(result);
    router.push(buildLocalePath(locale, `/projects/${projectId}/report`));
  }, [handleStageGateConfirmed, locale, projectId, router]);

  const reportGate = useMemo(() => {
    if (!reportModalOpen) {
      return null;
    }
    const reportStageValue = context?.stage ?? projectDetail?.currentStage ?? null;
    const isReportActive =
      isReportStage(reportStageValue) ||
      stageGateState?.stage?.trim().toLowerCase() === "report";
    if (!isReportActive) {
      return null;
    }
    if (stageGateState?.stage?.trim().toLowerCase() === "report") {
      return stageGateState;
    }
    return {
      stage: "report",
      nextStage: null,
      contextVersion: context?.contextVersion ?? null,
      contextUpdatedAt: context?.updatedAt ?? projectDetail?.updatedAt ?? null,
    };
  }, [
    context?.contextVersion,
    context?.stage,
    context?.updatedAt,
    projectDetail?.currentStage,
    projectDetail?.updatedAt,
    reportModalOpen,
    stageGateState,
  ]);

  useEffect(() => {
    return subscribeToChatControl((payload) => {
      if (payload.project_id && payload.project_id !== projectId) {
        return;
      }
      const type =
        typeof payload.type === "string" ? payload.type.trim().toLowerCase() : "";
      if (type === "report_review") {
        handleReportModalOpen();
        return;
      }
      if (type !== "stage_review") {
        return;
      }
      const stageValue =
        typeof payload.stage === "string"
          ? payload.stage
          : typeof payload.current_stage === "string"
            ? payload.current_stage
            : null;
      if (stageValue?.trim().toLowerCase() === "report") {
        handleReportModalOpen();
        return;
      }
      const incomingStage = normalizeStageKey(stageValue);
      if (!incomingStage) {
        return;
      }
      userSelectedRef.current = true;
      setActiveTab(incomingStage);
      setViewMode("draft");
      setReviewStage(incomingStage);
      setReviewError(null);
      setReviewSummaryStatus("queued");
      setReviewSummaryError(null);
      triggerReviewHighlight();
      requestAnimationFrame(() => {
        contextPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        contextBodyRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
  }, [handleReportModalOpen, projectId, triggerReviewHighlight]);

  const contextSnapshot = context?.dataRaw ?? null;
  const contextSections = useMemo(
    () =>
      buildContextSections(
        contextSnapshot,
        activeTab,
        context?.answerMeta ?? {},
        liveMessages
      ),
    [contextSnapshot, activeTab, context?.answerMeta, liveMessages]
  );

  const pendingItemMap = useMemo(
    () => new Map(pendingItems.map((item) => [item.path, item])),
    [pendingItems]
  );

  const userEditedPathSet = useMemo(() => {
    const byStage = context?.userEditedPaths ?? {};
    return new Set(byStage[activeTab] ?? []);
  }, [context?.userEditedPaths, activeTab]);

  const activeSummary = useMemo(() => {
    const key = activeTab.toLowerCase();
    return (
      stageSummaries.find(
        (entry) => entry.stage.trim().toLowerCase() === key
      ) ?? null
    );
  }, [activeTab, stageSummaries]);

  const activeDiagnosisCard = useMemo(() => {
    const contextStage = normalizeStageKey(context?.contextCard.stage);
    if (context?.contextCard && contextStage === activeTab) {
      return context.contextCard;
    }
    return activeSummary?.contextCard ?? null;
  }, [activeSummary?.contextCard, activeTab, context?.contextCard]);

  const activeValidationPlan = useMemo(
    () => activeSummary?.validationPlan ?? [],
    [activeSummary?.validationPlan]
  );

  const hasInsightSummary = Boolean(
    activeSummary?.draftSummaryMarkdown || activeSummary?.finalSummaryMarkdown
  );
  const gateStageKey = normalizeStageKey(stageGateState?.stage);
  const isReportGate = stageGateState?.stage?.toLowerCase() === "report";
  const isGateForActiveStage = Boolean(
    stageGateState && (isReportGate || gateStageKey === activeTab)
  );
  const insightEnabled = hasInsightSummary || isGateForActiveStage;
  const showInsightNotification = isGateForActiveStage && viewMode !== "insight";
  const isReviewEligible = Boolean(
    stageGateState && !isReportGate && gateStageKey === activeTab
  );
  const isReviewing =
    isReviewEligible && reviewStage === activeTab && viewMode === "draft";
  const pendingUserEdits = pendingItems.filter(
    (item) => item.source === "user" && inferStageForPath(item.path, activeTab) === activeTab
  );
  const hasPendingUserEdits = pendingUserEdits.length > 0;
  const hasPendingSuggestions = pendingItems.some(
    (item) => item.source !== "user"
  );

  useEffect(() => {
    if (viewMode === "insight" && !insightEnabled) {
      setViewMode("draft");
    }
  }, [insightEnabled, viewMode]);

  useEffect(() => {
    if (!stageGateState || (reviewStage && gateStageKey !== reviewStage)) {
      setReviewStage(null);
      setReviewError(null);
    }
  }, [gateStageKey, reviewStage, stageGateState]);


  const handleReviewPendingFromInsight = () => {
    setViewMode("draft");
    window.setTimeout(() => {
      handleReviewPending();
    }, 0);
  };

  const handleStageSelect = (stage: StageKey) => {
    userSelectedRef.current = true;
    setActiveTab(stage);
  };

  useEffect(() => {
    if (!contextSections.length) {
      previousValuesRef.current = new Map();
      return;
    }

    if (previousStageRef.current !== activeTab) {
      const currentValues = new Map<string, string>();
      contextSections.forEach((section) => {
        section.fields.forEach((field) => {
          currentValues.set(field.path, stableStringify(field.value));
        });
      });
      previousValuesRef.current = currentValues;
      previousStageRef.current = activeTab;
      setHighlightedKeys(new Set());
      return;
    }

    const currentValues = new Map<string, string>();
    const orderedPaths: string[] = [];

    contextSections.forEach((section) => {
      section.fields.forEach((field) => {
        orderedPaths.push(field.path);
        currentValues.set(field.path, stableStringify(field.value));
      });
    });

    const previousValues = previousValuesRef.current;
    const changed = orderedPaths.filter(
      (path) => previousValues.get(path) !== currentValues.get(path)
    );

    previousValuesRef.current = currentValues;

    if (!changed.length) {
      return;
    }

    const nextHighlights = new Set(changed);
    setHighlightedKeys(nextHighlights);

    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current);
    }
    highlightTimeoutRef.current = setTimeout(() => {
      setHighlightedKeys(new Set());
    }, 3000);

    const targetPath = orderedPaths.find((path) => nextHighlights.has(path));
    if (targetPath) {
      const node = fieldRefs.current.get(targetPath);
      if (node) {
        requestAnimationFrame(() => {
          node.scrollIntoView({ behavior: "smooth", block: "center" });
        });
      }
    }
  }, [contextSections, activeTab]);

  useEffect(
    () => () => {
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current);
      }
    },
    []
  );

  useEffect(() => {
    onSummaryVisibilityChange?.(true);
  }, [onSummaryVisibilityChange]);

  const hasPending = pendingItems.length > 0;
  const showPendingPanel =
    viewMode === "draft" &&
    (hasPending || isPendingLoading || Boolean(pendingErrorMessage));

  const reviewStageLabel = gateStageKey
    ? resolveStageLabel(gateStageKey, liveMessages)
    : liveMessages.labels.stageFallback;
  const reviewNextLabel = stageGateState?.nextStage
    ? resolveStageLabel(stageGateState.nextStage, liveMessages)
    : liveMessages.labels.nextStageFallback;
  const reviewContextVersion = resolveLatestContextVersion(
    stageGateState?.contextVersion,
    pendingConfirm?.contextVersion,
    context?.contextVersion
  );
  const isReviewSummaryPreparing =
    isReviewing &&
    (reviewSummaryStatus === "queued" || reviewSummaryStatus === "running");
  const isReviewSummaryFailed =
    isReviewing &&
    (reviewSummaryStatus === "failed" ||
      reviewSummaryStatus === "stale" ||
      reviewSummaryStatus === "error");
  const isReviewSummaryReady =
    !isReviewing || reviewSummaryStatus === "ready";
  const reviewButtonLabel = requiresVerification
    ? liveMessages.review.verifyEmailButton
    : isReviewSummaryPreparing
      ? appMessages.stageGate.actions.preparingSummary
      : isReviewSummaryFailed
        ? appMessages.stageGate.actions.retrySummary
    : isReviewSubmitting
      ? liveMessages.review.generatingSummaryButton
      : liveMessages.review.confirmGenerateButton;

  const handleReviewCancel = () => {
    setReviewStage(null);
    setReviewError(null);
    setReviewSummaryStatus("idle");
    setReviewSummaryError(null);
    handleEditCancel();
  };

  useEffect(() => {
    if (!isReviewing || !stageGateState || !gateStageKey) {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();

    const loadDraft = async (retryRequest = false) => {
      try {
        const draft = await getStageDraft({
          projectId,
          stage: stageGateState.stage,
          clientContextVersion: reviewContextVersion,
          outputLocale: locale,
          retry: retryRequest,
          signal: controller.signal,
        });
        if (cancelled) {
          return;
        }
        setReviewSummaryStatus(draft.generationStatus);
        setReviewSummaryError(
          draft.lastError
            ? resolveStageDraftUserError(draft.lastError, appMessages)
            : null
        );
        if (
          draft.generationStatus === "queued" ||
          draft.generationStatus === "running"
        ) {
          timeoutId = setTimeout(() => {
            void loadDraft(false);
          }, 2000);
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) {
          return;
        }
        const details = getStageGateErrorMessage(error);
        setReviewSummaryStatus("error");
        setReviewSummaryError(details.message);
        if (details.shouldRefresh) {
          void refreshPendingPanelForce();
        }
      }
    };

    void loadDraft(reviewSummaryRetryNonce > 0);

    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [
    appMessages,
    gateStageKey,
    isReviewing,
    locale,
    projectId,
    refreshPendingPanelForce,
    reviewContextVersion,
    reviewSummaryRetryNonce,
    stageGateState,
  ]);

  const handleReviewConfirm = async () => {
    if (!stageGateState || isReviewSubmitting || requiresVerification) {
      return;
    }
    if (isReviewSummaryPreparing) {
      return;
    }
    if (isReviewSummaryFailed || !isReviewSummaryReady) {
      setReviewSummaryStatus("queued");
      setReviewSummaryError(null);
      setReviewSummaryRetryNonce((value) => value + 1);
      return;
    }
    setIsReviewSubmitting(true);
    setReviewError(null);
    let contextVersion = 0;
    try {
      contextVersion =
        resolveLatestContextVersion(
          stageGateState.contextVersion,
          pendingConfirm?.contextVersion,
          context?.contextVersion
        ) ?? 0;
      if (hasPendingUserEdits) {
        const snapshot = await resolvePendingConfirm(projectId, {
          acceptPaths: pendingUserEdits.map((item) => item.path),
          rejectPaths: [],
          clientContextVersion: contextVersion,
        });
        contextVersion =
          resolveLatestContextVersion(contextVersion, snapshot.contextVersion) ??
          contextVersion;
        await refreshPendingPanelForce();
      }
      const draft = await getStageDraft({
        projectId,
        stage: stageGateState.stage,
        clientContextVersion: contextVersion,
        outputLocale: locale,
      });
      if (draft.generationStatus !== "ready") {
        setReviewSummaryStatus(draft.generationStatus);
        const safeDraftError = resolveStageDraftUserError(
          draft.lastError,
          appMessages
        );
        setReviewSummaryError(draft.lastError ? safeDraftError : null);
        setReviewError(
          `${liveMessages.review.summaryUnavailablePrefix} ${safeDraftError}`
        );
        return;
      }
      const result = await confirmStage({
        projectId,
        stage: stageGateState.stage,
        clientContextVersion: contextVersion,
        outputLocale: locale,
      });
      await handleStageGateConfirmed(result);
      handleReviewCancel();
    } catch (error) {
      let details = getStageGateErrorMessage(error);
      if (details.shouldRefresh) {
        await refreshPendingPanelForce();
        try {
          const latestSnapshot = await fetchProjectContext(projectId);
          const latestVersion =
            resolveLatestContextVersion(latestSnapshot.contextVersion, contextVersion) ??
            contextVersion;
          if (latestVersion !== contextVersion) {
            const draft = await getStageDraft({
              projectId,
              stage: stageGateState.stage,
              clientContextVersion: latestVersion,
              outputLocale: locale,
            });
            if (draft.generationStatus !== "ready") {
              setReviewSummaryStatus(draft.generationStatus);
              const safeDraftError = resolveStageDraftUserError(
                draft.lastError,
                appMessages
              );
              setReviewSummaryError(draft.lastError ? safeDraftError : null);
              setReviewError(
                `${liveMessages.review.summaryUnavailablePrefix} ${safeDraftError}`
              );
              return;
            }
            const result = await confirmStage({
              projectId,
              stage: stageGateState.stage,
              clientContextVersion: latestVersion,
              outputLocale: locale,
            });
            await handleStageGateConfirmed(result);
            handleReviewCancel();
            return;
          }
        } catch (retryError) {
          details = getStageGateErrorMessage(retryError);
        }
      }
      setReviewError(details.message);
    } finally {
      setIsReviewSubmitting(false);
    }
  };

  return (
    <LiveContextBoardSurface
      stageSummariesNotice={
        stageSummariesError
          ? `${liveMessages.review.summaryUnavailablePrefix} ${stageSummariesError}`
          : null
      }
      panelNotice={
        errorMessage
          ? `${liveMessages.review.summaryUnavailablePrefix} ${errorMessage}`
          : null
      }
      isReviewing={isReviewing}
      isReviewHighlight={isReviewHighlight}
      contextPanelRef={contextPanelRef}
      contextBodyRef={contextBodyRef}
      headerProps={{
        activeStage: activeTab,
        insightEnabled,
        messages: liveMessages,
        progressIndex,
        showInsightNotification,
        stages: STAGES,
        updatedLabel,
        viewMode,
        onStageSelect: handleStageSelect,
        onViewModeChange: setViewMode,
        resolveStageLabel: (stage) => resolveStageLabel(stage, liveMessages),
      }}
      viewMode={viewMode}
      reviewCtaProps={{
        disabled:
          isReviewSubmitting || requiresVerification || isReviewSummaryPreparing,
        label: reviewButtonLabel,
        onConfirm: handleReviewConfirm,
      }}
      reviewPanelProps={{
        appMessages,
        hasPendingSuggestions,
        hasPendingUserEdits,
        isReviewSummaryFailed,
        isReviewSummaryPreparing,
        messages: liveMessages,
        requiresVerification,
        reviewContextVersion,
        reviewError,
        reviewNextLabel,
        reviewStageLabel,
        reviewSummaryError,
        onReviewPending: handleReviewPending,
      }}
      draftViewProps={{
        context: context
          ? {
              stage: context.stage,
              contextVersion: context.contextVersion,
              answerMeta: context.answerMeta,
            }
          : null,
        sections: contextSections,
        pendingItemMap,
        userEditedPaths: userEditedPathSet,
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
        onEditStart: handleEditStart,
        onEditCancel: handleEditCancel,
        onEditChange: handleEditChange,
        onListItemChange: handleListItemChange,
        onListItemRemove: handleListItemRemove,
        onListDraftInputChange: handleListDraftInputChange,
        onListAdd: handleListAdd,
        onBooleanChange: handleBooleanChange,
        onEditSave: handleEditSave,
        messages: liveMessages,
      }}
      diagnosisViewProps={{
        contextCard: activeDiagnosisCard,
        validationPlan: activeValidationPlan,
        messages: liveMessages,
      }}
      insightViewProps={{
        projectId,
        activeStage: activeTab,
        stageSummaries,
        stageGateState,
        stageVerification,
        stageVerificationError,
        isVerificationLoading,
        refreshStageVerificationData,
        requestStageVerificationRefresh,
        showPendingOverrideHint,
        onReviewPending: handleReviewPendingFromInsight,
        onConfirmed: handleStageGateConfirmed,
        onRequestRefresh: refreshPendingPanelForce,
        messages: liveMessages,
      }}
      showPendingPanel={showPendingPanel}
      pendingPanelRef={pendingPanelRef}
      pendingPanelProps={{
        pending: pendingConfirm,
        mergedData: context?.dataRaw ?? null,
        isLoading: isPendingLoading,
        errorMessage: pendingErrorMessage,
        onAccept: async (paths) =>
          resolvePending({ acceptPaths: paths, rejectPaths: [] }),
        onReject: async (paths) =>
          resolvePending({ acceptPaths: [], rejectPaths: paths }),
        onUpdate: updatePendingValue,
        onRequestRefresh: refreshPendingPanelForce,
        onEditStateChange: handlePendingEditState,
      }}
      reportModalProps={
        reportGate
          ? {
              onClose: handleReportModalClose,
              projectId,
              stage: reportGate.stage,
              nextStage: reportGate.nextStage,
              contextVersion: reportGate.contextVersion,
              contextUpdatedAt: reportGate.contextUpdatedAt,
              stageSummaries,
              onConfirmed: handleReportConfirmed,
              onRequestRefresh: refreshPendingPanelForce,
              showPendingOverrideHint,
              onReviewPending: handleReviewPending,
            }
          : null
      }
    />
  );
}
