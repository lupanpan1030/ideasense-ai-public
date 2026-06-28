"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Button } from "@/components/ui/button";
import { MoreHorizontal, Sparkles, Square } from "lucide-react";
import { useUserSession } from "@/features/auth/user-session";
import { useAppMessages } from "@/lib/i18n/provider";
import type { ReportJobStatus } from "@/features/reports/reports-normalize";

const ENTER_TO_SEND_KEY = "ideasense.chat.enterToSend";

const getInitialEnterToSend = () => {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(ENTER_TO_SEND_KEY) === "1";
};

type ChatComposerProps = {
  isStreaming?: boolean;
  isStageComplete?: boolean;
  isStageConfirming?: boolean;
  reportJobStatus?: ReportJobStatus | null;
  isReportStatusUnavailable?: boolean;
  isReportStage?: boolean;
  onSend?: (
    message: string,
    meta?: Record<string, unknown>
  ) => boolean | Promise<boolean>;
  onCancelStream?: () => void;
  onStageGate?: () => void;
  onGenerateReport?: () => void;
};

export function ChatComposer({
  isStreaming = false,
  isStageComplete = false,
  isStageConfirming = false,
  reportJobStatus = null,
  isReportStatusUnavailable = false,
  isReportStage = false,
  onSend,
  onCancelStream,
  onStageGate,
  onGenerateReport,
}: ChatComposerProps) {
  const messages = useAppMessages().chatComposer;
  const [message, setMessage] = useState("");
  const [areQuickActionsOpen, setAreQuickActionsOpen] = useState(false);
  const [enterToSend, setEnterToSend] = useState(getInitialEnterToSend);
  const quickActionsId = useId();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { session } = useUserSession();
  const emailVerified = session?.user.emailVerified;
  const requiresVerification = emailVerified === false;

  const resizeTextarea = useCallback(() => {
    const element = textareaRef.current;
    if (!element) {
      return;
    }
    element.style.height = "auto";
    const nextHeight = Math.min(Math.max(element.scrollHeight, 48), 160);
    element.style.height = `${nextHeight}px`;
  }, []);

  const submitMessage = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    const result = onSend ? await onSend(trimmed) : false;
    if (result !== false) {
      setMessage("");
      setAreQuickActionsOpen(false);
    }
  }, [isStreaming, message, onSend]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      await submitMessage();
    },
    [submitMessage]
  );

  const handleKeyDown = useCallback(
    async (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (
        enterToSend &&
        event.key === "Enter" &&
        !event.shiftKey &&
        !event.nativeEvent.isComposing
      ) {
        event.preventDefault();
        await submitMessage();
      }
    },
    [enterToSend, submitMessage]
  );

  const quickActions = [
    {
      key: "unknown",
      label: messages.quickActions.unknown.label,
      sub: messages.quickActions.unknown.sub,
      message: messages.quickActions.unknown.message,
      meta: { answer_mode: "unknown", skip_reason: "cant_answer" },
    },
    {
      key: "undecided",
      label: messages.quickActions.undecided.label,
      sub: messages.quickActions.undecided.sub,
      message: messages.quickActions.undecided.message,
      meta: { answer_mode: "undecided", skip_reason: "undecided" },
    },
    {
      key: "not_applicable",
      label: messages.quickActions.notApplicable.label,
      sub: messages.quickActions.notApplicable.sub,
      message: messages.quickActions.notApplicable.message,
      meta: { answer_mode: "not_applicable", skip_reason: "not_applicable" },
    },
    {
      key: "ai_draft",
      label: messages.quickActions.aiDraft.label,
      sub: messages.quickActions.aiDraft.sub,
      message: messages.quickActions.aiDraft.message,
      meta: { answer_mode: "ai_draft" },
    },
  ] as const;

  const handleQuickAction = useCallback(
    async (action: (typeof quickActions)[number]) => {
      if (!onSend || isStreaming) {
        return;
      }
      const result = await onSend(action.message, action.meta);
      if (result !== false) {
        setMessage("");
        setAreQuickActionsOpen(false);
      }
    },
    [isStreaming, onSend]
  );

  useEffect(() => {
    resizeTextarea();
  }, [message, resizeTextarea]);

  const handleEnterToSendChange = useCallback((nextValue: boolean) => {
    setEnterToSend(nextValue);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ENTER_TO_SEND_KEY, nextValue ? "1" : "0");
    }
  }, []);

  const stopControl =
    isStreaming && onCancelStream ? (
      <Button
        type="button"
        variant="secondary"
        className="composer__cancel"
        onClick={onCancelStream}
        aria-label={messages.stopAriaLabel}
      >
        <Square className="h-4 w-4" />
        {messages.stopButton}
      </Button>
    ) : null;

  if (isReportStage) {
    const reportStatus = reportJobStatus?.status ?? null;
    const isReportPreparing =
      reportStatus === "queued" ||
      reportStatus === "running" ||
      reportStatus === "finalizing";
    const isReportRetryNeeded =
      reportStatus === "failed" || reportStatus === "stale";
    const isReportComplete = reportStatus === "ready";
    const buttonLabel = requiresVerification
      ? messages.reportStage.verifyEmailButton
      : isReportStatusUnavailable
      ? messages.reportStage.unavailableButton
      : isReportPreparing
      ? messages.reportStage.preparingButton
      : isReportRetryNeeded
      ? messages.reportStage.retryButton
      : isStageConfirming
      ? messages.reportStage.generatingButton
      : isReportComplete
      ? messages.reportStage.readyButton
      : messages.reportStage.defaultButton;
    const helperText = requiresVerification
      ? messages.reportStage.verifyEmailHelper
      : isReportStatusUnavailable
      ? messages.reportStage.unavailableHelper
      : isReportPreparing
      ? messages.reportStage.preparingHelper
      : isReportRetryNeeded
      ? messages.reportStage.retryHelper
      : isReportComplete
      ? messages.reportStage.readyHelper
      : messages.reportStage.defaultHelper;
    return (
      <div className="composer" aria-label={messages.reportStageAriaLabel}>
        <div className="composer__row flex-col items-stretch gap-3">
          <span className="text-sm text-muted-foreground">
            {helperText}
          </span>
          {stopControl}
          <Button
            type="button"
            size="lg"
            className="composer__submit w-full text-lg font-semibold shadow-lg transition-all hover:scale-[1.02]"
            onClick={onGenerateReport}
            disabled={
              isStreaming ||
              isStageConfirming ||
              !onGenerateReport ||
              requiresVerification
            }
          >
            <Sparkles className="mr-2 h-5 w-5" />
            {buttonLabel}
          </Button>
        </div>
      </div>
    );
  }

  if (isStageComplete) {
    const buttonLabel = requiresVerification
      ? messages.stageComplete.verifyEmailButton
      : isStageConfirming
      ? messages.stageComplete.preparingButton
      : messages.stageComplete.defaultButton;
    const helperText = requiresVerification
      ? messages.stageComplete.verifyEmailHelper
      : messages.stageComplete.defaultHelper;
    return (
      <div className="composer" aria-label={messages.stageCompleteAriaLabel}>
        <div className="composer__row flex-col items-stretch gap-3">
          <span className="text-sm text-muted-foreground">
            {helperText}
          </span>
          {stopControl}
          <Button
            type="button"
            size="lg"
            className="composer__submit w-full text-lg font-semibold shadow-lg transition-all hover:scale-[1.02]"
            onClick={onStageGate}
            disabled={
              isStreaming ||
              isStageConfirming ||
              !onStageGate ||
              requiresVerification
            }
          >
            <Sparkles className="mr-2 h-5 w-5" />
            {buttonLabel}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form className="composer" aria-label="Send a message" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="message">
        {messages.messageLabel}
      </label>
      {areQuickActionsOpen ? (
        <div
          id={quickActionsId}
          className="composer__quick-options"
          aria-label={messages.quickActionsAriaLabel}
        >
          {quickActions.map((action) => (
            <Button
              key={action.key}
              type="button"
              variant="ghost"
              size="sm"
              className="composer__quick-option"
              onClick={() => handleQuickAction(action)}
              disabled={isStreaming || !onSend}
            >
              <span className="composer__quick-option-label">
                <span>{action.label}</span>
                <span className="composer__quick-option-sub">{action.sub}</span>
              </span>
            </Button>
          ))}
        </div>
      ) : null}
      <div className="composer__row">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="composer__options-toggle"
          aria-label={messages.quickActionsToggle}
          aria-expanded={areQuickActionsOpen}
          aria-controls={quickActionsId}
          title={messages.quickActionsToggle}
          onClick={() => setAreQuickActionsOpen((value) => !value)}
          disabled={isStreaming || !onSend}
        >
          <MoreHorizontal className="composer__options-icon" aria-hidden="true" />
        </Button>
        <textarea
          id="message"
          className="textarea composer__input"
          rows={1}
          ref={textareaRef}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={messages.placeholder}
        />
        {!isStreaming ? (
          <Button
            type="submit"
            className="composer__submit"
            aria-label={messages.sendAriaLabel}
          >
            {messages.sendButton}
          </Button>
        ) : null}
        {stopControl}
      </div>
      <div className="composer__settings">
        <label className="composer__enter-toggle">
          <input
            type="checkbox"
            className="composer__enter-toggle-input"
            checked={enterToSend}
            onChange={(event) => handleEnterToSendChange(event.target.checked)}
          />
          <span className="composer__enter-toggle-track" aria-hidden="true" />
          <span>{messages.enterToSendLabel}</span>
        </label>
      </div>
    </form>
  );
}
