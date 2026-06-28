import type { MetadataRoute } from "next";

import { buildLocalePath, SUPPORTED_APP_LOCALES } from "@/lib/i18n/config";
import { SITE_URL } from "@/lib/site";

const PUBLIC_MARKETING_PATHS = [
  "/",
  "/methodology",
  "/sample",
  "/sample-report",
  "/privacy",
  "/terms",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return SUPPORTED_APP_LOCALES.flatMap((locale) =>
    PUBLIC_MARKETING_PATHS.map((pathname) => ({
      url: `${SITE_URL}${buildLocalePath(locale, pathname)}`,
      lastModified,
    }))
  );
}
