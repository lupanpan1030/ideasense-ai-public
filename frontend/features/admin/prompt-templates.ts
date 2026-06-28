import { apiClient } from "@/lib/api/client";
import {
  getSafeErrorMessage,
  type SafeErrorMessages,
} from "@/lib/api/safe-error-message";

export type PromptTemplate = {
  id: string;
  templateKey: string;
  version: string;
  content: string;
  purpose: string;
  stage: string | null;
  variant: string | null;
  orgId: string | null;
  isActive: boolean;
  createdAt: string | null;
  updatedAt: string | null;
};

export type PromptTemplateCreatePayload = {
  content: string;
  purpose?: string | null;
  stage?: string | null;
  variant?: string | null;
  version?: string | null;
};

export type PromptTemplateRevertResponse = {
  reverted: boolean;
  effectiveTemplate: PromptTemplate | null;
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

const toPromptTemplate = (value: unknown): PromptTemplate => {
  if (!isRecord(value)) {
    throw new Error("Invalid prompt template payload.");
  }
  const id = toOptionalString(value.id) ?? "";
  const templateKey = toOptionalString(value.template_key) ?? "";
  const version = toOptionalString(value.version) ?? "";
  const content = toOptionalString(value.content) ?? "";
  const purpose = toOptionalString(value.purpose) ?? "";
  if (!id || !templateKey) {
    throw new Error("Prompt template payload missing identifiers.");
  }
  return {
    id,
    templateKey,
    version,
    content,
    purpose,
    stage: toOptionalString(value.stage),
    variant: toOptionalString(value.variant),
    orgId: toOptionalString(value.org_id),
    isActive: Boolean(value.is_active),
    createdAt: toOptionalString(value.created_at),
    updatedAt: toOptionalString(value.updated_at),
  };
};

export const fetchPromptTemplates = async (): Promise<PromptTemplate[]> => {
  const response = await apiClient.fetchJson<unknown>("/admin-api/prompts");
  if (!isRecord(response) || !Array.isArray(response.templates)) {
    throw new Error("Invalid prompt templates payload.");
  }
  return response.templates.map(toPromptTemplate);
};

export const createPromptTemplate = async (
  templateKey: string,
  payload: PromptTemplateCreatePayload
): Promise<PromptTemplate> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/prompts/${encodeURIComponent(templateKey)}`,
    payload
  );
  return toPromptTemplate(response);
};

export const revertPromptTemplate = async (
  templateKey: string
): Promise<PromptTemplateRevertResponse> => {
  const response = await apiClient.postJson<unknown>(
    `/admin-api/prompts/${encodeURIComponent(templateKey)}/revert`,
    {}
  );
  if (!isRecord(response)) {
    throw new Error("Invalid prompt revert response.");
  }
  const effectiveTemplate = response.effective_template
    ? toPromptTemplate(response.effective_template)
    : null;
  return {
    reverted: Boolean(response.reverted),
    effectiveTemplate,
  };
};

const DEFAULT_PROMPT_TEMPLATE_ERROR_MESSAGES: SafeErrorMessages = {
  default: "Unable to update prompt templates.",
  accessDenied: "You do not have access to manage prompt templates.",
  network: "Prompt templates are unavailable. Try again shortly.",
  sessionExpired: "Your session expired. Please sign in again.",
  unavailable: "Prompt templates are unavailable. Try again shortly.",
};

export const getPromptTemplatesErrorMessage = (
  error: unknown,
  messages: SafeErrorMessages = DEFAULT_PROMPT_TEMPLATE_ERROR_MESSAGES
): string => getSafeErrorMessage(error, messages);
