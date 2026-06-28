import { CohortDetail } from "@/features/admin/components/cohorts/cohort-detail";

type AdminCohortDetailPageProps = {
  params: Promise<{ cohortId: string }>;
};

export default async function AdminCohortDetailPage({
  params,
}: AdminCohortDetailPageProps) {
  const resolvedParams = await params;
  return <CohortDetail cohortId={resolvedParams.cohortId} />;
}
