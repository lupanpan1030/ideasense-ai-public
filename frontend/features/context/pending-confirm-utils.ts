import { ApiError } from "@/lib/api/client";
import {
  PendingConfirmErrorDetails,
  PendingConfirmItem,
  PendingConfirmResolveOptions,
} from "./pending-confirm-types";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isPlainRecord = (value: unknown): value is Record<string, unknown> =>
  isRecord(value) && !Array.isArray(value);

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

type PendingConfirmMeta = {
  source: string | null;
  createdAt: string | null;
  priority: number | null;
  currentValue: unknown;
};

const normalizePriority = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const normalizeCreatedAt = (value: unknown): string | null => {
  const trimmed = toTrimmedString(value);
  if (!trimmed) {
    return null;
  }
  const timestamp = Date.parse(trimmed);
  if (Number.isNaN(timestamp)) {
    return null;
  }
  return trimmed;
};

const hasSuggestedValue = (value: Record<string, unknown>): boolean =>
  "value" in value || "suggested_value" in value || "suggested" in value;

const isMetaRecord = (value: Record<string, unknown>): boolean =>
  hasSuggestedValue(value);

const extractMeta = (value: Record<string, unknown>): PendingConfirmMeta => {
  const source = toTrimmedString(value.source);
  const createdAt = normalizeCreatedAt(value.created_at ?? value.createdAt);
  const priority = normalizePriority(value.priority);
  const currentValue = "current_value" in value ? value.current_value : undefined;
  return { source, createdAt, priority, currentValue };
};

const extractSuggestedValue = (value: Record<string, unknown>): unknown => {
  if ("value" in value) {
    return value.value;
  }
  if ("suggested_value" in value) {
    return value.suggested_value;
  }
  if ("suggested" in value) {
    return value.suggested;
  }
  if ("current_value" in value) {
    return value.current_value;
  }
  return value;
};

const normalizePendingValueForCompare = (value: unknown): unknown => {
  if (isPlainRecord(value) && isMetaRecord(value)) {
    return extractSuggestedValue(value);
  }
  return value;
};

const buildPendingItem = (path: string, value: unknown): PendingConfirmItem => {
  if (isPlainRecord(value) && isMetaRecord(value)) {
    const meta = extractMeta(value);
    return {
      path,
      value: extractSuggestedValue(value),
      source: meta.source,
      createdAt: meta.createdAt,
      priority: meta.priority,
      currentValue: meta.currentValue,
    };
  }
  return {
    path,
    value,
    source: null,
    createdAt: null,
    priority: null,
    currentValue: undefined,
  };
};

const parseCreatedAt = (value: string | null): number | null => {
  if (!value) {
    return null;
  }
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
};

const sortPendingItems = (items: PendingConfirmItem[]): PendingConfirmItem[] => {
  const withIndex = items.map((item, index) => ({ item, index }));
  withIndex.sort((left, right) => {
    const priorityA = left.item.priority;
    const priorityB = right.item.priority;
    if (priorityA !== null || priorityB !== null) {
      if (priorityA !== null && priorityB !== null && priorityA !== priorityB) {
        return priorityA - priorityB;
      }
      if (priorityA !== null) {
        return -1;
      }
      if (priorityB !== null) {
        return 1;
      }
    }

    const createdA = parseCreatedAt(left.item.createdAt);
    const createdB = parseCreatedAt(right.item.createdAt);
    if (createdA !== null || createdB !== null) {
      if (createdA !== null && createdB !== null && createdA !== createdB) {
        return createdB - createdA;
      }
      if (createdA !== null) {
        return -1;
      }
      if (createdB !== null) {
        return 1;
      }
    }

    const pathCompare = left.item.path.localeCompare(right.item.path);
    if (pathCompare !== 0) {
      return pathCompare;
    }
    return left.index - right.index;
  });
  return withIndex.map(({ item }) => item);
};

export const flattenPendingConfirm = (
  value: unknown,
  prefix = ""
): PendingConfirmItem[] => {
  if (!isPlainRecord(value)) {
    if (!prefix) {
      return [];
    }
    return [buildPendingItem(prefix, value)];
  }

  const entries = Object.entries(value);
  if (!entries.length) {
    return [];
  }

  const items = entries.flatMap(([key, nested]) => {
    const nextPath = prefix ? `${prefix}.${key}` : key;
    if (isPlainRecord(nested) && !isMetaRecord(nested)) {
      return flattenPendingConfirm(nested, nextPath);
    }
    return [buildPendingItem(nextPath, nested)];
  });

  return sortPendingItems(items);
};

type PathLookup = {
  found: boolean;
  value: unknown;
};

const splitPath = (path: string): string[] => {
  if (typeof path !== "string") {
    return [];
  }
  const trimmed = path.trim();
  if (!trimmed) {
    return [];
  }
  return trimmed
    .split(".")
    .map((segment) => segment.trim().replace(/\\[\\]$/, ""))
    .filter(Boolean);
};

const getPathValue = (
  target: Record<string, unknown> | null,
  path: string
): PathLookup => {
  if (!target) {
    return { found: false, value: null };
  }
  const parts = splitPath(path);
  if (!parts.length) {
    return { found: false, value: null };
  }
  let cursor: unknown = target;
  for (const segment of parts) {
    if (!isRecord(cursor) || !(segment in cursor)) {
      return { found: false, value: null };
    }
    cursor = cursor[segment];
  }
  return { found: true, value: cursor };
};

export const getPendingConfirmPathValue = (
  target: Record<string, unknown> | null,
  path: string
): PathLookup => getPathValue(target, path);

const deepEqual = (left: unknown, right: unknown): boolean => {
  if (Object.is(left, right)) {
    return true;
  }
  if (Array.isArray(left) && Array.isArray(right)) {
    if (left.length !== right.length) {
      return false;
    }
    return left.every((value, index) => deepEqual(value, right[index]));
  }
  if (isRecord(left) && isRecord(right)) {
    const leftKeys = Object.keys(left);
    const rightKeys = Object.keys(right);
    if (leftKeys.length !== rightKeys.length) {
      return false;
    }
    return leftKeys.every((key) => deepEqual(left[key], right[key]));
  }
  return false;
};

export const findPendingConfirmOverrides = (
  pendingData: Record<string, unknown>,
  mergedData: Record<string, unknown> | null,
  paths: string[]
): string[] => {
  if (!mergedData || !paths.length) {
    return [];
  }
  return paths.filter((path) => {
    const pendingValue = getPathValue(pendingData, path);
    if (!pendingValue.found) {
      return false;
    }
    const mergedValue = getPathValue(mergedData, path);
    if (!mergedValue.found) {
      return false;
    }
    const normalizedPendingValue = normalizePendingValueForCompare(
      pendingValue.value
    );
    return !deepEqual(normalizedPendingValue, mergedValue.value);
  });
};

export const isPendingConfirmConflict = (error: unknown): boolean => {
  return error instanceof ApiError && error.status === 409;
};

export const shouldRequirePendingOverrideConfirmation = (
  action: "accept" | "reject",
  overridePaths: string[],
  options: PendingConfirmResolveOptions = {}
): boolean => {
  if (action !== "accept") {
    return false;
  }
  if (options.overridesAcknowledged) {
    return false;
  }
  return overridePaths.length > 0;
};

export const getPendingConfirmErrorDetails = (
  error: unknown
): PendingConfirmErrorDetails => {
  if (isPendingConfirmConflict(error)) {
    return { type: "conflict", message: "Context updated, please refresh." };
  }
  return { type: "error", message: "Unable to resolve pending updates." };
};
