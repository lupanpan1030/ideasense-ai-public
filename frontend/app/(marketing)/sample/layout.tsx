import { Suspense } from "react";
import { SampleShell } from "@/components/sample/sample-shell";
import { getSampleProjectsCached } from "@/features/sample/sample-api";

export default async function SampleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const projects = await getSampleProjectsCached();
  return (
    <Suspense fallback={null}>
      <SampleShell projects={projects}>{children}</SampleShell>
    </Suspense>
  );
}
