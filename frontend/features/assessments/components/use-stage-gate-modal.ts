"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  confirmStage,
  getStageDraft,
  getStageGateErrorMessage,
  type StageConfirmResult,
  type StageDraftSummary,
  type StageSummaryGenerationStatus,
} from "../api";
import {
  formatUpdatedAt,
  hasVisibleStageDraftSummary,
  NEXT_STAGE_MAP,
  STAGE_LABELS,
} from "./stage-gate-utils";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type ConfirmStatus = "idle" | "submitting" | "computed" | "needs_retry" | "error";
type SummaryStatus = StageSummaryGenerationStatus | "idle" | "error";

type UseStageGateModalOptions = {
  projectId: string;
  stage: string;
  nextStage?: string | null;
  isFinalReport?: boolean;
  contextVersion: number | null;
  contextUpdatedAt?: string | null;
  onClose: () => void;
  onConfirmed?: (result: StageConfirmResult) => Promise<void> | void;
  onRequestRefresh?: () => Promise<void> | void;
  onReviewPending?: () => void;
  lockBodyScroll?: boolean;
  autoCloseOnConfirm?: boolean;
};

type HeaderBadge = { variant: "success" | "warning"; label: string };

export function useStageGateModalState({
  projectId,
  stage,
  nextStage,
  isFinalReport = false,
  contextVersion: initialContextVersion,
  contextUpdatedAt: initialContextUpdatedAt,
  onClose,
  onConfirmed,
  onRequestRefresh,
  onReviewPending,
  lockBodyScroll = true,
  autoCloseOnConfirm = true,
}: UseStageGateModalOptions) {
  const locale = useAppLocale();
  const messages = useAppMessages().stageGate;
  const isReportStage = stage.trim().toLowerCase() === "report";
  const isFinalGate = isFinalReport || isReportStage;
  const [confirmStatus, setConfirmStatus] = useState<ConfirmStatus>("idle");
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<StageConfirmResult | null>(
    null
  );
  const [draftSummary, setDraftSummary] = useState<StageDraftSummary | null>(
    null
  );
  const [summaryStatus, setSummaryStatus] = useState<SummaryStatus>(
    isFinalGate ? "ready" : "queued"
  );
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryRetryNonce, setSummaryRetryNonce] = useState(0);

  const stageLabel = useMemo(() => {
    const key = stage.trim().toLowerCase();
    return STAGE_LABELS[key] ?? stage;
  }, [stage]);

  const resolvedNextStage = useMemo(() => {
    if (nextStage && nextStage.trim()) {
      return nextStage;
    }
    const key = stage.trim().toLowerCase();
    return NEXT_STAGE_MAP[key] ?? null;
  }, [nextStage, stage]);

  const nextStageLabel = useMemo(() => {
    if (!resolvedNextStage) {
      return messages.nextStageFallback;
    }
    const key = resolvedNextStage.trim().toLowerCase();
    return STAGE_LABELS[key] ?? resolvedNextStage;
  }, [messages.nextStageFallback, resolvedNextStage]);

  const isSubmitting = confirmStatus === "submitting";
  const isComputed = confirmStatus === "computed";
  const isSummaryPreparing =
    !isFinalGate && (summaryStatus === "queued" || summaryStatus === "running");
  const hasDraftSummary = hasVisibleStageDraftSummary(draftSummary);
  const isSummaryReady =
    isFinalGate || (summaryStatus === "ready" && hasDraftSummary);
  const isSummaryFailed =
    !isFinalGate &&
    (summaryStatus === "failed" ||
      summaryStatus === "stale" ||
      summaryStatus === "error");

  const handleClose = useCallback(() => {
    if (isSubmitting) {
      return;
    }
    onClose();
  }, [isSubmitting, onClose]);

  const resolvedContextVersion = useMemo(() => {
    if (typeof initialContextVersion === "number") {
      return initialContextVersion;
    }
    return null;
  }, [initialContextVersion]);

  const resolvedContextUpdatedAt = useMemo(() => {
    return initialContextUpdatedAt ?? null;
  }, [initialContextUpdatedAt]);

  const resolveConfirmContextVersion = useCallback(() => {
    return typeof resolvedContextVersion === "number" ? resolvedContextVersion : 0;
  }, [resolvedContextVersion]);

  useEffect(() => {
    if (isFinalGate) {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();

    const loadDraft = async (retryRequest = false) => {
      setSummaryStatus((current) =>
        current === "ready" && !retryRequest ? current : "queued"
      );
      setSummaryError(null);
      try {
        const result = await getStageDraft({
          projectId,
          stage,
          clientContextVersion: resolvedContextVersion,
          outputLocale: locale,
          retry: retryRequest,
          signal: controller.signal,
        });
        if (cancelled) {
          return;
        }
        setDraftSummary(result);
        setSummaryStatus(result.generationStatus);
        setSummaryError(
          result.lastError ? messages.modal.summaryPreparationFailedRetry : null
        );
        if (
          result.generationStatus === "queued" ||
          result.generationStatus === "running"
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
        setSummaryStatus("error");
        setSummaryError(details.message);
        if (details.shouldRefresh) {
          void Promise.resolve(onRequestRefresh?.());
        }
      }
    };

    void loadDraft(summaryRetryNonce > 0);

    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [
    isFinalGate,
    locale,
    messages.modal.summaryPreparationFailedRetry,
    onRequestRefresh,
    projectId,
    resolvedContextVersion,
    stage,
    summaryRetryNonce,
  ]);

  const handleSummaryRetry = useCallback(() => {
    if (isSubmitting || isComputed) {
      return;
    }
    setSummaryRetryNonce((value) => value + 1);
  }, [isComputed, isSubmitting]);

  const handleConfirm = useCallback(async () => {
    if (isSubmitting || isComputed) {
      return;
    }
    if (!isFinalGate && !isSummaryReady) {
      return;
    }

    setConfirmStatus("submitting");
    setConfirmError(null);

    try {
      const result = await confirmStage({
        projectId,
        stage,
        clientContextVersion: resolveConfirmContextVersion(),
        outputLocale: locale,
      });

      setConfirmResult(result);

      if (result.scoreStatus === "needs_retry") {
        setConfirmStatus("needs_retry");
        setConfirmError(messages.modal.confirmationFailedRetry);
        return;
      }

      setConfirmStatus("computed");
      if (autoCloseOnConfirm) {
        onClose();
      }
      void Promise.resolve(onConfirmed?.(result));
    } catch (error) {
      const details = getStageGateErrorMessage(error);
      const isConflict = details.status === 409;
      setConfirmStatus(isConflict ? "needs_retry" : "error");
      setConfirmError(details.message);
      if (details.shouldRefresh) {
        await Promise.resolve(onRequestRefresh?.());
      }
    }
  }, [
    autoCloseOnConfirm,
    isComputed,
    isSubmitting,
    messages.modal.confirmationFailedRetry,
    isFinalGate,
    isSummaryReady,
    onClose,
    onConfirmed,
    onRequestRefresh,
    projectId,
    locale,
    resolveConfirmContextVersion,
    stage,
  ]);

  const handleReviewPending = useCallback(() => {
    onReviewPending?.();
  }, [onReviewPending]);

  const handlePrimaryAction = useCallback(() => {
    if (isComputed) {
      if (autoCloseOnConfirm) {
        handleClose();
      }
      return;
    }
    if (isSummaryFailed) {
      handleSummaryRetry();
      return;
    }
    if (!isSummaryReady) {
      return;
    }
    void handleConfirm();
  }, [
    autoCloseOnConfirm,
    handleClose,
    handleConfirm,
    handleSummaryRetry,
    isComputed,
    isSummaryFailed,
    isSummaryReady,
  ]);

  useEffect(() => {
    if (!lockBodyScroll) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleClose, lockBodyScroll]);

  const actionLabel = isSummaryPreparing
    ? messages.actions.preparingSummary
    : isSummaryFailed
    ? messages.actions.retrySummary
    : isSubmitting
    ? isFinalGate
      ? messages.actions.generatingReport
      : messages.actions.generatingSummary
    : confirmStatus === "needs_retry" || confirmStatus === "error"
    ? messages.actions.retryConfirm
    : isComputed
    ? messages.actions.close
    : isFinalGate
    ? messages.actions.generateReport
    : messages.actions.confirmAndAdvance;

  const headerTitle = isComputed
    ? isFinalGate
      ? messages.headers.reportGenerated
      : messages.headers.stageConfirmed
    : isFinalGate
    ? messages.headers.generateReport
    : messages.headers.confirmStage;
  const headerDescription = isComputed
    ? isFinalGate
      ? messages.headers.reportReadyToView
      : `Stage advanced to ${nextStageLabel}.`
    : isFinalGate
    ? messages.headers.reviewAndGenerate
    : `Generate the ${stageLabel} summary and advance to ${nextStageLabel}.`;
  const headerBadge: HeaderBadge = isComputed
    ? { variant: "success", label: messages.headers.confirmedBadge }
    : { variant: "warning", label: messages.headers.awaitingConfirmBadge };

  const scoreSummary = confirmResult?.scores ?? null;
  const totalScore = confirmResult?.totalScore ?? scoreSummary?.total ?? null;
  const updatedLabel = formatUpdatedAt(resolvedContextUpdatedAt);
  const primaryDisabled =
    isSubmitting || (!isSummaryReady && !isSummaryFailed);

  return {
    actionLabel,
    headerBadge,
    headerDescription,
    headerTitle,
    confirmStatus,
    confirmError,
    confirmResult,
    draftSummary,
    hasDraftSummary,
    isSubmitting,
    isComputed,
    isSummaryPreparing,
    isSummaryReady,
    isSummaryFailed,
    nextStageLabel,
    primaryDisabled,
    resolvedContextVersion,
    scoreSummary,
    stageLabel,
    totalScore,
    summaryError,
    summaryStatus,
    updatedLabel,
    handleClose,
    handleConfirm,
    handlePrimaryAction,
    handleReviewPending,
    handleSummaryRetry,
  };
}
