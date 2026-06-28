import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/features/auth/auth-guard";
import { UserSessionProvider } from "@/features/auth/user-session";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <UserSessionProvider>
        <Suspense fallback={null}>
          <AppShell>{children}</AppShell>
        </Suspense>
      </UserSessionProvider>
    </AuthGuard>
  );
}
