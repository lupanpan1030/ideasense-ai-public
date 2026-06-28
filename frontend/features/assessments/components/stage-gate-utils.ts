export const STAGE_LABELS: Record<string, string> = {
  problem: "Problem",
  market: "Market",
  tech: "Tech",
  report: "Report",
};

export const NEXT_STAGE_MAP: Record<string, string> = {
  problem: "market",
  market: "tech",
  tech: "report",
};

const resolveIntlLocale = (locale?: string) =>
  locale && locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const formatUpdatedAt = (
  value: string | null,
  options?: {
    locale?: string;
    prefix?: string;
    unknownLabel?: string;
  }
): string => {
  const prefix = options?.prefix ?? "Updated";
  const unknownLabel = options?.unknownLabel ?? "Updated unknown";
  if (!value) {
    return unknownLabel;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return unknownLabel;
  }
  const formatted = new Intl.DateTimeFormat(resolveIntlLocale(options?.locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
  return `${prefix} ${formatted}`;
};

export const formatScore = (value: number | null): string => {
  if (value === null || Number.isNaN(value)) {
    return "N/A";
  }
  if (Number.isInteger(value)) {
    return `${value}`;
  }
  return value.toFixed(1);
};

export const hasVisibleStageDraftSummary = (
  value?: { draftSummaryText?: string | null } | null
): boolean => Boolean(value?.draftSummaryText?.trim());

const escapeHtml = (value: string): string =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const formatInlineMarkdown = (value: string): string => {
  const code = value.replace(/`(.+?)`/g, "<code>$1</code>");
  const bold = code.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return bold.replace(/\*(.+?)\*/g, "<em>$1</em>");
};

export const renderMarkdown = (value: string): string => {
  const escaped = escapeHtml(value);
  const lines = escaped.split(/\r?\n/);
  const html: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  const openList = (type: "ul" | "ol") => {
    if (listType === type) {
      return;
    }
    closeList();
    html.push(`<${type}>`);
    listType = type;
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      openList("ul");
      html.push(`<li>${formatInlineMarkdown(trimmed.slice(2))}</li>`);
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+[\).]\s+(.+)$/);
    if (orderedMatch) {
      openList("ol");
      html.push(`<li>${formatInlineMarkdown(orderedMatch[1])}</li>`);
      continue;
    }

    closeList();

    if (trimmed.startsWith("### ")) {
      html.push(`<h4>${formatInlineMarkdown(trimmed.slice(4))}</h4>`);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      html.push(`<h3>${formatInlineMarkdown(trimmed.slice(3))}</h3>`);
      continue;
    }
    if (trimmed.startsWith("# ")) {
      html.push(`<h2>${formatInlineMarkdown(trimmed.slice(2))}</h2>`);
      continue;
    }

    html.push(`<p>${formatInlineMarkdown(trimmed)}</p>`);
  }

  closeList();
  return html.join("");
};
