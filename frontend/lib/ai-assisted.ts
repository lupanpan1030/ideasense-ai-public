const AI_ASSISTED_ALIAS_SOURCE = String.raw`ai-assisted|ai assist|ai辅助|ai补全`;

const AI_ASSISTED_ALIAS_PATTERN = new RegExp(AI_ASSISTED_ALIAS_SOURCE, "i");
const BRACKETED_AI_ASSISTED_MARKER_PATTERN = new RegExp(
  String.raw`\[\s*(?:${AI_ASSISTED_ALIAS_SOURCE})\s*\]\s*`,
  "gi"
);
const STANDALONE_AI_ASSISTED_LINE_PATTERN = new RegExp(
  String.raw`^\s*(?:[-*•]\s*)?(?:\[\s*)?(?:${AI_ASSISTED_ALIAS_SOURCE})(?:\s*\])?(?:\s+inputs?)?\s*:?\s*$`,
  "i"
);
const INLINE_AI_ASSISTED_ALIAS_PATTERN = new RegExp(
  AI_ASSISTED_ALIAS_SOURCE,
  "gi"
);

export const hasAiAssistedCopy = (value: string | null | undefined): boolean =>
  Boolean(value && AI_ASSISTED_ALIAS_PATTERN.test(value));

export const normalizeLegacyAiAssistedCopy = (
  value: string | null | undefined
): string => {
  if (!value) {
    return "";
  }

  const cleaned = value
    .split(/\r?\n/)
    .map((line) =>
      line
        .replace(BRACKETED_AI_ASSISTED_MARKER_PATTERN, "")
        .replace(INLINE_AI_ASSISTED_ALIAS_PATTERN, "AI-assisted")
        .trimEnd()
    )
    .filter((line) => !STANDALONE_AI_ASSISTED_LINE_PATTERN.test(line.trim()))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return cleaned;
};
