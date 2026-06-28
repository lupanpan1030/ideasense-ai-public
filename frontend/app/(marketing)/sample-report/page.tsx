import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ReportViewer } from "@/features/reports/report-viewer";
import { getFeaturedSampleReport } from "@/features/sample/sample-api";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const fullTitle = isZh
    ? "IdeaSense AI | 示例报告"
    : "IdeaSense AI | Sample Report";
  const description = isZh
    ? "查看 IdeaSense AI 示例报告，了解 DVF 评分、阶段证据、风险和验证计划如何汇总成决策备忘录。"
    : "View the IdeaSense AI sample report with DVF scoring, stage evidence, risks, and validation planning.";

  return {
    title: { absolute: fullTitle },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/sample-report"),
      languages: {
        en: buildLocalePath("en", "/sample-report"),
        zh: buildLocalePath("zh", "/sample-report"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/sample-report"),
      locale: isZh ? "zh_CN" : "en_US",
      type: "article",
    },
  };
}

export default async function SampleReportPage() {
  const locale = await getRequestLocale();
  const report = await getFeaturedSampleReport();
  if (!report) {
    redirect(buildLocalePath(locale, "/sample"));
  }

  return (
    <ReportViewer
      projectId={report.projectId}
      mode="sample"
      reportOverride={report}
    />
  );
}
