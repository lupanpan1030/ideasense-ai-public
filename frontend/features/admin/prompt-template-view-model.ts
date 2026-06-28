import type { PromptTemplate } from "@/features/admin/prompt-templates";
import type { PromptMessages } from "@/features/admin/prompt-template-messages";

export type PromptGroup = {
  key: string;
  org?: PromptTemplate;
  global?: PromptTemplate;
};

export type PurposeKey = "all" | "chat" | "report" | "summary" | "score" | "extract" | "evaluate";
export type StageKey = "all" | "problem" | "market" | "tech" | "report";
export type StageValue = Exclude<StageKey, "all">;
export type SourceKey = "all" | "org" | "global";

export const PURPOSE_KEYS: PurposeKey[] = [
  "all",
  "chat",
  "report",
  "summary",
  "score",
  "extract",
  "evaluate",
];
export const STAGE_KEYS: StageKey[] = ["all", "problem", "market", "tech", "report"];
export const STAGE_VALUES: StageValue[] = ["problem", "market", "tech", "report"];
export const SOURCE_KEYS: SourceKey[] = ["all", "org", "global"];

export const parseStageList = (value: string | null): StageValue[] => {
  if (!value) {
    return [];
  }
  const parts = value
    .split(",")
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
  const stages = new Set<StageValue>();
  parts.forEach((part) => {
    if (STAGE_VALUES.includes(part as StageValue)) {
      stages.add(part as StageValue);
    }
  });
  return Array.from(stages);
};

export const formatStageLabel = (
  value: string | null,
  messages: PromptMessages
): string | null => {
  const stages = parseStageList(value);
  if (!stages.length) {
    return null;
  }
  if (stages.length === 1) {
    return `${messages.meta.stage}: ${messages.stages[stages[0]]}`;
  }
  return `${messages.meta.stages}: ${stages
    .map((stage) => messages.stages[stage])
    .join(" · ")}`;
};

export const groupTemplates = (templates: PromptTemplate[]): PromptGroup[] => {
  const map = new Map<string, PromptGroup>();
  templates.forEach((template) => {
    const key = template.templateKey;
    const group = map.get(key) ?? { key };
    if (template.orgId) {
      group.org = template;
    } else {
      group.global = template;
    }
    map.set(key, group);
  });
  return Array.from(map.values()).sort((a, b) => a.key.localeCompare(b.key));
};
