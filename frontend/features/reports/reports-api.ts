import { ApiError, apiClient } from "@/lib/api/client";
import { normalizeProjectId } from "@/features/projects/project-id";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { normalizeAppLocale, type AppLocale } from "@/lib/i18n/config";
import { normalizeReportResponse } from "./reports-normalize";
import type {
  ReportJobStatus,
  ReportJobStatusValue,
  ReportSnapshot,
} from "./reports-normalize";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const normalizeReportJobStatusValue = (
  value: unknown
): ReportJobStatusValue | null => {
  const normalized = toTrimmedString(value)?.toLowerCase();
  if (
    normalized === "not_started" ||
    normalized === "queued" ||
    normalized === "running" ||
    normalized === "finalizing" ||
    normalized === "ready" ||
    normalized === "failed" ||
    normalized === "stale"
  ) {
    return normalized;
  }
  return null;
};

export const normalizeReportJobStatus = (
  payload: unknown,
  fallbackProjectId: string
): ReportJobStatus | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const projectId =
    normalizeProjectId(toTrimmedString(payload.project_id)) ?? fallbackProjectId;
  if (!projectId) {
    return null;
  }
  const status = normalizeReportJobStatusValue(payload.status);
  if (!status) {
    return null;
  }

  return {
    projectId,
    currentStage: toTrimmedString(payload.current_stage),
    stageStatus: toTrimmedString(payload.stage_status),
    jobType: toTrimmedString(payload.job_type),
    status,
    retryable: payload.retryable === true,
    reportId: toTrimmedString(payload.report_id),
    reportVersion: toNumber(payload.report_version),
    generatedAt: toTrimmedString(payload.generated_at),
    contextVersion: toNumber(payload.context_version),
    nextPollMs: Math.max(toNumber(payload.next_poll_ms) ?? 2000, 500),
  };
};

const withOutputLocale = (
  path: string,
  outputLocale: AppLocale | undefined
): string => {
  if (!outputLocale) {
    return path;
  }
  const query = new URLSearchParams({
    output_locale: normalizeAppLocale(outputLocale),
  });
  return `${path}?${query.toString()}`;
};

export async function fetchProjectReport(
  projectId: string,
  options: { signal?: AbortSignal; outputLocale?: AppLocale } = {}
): Promise<ReportSnapshot | null> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  try {
    const response = await apiClient.fetchJson<unknown>(
      withOutputLocale(
        `/projects/${normalizedProjectId}/report`,
        options.outputLocale
      ),
      {
        signal: options.signal,
      }
    );
    const normalized = normalizeReportResponse(response, normalizedProjectId);
    if (!normalized) {
      throw new Error("Invalid report payload.");
    }
    return normalized;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.message === "Report not found."
    ) {
      return null;
    }
    throw error;
  }
}

export async function fetchProjectReportStatus(
  projectId: string,
  options: { signal?: AbortSignal; outputLocale?: AppLocale } = {}
): Promise<ReportJobStatus> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.fetchJson<unknown>(
    withOutputLocale(
      `/projects/${normalizedProjectId}/report/status`,
      options.outputLocale
    ),
    {
      signal: options.signal,
    }
  );
  const normalized = normalizeReportJobStatus(response, normalizedProjectId);
  if (!normalized) {
    throw new Error("Invalid report status payload.");
  }
  return normalized;
}

export const getReportErrorMessage = (error: unknown): string => {
  return getSafeErrorMessage(error, {
    default: "Report request failed. Please try again.",
    sessionExpired: "Your session expired. Please sign in again.",
    unavailable: "Report service is unavailable. Please try again soon.",
  });
};
