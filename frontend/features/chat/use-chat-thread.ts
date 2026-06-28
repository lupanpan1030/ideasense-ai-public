"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { useRouter } from "next/navigation";
import {
  emitStageGate,
  isAwaitingConfirmStageGateSignal,
  normalizeStageGateSignal,
  type StageGateSignal,
} from "@/features/assessments/stage-gate-channel";
import { emitChatControl, subscribeToChatControl } from "./control-channel";
import { streamChatResponse } from "./chat-stream";
import {
  ChatMessage,
  appendMessageDelta,
  createLocalMessage,
  updateMessageStatus,
  updateMessageStreamStatus,
} from "./chat-state";
import { createChatStreamHandlers } from "./chat-stream-handlers";
import {
  resolveDoneError,
  resolveLatestMessageAt,
  resolveRequestError,
  resolveStreamError,
} from "./chat-thread-utils";
import { useChatHistory } from "./use-chat-history";
import { fetchProjectContext } from "@/features/context/project-context";
import { fetchProjectDetail } from "@/features/projects/project-detail";
import {
  fetchProjectReportStatus,
  normalizeReportJobStatus,
} from "@/features/reports/reports-api";
import type { ReportJobStatus } from "@/features/reports/reports-normalize";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

type UseChatThreadOptions = {
  projectId: string;
  currentStage?: string | null;
  stageStatus?: string | null;
  onFirstUserMessage?: () => void;
  onLatestMessageAt?: (value: string | null) => void;
};

type UseChatThreadResult = {
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  isLoadingMore: boolean;
  isStageComplete: boolean;
  isStageConfirming: boolean;
  reportJobStatus: ReportJobStatus | null;
  isReportStatusUnavailable: boolean;
  historyError: string | null;
  streamError: string | null;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  refreshHistory: () => Promise<void>;
  handleScroll: () => void;
  handleSend: (
    draft: string,
    meta?: Record<string, unknown>
  ) => Promise<boolean>;
  handleCancelStream: () => void;
  handleStageGate: () => void;
  handleGenerateReport: () => void;
};

const createClientMessageId = (): string => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  const segment = () =>
    Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .slice(1);
  return `${segment()}${segment()}-${segment()}-${segment()}-${segment()}-${segment()}${segment()}${segment()}`;
};

const isStageWaitingForConfirmationError = (value: string): boolean =>
  /stage is waiting for confirmation/i.test(value) ||
  /review or confirm the stage before answering/i.test(value);

export function useChatThread({
  projectId,
  currentStage,
  stageStatus,
  onFirstUserMessage,
  onLatestMessageAt,
}: UseChatThreadOptions): UseChatThreadResult {
  const locale = useAppLocale();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isStageComplete, setIsStageComplete] = useState(false);
  const [isStageConfirming, setIsStageConfirming] = useState(false);
  const [stageGateSnapshot, setStageGateSnapshot] =
    useState<StageGateSignal | null>(null);
  const [reportJobStatus, setReportJobStatus] =
    useState<ReportJobStatus | null>(null);
  const [isReportStatusUnavailable, setIsReportStatusUnavailable] =
    useState(false);
  const stageGatePayloadRef = useRef<Record<string, unknown> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const activeAssistantMessageIdRef = useRef<string | null>(null);
  const messageCounterRef = useRef(0);
  const isMountedRef = useRef(true);
  const latestMessageAtRef = useRef<string | null>(null);
  const router = useRouter();

  const {
    messages,
    setMessages,
    isLoading,
    isLoadingMore,
    historyError,
    scrollContainerRef,
    notifyHasUserMessage,
    setShouldAutoScroll,
    stopHistoryLoad,
    refreshHistory,
    handleScroll,
  } = useChatHistory({ projectId, outputLocale: locale, onFirstUserMessage });

  const nextMessageId = useCallback((prefix: string) => {
    messageCounterRef.current += 1;
    return `${prefix}-${Date.now()}-${messageCounterRef.current}`;
  }, []);

  const stopStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const handleCancelStream = useCallback(() => {
    const controller = abortRef.current;
    if (!controller) {
      return;
    }
    controller.abort();
    abortRef.current = null;
    const activeAssistantMessageId = activeAssistantMessageIdRef.current;
    activeAssistantMessageIdRef.current = null;
    if (activeAssistantMessageId) {
      setMessages((prev) =>
        updateMessageStatus(prev, activeAssistantMessageId, "complete")
      );
    }
    setIsStreaming(false);
    setStreamError("Response stopped.");
  }, [setMessages]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopStream();
      stopHistoryLoad();
    };
  }, [stopStream, stopHistoryLoad]);

  useEffect(() => {
    stopStream();
    activeAssistantMessageIdRef.current = null;
    latestMessageAtRef.current = null;
    stageGatePayloadRef.current = null;
    const timeoutId = setTimeout(() => {
      setIsStreaming(false);
      setStreamError(null);
      setIsStageComplete(false);
      setIsStageConfirming(false);
      setReportJobStatus(null);
      setIsReportStatusUnavailable(false);
      setStageGateSnapshot(null);
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [projectId, stopStream]);

  useEffect(() => {
    const isReportStage = currentStage?.trim().toLowerCase() === "report";
    const currentReportStatus = reportJobStatus?.status;
    const isReportJobPending =
      currentReportStatus === "queued" ||
      currentReportStatus === "running" ||
      currentReportStatus === "finalizing";
    if (!isReportStage && !reportJobStatus) {
      const timeoutId = setTimeout(() => {
        setReportJobStatus(null);
        setIsReportStatusUnavailable(false);
      }, 0);
      return () => clearTimeout(timeoutId);
    }
    if (!isReportStage && !isReportJobPending) {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();

    const loadStatus = async () => {
      try {
        const status = await fetchProjectReportStatus(projectId, {
          signal: controller.signal,
          outputLocale: locale,
        });
        if (cancelled || controller.signal.aborted) {
          return;
        }
        setReportJobStatus(status);
        setIsReportStatusUnavailable(false);
        if (
          status.status === "queued" ||
          status.status === "running" ||
          status.status === "finalizing"
        ) {
          timeoutId = setTimeout(loadStatus, status.nextPollMs);
        }
      } catch {
        if (!cancelled && !controller.signal.aborted) {
          setReportJobStatus(null);
          setIsReportStatusUnavailable(true);
        }
      }
    };

    void loadStatus();

    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [currentStage, locale, projectId, reportJobStatus]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      const normalizedStatus = stageStatus?.trim().toLowerCase() ?? null;
      if (normalizedStatus === "awaiting_confirm") {
        setIsStageComplete(true);
        return;
      }
      if (normalizedStatus && !stageGateSnapshot) {
        setIsStageComplete(false);
      }
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [stageGateSnapshot, stageStatus]);

  const handleSend = useCallback(
    async (draft: string, messageMeta?: Record<string, unknown>) => {
      const trimmed = draft.trim();
      if (!trimmed) {
        return false;
      }
      if (isStreaming || abortRef.current) {
        setStreamError("Finish the current response before sending again.");
        return false;
      }

      setStreamError(null);
      stopHistoryLoad();
      const clientMessageId = createClientMessageId();

      const userMessage = createLocalMessage({
        id: nextMessageId("user"),
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
        status: "complete",
        meta: messageMeta ?? null,
      });
      const assistantMessage = createLocalMessage({
        id: nextMessageId("assistant"),
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        status: "streaming",
      });

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setShouldAutoScroll(true);
      notifyHasUserMessage([userMessage]);

      const controller = new AbortController();
      abortRef.current = controller;
      activeAssistantMessageIdRef.current = assistantMessage.id;
      setIsStreaming(true);

      const { handlers, didReceiveDone } = createChatStreamHandlers({
        appendToken: (delta) => {
          setMessages((prev) =>
            appendMessageDelta(prev, assistantMessage.id, delta)
          );
        },
        updateStatus: (label) => {
          setMessages((prev) =>
            updateMessageStreamStatus(prev, assistantMessage.id, label)
          );
        },
        markDone: (payload) => {
          setMessages((prev) =>
            updateMessageStatus(prev, assistantMessage.id, "complete")
          );
          const doneError = resolveDoneError(payload);
          if (doneError) {
            setStreamError(doneError);
            setMessages((prev) =>
              updateMessageStatus(prev, assistantMessage.id, "error")
            );
          }
        },
        reportError: (payload) => {
          setStreamError(resolveStreamError(payload));
          setMessages((prev) =>
            updateMessageStatus(prev, assistantMessage.id, "error")
          );
        },
        refreshHistory: () => {
          void refreshHistory();
        },
      });

      const handleStageGateReady = (payload: Record<string, unknown>) => {
        const normalized = normalizeStageGateSignal(payload);
        if (!isAwaitingConfirmStageGateSignal(normalized, projectId)) {
          void refreshHistory();
          return;
        }
        stageGatePayloadRef.current = payload;
        setStageGateSnapshot(normalized);
        setIsStageComplete(true);
        emitStageGate(payload);
      };

      void streamChatResponse(
        projectId,
        trimmed,
        {
          ...handlers,
          onStageComplete: handleStageGateReady,
        },
        {
          signal: controller.signal,
          messageMeta,
          clientMessageId,
          outputLocale: locale,
        }
      )
        .then(() => {
          if (!didReceiveDone() && !controller.signal.aborted) {
            void refreshHistory();
          }
        })
        .catch((error) => {
          if (controller.signal.aborted || !isMountedRef.current) {
            return;
          }
          const requestError = resolveRequestError(error);
          setStreamError(requestError);
          if (isStageWaitingForConfirmationError(requestError)) {
            setIsStageComplete(true);
            void refreshHistory();
          }
          setMessages((prev) =>
            updateMessageStatus(
              updateMessageStreamStatus(prev, assistantMessage.id, null),
              assistantMessage.id,
              "error"
            )
          );
        })
        .finally(() => {
          if (abortRef.current === controller) {
            abortRef.current = null;
          }
          if (activeAssistantMessageIdRef.current === assistantMessage.id) {
            activeAssistantMessageIdRef.current = null;
          }
          if (isMountedRef.current) {
            setIsStreaming(false);
          }
        });

      return true;
    },
    [
      isStreaming,
      locale,
      nextMessageId,
      notifyHasUserMessage,
      projectId,
      refreshHistory,
      setMessages,
      setShouldAutoScroll,
      stopHistoryLoad,
    ]
  );

  useEffect(() => {
    const latestAt = resolveLatestMessageAt(messages);
    if (latestMessageAtRef.current === latestAt) {
      return;
    }
    latestMessageAtRef.current = latestAt;
    onLatestMessageAt?.(latestAt);
  }, [messages, onLatestMessageAt]);

  const handleStageGate = useCallback(() => {
    const payload = stageGatePayloadRef.current;
    if (isStageConfirming) {
      return;
    }
    if (payload && stageGateSnapshot) {
      const stage = stageGateSnapshot.stage;
      if (!stage) {
        setStreamError("Stage confirmation failed. Refresh and try again.");
        return;
      }
      setStreamError(null);
      emitChatControl({
        type: "stage_review",
        project_id: projectId,
        stage,
        context_version: stageGateSnapshot.contextVersion ?? undefined,
        context_updated_at: stageGateSnapshot.contextUpdatedAt ?? undefined,
      });
      return;
    }

    const normalizedStatus = stageStatus?.trim().toLowerCase() ?? null;
    const stage = currentStage?.trim().toLowerCase() ?? null;
    const canOpenReviewFromLocalStageComplete =
      isStageComplete && stage && stage !== "report";
    if (
      normalizedStatus !== "awaiting_confirm" &&
      !canOpenReviewFromLocalStageComplete
    ) {
      return;
    }
    if (!stage || stage === "report") {
      return;
    }
    setStreamError(null);
    void (async () => {
      try {
        if (normalizedStatus !== "awaiting_confirm") {
          const snapshot = await fetchProjectDetail(projectId);
          if (snapshot.stageStatus?.trim().toLowerCase() !== "awaiting_confirm") {
            setIsStageComplete(false);
            return;
          }
        }
        const context = await fetchProjectContext(projectId);
        emitChatControl({
          type: "stage_review",
          project_id: projectId,
          stage,
          context_version: context.contextVersion ?? undefined,
          context_updated_at: context.updatedAt ?? undefined,
        });
      } catch {
        setStreamError("Stage confirmation failed. Refresh and try again.");
      }
    })();
  }, [
    isStageConfirming,
    currentStage,
    isStageComplete,
    projectId,
    stageStatus,
    stageGateSnapshot,
  ]);

  const handleGenerateReport = useCallback(() => {
    if (isStageConfirming || isStreaming) {
      return;
    }
    setStreamError(null);
    const reportReady = reportJobStatus?.status === "ready";
    router.push(
      buildLocalePath(
        locale,
        `/projects/${projectId}/report`,
        reportReady ? null : "generate=1"
      )
    );
  }, [
    isStageConfirming,
    isStreaming,
    locale,
    projectId,
    reportJobStatus?.status,
    router,
  ]);

  useEffect(() => {
    return subscribeToChatControl((payload) => {
      if (payload.project_id && payload.project_id !== projectId) {
        return;
      }
      const type =
        typeof payload.type === "string" ? payload.type.trim().toLowerCase() : "";
      if (type !== "stage_confirmed") {
        return;
      }
      setIsStageComplete(false);
      setStageGateSnapshot(null);
      stageGatePayloadRef.current = null;
      const reportStatus = normalizeReportJobStatus(
        payload.report_job_status,
        projectId
      );
      if (reportStatus) {
        setReportJobStatus(reportStatus);
        setIsReportStatusUnavailable(false);
      } else if (
        typeof payload.next_stage === "string" &&
        payload.next_stage.trim().toLowerCase() === "report"
      ) {
        setReportJobStatus({
          projectId,
          currentStage: "report",
          stageStatus:
            typeof payload.stage_status === "string"
              ? payload.stage_status
              : null,
          jobType: "report_generation_v0",
          status: "queued",
          retryable: false,
          reportId: null,
          reportVersion: null,
          generatedAt: null,
          contextVersion:
            typeof payload.context_version === "number"
              ? payload.context_version
              : null,
          nextPollMs: 2000,
        });
        setIsReportStatusUnavailable(false);
      }
      void refreshHistory();
    });
  }, [projectId, refreshHistory]);

  return {
    messages,
    isLoading,
    isStreaming,
    isLoadingMore,
    isStageComplete,
    isStageConfirming,
    reportJobStatus,
    isReportStatusUnavailable,
    historyError,
    streamError,
    scrollContainerRef,
    refreshHistory,
    handleScroll,
    handleSend,
    handleCancelStream,
    handleStageGate,
    handleGenerateReport,
  };
}
