import { ApiError } from "@/lib/api/client";

export type SafeErrorMessages = {
  default: string;
  accessDenied?: string;
  conflict?: string;
  network?: string;
  notFound?: string;
  sessionExpired?: string;
  unavailable?: string;
};

const isStatusError = (error: unknown): error is { status: number } =>
  typeof error === "object" &&
  error !== null &&
  "status" in error &&
  typeof (error as { status?: unknown }).status === "number";

export const getSafeStatusErrorMessage = (
  status: number,
  messages: SafeErrorMessages
): string => {
  if (status === 401) {
    return messages.sessionExpired ?? messages.default;
  }
  if (status === 403) {
    return messages.accessDenied ?? messages.default;
  }
  if (status === 404) {
    return messages.notFound ?? messages.default;
  }
  if (status === 409) {
    return messages.conflict ?? messages.default;
  }
  if (status >= 500) {
    return messages.unavailable ?? messages.default;
  }
  return messages.default;
};

export const getSafeErrorMessage = (
  error: unknown,
  messages: SafeErrorMessages
): string => {
  if (error instanceof ApiError || isStatusError(error)) {
    return getSafeStatusErrorMessage(error.status, messages);
  }
  if (error instanceof TypeError) {
    return messages.network ?? messages.default;
  }
  return messages.default;
};

export const getSafeResponseErrorMessage = (
  response: Response,
  messages: SafeErrorMessages
): string => getSafeStatusErrorMessage(response.status, messages);
