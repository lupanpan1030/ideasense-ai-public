import { apiClient } from "@/lib/api/client";
import { normalizeProjectId } from "@/features/projects/project-id";
import { normalizeContextVersion } from "./context-refresh";
import { PendingConfirmSnapshot } from "./pending-confirm-types";

type PendingConfirmResponse = {
  project_id?: unknown;
  pending_confirm?: unknown;
  updated_at?: unknown;
  context_version?: unknown;
};

const DEFAULT_CONTEXT_VERSION = 0;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isPlainRecord = (value: unknown): value is Record<string, unknown> =>
  isRecord(value) && !Array.isArray(value);

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const normalizePendingConfirmSnapshot = (
  payload: unknown,
  fallbackProjectId: string
): PendingConfirmSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as PendingConfirmResponse;
  const projectId =
    normalizeProjectId(toTrimmedString(response.project_id)) ??
    normalizeProjectId(fallbackProjectId);
  if (!projectId) {
    return null;
  }

  const pendingConfirm = isPlainRecord(response.pending_confirm)
    ? (response.pending_confirm as Record<string, unknown>)
    : {};
  const updatedAt = toTrimmedString(response.updated_at);
  if (!updatedAt) {
    return null;
  }
  const contextVersion =
    normalizeContextVersion(response.context_version) ?? DEFAULT_CONTEXT_VERSION;

  return {
    projectId,
    pendingConfirm,
    updatedAt,
    contextVersion,
  };
};

export async function fetchPendingConfirm(
  projectId: string,
  options: { signal?: AbortSignal } = {}
): Promise<PendingConfirmSnapshot> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.fetchJson<unknown>(
    `/projects/${normalizedProjectId}/context/pending`,
    {
      signal: options.signal,
    }
  );
  const normalized = normalizePendingConfirmSnapshot(
    response,
    normalizedProjectId
  );
  if (!normalized) {
    throw new Error("Invalid pending confirm payload.");
  }
  return normalized;
}

type ResolvePendingConfirmPayload = {
  acceptPaths: string[];
  rejectPaths: string[];
  clientContextVersion: number | null;
};

export async function resolvePendingConfirm(
  projectId: string,
  payload: ResolvePendingConfirmPayload
): Promise<PendingConfirmSnapshot> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.postJson<unknown>(
    `/projects/${normalizedProjectId}/context/pending/resolve`,
    {
      accept_paths: payload.acceptPaths,
      reject_paths: payload.rejectPaths,
      client_context_version: payload.clientContextVersion,
    }
  );
  const normalized = normalizePendingConfirmSnapshot(
    response,
    normalizedProjectId
  );
  if (!normalized) {
    throw new Error("Invalid pending confirm payload.");
  }
  return normalized;
}

type UpdatePendingConfirmPayload = {
  updates: Record<string, unknown>;
  clientContextVersion: number | null;
};

export async function updatePendingConfirm(
  projectId: string,
  payload: UpdatePendingConfirmPayload
): Promise<PendingConfirmSnapshot> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.postJson<unknown>(
    `/projects/${normalizedProjectId}/context/pending`,
    {
      updates: payload.updates,
      client_context_version: payload.clientContextVersion,
    },
    { method: "PATCH" }
  );
  const normalized = normalizePendingConfirmSnapshot(
    response,
    normalizedProjectId
  );
  if (!normalized) {
    throw new Error("Invalid pending confirm payload.");
  }
  return normalized;
}
