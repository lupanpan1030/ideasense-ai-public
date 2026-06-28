import type { Metadata } from "next";

import {
  resolveMarketingContent,
} from "@/components/marketing/content";
import { MethodologyPageView } from "@/components/marketing/MethodologyPageView";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const pageTitle = isZh ? "方法论" : "Methodology";
  const fullTitle = `IdeaSense AI | ${pageTitle}`;
  const description = isZh
    ? "查看 IdeaSense AI 如何通过结构化追问、Stage Gate 与 DVF 评分，把模糊想法推进成更清楚的判断。"
    : "See how IdeaSense AI uses structured review, Stage Gate discipline, and DVF scoring to turn vague ideas into clearer decisions.";

  return {
    title: {
      absolute: fullTitle,
    },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/methodology"),
      languages: {
        en: buildLocalePath("en", "/methodology"),
        zh: buildLocalePath("zh", "/methodology"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/methodology"),
    },
  };
}

export default async function MethodologyPage() {
  const locale = await getRequestLocale();

  return (
    <MethodologyPageView
      content={resolveMarketingContent(locale).methodology}
      isZh={locale === "zh"}
    />
  );
}
