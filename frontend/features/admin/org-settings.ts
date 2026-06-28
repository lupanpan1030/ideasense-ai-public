import { ApiError, apiClient } from "@/lib/api/client";

export type OrgSettings = Record<string, unknown>;
export type OrgSettingsUpdatePayload = {
  name?: string | null;
  settings: OrgSettings;
};

export type QuestionBankStatus = {
  bankKey: string;
  version: string;
  source: string | null;
  activatedAt: string | null;
  createdAt: string | null;
};

export type OrgSettingsErrorMessages = {
  accessDenied: string;
  default: string;
  sessionExpired: string;
  unavailable: string;
};

export type QuestionBankStatusErrorMessages = OrgSettingsErrorMessages & {
  notFound: string;
};

const DEFAULT_ORG_SETTINGS_ERROR_MESSAGES: OrgSettingsErrorMessages = {
  accessDenied: "You do not have access to update organization settings.",
  default: "Unable to update organization settings.",
  sessionExpired: "Your session expired. Please sign in again.",
  unavailable: "Organization settings are unavailable. Try again shortly.",
};

const DEFAULT_QUESTION_BANK_STATUS_ERROR_MESSAGES: QuestionBankStatusErrorMessages =
  {
    accessDenied: "You do not have access to view the question bank.",
    default: "Unable to load question bank status.",
    notFound: "No active question bank version found.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Question bank status is unavailable. Try again shortly.",
  };

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

export const fetchOrgSettings = async (): Promise<OrgSettings> => {
  const response = await apiClient.fetchJson<unknown>("/admin-api/org/settings");
  if (!isRecord(response)) {
    throw new Error("Invalid organization settings payload.");
  }
  const settings = isRecord(response.settings) ? response.settings : {};
  return settings;
};

export const updateOrgSettings = async (
  payload: OrgSettingsUpdatePayload
): Promise<OrgSettings> => {
  const response = await apiClient.postJson<unknown>(
    "/admin-api/org/settings",
    payload,
    { method: "PATCH" }
  );
  if (!isRecord(response)) {
    throw new Error("Invalid organization settings payload.");
  }
  const updated = isRecord(response.settings) ? response.settings : {};
  return updated;
};

export const getOrgSettingsErrorMessage = (
  error: unknown,
  messages: OrgSettingsErrorMessages = DEFAULT_ORG_SETTINGS_ERROR_MESSAGES
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

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

export const fetchQuestionBankStatus = async (
  bankKey = "default"
): Promise<QuestionBankStatus> => {
  const query = new URLSearchParams({ bank_key: bankKey });
  const response = await apiClient.fetchJson<unknown>(
    `/admin-api/org/question-bank?${query.toString()}`
  );
  if (!isRecord(response)) {
    throw new Error("Invalid question bank payload.");
  }
  const bankKeyValue = toTrimmedString(response.bank_key) ?? bankKey;
  const version = toTrimmedString(response.version) ?? "unknown";
  const source = toTrimmedString(response.source);
  const activatedAt = toTrimmedString(response.activated_at);
  const createdAt = toTrimmedString(response.created_at);
  return {
    bankKey: bankKeyValue,
    version,
    source,
    activatedAt,
    createdAt,
  };
};

export const getQuestionBankErrorMessage = (
  error: unknown,
  messages: QuestionBankStatusErrorMessages =
    DEFAULT_QUESTION_BANK_STATUS_ERROR_MESSAGES
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.sessionExpired;
    }
    if (error.status === 403) {
      return messages.accessDenied;
    }
    if (error.status === 404) {
      return messages.notFound;
    }
    if (error.status >= 500) {
      return messages.unavailable;
    }
  }
  return messages.default;
};
