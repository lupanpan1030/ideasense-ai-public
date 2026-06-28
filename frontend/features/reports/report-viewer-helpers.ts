import type { ReportStageSummary } from "./reports-normalize";

export const LEAN_CANVAS_FIELDS = [
  { key: "problem", label: "Problem" },
  { key: "customerSegments", label: "Customer segments" },
  { key: "uniqueValueProposition", label: "Unique value proposition" },
  { key: "solution", label: "Solution" },
  { key: "channels", label: "Channels" },
  { key: "revenueStreams", label: "Revenue streams" },
  { key: "costStructure", label: "Cost structure" },
  { key: "keyMetrics", label: "Key metrics" },
  { key: "unfairAdvantage", label: "Unfair advantage" },
] as const;

const scoreFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

export const formatScore = (value: number | null): string =>
  typeof value === "number" ? scoreFormatter.format(value) : "-";

const resolveIntlLocale = (locale?: string) =>
  locale && locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const formatDateTime = (
  value: string | null,
  options?: {
    locale?: string;
    fallback?: string;
  }
): string => {
  const fallback = options?.fallback ?? "Unknown";
  if (!value) {
    return fallback;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }
  return new Intl.DateTimeFormat(resolveIntlLocale(options?.locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
};

export const resolveDecisionVariant = (
  value: string | null
): "info" | "warning" => {
  if (!value) {
    return "info";
  }
  const normalized = value.toLowerCase();
  if (
    normalized.includes("hold") ||
    normalized.includes("watch") ||
    normalized.includes("pivot")
  ) {
    return "warning";
  }
  return "info";
};

export const resolveStageStatus = (
  stage: ReportStageSummary,
  labels?: {
    confirmed: string;
    draft: string;
    pending: string;
  }
) => {
  const resolved = labels ?? {
    confirmed: "Confirmed summary",
    draft: "Draft summary (awaiting confirmation)",
    pending: "Pending summary",
  };
  if (stage.status === "confirmed") {
    return resolved.confirmed;
  }
  if (stage.status === "draft") {
    return resolved.draft;
  }
  return resolved.pending;
};

export const formatScoreStatus = (
  value: string | null,
  fallback = "Not scored"
): string => {
  if (!value) {
    return fallback;
  }
  return value.replace(/_/g, " ");
};

const listItemRegex = /^\s*(?:[-*•]|\d+\.)\s+(.+)$/;

export const formatNarrativeMarkdown = (value: string): string => {
  const lines = value.split(/\r?\n/);
  const output: string[] = [];
  let buffer: string[] = [];

  const flush = () => {
    if (!buffer.length) {
      return;
    }
    let paragraph = buffer.join("; ");
    if (!/[.!?。！？]$/.test(paragraph)) {
      paragraph += ".";
    }
    output.push(paragraph);
    buffer = [];
  };

  for (const line of lines) {
    const match = line.match(listItemRegex);
    if (match) {
      const item = match[1].trim();
      if (item) {
        buffer.push(item);
      }
      continue;
    }
    flush();
    output.push(line);
  }

  flush();
  return output.join("\n");
};
