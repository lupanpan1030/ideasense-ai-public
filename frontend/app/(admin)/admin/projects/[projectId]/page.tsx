import { redirect } from "next/navigation";
import { ProjectDetail } from "@/features/admin/components/projects/project-detail";
import { normalizeProjectId } from "@/features/projects/project-id";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";

type AdminProjectDetailPageProps = {
  params: Promise<{ projectId: string }>;
};

const isUuidLike = (value: string): boolean =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value
  );

export default async function AdminProjectDetailPage({
  params,
}: AdminProjectDetailPageProps) {
  const locale = await getRequestLocale();
  const resolvedParams = await params;
  const projectId = normalizeProjectId(resolvedParams.projectId);
  if (!projectId || !isUuidLike(projectId)) {
    redirect(buildLocalePath(locale, "/admin/projects"));
  }
  return <ProjectDetail projectId={projectId} />;
}
