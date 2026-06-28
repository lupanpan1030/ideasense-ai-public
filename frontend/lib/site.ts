import type { AppLocale } from "@/lib/i18n/config";

export const SITE_NAME = "IdeaSense AI";
export const SITE_URL = "https://ideasenseai.com";
export const SITE_OPERATOR_NAME = "Ethan Lu";
export const SITE_CONTACT_EMAIL = "ideasenseai@gmail.com";
export const SITE_PRIVACY_EMAIL = "ideasenseai@gmail.com";

export const SITE_STATUS_LABEL: Record<AppLocale, string> = {
  en: "Open registration",
  zh: "开放注册",
};

export const SITE_OPERATOR_LABEL: Record<AppLocale, string> = {
  en: `Independent product by ${SITE_OPERATOR_NAME}`,
  zh: `由 ${SITE_OPERATOR_NAME} 独立运营的产品`,
};

export const formatSiteCopyright = (year: number, locale: AppLocale) =>
  locale === "zh"
    ? `© ${year} ${SITE_NAME}。由 ${SITE_OPERATOR_NAME} 独立运营。保留所有权利。`
    : `© ${year} ${SITE_NAME}. Operated by ${SITE_OPERATOR_NAME}. All rights reserved.`;
