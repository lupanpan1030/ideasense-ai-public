import type { Metadata } from "next";

import HomePage from "@/components/marketing/HomePage";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const pageTitle = isZh ? "先验证，再构建" : "Validate Before You Build";
  const fullTitle = `IdeaSense AI | ${pageTitle}`;
  const description = isZh
    ? "IdeaSense AI 通过结构化评审、DVF 评分和决策就绪报告，帮助早期软件创业者在构建前先完成验证。"
    : "IdeaSense AI helps early-stage founders validate software ideas through structured review, DVF scoring, and decision-ready reports.";

  return {
    title: {
      absolute: fullTitle,
    },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/"),
      languages: {
        en: buildLocalePath("en", "/"),
        zh: buildLocalePath("zh", "/"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/"),
      locale: isZh ? "zh_CN" : "en_US",
      type: "website",
    },
    twitter: {
      title: fullTitle,
      description,
      card: "summary",
    },
  };
}

export default function MarketingPage() {
  return <HomePage />;
}
