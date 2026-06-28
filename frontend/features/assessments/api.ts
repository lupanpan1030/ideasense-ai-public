import { ApiError, apiClient } from "@/lib/api/client";
import {
  normalizeContextCard,
  normalizeValidationPlan,
  type ContextCard,
  type ValidationPlanItem,
} from "@/features/diagnosis/diagnosis-types";
import { normalizeContextVersion } from "@/features/context/context-refresh";
import { normalizeAppLocale, type AppLocale } from "@/lib/i18n/config";
import { normalizeArtifactLocale } from "@/lib/i18n/artifact-locale";
import { normalizeReportJobStatus } from "@/features/reports/reports-api";
import type { ReportJobStatus } from "@/features/reports/reports-normalize";

type StageDraftResponse = {
  assessment_id?: unknown;
  project_id?: unknown;
  stage?: unknown;
  stage_status?: unknown;
  draft_summary_text?: unknown;
  draft_output_locale?: unknown;
  context_version?: unknown;
  context_updated_at?: unknown;
  score_status?: unknown;
  generation_status?: unknown;
  retryable?: unknown;
  last_error?: unknown;
};

export type StageSummaryGenerationStatus =
  | "queued"
  | "running"
  | "ready"
  | "stale"
  | "failed";

export type StageDraftSummary = {
  assessmentId: string | null;
  projectId: string;
  stage: string;
  stageStatus: string | null;
  draftSummaryText: string;
  draftOutputLocale: AppLocale | null;
  contextVersion: number | null;
  contextUpdatedAt: string | null;
  scoreStatus: string | null;
  generationStatus: StageSummaryGenerationStatus;
  retryable: boolean;
  lastError: string | null;
};

type StageConfirmResponse = {
  score_status?: unknown;
  scores?: unknown;
  scores_json?: unknown;
  score_breakdown?: unknown;
  total_score?: unknown;
  computed_at?: unknown;
  next_stage?: unknown;
  error?: unknown;
  stage_status?: unknown;
  updated_project?: unknown;
  assessment_snapshot?: unknown;
  context_card?: unknown;
  validation_plan?: unknown;
  report_job_status?: unknown;
};

type StageSummariesResponse = {
  project_id?: unknown;
  summaries?: unknown;
};

type VerificationSourceResponse = {
  title?: unknown;
  url?: unknown;
  domain?: unknown;
  snippet?: unknown;
};

type StageQuestionVerificationResponse = {
  question_id?: unknown;
  question_title?: unknown;
  priority?: unknown;
  status?: unknown;
  status_detail?: unknown;
  supported_claims?: unknown;
  contradicted_claims?: unknown;
  uncertain_claims?: unknown;
  total_claims?: unknown;
  sources?: unknown;
};

type StageVerificationSummaryResponse = {
  stage?: unknown;
  total?: unknown;
  supported?: unknown;
  contradicted?: unknown;
  uncertain?: unknown;
  failed?: unknown;
  stale?: unknown;
  provider_unavailable?: unknown;
  not_checked?: unknown;
  verified?: unknown;
  verifying?: unknown;
  no_evidence?: unknown;
  not_applicable?: unknown;
  questions?: unknown;
};

type ProjectVerificationResponse = {
  project_id?: unknown;
  stages?: unknown;
};

type VerificationRefreshResponse = {
  project_id?: unknown;
  stage?: unknown;
  enqueued?: unknown;
  skipped?: unknown;
};

type AssessmentSnapshotResponse = {
  scores_json?: unknown;
  score_breakdown?: unknown;
  scores?: unknown;
  total_score?: unknown;
  stage_status?: unknown;
};

export type StageScoreSummary = {
  total: number | null;
  desirability: number | null;
  viability: number | null;
  feasibility: number | null;
};

export type StageConfirmResult = {
  scoreStatus: string;
  scores: StageScoreSummary | null;
  totalScore: number | null;
  computedAt: string | null;
  nextStage: string | null;
  error: string | null;
  stageStatus: string | null;
  contextCard: ContextCard;
  validationPlan: ValidationPlanItem[];
  reportJobStatus: ReportJobStatus | null;
};

export type StageSummarySnapshot = {
  stage: string;
  draftSummaryMarkdown: string | null;
  draftOutputLocale: AppLocale | null;
  finalSummaryMarkdown: string | null;
  finalOutputLocale: AppLocale | null;
  confirmed: boolean;
  updatedAt: string | null;
  userEditedPaths: string[];
  contextCard: ContextCard;
  validationPlan: ValidationPlanItem[];
};

export type VerificationSource = {
  title: string | null;
  url: string | null;
  domain: string | null;
  snippet: string | null;
};

export type StageQuestionVerification = {
  questionId: string;
  questionTitle: string | null;
  priority: string;
  status: string;
  statusDetail: string | null;
  supportedClaims: number;
  contradictedClaims: number;
  uncertainClaims: number;
  totalClaims: number;
  sources: VerificationSource[];
};

export type StageVerificationSummary = {
  stage: string;
  total: number;
  supported: number;
  contradicted: number;
  uncertain: number;
  failed: number;
  stale: number;
  providerUnavailable: number;
  notChecked: number;
  verified: number;
  verifying: number;
  noEvidence: number;
  notApplicable: number;
  questions: StageQuestionVerification[];
};

export type ProjectVerificationSnapshot = {
  projectId: string;
  stages: StageVerificationSummary[];
};

export type VerificationRefreshSnapshot = {
  projectId: string;
  stage: string | null;
  enqueued: number;
  skipped: number;
};

export type StageGateErrorDetails = {
  message: string;
  shouldRefresh: boolean;
  status?: number;
};

const STAGE_SUMMARY_TIMEOUT_MESSAGE =
  "Stage summary generation timed out. Try again in a moment.";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toLowerTrimmedString = (value: unknown): string | null => {
  const raw = toTrimmedString(value);
  return raw ? raw.toLowerCase() : null;
};

const toBoolean = (value: unknown): boolean => value === true;

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  if (isRecord(value)) {
    const score = value.score ?? value.value ?? value.total ?? value.total_score;
    if (score !== undefined) {
      return toNumber(score);
    }
  }
  return null;
};

const normalizeStageSummaryGenerationStatus = (
  value: unknown,
  draftSummaryText: string
): StageSummaryGenerationStatus => {
  const normalized = toLowerTrimmedString(value);
  if (
    normalized === "queued" ||
    normalized === "running" ||
    normalized === "ready" ||
    normalized === "stale" ||
    normalized === "failed"
  ) {
    return normalized;
  }
  return draftSummaryText ? "ready" : "queued";
};

export const normalizeStageDraftResponse = (
  payload: unknown,
  fallbackProjectId: string,
  fallbackStage: string
): StageDraftSummary | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as StageDraftResponse;
  const projectId = toTrimmedString(response.project_id) ?? fallbackProjectId;
  if (!projectId) {
    return null;
  }

  const stage = toTrimmedString(response.stage) ?? fallbackStage;
  if (!stage) {
    return null;
  }

  const assessmentId = toTrimmedString(response.assessment_id);
  const stageStatus = toLowerTrimmedString(response.stage_status);
  const draftSummaryText = toTrimmedString(response.draft_summary_text) ?? "";
  const draftOutputLocale = normalizeArtifactLocale(response.draft_output_locale);
  const contextVersion = normalizeContextVersion(response.context_version);
  const contextUpdatedAt =
    toTrimmedString(response.context_updated_at) ?? null;
  const scoreStatus = toLowerTrimmedString(response.score_status);
  const generationStatus = normalizeStageSummaryGenerationStatus(
    response.generation_status,
    draftSummaryText
  );
  const retryable =
    toBoolean(response.retryable) ||
    generationStatus === "failed" ||
    generationStatus === "stale";
  const lastError = toTrimmedString(response.last_error);

  return {
    assessmentId,
    projectId,
    stage,
    stageStatus,
    draftSummaryText,
    draftOutputLocale,
    contextVersion,
    contextUpdatedAt,
    scoreStatus,
    generationStatus,
    retryable,
    lastError,
  };
};

const getScoreValue = (
  payload: Record<string, unknown>,
  keys: string[]
): number | null => {
  for (const key of keys) {
    if (key in payload) {
      const value = toNumber(payload[key]);
      if (value !== null) {
        return value;
      }
    }
  }

  const lowerMap = new Map(
    Object.entries(payload).map(([key, value]) => [key.toLowerCase(), value])
  );
  for (const key of keys) {
    const value = lowerMap.get(key.toLowerCase());
    const parsed = toNumber(value);
    if (parsed !== null) {
      return parsed;
    }
  }

  return null;
};

const resolveScoresPayload = (
  payload: StageConfirmResponse
): Record<string, unknown> | null => {
  const snapshot = isRecord(payload.assessment_snapshot)
    ? (payload.assessment_snapshot as AssessmentSnapshotResponse)
    : null;

  const candidates = [
    payload.scores,
    payload.scores_json,
    payload.score_breakdown,
    snapshot?.scores_json,
    snapshot?.score_breakdown,
    snapshot?.scores,
  ];

  for (const candidate of candidates) {
    if (!isRecord(candidate)) {
      continue;
    }
    if (isRecord(candidate.dvf)) {
      return candidate.dvf as Record<string, unknown>;
    }
    return candidate as Record<string, unknown>;
  }

  return null;
};

const normalizeScoreSummary = (
  payload: Record<string, unknown> | null
): StageScoreSummary | null => {
  if (!payload) {
    return null;
  }

  const total = getScoreValue(payload, ["total", "total_score", "totalScore"]);
  const desirability = getScoreValue(payload, [
    "desirability",
    "desirability_score",
    "d",
  ]);
  const viability = getScoreValue(payload, [
    "viability",
    "viability_score",
    "v",
  ]);
  const feasibility = getScoreValue(payload, [
    "feasibility",
    "feasibility_score",
    "f",
  ]);

  const hasAny =
    total !== null ||
    desirability !== null ||
    viability !== null ||
    feasibility !== null;

  if (!hasAny) {
    return null;
  }

  return {
    total,
    desirability,
    viability,
    feasibility,
  };
};

export const normalizeConfirmResponse = (
  payload: unknown
): StageConfirmResult | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as StageConfirmResponse;
  const scoreStatus = toLowerTrimmedString(response.score_status) ?? "unknown";
  const computedAt = toTrimmedString(response.computed_at);
  const nextStage = toTrimmedString(response.next_stage);
  const error = toTrimmedString(response.error);

  const snapshot = isRecord(response.assessment_snapshot)
    ? (response.assessment_snapshot as AssessmentSnapshotResponse)
    : null;

  const stageStatus =
    toLowerTrimmedString(response.stage_status) ??
    (snapshot ? toLowerTrimmedString(snapshot.stage_status) : null) ??
    (isRecord(response.updated_project)
      ? toLowerTrimmedString(response.updated_project.stage_status)
      : null);

  const scoresPayload = resolveScoresPayload(response);
  const scoreSummary = normalizeScoreSummary(scoresPayload);
  const totalScore =
    toNumber(response.total_score) ??
    (snapshot ? toNumber(snapshot.total_score) : null) ??
    scoreSummary?.total ??
    null;

  const scores: StageScoreSummary | null = scoreSummary
    ? {
        ...scoreSummary,
        total: totalScore ?? scoreSummary.total,
      }
    : totalScore !== null
    ? {
        total: totalScore,
        desirability: null,
        viability: null,
        feasibility: null,
      }
    : null;

  return {
    scoreStatus,
    scores,
    totalScore,
    computedAt,
    nextStage,
    error,
    stageStatus,
    contextCard: normalizeContextCard(response.context_card),
    validationPlan: normalizeValidationPlan(response.validation_plan),
    reportJobStatus: normalizeReportJobStatus(response.report_job_status, ""),
  };
};

const normalizeStageSummaryItem = (
  value: unknown
): StageSummarySnapshot | null => {
  if (!isRecord(value)) {
    return null;
  }
  const stage =
    toLowerTrimmedString(value.stage) ?? toTrimmedString(value.stage);
  if (!stage) {
    return null;
  }

  const draftSummaryMarkdown = toTrimmedString(value.draft_summary_markdown);
  const draftOutputLocale = normalizeArtifactLocale(value.draft_output_locale);
  const finalSummaryMarkdown = toTrimmedString(value.final_summary_markdown);
  const finalOutputLocale = normalizeArtifactLocale(value.final_output_locale);
  const updatedAt = toTrimmedString(value.updated_at);
  const confirmed = toBoolean(value.confirmed);
  const userEditedPaths = Array.isArray(value.user_edited_paths)
    ? value.user_edited_paths.filter(
        (path): path is string => typeof path === "string" && path.trim().length > 0
      )
    : [];

  return {
    stage,
    draftSummaryMarkdown,
    draftOutputLocale,
    finalSummaryMarkdown,
    finalOutputLocale,
    confirmed,
    updatedAt,
    userEditedPaths,
    contextCard: normalizeContextCard(value.context_card),
    validationPlan: normalizeValidationPlan(value.validation_plan),
  };
};

const normalizeStageSummariesResponse = (
  payload: unknown
): StageSummarySnapshot[] | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as StageSummariesResponse;
  if (!Array.isArray(response.summaries)) {
    return null;
  }

  const summaries = response.summaries
    .map((entry) => normalizeStageSummaryItem(entry))
    .filter((entry): entry is StageSummarySnapshot => Boolean(entry));

  return summaries;
};

const normalizeVerificationSource = (
  value: unknown
): VerificationSource | null => {
  if (!isRecord(value)) {
    return null;
  }
  const source = value as VerificationSourceResponse;
  return {
    title: toTrimmedString(source.title),
    url: toTrimmedString(source.url),
    domain: toTrimmedString(source.domain),
    snippet: toTrimmedString(source.snippet),
  };
};

const normalizeStageQuestionVerification = (
  value: unknown
): StageQuestionVerification | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as StageQuestionVerificationResponse;
  const questionId = toTrimmedString(response.question_id);
  if (!questionId) {
    return null;
  }
  const sources = Array.isArray(response.sources)
    ? response.sources
        .map((item) => normalizeVerificationSource(item))
        .filter((item): item is VerificationSource => Boolean(item))
    : [];
  return {
    questionId,
    questionTitle: toTrimmedString(response.question_title),
    priority: toLowerTrimmedString(response.priority) ?? "none",
    status: toLowerTrimmedString(response.status) ?? "not_checked",
    statusDetail: toTrimmedString(response.status_detail),
    supportedClaims: toNumber(response.supported_claims) ?? 0,
    contradictedClaims: toNumber(response.contradicted_claims) ?? 0,
    uncertainClaims: toNumber(response.uncertain_claims) ?? 0,
    totalClaims: toNumber(response.total_claims) ?? 0,
    sources,
  };
};

const normalizeStageVerificationSummary = (
  value: unknown
): StageVerificationSummary | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as StageVerificationSummaryResponse;
  const stage = toLowerTrimmedString(response.stage) ?? toTrimmedString(response.stage);
  if (!stage) {
    return null;
  }
  const questions = Array.isArray(response.questions)
    ? response.questions
        .map((item) => normalizeStageQuestionVerification(item))
        .filter((item): item is StageQuestionVerification => Boolean(item))
    : [];
  return {
    stage,
    total: toNumber(response.total) ?? 0,
    supported: toNumber(response.supported) ?? toNumber(response.verified) ?? 0,
    contradicted: toNumber(response.contradicted) ?? 0,
    uncertain: toNumber(response.uncertain) ?? 0,
    failed: toNumber(response.failed) ?? 0,
    stale: toNumber(response.stale) ?? 0,
    providerUnavailable: toNumber(response.provider_unavailable) ?? 0,
    notChecked: toNumber(response.not_checked) ?? 0,
    verified: toNumber(response.verified) ?? toNumber(response.supported) ?? 0,
    verifying: toNumber(response.verifying) ?? 0,
    noEvidence: toNumber(response.no_evidence) ?? 0,
    notApplicable: toNumber(response.not_applicable) ?? 0,
    questions,
  };
};

const normalizeProjectVerificationResponse = (
  payload: unknown
): ProjectVerificationSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const response = payload as ProjectVerificationResponse;
  const projectId = toTrimmedString(response.project_id);
  if (!projectId) {
    return null;
  }
  const stages = Array.isArray(response.stages)
    ? response.stages
        .map((item) => normalizeStageVerificationSummary(item))
        .filter((item): item is StageVerificationSummary => Boolean(item))
    : [];
  return { projectId, stages };
};

const normalizeVerificationRefreshResponse = (
  payload: unknown
): VerificationRefreshSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }
  const response = payload as VerificationRefreshResponse;
  const projectId = toTrimmedString(response.project_id);
  if (!projectId) {
    return null;
  }
  return {
    projectId,
    stage: toLowerTrimmedString(response.stage),
    enqueued: toNumber(response.enqueued) ?? 0,
    skipped: toNumber(response.skipped) ?? 0,
  };
};

export const getStageGateErrorMessage = (
  error: unknown
): StageGateErrorDetails => {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return {
        message: "Your session expired. Please sign in again.",
        shouldRefresh: false,
        status: error.status,
      };
    }

    if (error.status === 404) {
      return {
        message: "Project not found or it was deleted.",
        shouldRefresh: false,
        status: error.status,
      };
    }

    if (error.status === 409) {
      return {
        message: "Context updated while you were away. Refreshing the review state.",
        shouldRefresh: true,
        status: error.status,
      };
    }

    if (error.status >= 500) {
      if (error.message === STAGE_SUMMARY_TIMEOUT_MESSAGE) {
        return {
          message: STAGE_SUMMARY_TIMEOUT_MESSAGE,
          shouldRefresh: false,
          status: error.status,
        };
      }

      return {
        message: "Stage gate service is unavailable. Try again soon.",
        shouldRefresh: false,
        status: error.status,
      };
    }

    return {
      message: "Unable to complete the stage review.",
      shouldRefresh: false,
      status: error.status,
    };
  }

  if (error instanceof TypeError) {
    return {
      message: "Network error. Check your connection and try again.",
      shouldRefresh: false,
    };
  }

  return { message: "Unable to complete the stage review.", shouldRefresh: false };
};

export async function getStageDraft({
  projectId,
  stage,
  clientContextVersion,
  outputLocale,
  retry,
  signal,
}: {
  projectId: string;
  stage: string;
  clientContextVersion?: number | null;
  outputLocale?: AppLocale;
  retry?: boolean;
  signal?: AbortSignal;
}): Promise<StageDraftSummary> {
  const query = new URLSearchParams({ project_id: projectId });
  if (typeof clientContextVersion === "number" && Number.isFinite(clientContextVersion)) {
    query.set("client_context_version", `${clientContextVersion}`);
  }
  query.set("output_locale", normalizeAppLocale(outputLocale));
  if (retry) {
    query.set("retry", "true");
  }
  const response = await apiClient.fetchJson<unknown>(
    `/assessments/${stage}/draft?${query.toString()}`,
    { signal }
  );

  const normalized = normalizeStageDraftResponse(response, projectId, stage);
  if (!normalized) {
    throw new Error("Invalid stage draft payload.");
  }

  return normalized;
}

export async function confirmStage({
  projectId,
  stage,
  clientContextVersion,
  outputLocale,
  signal,
}: {
  projectId: string;
  stage: string;
  clientContextVersion: number;
  outputLocale?: AppLocale;
  signal?: AbortSignal;
}): Promise<StageConfirmResult> {
  const response = await apiClient.postJson<unknown>(
    `/assessments/${stage}/confirm`,
    {
      project_id: projectId,
      client_context_version: clientContextVersion,
      output_locale: normalizeAppLocale(outputLocale),
    },
    { signal }
  );

  const normalized = normalizeConfirmResponse(response);
  if (!normalized) {
    throw new Error("Invalid stage confirmation payload.");
  }

  return normalized;
}

export async function fetchStageSummaries(
  projectId: string,
  options: { signal?: AbortSignal } = {}
): Promise<StageSummarySnapshot[]> {
  const response = await apiClient.fetchJson<unknown>(
    `/assessments/project/${projectId}/summaries`,
    { signal: options.signal }
  );

  const normalized = normalizeStageSummariesResponse(response);
  if (!normalized) {
    throw new Error("Invalid stage summaries payload.");
  }

  return normalized;
}

export async function fetchStageVerification(
  projectId: string,
  options: { stage?: string; signal?: AbortSignal } = {}
): Promise<ProjectVerificationSnapshot> {
  const query = new URLSearchParams();
  if (options.stage) {
    query.set("stage", options.stage);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await apiClient.fetchJson<unknown>(
    `/assessments/project/${projectId}/verification${suffix}`,
    { signal: options.signal }
  );
  const normalized = normalizeProjectVerificationResponse(response);
  if (!normalized) {
    throw new Error("Invalid verification payload.");
  }
  return normalized;
}

export async function refreshStageVerification(
  projectId: string,
  options: { stage?: string; signal?: AbortSignal } = {}
): Promise<VerificationRefreshSnapshot> {
  const query = new URLSearchParams();
  if (options.stage) {
    query.set("stage", options.stage);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await apiClient.postJson<unknown>(
    `/assessments/project/${projectId}/verification/refresh${suffix}`,
    {},
    { signal: options.signal }
  );
  const normalized = normalizeVerificationRefreshResponse(response);
  if (!normalized) {
    throw new Error("Invalid verification refresh payload.");
  }
  return normalized;
}
