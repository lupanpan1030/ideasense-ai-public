"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import {
  CaptchaWidget,
  isCaptchaEnabled,
} from "@/components/auth/captcha-widget";
import { Button, buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import {
  clearOneTimeTokenFromUrl,
  readOneTimeTokenFromUrl,
} from "@/lib/auth/one-time-token-url";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type VerifyState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success" }
  | { status: "error"; message: string }
  | { status: "missing" };

type ResendState =
  | { status: "idle" }
  | { status: "sending" }
  | { status: "sent" }
  | { status: "error"; message: string };

export default function VerifyEmailClient() {
  const locale = useAppLocale();
  const messages = useAppMessages().auth.verifyEmail;
  const searchParams = useSearchParams();
  const [state, setState] = useState<VerifyState>({ status: "idle" });
  const [resendState, setResendState] = useState<ResendState>({
    status: "idle",
  });
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaKey, setCaptchaKey] = useState(0);
  const [token] = useState(() => readOneTimeTokenFromUrl(searchParams));
  const captchaEnabled = isCaptchaEnabled();

  const resolveErrorMessage = useCallback(
    (error: unknown): string => {
      return getSafeErrorMessage(error, {
        default: messages.errors.verifyDefault,
        unavailable: messages.errors.verifyDefault,
      });
    },
    [messages.errors.verifyDefault]
  );

  useEffect(() => {
    if (!token) {
      setState({ status: "missing" });
      return;
    }
    let isActive = true;
    clearOneTimeTokenFromUrl();
    setState({ status: "loading" });
    apiClient
      .postJson("/auth/verify-email", { token })
      .then(() => {
        if (isActive) {
          setState({ status: "success" });
        }
      })
      .catch((error) => {
        if (isActive) {
          setState({ status: "error", message: resolveErrorMessage(error) });
        }
      });
    return () => {
      isActive = false;
    };
  }, [resolveErrorMessage, token]);

  const handleResend = async () => {
    if (resendState.status === "sending") {
      return;
    }
    if (captchaEnabled && !captchaToken) {
      setResendState({
        status: "error",
        message: messages.errors.captchaRequired,
      });
      return;
    }
    setResendState({ status: "sending" });
    try {
      await apiClient.postJson("/auth/verify-email/resend", {
        captcha_token: captchaToken ?? undefined,
      });
      setResendState({ status: "sent" });
    } catch (error) {
      setResendState({
        status: "error",
        message: resolveErrorMessage(error),
      });
    } finally {
      if (captchaEnabled) {
        setCaptchaToken(null);
        setCaptchaKey((prev) => prev + 1);
      }
    }
  };

  const subtitle =
    state.status === "loading"
      ? messages.subtitleLoading
      : state.status === "success"
        ? messages.subtitleSuccess
        : state.status === "missing"
          ? messages.subtitleMissing
          : state.status === "error"
            ? state.message
            : messages.subtitleIdle;

  return (
    <AuthSplitLayout
      badge={messages.badge}
      title={messages.title}
      subtitle={subtitle}
      visualTitle={messages.visualTitle}
      visualDescription={messages.visualDescription}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>
            {state.status === "success"
              ? messages.cardTitleSuccess
              : messages.cardTitleIdle}
          </CardTitle>
          <CardDescription>
            {state.status === "success"
              ? messages.cardDescriptionSuccess
              : messages.cardDescriptionIdle}
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="stack-sm">
          {state.status === "success" ? (
            <Link
              className={buttonClassNames()}
              href={buildLocalePath(locale, "/projects")}
            >
              {messages.goToWorkspace}
            </Link>
          ) : state.status === "loading" || state.status === "idle" ? (
            <span className="text-muted">{messages.subtitleLoading}</span>
          ) : (
            <>
              <Button
                type="button"
                variant="secondary"
                onClick={handleResend}
                disabled={
                  resendState.status === "sending" ||
                  (captchaEnabled && !captchaToken)
                }
              >
                {resendState.status === "sending"
                  ? messages.resendBusy
                  : messages.resendIdle}
              </Button>
              {captchaEnabled ? (
                <CaptchaWidget
                  key={captchaKey}
                  onToken={(nextToken) => setCaptchaToken(nextToken)}
                />
              ) : null}
              {resendState.status === "sent" ? (
                <span className="text-muted">{messages.sent}</span>
              ) : null}
              {resendState.status === "error" ? (
                <span className="text-muted">{resendState.message}</span>
              ) : null}
            </>
          )}
        </CardContent>
        <Separator />
        <CardFooter>
          <Link
            className={buttonClassNames({ variant: "ghost" })}
            href={buildLocalePath(locale, "/login")}
          >
            {messages.backToSignIn}
          </Link>
        </CardFooter>
      </Card>
    </AuthSplitLayout>
  );
}
