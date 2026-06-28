import { redirect } from "next/navigation";
import { normalizeProjectId } from "@/features/projects/project-id";
import { ReportViewer } from "@/features/reports/report-viewer";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

type ReportPageProps = {
  params: Promise<{ projectId: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

const readSearchParam = (
  params: Record<string, string | string[] | undefined>,
  key: string
): string | null => {
  const value = params[key];
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }
  return value ?? null;
};

export default async function ReportPage({ params, searchParams }: ReportPageProps) {
  const locale = await getRequestLocale();
  const resolvedParams = await params;
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const projectId = normalizeProjectId(resolvedParams.projectId);
  if (!projectId) {
    redirect(buildLocalePath(locale, "/projects"));
  }
  const autoStartReport = readSearchParam(resolvedSearchParams, "generate") === "1";

  return <ReportViewer projectId={projectId} autoStartReport={autoStartReport} />;
}
