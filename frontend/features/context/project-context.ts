import { apiClient } from "@/lib/api/client";
import {
  normalizeContextCard,
  type ContextCard,
} from "@/features/diagnosis/diagnosis-types";
import { normalizeProjectId } from "@/features/projects/project-id";
import { normalizeContextVersion } from "./context-refresh";

type ContextData = Record<string, unknown>;

export type AnswerMetaEntry = {
  resolutionStatus: string;
  claimType: string;
  evidenceLevel: string;
  source: string;
  note: string | null;
  updatedAt: string;
};

export type ProjectContextSnapshot = {
  projectId: string;
  stage: string;
  currentQuestionId: string | null;
  nextQuestionId: string | null;
  turnState: string;
  missingFields: string[];
  data: ContextData;
  dataRaw: Record<string, unknown>;
  userEditedPaths: Record<string, string[]>;
  answerMeta: Record<string, AnswerMetaEntry>;
  contextCard: ContextCard;
  updatedAt: string;
  contextVersion: number;
};

type ProjectContextResponse = {
  project_id?: unknown;
  stage?: unknown;
  current_question_id?: unknown;
  next_question_id?: unknown;
  turn_state?: unknown;
  missing_fields?: unknown;
  data?: unknown;
  user_edited_paths?: unknown;
  answer_meta?: unknown;
  context_card?: unknown;
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

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
};

const normalizeContextData = (value: unknown): ContextData => {
  if (!isPlainRecord(value)) {
    return {};
  }
  return value;
};

const normalizeUserEditedPaths = (
  value: unknown
): Record<string, string[]> => {
  if (!isPlainRecord(value)) {
    return {};
  }
  const normalized: Record<string, string[]> = {};
  for (const [stage, paths] of Object.entries(value)) {
    if (typeof stage !== "string" || !Array.isArray(paths)) {
      continue;
    }
    const stageKey = stage.trim().toLowerCase();
    if (!stageKey) {
      continue;
    }
    const cleaned = paths
      .map((item) => (typeof item === "string" ? item.trim() : ""))
      .filter(Boolean);
    if (cleaned.length) {
      normalized[stageKey] = cleaned;
    }
  }
  return normalized;
};

const normalizeAnswerMeta = (
  value: unknown
): Record<string, AnswerMetaEntry> => {
  if (!isPlainRecord(value)) {
    return {};
  }
  const normalized: Record<string, AnswerMetaEntry> = {};
  for (const [path, entry] of Object.entries(value)) {
    const trimmedPath = path.trim();
    if (!trimmedPath || !isPlainRecord(entry)) {
      continue;
    }
    const resolutionStatus = toTrimmedString(entry.resolution_status);
    const claimType = toTrimmedString(entry.claim_type);
    const evidenceLevel = toTrimmedString(entry.evidence_level);
    const source = toTrimmedString(entry.source);
    const updatedAt = toTrimmedString(entry.updated_at);
    if (
      !resolutionStatus ||
      !claimType ||
      !evidenceLevel ||
      !source ||
      !updatedAt
    ) {
      continue;
    }
    normalized[trimmedPath] = {
      resolutionStatus,
      claimType,
      evidenceLevel,
      source,
      note: toTrimmedString(entry.note),
      updatedAt,
    };
  }
  return normalized;
};

const normalizeProjectContext = (
  payload: unknown,
  fallbackProjectId: string
): ProjectContextSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as ProjectContextResponse;
  const projectId =
    normalizeProjectId(toTrimmedString(response.project_id)) ??
    normalizeProjectId(fallbackProjectId);
  if (!projectId) {
    return null;
  }

  const stage = toTrimmedString(response.stage);
  const currentQuestionId = toTrimmedString(response.current_question_id);
  const turnState = toTrimmedString(response.turn_state);
  const updatedAt = toTrimmedString(response.updated_at);
  if (!stage || !turnState || !updatedAt) {
    return null;
  }
  const isReportStage = stage.toLowerCase() === "report";
  if (!currentQuestionId && !isReportStage) {
    return null;
  }

  const nextQuestionId =
    toTrimmedString(response.next_question_id) ?? currentQuestionId ?? null;
  const missingFields = toStringArray(response.missing_fields);
  const data = normalizeContextData(response.data);
  const dataRaw = data;
  const userEditedPaths = normalizeUserEditedPaths(response.user_edited_paths);
  const answerMeta = normalizeAnswerMeta(response.answer_meta);
  const contextCard = normalizeContextCard(response.context_card);
  const contextVersion =
    normalizeContextVersion(response.context_version) ?? DEFAULT_CONTEXT_VERSION;

  return {
    projectId,
    stage,
    currentQuestionId,
    nextQuestionId,
    turnState,
    missingFields,
    data,
    dataRaw,
    userEditedPaths,
    answerMeta,
    contextCard,
    updatedAt,
    contextVersion,
  };
};

export async function fetchProjectContext(
  projectId: string,
  options: { signal?: AbortSignal } = {}
): Promise<ProjectContextSnapshot> {
  const normalizedProjectId = normalizeProjectId(projectId);
  if (!normalizedProjectId) {
    throw new Error("Invalid project id.");
  }

  const response = await apiClient.fetchJson<unknown>(
    `/projects/${normalizedProjectId}/context`,
    { signal: options.signal }
  );
  const normalized = normalizeProjectContext(response, normalizedProjectId);
  if (!normalized) {
    throw new Error("Invalid project context payload.");
  }
  return normalized;
}
