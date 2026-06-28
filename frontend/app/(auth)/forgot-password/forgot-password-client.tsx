"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
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
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import type { AnimatedCharactersActiveField } from "@/components/ui/animated-characters-login-page";
import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

const isValidEmail = (value: string) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

type RequestState =
  | { status: "idle" }
  | { status: "sending" }
  | { status: "sent" }
  | { status: "error"; message: string };

export default function ForgotPasswordClient() {
  const locale = useAppLocale();
  const messages = useAppMessages().auth.forgotPassword;
  const [email, setEmail] = useState("");
  const [state, setState] = useState<RequestState>({ status: "idle" });
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaKey, setCaptchaKey] = useState(0);
  const [activeField, setActiveField] =
    useState<AnimatedCharactersActiveField>(null);
  const captchaEnabled = isCaptchaEnabled();

  const resolveErrorMessage = (error: unknown): string => {
    return getSafeErrorMessage(error, {
      default: messages.errors.requestDefault,
      unavailable: messages.errors.requestDefault,
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (state.status === "sending") {
      return;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setState({ status: "error", message: messages.errors.emailRequired });
      return;
    }
    if (/\s/.test(trimmedEmail)) {
      setState({ status: "error", message: messages.errors.emailNoSpaces });
      return;
    }
    if (!isValidEmail(trimmedEmail)) {
      setState({ status: "error", message: messages.errors.emailInvalid });
      return;
    }
    if (captchaEnabled && !captchaToken) {
      setState({ status: "error", message: messages.errors.captchaRequired });
      return;
    }

    setState({ status: "sending" });
    try {
      await apiClient.postJson("/auth/password-reset/request", {
        email: trimmedEmail,
        captcha_token: captchaToken ?? undefined,
      });
      setState({ status: "sent" });
    } catch (error) {
      setState({ status: "error", message: resolveErrorMessage(error) });
    } finally {
      if (captchaEnabled) {
        setCaptchaToken(null);
        setCaptchaKey((prev) => prev + 1);
      }
    }
  };

  const fieldError = state.status === "error" ? state.message : undefined;
  const subtitle =
    state.status === "sent"
      ? messages.subtitleSent
      : messages.subtitleIdle;

  return (
    <AuthSplitLayout
      badge={messages.badge}
      title={messages.title}
      subtitle={subtitle}
      visualTitle={messages.visualTitle}
      visualDescription={messages.visualDescription}
      activeField={activeField}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>{messages.cardTitle}</CardTitle>
          <CardDescription>{messages.cardDescription}</CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="stack-sm">
          {state.status !== "sent" ? (
            <form className="stack" onSubmit={handleSubmit}>
              <Input
                id="email"
                label={messages.emailLabel}
                type="email"
                name="email"
                autoComplete="email"
                placeholder={messages.emailPlaceholder}
                required
                value={email}
                error={fieldError}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (state.status === "error") {
                    setState({ status: "idle" });
                  }
                }}
                onFocus={() => setActiveField("email")}
                onBlur={() =>
                  setActiveField((current) =>
                    current === "email" ? null : current
                  )
                }
                disabled={state.status === "sending"}
              />
              {captchaEnabled ? (
                <CaptchaWidget
                  key={captchaKey}
                  onToken={(token) => {
                    setCaptchaToken(token);
                    if (state.status === "error") {
                      setState({ status: "idle" });
                    }
                  }}
                />
              ) : null}
              <Button type="submit" disabled={state.status === "sending"}>
                {state.status === "sending"
                  ? messages.submitBusy
                  : messages.submitIdle}
              </Button>
            </form>
          ) : (
            <span className="text-muted">{messages.sentState}</span>
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
