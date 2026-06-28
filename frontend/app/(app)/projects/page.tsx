import { Suspense } from "react";
import ProjectsClient from "./projects-client";

export default function ProjectsPage() {
  return (
    <Suspense fallback={<div className="page" />}>
      <ProjectsClient />
    </Suspense>
  );
}
