import { apiClient } from "@/lib/api/client";
import {
  getSafeErrorMessage,
  type SafeErrorMessages,
} from "@/lib/api/safe-error-message";

export type QuestionBankVersion = {
  id: string;
  bankKey: string;
  version: string;
  source: string | null;
  orgId: string | null;
  isActive: boolean;
  createdAt: string | null;
  activatedAt: string | null;
};

export type QuestionBankQuestion = {
  questionId: string;
  stage: string;
  variant: string;
  orderIndex: number;
  title: string | null;
  typeRaw: string | null;
  prompt: string | null;
  standardQuestion: string | null;
  consultantTactic: string | null;
  instruction: string | null;
  validationRule: string | null;
  schemaPaths: string[];
  expectedKeyPoints: string[];
  promptMeta: Record<string, unknown>;
  notes: string | null;
};

export type QuestionBankDraft = {
  version: QuestionBankVersion;
  questions: QuestionBankQuestion[];
};

export type QuestionUpdatePayload = Partial<{
  title: string | null;
  type_raw: string | null;
  prompt: string | null;
  standard_question: string | null;
  consultant_tactic: string | null;
  instruction: string | null;
  validation_rule: string | null;
  schema_paths: string[] | null;
  expected_key_points: string[] | null;
  prompt_meta: Record<string, unknown> | null;
  notes: string | null;
}>;

export type ImportPayload = {
  yaml: string;
  mode?: "replace" | "merge";
};

export type ImportJsonPayload = {
  json: string;
  mode?: "replace" | "merge";
};

export type PublishPayload = {
  version?: string | null;
  source?: string | null;
};

export type ReorderGroupPayload = {
  stage: string;
  variant: string;
  question_ids: string[];
};

export type ReorderPayload = {
  groups: ReorderGroupPayload[];
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

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
};

const toQuestionBankVersion = (value: unknown): QuestionBankVersion => {
  if (!isRecord(value)) {
    throw new Error("Invalid question bank version payload.");
  }
  const id = toOptionalString(value.id) ?? "";
  const bankKey = toOptionalString(value.bank_key) ?? "";
  const version = toOptionalString(value.version) ?? "";
  if (!id || !bankKey) {
    throw new Error("Question bank version payload missing identifiers.");
  }
  return {
    id,
    bankKey,
    version,
    source: toOptionalString(value.source),
    orgId: toOptionalString(value.org_id),
    isActive: Boolean(value.is_active),
    createdAt: toOptionalString(value.created_at),
    activatedAt: toOptionalString(value.activated_at),
  };
};

const toQuestion = (value: unknown): QuestionBankQuestion => {
  if (!isRecord(value)) {
    throw new Error("Invalid question payload.");
  }
  const questionId = toOptionalString(value.question_id) ?? "";
  if (!questionId) {
    throw new Error("Question payload missing question_id.");
  }
  return {
    questionId,
    stage: toOptionalString(value.stage) ?? "",
    variant: toOptionalString(value.variant) ?? "",
    orderIndex: Number(value.order_index ?? 0),
    title: toOptionalString(value.title),
    typeRaw: toOptionalString(value.type_raw),
    prompt: toOptionalString(value.prompt),
    standardQuestion: toOptionalString(value.standard_question),
    consultantTactic: toOptionalString(value.consultant_tactic),
    instruction: toOptionalString(value.instruction),
    validationRule: toOptionalString(value.validation_rule),
    schemaPaths: toStringArray(value.schema_paths),
    expectedKeyPoints: toStringArray(value.expected_key_points),
    promptMeta: isRecord(value.prompt_meta) ? value.prompt_meta : {},
    notes: toOptionalString(value.notes),
  };
};

const toDraft = (value: unknown): QuestionBankDraft => {
  if (!isRecord(value)) {
    throw new Error("Invalid draft payload.");
  }
  const version = toQuestionBankVersion(value.version);
  const questions = Array.isArray(value.questions)
    ? value.questions.map(toQuestion)
    : [];
  return { version, questions };
};

export const fetchActiveQuestionBank = async (
  bankKey: string
): Promise<QuestionBankVersion> => {
  const response = await apiClient.fetchJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/active`
  );
  return toQuestionBankVersion(response);
};

export const fetchActiveQuestionBankDetail = async (
  bankKey: string,
  includeQuestions = true
): Promise<QuestionBankDraft> => {
  const query = new URLSearchParams({
    include_questions: includeQuestions ? "true" : "false",
  });
  const response = await apiClient.fetchJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(
      bankKey
    )}/active/details?${query.toString()}`
  );
  return toDraft(response);
};

export const fetchDraftQuestionBank = async (
  bankKey: string,
  includeQuestions = true
): Promise<QuestionBankDraft> => {
  const query = new URLSearchParams({
    include_questions: includeQuestions ? "true" : "false",
  });
  const response = await apiClient.fetchJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft?${query.toString()}`
  );
  return toDraft(response);
};

export const createDraftQuestionBank = async (
  bankKey: string
): Promise<QuestionBankVersion> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft`,
    {}
  );
  return toQuestionBankVersion(response);
};

export const updateDraftQuestion = async (
  bankKey: string,
  questionId: string,
  payload: QuestionUpdatePayload
): Promise<QuestionBankQuestion> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(
      bankKey
    )}/draft/questions/${encodeURIComponent(questionId)}`,
    payload,
    { method: "PATCH" }
  );
  return toQuestion(response);
};

export const importDraftYaml = async (
  bankKey: string,
  payload: ImportPayload
): Promise<QuestionBankDraft> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft/import`,
    payload
  );
  return toDraft(response);
};

export const importDraftJson = async (
  bankKey: string,
  payload: ImportJsonPayload
): Promise<QuestionBankDraft> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft/import-json`,
    payload
  );
  return toDraft(response);
};

export const reorderDraftQuestions = async (
  bankKey: string,
  payload: ReorderPayload
): Promise<QuestionBankDraft> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft/reorder`,
    payload,
    { method: "PATCH" }
  );
  return toDraft(response);
};

export const publishDraftQuestionBank = async (
  bankKey: string,
  payload: PublishPayload
): Promise<QuestionBankVersion> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/question-banks/${encodeURIComponent(bankKey)}/draft/publish`,
    payload
  );
  return toQuestionBankVersion(response);
};

const DEFAULT_QUESTION_BANK_ERROR_MESSAGES: SafeErrorMessages = {
  default: "Unable to update question bank.",
  accessDenied: "You do not have access to manage the question bank.",
  network: "Question bank service is unavailable. Try again shortly.",
  notFound: "Question bank resource not found.",
  sessionExpired: "Your session expired. Please sign in again.",
  unavailable: "Question bank service is unavailable. Try again shortly.",
};

export const getQuestionBankAdminErrorMessage = (
  error: unknown,
  messages: SafeErrorMessages = DEFAULT_QUESTION_BANK_ERROR_MESSAGES
): string => getSafeErrorMessage(error, messages);
