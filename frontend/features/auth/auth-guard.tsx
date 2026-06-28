"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AUTH_UNAUTHORIZED_EVENT,
  ORG_CONTEXT_INVALID_EVENT,
} from "@/lib/api/client";
import { isTokenUsable } from "@/lib/auth/token";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import { tokenStorage } from "@/lib/storage/token";

const LOGIN_PATH = "/login";
const UNAUTHORIZED_REASON = "unauthorized";

type GuardStatus = "checking" | "allowed" | "redirecting";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const locale = useAppLocale();
  const [status, setStatus] = useState<GuardStatus>("checking");

  useEffect(() => {
    const token = tokenStorage.getToken();
    if (!token) {
      setStatus("redirecting");
      router.replace(buildLocalePath(locale, LOGIN_PATH));
      return;
    }
    if (!isTokenUsable(token)) {
      tokenStorage.clearToken();
      setStatus("redirecting");
      router.replace(
        buildLocalePath(locale, LOGIN_PATH, `?reason=${UNAUTHORIZED_REASON}`)
      );
      return;
    }

    setStatus("allowed");

    const handleUnauthorized = () => {
      setStatus("redirecting");
      router.replace(
        buildLocalePath(locale, LOGIN_PATH, `?reason=${UNAUTHORIZED_REASON}`)
      );
    };
    const handleOrgContextInvalid = () => {
      setStatus("redirecting");
      router.replace(buildLocalePath(locale, "/projects"));
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    window.addEventListener(ORG_CONTEXT_INVALID_EVENT, handleOrgContextInvalid);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
      window.removeEventListener(
        ORG_CONTEXT_INVALID_EVENT,
        handleOrgContextInvalid
      );
    };
  }, [locale, router]);

  if (status !== "allowed") {
    return null;
  }

  return <>{children}</>;
}
