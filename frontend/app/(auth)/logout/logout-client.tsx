"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import { tokenStorage } from "@/lib/storage/token";

type LogoutClientProps = {
  reason: string;
};

const normalizeReason = (value: string): string => {
  const trimmed = value.trim();
  return trimmed ? trimmed : "logout";
};

export function LogoutClient({ reason }: LogoutClientProps) {
  const router = useRouter();
  const locale = useAppLocale();

  useEffect(() => {
    tokenStorage.clearToken();
    const resolvedReason = normalizeReason(reason);
    const redirectTo =
      resolvedReason === "logout"
        ? buildLocalePath(locale, "/")
        : buildLocalePath(
            locale,
            "/login",
            `?reason=${encodeURIComponent(resolvedReason)}`
          );
    router.replace(redirectTo);
  }, [locale, router, reason]);

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <p className="text-muted">Signing out...</p>
      </div>
    </div>
  );
}
