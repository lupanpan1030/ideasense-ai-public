import { emitChatControl, ChatControlPayload } from "./control-channel";
import { buildApiUrl, emitUnauthorizedEvent } from "../../lib/api/client";
import { getSafeResponseErrorMessage } from "@/lib/api/safe-error-message";
import { orgStorage } from "../../lib/storage/org";
import { tokenStorage } from "../../lib/storage/token";
import { normalizeAppLocale, type AppLocale } from "@/lib/i18n/config";

type ControlEmitter = (payload: ChatControlPayload) => void;

type Logger = Pick<Console, "warn">;

const DEFAULT_LOGGER: Logger = console;
const STREAM_IDLE_TIMEOUT_MS = 45_000;
const STREAM_IDLE_TIMEOUT_MESSAGE =
  "Chat stream stalled. Stop and try again.";

type SseEvent = {
  event: string;
  data: string;
};

type ChatStreamHandlers = {
  onToken?: (delta: string) => void;
  onStatus?: (payload: Record<string, unknown>) => void;
  onDone?: (payload: unknown) => void;
  onError?: (payload: unknown) => void;
  onMeta?: (payload: Record<string, unknown>) => void;
  onStageComplete?: (payload: Record<string, unknown>) => void;
  onQuestionMeta?: (payload: Record<string, unknown>) => void;
  emitControl?: ControlEmitter;
  emitMeta?: ControlEmitter;
  logger?: Logger;
};

const parseSseBlock = (block: string): SseEvent | null => {
  const lines = block.split(/\r?\n/);
  let eventName = "";
  const dataLines: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  return { event: eventName, data: dataLines.join("\n") };
};

const safeJsonParse = (raw: string, logger: Logger): unknown => {
  try {
    return JSON.parse(raw);
  } catch (error) {
    logger.warn("Failed to parse SSE JSON payload.", error);
    return null;
  }
};

const safeJsonParseSilent = (raw: string): unknown => {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

const resolveStreamStartError = async (
  response: Response
): Promise<string> => {
  return getSafeResponseErrorMessage(response, {
    accessDenied: "You do not have access to this chat.",
    default: "Failed to start chat stream.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Chat service is unavailable. Try again shortly.",
  });
};

const resolveControlType = (payload: Record<string, unknown>): string => {
  const rawType = payload.type;
  if (typeof rawType === "string") {
    const trimmed = rawType.trim();
    if (trimmed) {
      return trimmed;
    }
  }
  return "control";
};

const parseControlPayload = (
  rawData: string,
  logger: Logger
): ChatControlPayload | null => {
  const parsed = safeJsonParse(rawData, logger);
  if (!parsed || typeof parsed !== "object") {
    return null;
  }
  const payload = parsed as Record<string, unknown>;
  return { ...payload, type: resolveControlType(payload) } as ChatControlPayload;
};

export const handleSseControlEvent = (
  rawData: string,
  emitControl: ControlEmitter,
  logger: Logger = DEFAULT_LOGGER
): boolean => {
  const parsed = parseControlPayload(rawData, logger);
  if (!parsed) {
    return false;
  }
  emitControl(parsed);
  return true;
};

const dispatchControlEvent = (
  rawData: string,
  handlers: ChatStreamHandlers
): void => {
  const logger = handlers.logger ?? DEFAULT_LOGGER;
  const payload = parseControlPayload(rawData, logger);
  if (!payload) {
    return;
  }
  (handlers.emitControl ?? emitChatControl)(payload);
  if (payload.type === "stage_complete") {
    handlers.onStageComplete?.(payload);
  }
};

const normalizeProjectIdValue = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const buildMetaPayload = (
  payload: Record<string, unknown>,
  projectId?: string
): ChatControlPayload => {
  const metaPayload: ChatControlPayload = { ...payload, type: "meta" };
  const resolvedProjectId = normalizeProjectIdValue(metaPayload.project_id);
  if (resolvedProjectId) {
    metaPayload.project_id = resolvedProjectId;
    return metaPayload;
  }
  if (projectId) {
    metaPayload.project_id = projectId;
  }
  return metaPayload;
};

export const dispatchSseEvent = (
  event: SseEvent,
  handlers: ChatStreamHandlers,
  projectId?: string
): void => {
  const logger = handlers.logger ?? DEFAULT_LOGGER;
  if (event.event === "control") {
    dispatchControlEvent(event.data, handlers);
    return;
  }

  if (event.event === "stage_complete") {
    const payload = safeJsonParse(event.data, logger);
    if (payload && typeof payload === "object") {
      handlers.onStageComplete?.(payload as Record<string, unknown>);
    }
    return;
  }

  if (event.event === "stage_gate_ready") {
    const payload = safeJsonParse(event.data, logger);
    if (payload && typeof payload === "object") {
      handlers.onStageComplete?.(payload as Record<string, unknown>);
    }
    return;
  }

  if (event.event === "question_meta") {
    const payload = safeJsonParse(event.data, logger);
    if (payload && typeof payload === "object") {
      handlers.onQuestionMeta?.(payload as Record<string, unknown>);
    }
    return;
  }

  if (
    event.event === "assistant_first_token" ||
    event.event === "assistant_done" ||
    event.event === "extract_queued"
  ) {
    const payload = safeJsonParse(event.data, logger);
    const recordPayload =
      payload && typeof payload === "object"
        ? (payload as Record<string, unknown>)
        : {};
    const metaPayload = buildMetaPayload(
      { ...recordPayload, type: event.event },
      projectId
    );
    (handlers.emitMeta ?? handlers.emitControl ?? emitChatControl)(metaPayload);
    handlers.onMeta?.(metaPayload);
    return;
  }

  if (event.event === "token") {
    const payload = safeJsonParseSilent(event.data);
    if (payload && typeof payload === "object" && "delta" in payload) {
      const delta = (payload as { delta?: unknown }).delta;
      if (typeof delta === "string") {
        handlers.onToken?.(delta);
      }
    }
    return;
  }

  if (event.event === "status") {
    const payload = safeJsonParse(event.data, logger);
    if (payload && typeof payload === "object") {
      handlers.onStatus?.(payload as Record<string, unknown>);
    }
    return;
  }

  if (event.event === "done") {
    handlers.onDone?.(safeJsonParseSilent(event.data));
    return;
  }

  if (event.event === "meta") {
    const payload = safeJsonParse(event.data, logger);
    const recordPayload =
      payload && typeof payload === "object"
        ? (payload as Record<string, unknown>)
        : {};
    const metaPayload = buildMetaPayload(recordPayload, projectId);
    (handlers.emitMeta ?? handlers.emitControl ?? emitChatControl)(metaPayload);
    if (payload && typeof payload === "object") {
      handlers.onMeta?.(recordPayload);
    }
    return;
  }

  if (event.event === "error") {
    handlers.onError?.(safeJsonParseSilent(event.data));
  }
};

export async function streamChatResponse(
  projectId: string,
  message: string,
  handlers: ChatStreamHandlers = {},
  options: {
    signal?: AbortSignal;
    messageMeta?: Record<string, unknown>;
    clientMessageId?: string;
    outputLocale?: AppLocale;
    idleTimeoutMs?: number;
  } = {}
): Promise<void> {
  const token = tokenStorage.getToken();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const orgId = orgStorage.getOrgId();
  if (orgId) {
    headers.set("X-Org-ID", orgId);
  }

  const response = await fetch(buildApiUrl("/chat/stream"), {
    method: "POST",
    headers,
    body: JSON.stringify({
      project_id: projectId,
      message,
      message_meta: options.messageMeta ?? undefined,
      client_message_id: options.clientMessageId ?? undefined,
      output_locale: normalizeAppLocale(options.outputLocale),
    }),
    signal: options.signal,
  });

  if (!response.ok) {
    const message = await resolveStreamStartError(response);
    if (response.status === 401) {
      tokenStorage.clearToken();
      emitUnauthorizedEvent(new Error(message));
    }
    throw new Error(message);
  }

  const refreshedToken = response.headers.get("x-auth-token");
  if (refreshedToken) {
    tokenStorage.setTokenPreservingPersistence(refreshedToken);
  }

  if (!response.body) {
    throw new Error("Chat stream unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const idleTimeoutMs = options.idleTimeoutMs ?? STREAM_IDLE_TIMEOUT_MS;
  let buffer = "";

  while (true) {
    const { value, done } = await readStreamChunk(reader, idleTimeoutMs);
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = parseSseBlock(chunk);
      if (event) {
        dispatchSseEvent(event, handlers, projectId);
      }
    }
  }

  if (buffer.trim()) {
    const event = parseSseBlock(buffer);
    if (event) {
      dispatchSseEvent(event, handlers, projectId);
    }
  }
}

const readStreamChunk = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  idleTimeoutMs: number
): Promise<ReadableStreamReadResult<Uint8Array>> => {
  if (idleTimeoutMs <= 0) {
    return reader.read();
  }

  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      void reader.cancel(STREAM_IDLE_TIMEOUT_MESSAGE).catch(() => {});
      reject(new Error(STREAM_IDLE_TIMEOUT_MESSAGE));
    }, idleTimeoutMs);
  });

  try {
    return await Promise.race([reader.read(), timeout]);
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
};
