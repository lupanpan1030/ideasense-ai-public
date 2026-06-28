const INVALID_PROJECT_IDS = new Set(["undefined", "null"]);

export const normalizeProjectId = (
  value: string | null | undefined
): string | null => {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const lowered = trimmed.toLowerCase();
  if (INVALID_PROJECT_IDS.has(lowered)) {
    return null;
  }

  return trimmed;
};
