import { ChatMessage } from "./chat-state";

export const resolveHistoryError = (error: unknown): string => {
  void error;
  return "Conversation history is unavailable.";
};

export const resolveStreamError = (payload: unknown): string => {
  void payload;
  return "Chat stream failed. Please try again.";
};

export const resolveDoneError = (payload: unknown): string | null => {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const status = (payload as { status?: unknown }).status;
  if (status !== "error") {
    return null;
  }
  return "Chat response ended with an error.";
};

export const resolveRequestError = (error: unknown): string => {
  void error;
  return "Chat request failed. Please try again.";
};

export const mergeLatestMessages = (
  previous: ChatMessage[],
  latest: ChatMessage[]
): ChatMessage[] => {
  if (!previous.length) {
    return latest;
  }
  if (!latest.length) {
    return previous;
  }
  const latestIds = new Set(latest.map((message) => message.id));
  const latestKeys = new Set(
    latest.map((message) => `${message.role}|${message.content}`)
  );

  const merged = previous.filter((message) => {
    if (latestIds.has(message.id)) {
      return false;
    }
    const isLocal =
      message.id.startsWith("user-") || message.id.startsWith("assistant-");
    if (isLocal && latestKeys.has(`${message.role}|${message.content}`)) {
      return false;
    }
    return true;
  });

  return [...merged, ...latest];
};

export const mergeOlderMessages = (
  previous: ChatMessage[],
  older: ChatMessage[]
): ChatMessage[] => {
  if (!older.length) {
    return previous;
  }
  const existingIds = new Set(previous.map((message) => message.id));
  const deduped = older.filter((message) => !existingIds.has(message.id));
  return [...deduped, ...previous];
};

export const resolveLatestMessageAt = (
  items: ChatMessage[]
): string | null => {
  let latestAt: string | null = null;
  let latestTime = 0;
  for (const message of items) {
    if (!message.createdAt) {
      continue;
    }
    const timestamp = Date.parse(message.createdAt);
    if (Number.isNaN(timestamp)) {
      continue;
    }
    if (!latestAt || timestamp > latestTime) {
      latestAt = message.createdAt;
      latestTime = timestamp;
    }
  }
  return latestAt;
};
