import { apiClient } from "@/lib/api/client";
import {
  getSafeErrorMessage,
  type SafeErrorMessages,
} from "@/lib/api/safe-error-message";

export type UserSettings = {
  email_notifications: boolean;
  weekly_summary: boolean;
  time_zone: string | null;
};

export type UserSettingsUpdate = Partial<UserSettings>;

export type UserProfileUpdate = {
  display_name: string | null;
};

export type UserProfileResponse = {
  id: string;
  email: string | null;
  display_name: string | null;
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

const toBoolean = (value: unknown, fallback: boolean): boolean =>
  typeof value === "boolean" ? value : fallback;

const normalizeUserSettings = (payload: unknown): UserSettings => {
  if (!isRecord(payload)) {
    throw new Error("Invalid user settings payload.");
  }
  return {
    email_notifications: toBoolean(payload.email_notifications, true),
    weekly_summary: toBoolean(payload.weekly_summary, true),
    time_zone: toOptionalString(payload.time_zone),
  };
};

const normalizeUserProfile = (payload: unknown): UserProfileResponse => {
  if (!isRecord(payload)) {
    throw new Error("Invalid user profile payload.");
  }
  const id = typeof payload.id === "string" ? payload.id : "";
  if (!id) {
    throw new Error("Invalid user profile payload.");
  }
  return {
    id,
    email: toOptionalString(payload.email),
    display_name: toOptionalString(payload.display_name),
  };
};

export const fetchUserSettings = async (): Promise<UserSettings> => {
  const response = await apiClient.fetchJson<unknown>("/user-settings");
  return normalizeUserSettings(response);
};

export const updateUserSettings = async (
  payload: UserSettingsUpdate
): Promise<UserSettings> => {
  const response = await apiClient.postJson<unknown>(
    "/user-settings",
    payload,
    { method: "PATCH" }
  );
  return normalizeUserSettings(response);
};

export const updateUserProfile = async (
  payload: UserProfileUpdate
): Promise<UserProfileResponse> => {
  const response = await apiClient.postJson<unknown>("/users/me", payload, {
    method: "PATCH",
  });
  return normalizeUserProfile(response);
};

const DEFAULT_USER_SETTINGS_ERROR_MESSAGES: SafeErrorMessages = {
    default: "Unable to update user settings.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "User settings are unavailable. Try again shortly.",
};

const DEFAULT_USER_PROFILE_ERROR_MESSAGES: SafeErrorMessages = {
    default: "Unable to update profile.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Profile updates are unavailable. Try again shortly.",
};

export const getUserSettingsErrorMessage = (
  error: unknown,
  messages: SafeErrorMessages = DEFAULT_USER_SETTINGS_ERROR_MESSAGES
): string => getSafeErrorMessage(error, messages);

export const getUserProfileErrorMessage = (
  error: unknown,
  messages: SafeErrorMessages = DEFAULT_USER_PROFILE_ERROR_MESSAGES
): string => getSafeErrorMessage(error, messages);
