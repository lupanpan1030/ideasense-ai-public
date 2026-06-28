import { NextResponse, type NextRequest } from "next/server";
import { adminUiEnabled } from "@/lib/admin-config";
import {
  APP_LOCALE_COOKIE_NAME,
  DEFAULT_APP_LOCALE,
  buildLocalePath,
  extractLocaleFromPathname,
  isSupportedAppLocale,
  normalizeAppLocale,
  stripLocalePrefix,
} from "@/lib/i18n/config";

const AUTH_COOKIE_NAME = "ideasense.auth.token";
const PUBLIC_FILE = /\.(.*)$/;
const AUTH_ROUTES = ["/login", "/register", "/logout"];
const AUTH_REDIRECT_ROUTES = ["/login", "/register"];
const APP_ROUTE = "/projects";
const ADMIN_ROUTE = "/admin";
const INTERNAL_LOCALE_HEADER = "x-ideasense-locale";

const isPathMatch = (pathname: string, prefix: string) =>
  pathname === prefix || pathname.startsWith(`${prefix}/`);

const isPublicRoute = (pathname: string) =>
  AUTH_ROUTES.some((route) => isPathMatch(pathname, route));

const isAuthRedirectRoute = (pathname: string) =>
  AUTH_REDIRECT_ROUTES.some((route) => isPathMatch(pathname, route));

const isProtectedRoute = (pathname: string) => isPathMatch(pathname, APP_ROUTE);

const isBypassRoute = (pathname: string) =>
  pathname.startsWith("/_next") || pathname.startsWith("/api") || PUBLIC_FILE.test(pathname);

const applyLocaleCookie = (response: NextResponse, locale: string) => {
  response.cookies.set(APP_LOCALE_COOKIE_NAME, locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
  return response;
};

const rewriteWithLocale = (
  request: NextRequest,
  pathname: string,
  locale: string
) => {
  const rewriteUrl = request.nextUrl.clone();
  rewriteUrl.pathname = pathname;
  const headers = new Headers(request.headers);
  headers.set(INTERNAL_LOCALE_HEADER, locale);
  return applyLocaleCookie(
    NextResponse.rewrite(rewriteUrl, {
      request: {
        headers,
      },
    }),
    locale
  );
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const headerLocale = request.headers.get(INTERNAL_LOCALE_HEADER);
  const internalResolvedLocale = isSupportedAppLocale(headerLocale)
    ? headerLocale
    : null;
  const localePrefix = extractLocaleFromPathname(pathname);
  const routePathname = localePrefix ? stripLocalePrefix(pathname) : pathname;
  const cookieLocale = normalizeAppLocale(
    request.cookies.get(APP_LOCALE_COOKIE_NAME)?.value
  );
  const activeLocale =
    localePrefix ?? internalResolvedLocale ?? cookieLocale ?? DEFAULT_APP_LOCALE;

  if (isBypassRoute(routePathname)) {
    if (!localePrefix) {
      return NextResponse.next();
    }
    return rewriteWithLocale(request, routePathname, activeLocale);
  }

  if (!adminUiEnabled && isPathMatch(routePathname, ADMIN_ROUTE)) {
    return new NextResponse(null, { status: 404 });
  }

  if (!localePrefix && !internalResolvedLocale) {
    const url = request.nextUrl.clone();
    url.pathname = buildLocalePath(activeLocale, routePathname, "");
    return applyLocaleCookie(NextResponse.redirect(url), activeLocale);
  }

  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (token && isAuthRedirectRoute(routePathname)) {
    const url = request.nextUrl.clone();
    url.pathname = buildLocalePath(activeLocale, APP_ROUTE, "");
    url.search = "";
    return applyLocaleCookie(NextResponse.redirect(url), activeLocale);
  }

  if (isPublicRoute(routePathname)) {
    if (localePrefix) {
      return rewriteWithLocale(request, routePathname, activeLocale);
    }
    return NextResponse.next();
  }

  if (!token && isProtectedRoute(routePathname)) {
    const url = request.nextUrl.clone();
    url.pathname = buildLocalePath(activeLocale, "/login", "");
    url.search = "";
    return applyLocaleCookie(NextResponse.redirect(url), activeLocale);
  }

  if (localePrefix) {
    return rewriteWithLocale(request, routePathname, activeLocale);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/:path*"],
};
