export type ChatMessageRole = "user" | "assistant" | "system";

export type ChatMessageStatus = "streaming" | "complete" | "error";

export type ChatMessage = {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt: string | null;
  stage?: string | null;
  meta?: Record<string, unknown> | null;
  status?: ChatMessageStatus;
  streamStatus?: string | null;
};

export const normalizeChatRole = (value: unknown): ChatMessageRole | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) {
    return null;
  }
  if (trimmed === "user") {
    return "user";
  }
  if (trimmed === "assistant" || trimmed === "ai") {
    return "assistant";
  }
  if (trimmed === "system") {
    return "system";
  }
  return null;
};

export const createLocalMessage = ({
  id,
  role,
  content,
  createdAt = null,
  stage = null,
  meta = null,
  status,
}: {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt?: string | null;
  stage?: string | null;
  meta?: Record<string, unknown> | null;
  status?: ChatMessageStatus;
}): ChatMessage => ({
  id,
  role,
  content,
  createdAt,
  stage,
  meta,
  status,
});

export const appendMessageDelta = (
  messages: ChatMessage[],
  messageId: string,
  delta: string
): ChatMessage[] => {
  if (!delta) {
    return messages;
  }
  let didUpdate = false;
  const updated = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    didUpdate = true;
    return { ...message, content: `${message.content}${delta}` };
  });
  return didUpdate ? updated : messages;
};

export const updateMessageStatus = (
  messages: ChatMessage[],
  messageId: string,
  status: ChatMessageStatus
): ChatMessage[] => {
  let didUpdate = false;
  const updated = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    didUpdate = true;
    return { ...message, status };
  });
  return didUpdate ? updated : messages;
};

export const updateMessageStreamStatus = (
  messages: ChatMessage[],
  messageId: string,
  streamStatus: string | null
): ChatMessage[] => {
  let didUpdate = false;
  const updated = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    didUpdate = true;
    return { ...message, streamStatus };
  });
  return didUpdate ? updated : messages;
};
