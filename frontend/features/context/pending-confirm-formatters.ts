type PendingConfirmFormatterMessages = {
  notSet: string;
  nullValue: string;
  modelInferred: string;
  userEdit: string;
};

const DEFAULT_FORMATTER_MESSAGES: PendingConfirmFormatterMessages = {
  notSet: "Not set",
  nullValue: "null",
  modelInferred: "Model inferred",
  userEdit: "User edit",
};

export const formatValue = (
  value: unknown,
  messages: PendingConfirmFormatterMessages = DEFAULT_FORMATTER_MESSAGES
): string => {
  if (value === undefined) {
    return messages.notSet;
  }
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return messages.nullValue;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export const formatSource = (
  value: string | null,
  messages: PendingConfirmFormatterMessages = DEFAULT_FORMATTER_MESSAGES
): string => {
  if (!value) {
    return messages.modelInferred;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === "user") {
    return messages.userEdit;
  }
  return value;
};

export const formatCreatedAt = (
  value: string | null,
  locale = "en-US"
): string | null => {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
  }).format(date);
};
