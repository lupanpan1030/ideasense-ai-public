import { ApiError, apiClient } from "@/lib/api/client";

export type ReportQualityStatus = "pass" | "warn" | "fail";

export type ReportQualityObservation = {
  id: string;
  orgId: string;
  orgName: string | null;
  orgSlug: string | null;
  projectId: string;
  projectTitle: string | null;
  reportId: string;
  reportVersion: number;
  generatedFromStateVersion: number;
  observationSchemaVersion: string;
  status: ReportQualityStatus;
  failedInvariants: string[];
  warningInvariants: string[];
  scoreSnapshot: Record<string, unknown>;
  evidenceCounts: Record<string, unknown>;
  canonicalBoundaries: Record<string, unknown>;
  observedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};

export type ReportQualityObservationDetail = ReportQualityObservation & {
  observation: Record<string, unknown>;
};

export type ReportQualityListResponse = {
  observations: ReportQualityObservation[];
  total: number;
  limit: number;
  offset: number;
};

export type ReportQualityStatusCount = {
  status: ReportQualityStatus;
  count: number;
};

export type ReportQualityInvariantCount = {
  invariantId: string;
  severity: "fail" | "warn";
  count: number;
};

export type ReportQualitySummary = {
  total: number;
  statusCounts: ReportQualityStatusCount[];
  invariantCounts: ReportQualityInvariantCount[];
};

export type ReportQualityFilters = {
  status?: ReportQualityStatus | "all";
  q?: string;
  limit?: number;
  offset?: number;
};

export type ReportQualityErrorMessages = {
  accessDenied: string;
  default: string;
  sessionExpired: string;
  unavailable: string;
};

const DEFAULT_LIMIT = 20;

const DEFAULT_ERROR_MESSAGES: ReportQualityErrorMessages = {
  accessDenied: "You do not have access to report quality operations.",
  default: "Unable to load report quality data.",
  sessionExpired: "Your session expired. Please sign in again.",
  unavailable: "Report quality data is unavailable. Try again shortly.",
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

const toRequiredString = (value: unknown, label: string): string => {
  const resolved = toOptionalString(value);
  if (!resolved) {
    throw new Error(`Invalid report quality ${label}`);
  }
  return resolved;
};

const toNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
};

const toRecord = (value: unknown): Record<string, unknown> =>
  isRecord(value) ? value : {};

const toStringList = (value: unknown): string[] =>
  Array.isArray(value)
    ? value
        .map((item) => (typeof item === "string" ? item.trim() : String(item)))
        .filter(Boolean)
    : [];

const toStatus = (value: unknown): ReportQualityStatus => {
  const status = toOptionalString(value);
  return status === "pass" || status === "warn" || status === "fail"
    ? status
    : "fail";
};

const toSeverity = (value: unknown): "fail" | "warn" =>
  toOptionalString(value) === "warn" ? "warn" : "fail";

const toObservation = (value: unknown): ReportQualityObservation => {
  if (!isRecord(value)) {
    throw new Error("Invalid report quality observation.");
  }
  return {
    id: toRequiredString(value.id, "id"),
    orgId: toRequiredString(value.org_id, "org_id"),
    orgName: toOptionalString(value.org_name),
    orgSlug: toOptionalString(value.org_slug),
    projectId: toRequiredString(value.project_id, "project_id"),
    projectTitle: toOptionalString(value.project_title),
    reportId: toRequiredString(value.report_id, "report_id"),
    reportVersion: toNumber(value.report_version, 1),
    generatedFromStateVersion: toNumber(value.generated_from_state_version, 1),
    observationSchemaVersion:
      toOptionalString(value.observation_schema_version) ??
      "assessment_quality_observation_v1",
    status: toStatus(value.status),
    failedInvariants: toStringList(value.failed_invariants),
    warningInvariants: toStringList(value.warning_invariants),
    scoreSnapshot: toRecord(value.score_snapshot),
    evidenceCounts: toRecord(value.evidence_counts),
    canonicalBoundaries: toRecord(value.canonical_boundaries),
    observedAt: toOptionalString(value.observed_at),
    createdAt: toOptionalString(value.created_at),
    updatedAt: toOptionalString(value.updated_at),
  };
};

const buildQuery = (filters: ReportQualityFilters): string => {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit ?? DEFAULT_LIMIT));
  params.set("offset", String(filters.offset ?? 0));
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  const query = filters.q?.trim();
  if (query) {
    params.set("q", query);
  }
  return params.toString();
};

export const fetchReportQualityObservations = async (
  filters: ReportQualityFilters = {}
): Promise<ReportQualityListResponse> => {
  const query = buildQuery(filters);
  const payload = await apiClient.fetchJson<unknown>(
    `/platform-api/report-quality/observations?${query}`
  );
  if (!isRecord(payload)) {
    throw new Error("Invalid report quality list payload.");
  }
  const observations = Array.isArray(payload.observations)
    ? payload.observations.map(toObservation)
    : [];
  return {
    observations,
    total: toNumber(payload.total, observations.length),
    limit: toNumber(payload.limit, filters.limit ?? DEFAULT_LIMIT),
    offset: toNumber(payload.offset, filters.offset ?? 0),
  };
};

export const fetchReportQualitySummary = async (
  filters: ReportQualityFilters = {}
): Promise<ReportQualitySummary> => {
  const query = buildQuery(filters);
  const payload = await apiClient.fetchJson<unknown>(
    `/platform-api/report-quality/summary?${query}`
  );
  if (!isRecord(payload)) {
    throw new Error("Invalid report quality summary payload.");
  }
  const statusCounts = Array.isArray(payload.status_counts)
    ? payload.status_counts
        .filter(isRecord)
        .map((item) => ({
          status: toStatus(item.status),
          count: toNumber(item.count),
        }))
    : [];
  const invariantCounts = Array.isArray(payload.invariant_counts)
    ? payload.invariant_counts
        .filter(isRecord)
        .map((item) => ({
          invariantId: toRequiredString(item.invariant_id, "invariant_id"),
          severity: toSeverity(item.severity),
          count: toNumber(item.count),
        }))
    : [];
  return {
    total: toNumber(payload.total),
    statusCounts,
    invariantCounts,
  };
};

export const fetchReportQualityObservation = async (
  observationId: string
): Promise<ReportQualityObservationDetail> => {
  const payload = await apiClient.fetchJson<unknown>(
    `/platform-api/report-quality/observations/${observationId}`
  );
  const observation = toObservation(payload);
  return {
    ...observation,
    observation: isRecord(payload) ? toRecord(payload.observation) : {},
  };
};

export const getReportQualityErrorMessage = (
  error: unknown,
  messages: ReportQualityErrorMessages = DEFAULT_ERROR_MESSAGES
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
