"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { isCaptchaEnabled } from "@/components/auth/captcha-widget";
import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { useUserSession } from "@/features/auth/user-session";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type ResendState =
  | { status: "idle" }
  | { status: "sending" }
  | { status: "sent" }
  | { status: "error"; message: string };

const resolveErrorMessage = (
  error: unknown,
  fallbackMessage: string
): string => {
  return getSafeErrorMessage(error, {
    default: fallbackMessage,
    unavailable: fallbackMessage,
  });
};

export function EmailVerificationBanner() {
  const locale = useAppLocale();
  const messages = useAppMessages().emailVerificationBanner;
  const { session } = useUserSession();
  const emailVerified = session?.user.emailVerified;
  const email = session?.user.email ?? null;
  const captchaEnabled = isCaptchaEnabled();
  const [resendState, setResendState] = useState<ResendState>({
    status: "idle",
  });

  if (emailVerified !== false) {
    return null;
  }

  const handleResend = async () => {
    if (resendState.status === "sending") {
      return;
    }
    if (captchaEnabled) {
      setResendState({ status: "idle" });
      return;
    }
    setResendState({ status: "sending" });
    try {
      await apiClient.postJson("/auth/verify-email/resend", {});
      setResendState({ status: "sent" });
    } catch (error) {
      setResendState({
        status: "error",
        message: resolveErrorMessage(error, messages.errors.resendDefault),
      });
    }
  };

  const description = email
    ? messages.descriptionWithEmail.replace("{email}", email)
    : messages.descriptionWithoutEmail;

  return (
    <Card variant="alert" className="app-shell__notice">
      <CardHeader className="stack-sm">
        <div className="cluster-tight">
          <CardTitle>{messages.title}</CardTitle>
          <Badge variant="warning">{messages.badge}</Badge>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        <div className="cluster">
          {captchaEnabled ? null : (
            <Button
              type="button"
              variant="secondary"
              onClick={handleResend}
              disabled={resendState.status === "sending"}
            >
              {resendState.status === "sending"
                ? messages.resendBusy
                : messages.resendIdle}
            </Button>
          )}
          <Link
            className={buttonClassNames({ variant: "ghost" })}
            href={buildLocalePath(locale, "/verify-email")}
          >
            {messages.openPage}
          </Link>
        </div>
        {resendState.status === "sent" ? (
          <span className="text-muted">{messages.sent}</span>
        ) : null}
        {resendState.status === "error" ? (
          <span className="text-muted">{resendState.message}</span>
        ) : null}
      </CardContent>
    </Card>
  );
}
