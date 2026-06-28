import type { ChatControlPayload } from "@/features/chat/control-channel";

const POLL_BACKOFF_BASE_MS = 12000;
const POLL_BACKOFF_MAX_MS = 60000;

export const normalizeContextVersion = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
};

export const shouldRefreshContext = (
  currentVersion: number | null,
  incomingVersion: unknown
): boolean => {
  const nextVersion = normalizeContextVersion(incomingVersion);
  if (nextVersion === null) {
    return false;
  }
  if (currentVersion === null) {
    return true;
  }
  return nextVersion !== currentVersion;
};

export const resolvePollBackoffMs = (failureCount: number): number => {
  if (!Number.isFinite(failureCount) || failureCount <= 0) {
    return 0;
  }
  const multiplier = 2 ** Math.min(failureCount - 1, 3);
  return Math.min(POLL_BACKOFF_BASE_MS * multiplier, POLL_BACKOFF_MAX_MS);
};

export const shouldRunPollRefresh = ({
  isDocumentHidden,
  inFlight,
  now,
  nextRetryAt,
}: {
  isDocumentHidden: boolean;
  inFlight: boolean;
  now: number;
  nextRetryAt: number;
}): boolean => {
  if (isDocumentHidden || inFlight) {
    return false;
  }
  return nextRetryAt <= 0 || now >= nextRetryAt;
};

type ChatControlRefreshOptions = {
  payload: ChatControlPayload;
  projectId: string;
  currentVersion: number | null;
  onRefresh: () => void;
  onUpdateLatestVersion?: (version: number) => void;
};

export const handleChatControlRefresh = ({
  payload,
  projectId,
  currentVersion,
  onRefresh,
  onUpdateLatestVersion,
}: ChatControlRefreshOptions): boolean => {
  if (payload.project_id && payload.project_id !== projectId) {
    return false;
  }

  const incomingVersion = normalizeContextVersion(payload.context_version);
  if (incomingVersion !== null) {
    onUpdateLatestVersion?.(incomingVersion);
  }

  const normalizedType =
    typeof payload.type === "string" ? payload.type.trim().toLowerCase() : "";
  const forceRefresh =
    normalizedType === "stage_complete" || normalizedType === "stage_confirmed";
  if (forceRefresh) {
    onRefresh();
    return true;
  }

  const shouldRefresh =
    normalizedType === "meta"
      ? incomingVersion === null
        ? true
        : shouldRefreshContext(currentVersion, incomingVersion)
      : shouldRefreshContext(currentVersion, payload.context_version);

  if (!shouldRefresh) {
    return false;
  }

  onRefresh();
  return true;
};
