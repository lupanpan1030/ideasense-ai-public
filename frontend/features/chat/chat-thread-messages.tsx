"use client";

import { Fragment, type RefObject, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessage } from "./chat-state";
import {
  STAGE_LABELS,
  renderMarkdown,
} from "@/features/assessments/components/stage-gate-utils";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

const GLOSSARY: Record<string, string> = {
  TAM: "Total Addressable Market: the full market size if everyone who could buy does buy.",
  SAM: "Serviceable Available Market: the portion of TAM you can realistically target.",
  SOM: "Serviceable Obtainable Market: the share of SAM you can capture in the near term.",
  CAC: "Customer Acquisition Cost: how much it costs to acquire one paying customer.",
  LTV: "Lifetime Value: total value a customer generates over their lifetime.",
  GM: "Gross Margin: revenue left after direct costs (as a percentage).",
  ARPA: "Average Revenue Per Account.",
  ARPU: "Average Revenue Per User.",
  ARR: "Annual Recurring Revenue.",
  MRR: "Monthly Recurring Revenue.",
  NRR: "Net Revenue Retention: expansion and churn impact on recurring revenue.",
  ROI: "Return on Investment.",
  MOM: "Month-over-Month growth.",
  QOQ: "Quarter-over-Quarter growth.",
};

const GLOSSARY_TERMS = Object.keys(GLOSSARY).sort(
  (a, b) => b.length - a.length
);
const GLOSSARY_REGEX = new RegExp(
  `(^|[^A-Z0-9])(${GLOSSARY_TERMS.join("|")})(?![A-Z0-9])`,
  "g"
);
const GLOSSARY_TOKEN_REGEX = /\[\[GLOSSARY:([A-Z0-9]+)\]\]/g;

const escapeAttribute = (value: string): string =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const injectGlossaryTokens = (value: string): string =>
  value.replace(GLOSSARY_REGEX, (match, prefix, term: string) => {
    if (prefix === "[" || prefix === "`") {
      return match;
    }
    return `${prefix}[[GLOSSARY:${term}]]`;
  });

const applyGlossaryTokens = (html: string): string =>
  html.replace(GLOSSARY_TOKEN_REGEX, (match, term: string) => {
    const desc = GLOSSARY[term];
    if (!desc) {
      return term;
    }
    const escapedDesc = escapeAttribute(desc);
    return `<span class="glossary-term" data-term="${term}" data-desc="${escapedDesc}" tabindex="0">${term}</span>`;
  });

const renderMarkdownWithGlossary = (value: string): string => {
  const tokenized = injectGlossaryTokens(value);
  const html = renderMarkdown(tokenized);
  return applyGlossaryTokens(html);
};

type ChatThreadMessagesProps = {
  messages: ChatMessage[];
  isLoading: boolean;
  isLoadingMore: boolean;
  isStreaming?: boolean;
  historyError: string | null;
  streamError: string | null;
  onRetryHistory: () => void;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
  onQuickOptionSelect?: (
    message: string,
    meta?: Record<string, unknown>
  ) => void | Promise<void>;
};

type QuestionMetaPayload = {
  question_id?: unknown;
  stage?: unknown;
  variant?: unknown;
  ui?: unknown;
};

type QuestionUiOption = {
  key?: unknown;
  label?: unknown;
  value?: unknown;
};

type LocalizedOptionText = {
  en?: string;
  zh?: string;
};

const normalizeOptionText = (value: string): string =>
  value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/[\u3002\uFF0E.!?]+$/g, "");

const stripOptionPrefix = (value: string): string =>
  value
    .replace(/^\s*[-*]\s+/, "")
    .replace(/^\s*\u2022\s+/, "")
    .replace(/^\s*[a-c1-3][\).]\s+/i, "");

const resolveStageKey = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed.toLowerCase() : null;
};

const collectOptionStrings = (
  option: {
    label: string | LocalizedOptionText;
    value?: string | LocalizedOptionText;
  }
): string[] => {
  const results: string[] = [];
  const pushValue = (value?: string | LocalizedOptionText) => {
    if (!value) {
      return;
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) {
        results.push(trimmed);
      }
      return;
    }
    if (value.en && value.en.trim()) {
      results.push(value.en.trim());
    }
    if (value.zh && value.zh.trim()) {
      results.push(value.zh.trim());
    }
  };
  pushValue(option.label);
  pushValue(option.value);
  return results;
};

const stripQuickOptionContent = (
  content: string,
  options: {
    key: string;
    label: string | { en?: string; zh?: string };
    value?: string | { en?: string; zh?: string };
  }[]
): string => {
  if (!content.trim() || options.length === 0) {
    return content;
  }
  const normalizedOptions = new Set(
    options
      .flatMap((option) => collectOptionStrings(option))
      .map((text) => normalizeOptionText(text))
      .filter(Boolean)
  );
  if (!normalizedOptions.size) {
    return content;
  }
  const lines = content.split(/\r?\n/);
  const filtered: string[] = [];
  let lastBlank = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (!lastBlank) {
        filtered.push("");
        lastBlank = true;
      }
      continue;
    }
    const normalized = normalizeOptionText(stripOptionPrefix(line));
    if (normalizedOptions.has(normalized)) {
      continue;
    }
    filtered.push(line);
    lastBlank = false;
  }
  const nextContent = filtered.join("\n").trim();
  return nextContent ? nextContent : content;
};

const ROUTER_QUESTION_ID = "S3Q0";
// Keep legacy router options for stored assistant messages created
// before question_meta was persisted on the message payload.
const LEGACY_ROUTER_QUESTION_META: QuestionMetaPayload = {
  question_id: ROUTER_QUESTION_ID,
  stage: "tech",
  variant: "router",
  ui: {
    input_mode: "single_select_with_free_text",
    options: [
      {
        key: "pro",
        label: "I'm a developer or engineer",
        value: "I'm a developer or engineer",
      },
      {
        key: "mid",
        label: "I can follow roughly, but I'm not an expert",
        value: "I can follow roughly, but I'm not an expert",
      },
      {
        key: "lite",
        label: "I'm non-technical or I prefer plain language",
        value: "I'm non-technical or I prefer plain language",
      },
    ],
  },
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isLocalizedOptionText = (
  value: unknown
): value is LocalizedOptionText => {
  if (!isRecord(value)) {
    return false;
  }
  const en = value.en;
  const zh = value.zh;
  return (
    (en === undefined || typeof en === "string") &&
    (zh === undefined || typeof zh === "string")
  );
};

const normalizeOptionValue = (
  value: unknown
): string | LocalizedOptionText | null => {
  if (typeof value === "string") {
    return value;
  }
  if (isLocalizedOptionText(value)) {
    return value;
  }
  return null;
};

const normalizeQuestionMeta = (
  payload: unknown
): QuestionMetaPayload | null => {
  if (!isRecord(payload)) {
    return null;
  }
  return payload as QuestionMetaPayload;
};

const resolveLegacyQuestionMeta = (
  payload: unknown
): QuestionMetaPayload | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const questionId =
    typeof payload.question_id === "string"
      ? payload.question_id.trim().toLowerCase()
      : "";
  if (questionId === ROUTER_QUESTION_ID.toLowerCase()) {
    return LEGACY_ROUTER_QUESTION_META;
  }
  return null;
};

const resolveMessageQuestionMeta = (
  payload: unknown
): QuestionMetaPayload | null => {
  if (!isRecord(payload)) {
    return null;
  }
  return normalizeQuestionMeta(payload.question_meta) ?? resolveLegacyQuestionMeta(payload);
};

const normalizeQuickOptions = (
  payload: QuestionMetaPayload | null
): {
  key: string;
  label: string | { en?: string; zh?: string };
  value?: string | { en?: string; zh?: string };
}[] => {
  if (!payload) {
    return [];
  }
  const ui = payload.ui;
  if (!isRecord(ui)) {
    return [];
  }
  const inputMode = typeof ui.input_mode === "string" ? ui.input_mode : "";
  if (inputMode !== "single_select_with_free_text") {
    return [];
  }
  const rawOptions = Array.isArray(ui.options) ? ui.options : [];
  const normalized: {
    key: string;
    label: string | { en?: string; zh?: string };
    value?: string | { en?: string; zh?: string };
  }[] = [];

  for (const rawOption of rawOptions) {
    if (!isRecord(rawOption)) {
      continue;
    }
    const option = rawOption as QuestionUiOption;
    const key = typeof option.key === "string" ? option.key.trim() : "";
    if (!key) {
      continue;
    }
    const label = normalizeOptionValue(option.label);
    if (!label) {
      continue;
    }
    if (typeof label === "string" && !label.trim()) {
      continue;
    }
    const value = normalizeOptionValue(option.value);
    const nextOption: {
      key: string;
      label: string | LocalizedOptionText;
      value?: string | LocalizedOptionText;
    } = { key, label };
    if (value !== null) {
      nextOption.value = value;
    }
    normalized.push(nextOption);
  }

  return normalized;
};

export function ChatThreadMessages({
  messages,
  isLoading,
  isLoadingMore,
  isStreaming = false,
  historyError,
  streamError,
  onRetryHistory,
  scrollContainerRef,
  onScroll,
  onQuickOptionSelect,
}: ChatThreadMessagesProps) {
  const appMessages = useAppMessages();
  const locale = useAppLocale();
  const messagesText = appMessages.chatThread;
  const liveContextMessages = appMessages.liveContext;
  const stageOrder = new Map([
    ["problem", 1],
    ["market", 2],
    ["tech", 3],
    ["report", 4],
  ]);

  const resolveStageLabel = (stageKey: string) =>
    liveContextMessages.stageLabels[stageKey] ??
    STAGE_LABELS[stageKey] ??
    stageKey;

  const resolveDividerLabel = (stageKey: string) => {
    const label = resolveStageLabel(stageKey);
    const order = stageOrder.get(stageKey);
    const stageLabel = liveContextMessages.labels.stageFallback;
    return order
      ? `${stageLabel} ${order} · ${label}`
      : `${stageLabel} · ${label}`;
  };

  const resolveLocalizedText = useCallback(
    (value: string | { en?: string; zh?: string } | undefined): string => {
      if (!value) {
        return "";
      }
      if (typeof value === "string") {
        return value;
      }
      return value[locale] || value.en || value.zh || "";
    },
    [locale]
  );

  const renderOptionLabel = (
    value: string | { en?: string; zh?: string }
  ) => {
    if (typeof value === "string") {
      return <span>{value}</span>;
    }
    return <span>{value[locale] || value.en || value.zh || ""}</span>;
  };

  const { activeMessageId, activeOptions } = useMemo(() => {
    let candidateId: string | null = null;
    let candidateOptions: {
      key: string;
      label: string | { en?: string; zh?: string };
      value?: string | { en?: string; zh?: string };
    }[] = [];

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role !== "assistant") {
        continue;
      }
      if (!isRecord(message.meta)) {
        continue;
      }
      const questionMeta = resolveMessageQuestionMeta(message.meta);
      const options = normalizeQuickOptions(questionMeta);
      if (!options.length) {
        continue;
      }
      const hasUserAfter = messages
        .slice(index + 1)
        .some((item) => item.role === "user");
      if (!hasUserAfter) {
        candidateId = message.id;
        candidateOptions = options;
      }
      break;
    }

    return { activeMessageId: candidateId, activeOptions: candidateOptions };
  }, [messages]);

  const handleOptionSelect = useCallback(
    async (option: {
      key: string;
      label: string | { en?: string; zh?: string };
      value?: string | { en?: string; zh?: string };
    }) => {
      if (!onQuickOptionSelect || isStreaming) {
        return;
      }
      const resolved =
        resolveLocalizedText(option.value) ||
        resolveLocalizedText(option.label);
      if (!resolved) {
        return;
      }
      await onQuickOptionSelect(resolved, {
        selected_option_key: option.key,
      });
    },
    [isStreaming, onQuickOptionSelect, resolveLocalizedText]
  );

  const stageMeta = useMemo(() => {
    const stageKeys = messages.map((message) =>
      resolveStageKey(message.stage)
    );
    return stageKeys.map((stageKey, index) => {
      const previousStage =
        stageKeys
          .slice(0, index)
          .reverse()
          .find((value): value is string => Boolean(value)) ?? null;
      const showDivider =
        Boolean(stageKey) &&
        Boolean(previousStage) &&
        stageKey !== previousStage;
      return { stageKey, showDivider };
    });
  }, [messages]);
  return (
    <div
      ref={scrollContainerRef}
      className="chat-thread__messages"
      aria-live="polite"
      onScroll={onScroll}
    >
      {isLoadingMore ? (
        <div className="message-row message-row--system">
          <div className="message-bubble message-bubble--system">
            {messagesText.loadingEarlier}
          </div>
        </div>
      ) : null}
      {isLoading && messages.length === 0 ? (
        <div className="message-list">
          <Skeleton className="skeleton--line" />
          <Skeleton className="skeleton--line" />
          <Skeleton className="skeleton--line" />
        </div>
      ) : messages.length === 0 ? (
        <div className="message-row message-row--system">
          <div className="message-bubble message-bubble--system">
            {messagesText.empty}
          </div>
        </div>
      ) : (
        <div className="message-list">
          {messages.map((message, index) => {
            const statusLabel =
              message.status === "streaming"
                ? message.streamStatus || messagesText.typing
                : message.status === "error"
                  ? messagesText.error
                  : null;
            const isTyping = message.status === "streaming";
            const content = message.content || "";
            const messageMeta = isRecord(message.meta) ? message.meta : null;
            const questionMeta = messageMeta
              ? resolveMessageQuestionMeta(messageMeta)
              : null;
            const quickOptionsForMessage = normalizeQuickOptions(questionMeta);
            const contentForRender =
              message.role === "assistant" && quickOptionsForMessage.length
                ? stripQuickOptionContent(content, quickOptionsForMessage)
                : content;
            const renderedContent = contentForRender
              ? renderMarkdownWithGlossary(contentForRender)
              : "";
            const showStatus =
              statusLabel &&
              (message.status !== "streaming" || content.length === 0);
            const stageKey = stageMeta[index]?.stageKey ?? null;
            const showDivider = stageMeta[index]?.showDivider ?? false;
            return (
              <Fragment key={message.id}>
                {showDivider && stageKey ? (
                  <div className="message-stage-divider" role="separator">
                    <span className="message-stage-divider__label">
                      {resolveDividerLabel(stageKey)}
                    </span>
                  </div>
                ) : null}
                <div className={`message-row message-row--${message.role}`}>
                  {message.role !== "system" ? (
                    <span
                      className={`message-avatar message-avatar--${message.role}`}
                      aria-label={message.role}
                    >
                      {message.role === "user" ? "U" : "AI"}
                    </span>
                  ) : null}
                  <div className="message-stack">
                    <div
                      className={[
                        "message-bubble",
                        `message-bubble--${message.role}`,
                        message.status === "error" ? "message-bubble--error" : "",
                        isTyping ? "message-bubble--typing" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {renderedContent ? (
                        <div
                          className="message-content markdown-preview"
                          dangerouslySetInnerHTML={{ __html: renderedContent }}
                        />
                      ) : null}
                      {showStatus ? (
                        <span
                          className={[
                            "message-status",
                            isTyping ? "message-status--typing" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        >
                          {statusLabel}
                        </span>
                      ) : null}
                    </div>
                    {message.id === activeMessageId && activeOptions.length ? (
                      <div
                        className="message-quick-options"
                        aria-label={messagesText.quickOptionsAriaLabel}
                      >
                        {activeOptions.map((option) => (
                          <Button
                            key={option.key}
                            type="button"
                            size="sm"
                            variant="secondary"
                            className="message-quick-option"
                            onClick={() => handleOptionSelect(option)}
                            disabled={isStreaming}
                          >
                            {renderOptionLabel(option.label)}
                          </Button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </Fragment>
            );
          })}
        </div>
      )}

      {historyError ? (
        <div className="message-row message-row--system" role="alert">
          <div className="message-bubble message-bubble--alert">
            <div className="stack-sm">
              <span className="eyebrow">{messagesText.historyUnavailable}</span>
              <p>{historyError}</p>
              <Button type="button" size="sm" onClick={onRetryHistory}>
                {messagesText.retry}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {streamError ? (
        <div className="message-row message-row--system" role="alert">
          <div className="message-bubble message-bubble--alert">
            <div className="stack-sm">
              <span className="eyebrow">{messagesText.messageFailed}</span>
              <p>{streamError}</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
