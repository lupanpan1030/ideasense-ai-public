"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, RefObject, SetStateAction } from "react";
import { fetchConversationHistory } from "./chat-history";
import { ChatMessage } from "./chat-state";
import type { AppLocale } from "@/lib/i18n/config";
import {
  mergeLatestMessages,
  mergeOlderMessages,
  resolveHistoryError,
} from "./chat-thread-utils";

type UseChatHistoryOptions = {
  projectId: string;
  outputLocale: AppLocale;
  onFirstUserMessage?: () => void;
};

type UseChatHistoryResult = {
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  isLoading: boolean;
  isLoadingMore: boolean;
  historyError: string | null;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  notifyHasUserMessage: (nextMessages: ChatMessage[]) => void;
  setShouldAutoScroll: (value: boolean) => void;
  stopHistoryLoad: () => void;
  refreshHistory: () => Promise<void>;
  handleScroll: () => void;
};

const HISTORY_PAGE_SIZE = 30;
const SCROLL_TOP_THRESHOLD = 32;
const SCROLL_BOTTOM_THRESHOLD = 120;
const SERVER_ID_PREFIX = "server-";

const resolveServerId = (value: string): string | null => {
  if (!value.startsWith(SERVER_ID_PREFIX)) {
    return null;
  }
  const raw = value.slice(SERVER_ID_PREFIX.length).trim();
  return raw ? raw : null;
};

export function useChatHistory({
  projectId,
  outputLocale,
  onFirstUserMessage,
}: UseChatHistoryOptions): UseChatHistoryResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const historyAbortRef = useRef<AbortController | null>(null);
  const historyRequestIdRef = useRef(0);
  const isMountedRef = useRef(true);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const hasUserMessageRef = useRef(false);

  const notifyHasUserMessage = useCallback(
    (nextMessages: ChatMessage[]) => {
      if (hasUserMessageRef.current) {
        return;
      }
      const hasUser = nextMessages.some((message) => message.role === "user");
      if (hasUser) {
        hasUserMessageRef.current = true;
        onFirstUserMessage?.();
      }
    },
    [onFirstUserMessage]
  );

  const setShouldAutoScroll = useCallback((value: boolean) => {
    shouldAutoScrollRef.current = value;
  }, []);

  const stopHistoryLoad = useCallback(() => {
    if (historyAbortRef.current) {
      historyAbortRef.current.abort();
      historyAbortRef.current = null;
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopHistoryLoad();
    };
  }, [stopHistoryLoad]);

  useEffect(() => {
    stopHistoryLoad();
    setMessages([]);
    setIsLoading(true);
    setIsLoadingMore(false);
    setHasMoreHistory(true);
    setHistoryError(null);
    shouldAutoScrollRef.current = true;
    hasUserMessageRef.current = false;
  }, [outputLocale, projectId, stopHistoryLoad]);

  const scrollToBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }, []);

  const isNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return true;
    }
    return (
      container.scrollHeight - container.scrollTop - container.clientHeight <
      SCROLL_BOTTOM_THRESHOLD
    );
  }, []);

  const loadInitialHistory = useCallback(async () => {
    const requestId = historyRequestIdRef.current + 1;
    historyRequestIdRef.current = requestId;
    const controller = new AbortController();
    stopHistoryLoad();
    historyAbortRef.current = controller;
    try {
      const history = await fetchConversationHistory(projectId, {
        signal: controller.signal,
        limit: HISTORY_PAGE_SIZE,
        outputLocale,
      });
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setMessages(history);
      setHistoryError(null);
      setHasMoreHistory(history.length === HISTORY_PAGE_SIZE);
      shouldAutoScrollRef.current = true;
      notifyHasUserMessage(history);
    } catch (error) {
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setHistoryError(resolveHistoryError(error));
    } finally {
      if (historyAbortRef.current === controller) {
        historyAbortRef.current = null;
      }
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setIsLoading((prev) => (prev ? false : prev));
    }
  }, [notifyHasUserMessage, outputLocale, projectId, stopHistoryLoad]);

  const refreshHistory = useCallback(async () => {
    const requestId = historyRequestIdRef.current + 1;
    historyRequestIdRef.current = requestId;
    const controller = new AbortController();
    stopHistoryLoad();
    historyAbortRef.current = controller;
    try {
      const history = await fetchConversationHistory(projectId, {
        signal: controller.signal,
        limit: HISTORY_PAGE_SIZE,
        outputLocale,
      });
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setMessages((prev) => {
        const merged = mergeLatestMessages(prev, history);
        notifyHasUserMessage(merged);
        return merged;
      });
      setHistoryError(null);
      if (history.length < HISTORY_PAGE_SIZE) {
        setHasMoreHistory(false);
      }
    } catch (error) {
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setHistoryError(resolveHistoryError(error));
    } finally {
      if (historyAbortRef.current === controller) {
        historyAbortRef.current = null;
      }
    }
  }, [notifyHasUserMessage, outputLocale, projectId, stopHistoryLoad]);

  const loadOlderHistory = useCallback(async () => {
    if (isLoadingMore || !hasMoreHistory) {
      return;
    }
    const container = scrollContainerRef.current;
    const beforeMessage =
      messages.find(
        (message) => message.createdAt && resolveServerId(message.id)
      ) ?? messages.find((message) => message.createdAt);
    const before = beforeMessage?.createdAt ?? null;
    const beforeId = beforeMessage?.id
      ? resolveServerId(beforeMessage.id)
      : null;
    if (!before) {
      setHasMoreHistory(false);
      return;
    }
    const requestId = historyRequestIdRef.current + 1;
    historyRequestIdRef.current = requestId;
    const controller = new AbortController();
    stopHistoryLoad();
    historyAbortRef.current = controller;
    const previousScrollHeight = container?.scrollHeight ?? 0;
    const previousScrollTop = container?.scrollTop ?? 0;
    setIsLoadingMore(true);
    shouldAutoScrollRef.current = false;
    try {
      const history = await fetchConversationHistory(projectId, {
        signal: controller.signal,
        limit: HISTORY_PAGE_SIZE,
        before,
        beforeId: beforeId ?? undefined,
      });
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setMessages((prev) => {
        const merged = mergeOlderMessages(prev, history);
        notifyHasUserMessage(merged);
        return merged;
      });
      setHasMoreHistory(history.length === HISTORY_PAGE_SIZE);
    } catch (error) {
      if (
        !isMountedRef.current ||
        controller.signal.aborted ||
        historyRequestIdRef.current !== requestId
      ) {
        return;
      }
      setHistoryError(resolveHistoryError(error));
    } finally {
      if (historyAbortRef.current === controller) {
        historyAbortRef.current = null;
      }
      if (isMountedRef.current) {
        setIsLoadingMore(false);
      }
      if (container) {
        requestAnimationFrame(() => {
          const nextHeight = container.scrollHeight;
          container.scrollTop =
            previousScrollTop + (nextHeight - previousScrollHeight);
        });
      }
    }
  }, [hasMoreHistory, isLoadingMore, messages, notifyHasUserMessage, projectId, stopHistoryLoad]);

  useEffect(() => {
    void loadInitialHistory();
  }, [loadInitialHistory]);

  useEffect(() => {
    if (!messages.length) {
      return;
    }
    if (shouldAutoScrollRef.current || isNearBottom()) {
      scrollToBottom();
    }
  }, [messages, isNearBottom, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }
    shouldAutoScrollRef.current = isNearBottom();
    if (
      container.scrollTop <= SCROLL_TOP_THRESHOLD &&
      hasMoreHistory &&
      !isLoadingMore
    ) {
      void loadOlderHistory();
    }
  }, [hasMoreHistory, isLoadingMore, isNearBottom, loadOlderHistory]);

  return {
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
  };
}
