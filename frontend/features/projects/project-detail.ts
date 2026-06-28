import { apiClient } from "@/lib/api/client";
import { normalizeProjectId } from "./project-id";

type ProjectDetailResponse = {
  project?: unknown;
  runtime?: unknown;
  current_question_instance_id?: unknown;
};

type ProjectRecord = {
  id?: unknown;
  current_stage?: unknown;
  current_variant?: unknown;
  stage_status?: unknown;
  question_bank_version_id?: unknown;
  updated_at?: unknown;
};

type RuntimeRecord = {
  stage?: unknown;
  variant?: unknown;
  current_question_bank_question_id?: unknown;
  next_question_bank_question_id?: unknown;
  missing_paths?: unknown;
  turn_state?: unknown;
  runtime_version?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
};

export type ProjectRuntimeSnapshot = {
  stage: string;
  variant: string;
  currentQuestionId: string | null;
  nextQuestionId: string | null;
  missingPaths: string[];
  turnState: string;
  runtimeVersion: number;
  createdAt: string | null;
  updatedAt: string | null;
};

export type ProjectDetailSnapshot = {
  projectId: string;
  currentStage: string | null;
  currentVariant: string | null;
  stageStatus: string | null;
  updatedAt: string | null;
  questionBankVersionId: string | null;
  runtime: ProjectRuntimeSnapshot | null;
  currentQuestionInstanceId: string | null;
};

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

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
};

const normalizeProjectDetail = (
  payload: unknown,
  fallbackProjectId: string
): ProjectDetailSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as ProjectDetailResponse;
  if (!isRecord(response.project) || !isRecord(response.runtime)) {
    return null;
  }

  const project = response.project as ProjectRecord;
  const runtime = response.runtime as RuntimeRecord;
  const projectId =
    normalizeProjectId(toTrimmedString(project.id)) ??
    normalizeProjectId(fallbackProjectId);
  if (!projectId) {
    return null;
  }

  const runtimeStage = toTrimmedString(runtime.stage);
  const runtimeVariant = toTrimmedString(runtime.variant);
  const currentQuestionId = toTrimmedString(
    runtime.current_question_bank_question_id
  );
  const runtimeVersion = toNumber(runtime.runtime_version);
  const turnState = toTrimmedString(runtime.turn_state);
  if (!runtimeStage || !runtimeVariant || runtimeVersion === null || !turnState) {
    return null;
  }
  const isReportStage = runtimeStage.toLowerCase() === "report";
  if (!currentQuestionId && !isReportStage) {
    return null;
  }

  const currentStage = runtimeStage;
  const currentVariant = runtimeVariant;
  const stageStatus = toTrimmedString(project.stage_status);
  const updatedAt = toTrimmedString(project.updated_at);
  const questionBankVersionId = toTrimmedString(
    project.question_bank_version_id
  );

  const runtimeSnapshot: ProjectRuntimeSnapshot = {
    stage: runtimeStage,
    variant: runtimeVariant,
    currentQuestionId: currentQuestionId ?? null,
    nextQuestionId: toTrimmedString(
      runtime.next_question_bank_question_id
    ) ?? currentQuestionId ?? null,
    missingPaths: toStringArray(runtime.missing_paths),
    turnState,
    runtimeVersion,
    createdAt: toTrimmedString(runtime.created_at),
    updatedAt: toTrimmedString(runtime.updated_at),
  };

  return {
    projectId,
    currentStage,
    currentVariant,
    stageStatus,
    updatedAt,
    questionBankVersionId,
    runtime: runtimeSnapshot,
    currentQuestionInstanceId: toTrimmedString(
      response.current_question_instance_id
    ),
  };
};

export async function fetchProjectDetail(
  projectId: string,
  options: { signal?: AbortSignal } = {}
): Promise<ProjectDetailSnapshot> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.fetchJson<unknown>(
    `/projects/${normalizedProjectId}`,
    {
      signal: options.signal,
    }
  );
  const normalized = normalizeProjectDetail(response, normalizedProjectId);
  if (!normalized) {
    throw new Error("Invalid project detail payload.");
  }
  return normalized;
}
