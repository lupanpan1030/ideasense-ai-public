import { ApiError, apiClient } from "@/lib/api/client";

export type PlatformSettingEntry = {
  key: string;
  value: unknown;
  updatedBy: string | null;
  updatedByEmail: string | null;
  updatedByName: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};

export type PlatformSettingsPayload = {
  settings?: Record<string, unknown>;
  remove?: string[];
};

export type PlatformSettingsResponse = {
  settings: Record<string, unknown>;
  entries: PlatformSettingEntry[];
};

export type PlatformSettingsErrorMessages = {
  accessDenied: string;
  default: string;
  sessionExpired: string;
  unavailable: string;
};

const DEFAULT_PLATFORM_SETTINGS_ERROR_MESSAGES: PlatformSettingsErrorMessages = {
  accessDenied: "You do not have access to manage platform settings.",
  default: "Unable to update platform settings.",
  sessionExpired: "Your session expired. Please sign in again.",
  unavailable: "Platform settings are unavailable. Try again shortly.",
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toOptionalString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toEntry = (value: unknown): PlatformSettingEntry => {
  if (!isRecord(value)) {
    throw new Error("Invalid platform setting entry.");
  }
  const key = toOptionalString(value.key) ?? "";
  if (!key) {
    throw new Error("Platform setting entry missing key.");
  }
  return {
    key,
    value: value.value ?? null,
    updatedBy: toOptionalString(value.updated_by),
    updatedByEmail: toOptionalString(value.updated_by_email),
    updatedByName: toOptionalString(value.updated_by_name),
    createdAt: toOptionalString(value.created_at),
    updatedAt: toOptionalString(value.updated_at),
  };
};

const normalizeResponse = (payload: unknown): PlatformSettingsResponse => {
  if (!isRecord(payload)) {
    throw new Error("Invalid platform settings payload.");
  }
  const settings = isRecord(payload.settings) ? payload.settings : {};
  const entries = Array.isArray(payload.entries)
    ? payload.entries.map(toEntry)
    : [];
  return { settings, entries };
};

export const fetchPlatformSettings = async (): Promise<PlatformSettingsResponse> => {
  const response = await apiClient.fetchJson<unknown>("/platform-api/settings");
  return normalizeResponse(response);
};

export const updatePlatformSettings = async (
  payload: PlatformSettingsPayload
): Promise<PlatformSettingsResponse> => {
  const response = await apiClient.postJson<unknown>(
    "/platform-api/settings",
    payload,
    { method: "PATCH" }
  );
  return normalizeResponse(response);
};

export const getPlatformSettingsErrorMessage = (
  error: unknown,
  messages: PlatformSettingsErrorMessages = DEFAULT_PLATFORM_SETTINGS_ERROR_MESSAGES
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.sessionExpired;
    }
    if (error.status === 403) {
      return messages.accessDenied;
    }
    if (error.status >= 500) {
      return messages.unavailable;
    }
  }
  return messages.default;
};
