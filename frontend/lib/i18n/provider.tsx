"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import {
  APP_LOCALE_COOKIE_NAME,
  DEFAULT_APP_LOCALE,
  extractLocaleFromPathname,
  type AppLocale,
} from "./config";
import {
  APP_MESSAGES,
  DEFAULT_APP_MESSAGES,
  type AppMessages,
} from "./messages";

type AppI18nContextValue = {
  locale: AppLocale;
  messages: AppMessages;
};

const AppI18nContext = createContext<AppI18nContextValue>({
  locale: DEFAULT_APP_LOCALE,
  messages: DEFAULT_APP_MESSAGES,
});

export function AppI18nProvider({
  children,
  initialLocale = DEFAULT_APP_LOCALE,
}: {
  children: ReactNode;
  initialLocale?: AppLocale;
}) {
  const pathname = usePathname();
  const locale = extractLocaleFromPathname(pathname) ?? initialLocale;
  const messages = APP_MESSAGES[locale] ?? DEFAULT_APP_MESSAGES;

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dataset.locale = locale;
    document.cookie = `${APP_LOCALE_COOKIE_NAME}=${locale}; Path=/; Max-Age=31536000; SameSite=Lax`;
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      messages,
    }),
    [locale, messages]
  );

  return (
    <AppI18nContext.Provider value={value}>{children}</AppI18nContext.Provider>
  );
}

export function useAppI18n(): AppI18nContextValue {
  return useContext(AppI18nContext);
}

export function useAppLocale(): AppLocale {
  return useAppI18n().locale;
}

export function useAppMessages(): AppMessages {
  return useAppI18n().messages;
}
