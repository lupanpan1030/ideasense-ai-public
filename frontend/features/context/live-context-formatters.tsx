import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { AnswerMetaEntry } from "./project-context";
import type { StageSummaryGenerationStatus } from "@/features/assessments/api";
import type { AppMessages } from "@/lib/i18n/messages";

export const STAGES = [
  { key: "problem" },
  { key: "market" },
  { key: "tech" },
] as const;

export type StageKey = (typeof STAGES)[number]["key"];
export type ViewMode = "draft" | "insight" | "diagnosis";
export type ReviewSummaryStatus = StageSummaryGenerationStatus | "idle" | "error";
export type LiveContextMessages = AppMessages["liveContext"];

export type ContextField = {
  path: string;
  label: string;
  value: unknown;
};

export type ContextSection = {
  key: string;
  label: string;
  fields: ContextField[];
};

const ANSWER_STATUS_VARIANTS: Record<
  string,
  "default" | "outline" | "secondary" | "success" | "warning" | "danger" | "info"
> = {
  answered: "success",
  partial: "info",
  unknown: "warning",
  undecided: "secondary",
  not_applicable: "secondary",
  suggested: "info",
};

const UNRESOLVED_ANSWER_STATUSES = new Set([
  "unknown",
  "undecided",
  "not_applicable",
]);

const UNKNOWN_VALUE_STRINGS = new Set([
  "unknown",
  "unsure",
  "not sure",
  "i'm not sure",
  "i am not sure",
  "undecided",
  "n/a",
  "na",
  "未知",
  "不确定",
  "不知道",
  "未决定",
]);

export const STAGE_ORDER = new Map<StageKey, number>(
  STAGES.map((stage, index) => [stage.key, index])
);

const STAGE_ROOT_KEYS: Record<StageKey, string[]> = {
  problem: [
    "problem_user",
    "problem",
    "target_user",
    "impact",
    "alternatives",
    "evidence",
  ],
  market: ["market_strategy"],
  tech: ["tech_execution"],
};

export const resolveLatestContextVersion = (
  ...candidates: Array<number | null | undefined>
): number | null => {
  const values = candidates.filter(
    (value): value is number => typeof value === "number" && Number.isFinite(value)
  );
  if (!values.length) {
    return null;
  }
  return Math.max(...values);
};

export const resolveStageDraftUserError = (
  rawError: string | null | undefined,
  appMessages: AppMessages
): string =>
  rawError
    ? appMessages.stageGate.modal.summaryPreparationFailedRetry
    : appMessages.stageGate.loading.descriptionPreparingSummary;

export const formatLabel = (value: string) =>
  value
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());

export const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const normalizeStageKey = (
  value: string | null | undefined
): StageKey | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim().toLowerCase();
  return STAGES.find((stage) => stage.key === trimmed)?.key ?? null;
};

export const resolveStageKey = (value: string | null | undefined): StageKey => {
  const trimmed = value?.trim().toLowerCase() ?? "";
  if (trimmed === "report") {
    return "tech";
  }
  return normalizeStageKey(value) ?? "problem";
};

export const resolveStageLabel = (
  stage: string | null | undefined,
  messages: LiveContextMessages
): string => {
  const key = normalizeStageKey(stage);
  if (!key) {
    return stage?.trim() || messages.stageLabels.problem;
  }
  return messages.stageLabels[key] ?? formatLabel(key);
};

const formatPathLabel = (path: string, messages: LiveContextMessages) => {
  const mapped = messages.contextFieldLabels[path];
  if (mapped) {
    return mapped;
  }
  const lastSegment = path.split(".").pop() ?? path;
  return formatLabel(lastSegment);
};

const truncateValue = (value: string, max = 72) =>
  value.length > max ? `${value.slice(0, max).trim()}...` : value;

const formatAnswerMetaLabel = (
  value: string,
  messages: LiveContextMessages
): string => messages.answerStatuses[value] ?? formatLabel(value);

export const renderAnswerMetaBadges = (
  entry: AnswerMetaEntry | undefined,
  messages: LiveContextMessages
): ReactNode => {
  if (!entry) {
    return null;
  }
  return (
    <div className="cluster-tight">
      <Badge
        variant={ANSWER_STATUS_VARIANTS[entry.resolutionStatus] ?? "secondary"}
      >
        {formatAnswerMetaLabel(entry.resolutionStatus, messages)}
      </Badge>
      <Badge variant="outline">{formatLabel(entry.claimType)}</Badge>
      <Badge variant="outline">{entry.evidenceLevel}</Badge>
    </div>
  );
};

const isUnknownValue = (value: unknown): boolean => {
  if (typeof value !== "string") {
    return false;
  }
  const normalized = value.trim().toLowerCase().replace(/\s+/g, " ");
  return UNKNOWN_VALUE_STRINGS.has(normalized);
};

export const isUnresolvedAnswer = (entry: AnswerMetaEntry | undefined): boolean =>
  Boolean(entry && UNRESOLVED_ANSWER_STATUSES.has(entry.resolutionStatus));

export const resolveConfirmedDisplayValue = (
  value: unknown,
  entry: AnswerMetaEntry | undefined
): unknown => {
  if (isUnresolvedAnswer(entry) || isUnknownValue(value)) {
    return null;
  }
  return value;
};

export const resolveVerificationBadge = (
  status: string,
  messages: LiveContextMessages
) => {
  switch (status) {
    case "supported":
      return { label: messages.verificationStatuses.supported, variant: "success" as const };
    case "verified":
      return { label: messages.verificationStatuses.verified, variant: "success" as const };
    case "contradicted":
      return {
        label: messages.verificationStatuses.contradicted,
        variant: "danger" as const,
      };
    case "uncertain":
      return {
        label: messages.verificationStatuses.uncertain,
        variant: "warning" as const,
      };
    case "verifying":
      return { label: messages.verificationStatuses.verifying, variant: "info" as const };
    case "not_applicable":
      return {
        label: messages.verificationStatuses.not_applicable,
        variant: "secondary" as const,
      };
    case "failed":
      return { label: messages.verificationStatuses.failed, variant: "danger" as const };
    case "stale":
      return { label: messages.verificationStatuses.stale, variant: "warning" as const };
    case "provider_unavailable":
      return {
        label: messages.verificationStatuses.provider_unavailable,
        variant: "secondary" as const,
      };
    case "no_evidence":
    case "not_checked":
    default:
      return { label: messages.verificationStatuses.not_checked, variant: "secondary" as const };
  }
};

export const stableStringify = (value: unknown): string => {
  if (value === undefined) {
    return "__undefined__";
  }
  if (value === null) {
    return "null";
  }
  if (typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  return `{${keys
    .map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`)
    .join(",")}}`;
};

const formatBadgeValue = (value: unknown): string => {
  if (typeof value === "string") {
    return value.trim();
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value === null || value === undefined) {
    return "";
  }
  if (isPlainObject(value)) {
    return truncateValue(JSON.stringify(value));
  }
  return truncateValue(String(value));
};

type ValueTone = "confirmed" | "draft";

const VALUE_TONE_STYLES: Record<ValueTone, { text: string; muted: string }> = {
  confirmed: {
    text: "context-value",
    muted: "context-value context-value--muted",
  },
  draft: {
    text: "context-value context-value--accent",
    muted: "context-value context-value--muted",
  },
};

export const renderValue = (
  value: unknown,
  tone: ValueTone = "confirmed",
  emptyLabel = ""
): ReactNode => {
  const toneStyles = VALUE_TONE_STYLES[tone];

  if (value === null || value === undefined) {
    return (
      <span className={`${toneStyles.muted} context-value--empty`}>
        {emptyLabel}
      </span>
    );
  }

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    const text = typeof value === "string" ? value.trim() : String(value);
    if (!text) {
      return (
        <span className={`${toneStyles.muted} context-value--empty`}>
          {emptyLabel}
        </span>
      );
    }
    return <span className={toneStyles.text}>{text}</span>;
  }

  if (Array.isArray(value)) {
    const objectItems = value.filter((item) => isPlainObject(item));
    if (objectItems.length === value.length && objectItems.length > 0) {
      return (
        <div className="context-value__stack">
          {objectItems.map((item, index) => (
            <div key={`object-${index}`} className="context-value__group">
              {renderValue(item, tone, emptyLabel)}
            </div>
          ))}
        </div>
      );
    }
    const filtered = value
      .map(formatBadgeValue)
      .filter((item) => item && item.trim().length > 0);
    if (!filtered.length) {
      return (
        <span className={`${toneStyles.muted} context-value--empty`}>
          {emptyLabel}
        </span>
      );
    }
    return (
      <ul className={`context-value__list ${toneStyles.text}`}>
        {filtered.map((item, index) => (
          <li key={`${item}-${index}`} className="context-value__item">
            {item}
          </li>
        ))}
      </ul>
    );
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value).filter(
      ([, entryValue]) => entryValue !== undefined
    );
    if (!entries.length) {
      return (
        <span className={`${toneStyles.muted} context-value--empty`}>
          {emptyLabel}
        </span>
      );
    }
    return (
      <div className="context-value__stack">
        {entries
          .sort(([left], [right]) => left.localeCompare(right))
          .map(([key, entryValue]) => (
            <div key={key} className="context-value__stack">
              <div className={`${toneStyles.muted} context-value__label`}>
                {formatLabel(key)}
              </div>
              <div>{renderValue(entryValue, tone, emptyLabel)}</div>
            </div>
          ))}
      </div>
    );
  }

  return <span className={toneStyles.text}>{String(value)}</span>;
};

export type EditMode = "text" | "number" | "boolean" | "string_list";

export const isStringList = (value: unknown): value is string[] =>
  Array.isArray(value) &&
  value.every((item) => typeof item === "string");

export const isEditableValue = (value: unknown) => {
  if (isPlainObject(value)) {
    return false;
  }
  if (Array.isArray(value) && !isStringList(value)) {
    return false;
  }
  return true;
};

export const resolveEditMode = (value: unknown): EditMode => {
  if (isStringList(value)) {
    return "string_list";
  }
  if (typeof value === "number") {
    return "number";
  }
  if (typeof value === "boolean") {
    return "boolean";
  }
  return "text";
};

export const formatDraftValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

export const ListeningIndicator = ({ label }: { label: string }) => (
  <div className="context-listening">
    <span className="context-listening__line" />
    <span className="context-listening__label">{label}</span>
    <span className="context-listening__line" />
  </div>
);

export const inferStageForPath = (path: string, fallback: StageKey): StageKey => {
  const root = path.split(".")[0]?.trim();
  if (!root) {
    return fallback;
  }
  for (const [stage, roots] of Object.entries(STAGE_ROOT_KEYS)) {
    if (roots.includes(root)) {
      return stage as StageKey;
    }
  }
  if (root.startsWith("problem")) {
    return "problem";
  }
  if (root.startsWith("market")) {
    return "market";
  }
  if (root.startsWith("tech")) {
    return "tech";
  }
  return fallback;
};

export const isReportStage = (value: string | null | undefined) =>
  value?.trim().toLowerCase() === "report";

export const buildContextSections = (
  snapshot: Record<string, unknown> | null,
  activeStage: StageKey,
  answerMeta: Record<string, AnswerMetaEntry> = {},
  messages: LiveContextMessages
): ContextSection[] => {
  if (!snapshot) {
    return [];
  }

  const allowedRoots = STAGE_ROOT_KEYS[activeStage] ?? [];
  const entries = Object.entries(snapshot)
    .filter(([key]) => (allowedRoots.length ? allowedRoots.includes(key) : true))
    .sort(([left], [right]) => left.localeCompare(right));

  const flattenEntries = (
    value: Record<string, unknown>,
    prefix: string[] = []
  ): ContextField[] =>
    Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .flatMap(([key, entryValue]) => {
        const nextPath = [...prefix, key];
        if (isPlainObject(entryValue)) {
          return flattenEntries(entryValue, nextPath);
        }
        return [
          {
            path: nextPath.join("."),
            label: formatPathLabel(nextPath.join("."), messages),
            value: entryValue,
          },
        ];
      });

  const sections = entries.map(([key, value]) => {
    const fields = isPlainObject(value)
      ? flattenEntries(value, [key])
      : [
          {
            path: key,
            label: formatPathLabel(key, messages),
            value,
          },
        ];
    return {
      key,
      label: messages.contextSectionLabels[key] ?? formatLabel(key),
      fields,
    };
  });

  const knownPaths = new Set(
    sections.flatMap((section) => section.fields.map((field) => field.path))
  );
  const statusFields = Object.entries(answerMeta)
    .filter(([path, entry]) => {
      if (knownPaths.has(path)) {
        return false;
      }
      if (!entry || entry.resolutionStatus === "answered") {
        return false;
      }
      return inferStageForPath(path, activeStage) === activeStage;
    })
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([path, entry]) => ({
      path,
      label: formatPathLabel(path, messages),
      value:
        entry.note ??
        (entry.resolutionStatus === "not_applicable"
          ? messages.markedNotApplicable
          : messages.noConfirmedValue),
    }));

  if (statusFields.length) {
    sections.push({
      key: "answer_meta_status",
      label: messages.statusTrackingTitle,
      fields: statusFields,
    });
  }

  return sections;
};
