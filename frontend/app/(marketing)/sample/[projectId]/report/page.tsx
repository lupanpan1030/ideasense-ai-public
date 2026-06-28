import Link from "next/link";
import { ReportViewer } from "@/features/reports/report-viewer";
import { SampleNotice } from "@/components/sample/sample-notice";
import { buttonClassNames } from "@/components/ui/button";
import { fetchSampleReport } from "@/features/sample/sample-api";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

type SampleReportPageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function SampleReportPage({
  params,
}: SampleReportPageProps) {
  const { projectId } = await params;
  const locale = await getRequestLocale();
  const isZh = locale === "zh";

  let report = null;
  try {
    report = await fetchSampleReport(projectId);
  } catch {
    report = null;
  }

  if (!report) {
    return (
      <div className="stack-lg">
        <SampleNotice />
        <div className="rounded-[2rem] border border-black/6 bg-white/78 p-10 text-center shadow-[0_20px_56px_rgba(15,23,42,0.05)]">
          <p className="text-[17px] font-medium text-[#0f172a]">
            {isZh ? "未找到该样例报告" : "Sample report not found"}
          </p>
          <p className="mt-3 text-[15px] leading-[1.8] text-[#475569]">
            {isZh
              ? "这份样例可能已更新或暂时不可用。"
              : "This sample may have changed or is temporarily unavailable."}
          </p>
          <div className="mt-6">
            <Link
              className={buttonClassNames({ variant: "secondary" })}
              href={buildLocalePath(locale, "/sample")}
            >
              {isZh ? "返回示例工作区" : "Back to samples"}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stack-lg">
      <SampleNotice />
      <ReportViewer projectId={projectId} mode="sample" reportOverride={report} />
    </div>
  );
}
