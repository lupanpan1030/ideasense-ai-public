import { LogoutClient } from "./logout-client";

type LogoutPageProps = {
  searchParams: Promise<{ reason?: string | string[] }>;
};

export default async function LogoutPage({ searchParams }: LogoutPageProps) {
  const { reason } = await searchParams;
  const resolvedReason = Array.isArray(reason) ? reason[0] : reason;

  return <LogoutClient reason={resolvedReason ?? "logout"} />;
}
