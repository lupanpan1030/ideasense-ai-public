import { cookies, headers } from "next/headers";

import {
  APP_LOCALE_COOKIE_NAME,
  isSupportedAppLocale,
  normalizeAppLocale,
  type AppLocale,
} from "./config";

const INTERNAL_LOCALE_HEADER = "x-ideasense-locale";

export async function getRequestLocale(): Promise<AppLocale> {
  const requestHeaders = await headers();
  const headerLocale = requestHeaders.get(INTERNAL_LOCALE_HEADER);
  if (isSupportedAppLocale(headerLocale)) {
    return headerLocale;
  }

  const cookieStore = await cookies();
  return normalizeAppLocale(cookieStore.get(APP_LOCALE_COOKIE_NAME)?.value);
}
