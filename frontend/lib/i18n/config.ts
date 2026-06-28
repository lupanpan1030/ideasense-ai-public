export const SUPPORTED_APP_LOCALES = ["en", "zh"] as const;
export const APP_LOCALE_COOKIE_NAME = "ideasense.locale";

export type AppLocale = (typeof SUPPORTED_APP_LOCALES)[number];

export const DEFAULT_APP_LOCALE: AppLocale = "en";

export const isSupportedAppLocale = (value: unknown): value is AppLocale =>
  typeof value === "string" &&
  (SUPPORTED_APP_LOCALES as readonly string[]).includes(value);

export const normalizeAppLocale = (value: unknown): AppLocale =>
  isSupportedAppLocale(value) ? value : DEFAULT_APP_LOCALE;

export const extractLocaleFromPathname = (pathname: string | null): AppLocale | null => {
  if (!pathname) {
    return null;
  }

  const [, firstSegment] = pathname.split("/");
  return isSupportedAppLocale(firstSegment) ? firstSegment : null;
};

export const stripLocalePrefix = (pathname: string): string => {
  const locale = extractLocaleFromPathname(pathname);
  if (!locale) {
    return pathname || "/";
  }

  const normalized = pathname.replace(new RegExp(`^/${locale}`), "") || "/";
  return normalized.startsWith("/") ? normalized : `/${normalized}`;
};

export const buildLocalePath = (
  locale: AppLocale,
  pathname: string | null,
  search?: string | null
): string => {
  const normalizedPath = stripLocalePrefix(pathname || "/");
  const prefixedPath = normalizedPath === "/" ? `/${locale}` : `/${locale}${normalizedPath}`;
  if (!search) {
    return prefixedPath;
  }
  return search.startsWith("?") ? `${prefixedPath}${search}` : `${prefixedPath}?${search}`;
};
