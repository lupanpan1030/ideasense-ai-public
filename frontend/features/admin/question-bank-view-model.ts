import type { QuestionBankQuestion } from "@/features/admin/question-banks";

export const formatQuestionBankTimestamp = (
  value: string | null,
  locale: "en" | "zh",
  unknownLabel: string
) => {
  if (!value) {
    return unknownLabel;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return unknownLabel;
  }
  return date.toLocaleString(locale === "zh" ? "zh-CN" : "en-US");
};

export const questionBankListToText = (items: string[]) => items.join("\n");

export const questionBankTextToList = (value: string): string[] =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

export const formatQuestionBankQuestionLabel = (question: QuestionBankQuestion) =>
  `${question.orderIndex}. ${question.title || question.questionId}`;

export const safeQuestionBankJsonStringify = (value: unknown) => {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
};

export const parseQuestionBankJson = (
  value: string,
  objectErrorMessage: string
): Record<string, unknown> => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error(objectErrorMessage);
  }
  return parsed as Record<string, unknown>;
};

export const formatQuestionBankStageValue = (
  stage: string,
  stages: Record<string, string>
): string => stages[stage as keyof typeof stages] ?? stage;
