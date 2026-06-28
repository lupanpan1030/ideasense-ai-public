"use client";

import { ChatComposer } from "./chat-composer";
import { ChatThreadMessages } from "./chat-thread-messages";
import { useChatThread } from "./use-chat-thread";

type ChatThreadProps = {
  projectId: string;
  currentStage?: string | null;
  stageStatus?: string | null;
  onFirstUserMessage?: () => void;
  onLatestMessageAt?: (value: string | null) => void;
};

export function ChatThread({
  projectId,
  currentStage,
  stageStatus,
  onFirstUserMessage,
  onLatestMessageAt,
}: ChatThreadProps) {
  const {
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
  } = useChatThread({
    projectId,
    currentStage,
    stageStatus,
    onFirstUserMessage,
    onLatestMessageAt,
  });
  const reportStatus = reportJobStatus?.status ?? null;
  const isReportStage =
    currentStage?.toLowerCase() === "report" ||
    reportJobStatus?.currentStage?.toLowerCase() === "report" ||
    reportStatus === "queued" ||
    reportStatus === "running" ||
    reportStatus === "finalizing" ||
    reportStatus === "ready" ||
    reportStatus === "failed" ||
    reportStatus === "stale";
  const handleQuickOptionSelect = (
    message: string,
    meta?: Record<string, unknown>
  ) => {
    void handleSend(message, meta);
  };

  return (
    <div className="chat-thread">
      <ChatThreadMessages
        messages={messages}
        isLoading={isLoading}
        isLoadingMore={isLoadingMore}
        isStreaming={isStreaming}
        historyError={historyError}
        streamError={streamError}
        onRetryHistory={refreshHistory}
        scrollContainerRef={scrollContainerRef}
        onScroll={handleScroll}
        onQuickOptionSelect={handleQuickOptionSelect}
      />

      <ChatComposer
        isStreaming={isStreaming}
        isStageComplete={isStageComplete}
        isStageConfirming={isStageConfirming}
        reportJobStatus={reportJobStatus}
        isReportStatusUnavailable={isReportStatusUnavailable}
        isReportStage={isReportStage}
        onSend={handleSend}
        onCancelStream={handleCancelStream}
        onStageGate={handleStageGate}
        onGenerateReport={handleGenerateReport}
      />
    </div>
  );
}
