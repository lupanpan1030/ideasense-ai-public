import { apiClient } from "@/lib/api/client";
import { normalizeProjectId } from "@/features/projects/project-id";
import { ChatMessage, normalizeChatRole } from "./chat-state";
import { normalizeAppLocale, type AppLocale } from "@/lib/i18n/config";

type ConversationMessage = {
  id?: unknown;
  role?: unknown;
  content?: unknown;
  created_at?: unknown;
  stage?: unknown;
  meta?: unknown;
};

type ConversationListResponse = {
  conversations?: unknown;
  messages?: unknown;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const normalizeStageValue = (value: unknown): string | null => {
  const trimmed = toTrimmedString(value);
  return trimmed ? trimmed.toLowerCase() : null;
};

const toConversationArray = (payload: unknown): unknown[] => {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (isRecord(payload)) {
    const response = payload as ConversationListResponse;
    if (Array.isArray(response.messages)) {
      return response.messages;
    }
    if (Array.isArray(response.conversations)) {
      return response.conversations;
    }
  }
  return [];
};

const resolveMessageId = (value: unknown, fallbackIndex: number): string => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `server-${value}`;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed) {
      return `server-${trimmed}`;
    }
  }
  return `server-${fallbackIndex}`;
};

const normalizeConversationMessage = (
  payload: unknown,
  index: number
): ChatMessage | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as ConversationMessage;
  const role = normalizeChatRole(response.role);
  if (!role) {
    return null;
  }

  const content = typeof response.content === "string" ? response.content : "";
  const createdAt = toTrimmedString(response.created_at);
  const stage = normalizeStageValue(response.stage);
  const meta = isRecord(response.meta) ? response.meta : null;

  return {
    id: resolveMessageId(response.id, index),
    role,
    content,
    createdAt,
    stage,
    meta,
    status: "complete",
  };
};

export async function fetchConversationHistory(
  projectId: string,
  options: {
    signal?: AbortSignal;
    limit?: number;
    before?: string;
    beforeId?: string;
    outputLocale?: AppLocale;
  } = {}
): Promise<ChatMessage[]> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const params = new URLSearchParams();
  if (typeof options.limit === "number") {
    params.set("limit", String(options.limit));
  }
  if (options.before) {
    params.set("before", options.before);
  }
  if (options.beforeId) {
    params.set("before_id", options.beforeId);
  }
  if (options.outputLocale) {
    params.set("output_locale", normalizeAppLocale(options.outputLocale));
  }
  const query = params.toString();
  const url = query
    ? `/projects/${normalizedProjectId}/conversations?${query}`
    : `/projects/${normalizedProjectId}/conversations`;

  const response = await apiClient.fetchJson<unknown>(
    url,
    { signal: options.signal }
  );
  const items = toConversationArray(response);
  if (
    !Array.isArray(response) &&
    !(isRecord(response) &&
      (Array.isArray(response.conversations) || Array.isArray(response.messages)))
  ) {
    throw new Error("Invalid conversation history payload.");
  }
  if (!items.length) {
    return [];
  }

  return items
    .map((item, index) => normalizeConversationMessage(item, index))
    .filter((item): item is ChatMessage => Boolean(item));
}
