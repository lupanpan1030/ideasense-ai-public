import {
  isSupportedAppLocale,
  normalizeAppLocale,
  type AppLocale,
} from "./config";
import type { AppMessages } from "./messages";

export const normalizeArtifactLocale = (value: unknown): AppLocale | null =>
  isSupportedAppLocale(value) ? normalizeAppLocale(value) : null;

export const getLocaleDisplayName = (
  messages: AppMessages,
  locale: AppLocale | null | undefined
): string | null => {
  if (!locale) {
    return null;
  }
  return messages.localeSwitcher.locales[locale]?.full ?? locale.toUpperCase();
};
