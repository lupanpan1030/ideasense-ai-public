"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthPasswordField } from "@/components/auth/auth-password-field";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
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
import type { AnimatedCharactersActiveField } from "@/components/ui/animated-characters-login-page";
import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import {
  clearOneTimeTokenFromUrl,
  readOneTimeTokenFromUrl,
} from "@/lib/auth/one-time-token-url";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type ResetState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success" }
  | { status: "error"; message: string }
  | { status: "missing" };

type FieldErrors = {
  password?: string;
  confirmPassword?: string;
};

export default function ResetPasswordClient() {
  const locale = useAppLocale();
  const authMessages = useAppMessages().auth;
  const messages = authMessages.resetPassword;
  const searchParams = useSearchParams();
  const [token] = useState(() => readOneTimeTokenFromUrl(searchParams));

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [state, setState] = useState<ResetState>({ status: "idle" });
  const [activeField, setActiveField] =
    useState<AnimatedCharactersActiveField>(null);
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  useEffect(() => {
    if (token) {
      clearOneTimeTokenFromUrl();
    }
  }, [token]);

  const resolveErrorMessage = (error: unknown): string => {
    return getSafeErrorMessage(error, {
      default: messages.errors.resetDefault,
      unavailable: messages.errors.resetDefault,
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (state.status === "submitting") {
      return;
    }

    if (!token) {
      setState({ status: "missing" });
      return;
    }

    const nextErrors: FieldErrors = {};
    if (!password) {
      nextErrors.password = messages.errors.passwordRequired;
    } else if (password.length < 8 || password.length > 128) {
      nextErrors.password = messages.errors.passwordLength;
    }

    if (!confirmPassword) {
      nextErrors.confirmPassword = messages.errors.confirmPasswordRequired;
    } else if (confirmPassword !== password) {
      nextErrors.confirmPassword = messages.errors.confirmPasswordMismatch;
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setState({ status: "idle" });
      return;
    }

    setFieldErrors({});
    setState({ status: "submitting" });

    try {
      await apiClient.postJson("/auth/password-reset/confirm", {
        token,
        password,
      });
      clearOneTimeTokenFromUrl();
      setState({ status: "success" });
    } catch (error) {
      setState({ status: "error", message: resolveErrorMessage(error) });
    }
  };

  const subtitle =
    !token
      ? messages.subtitleMissing
      : state.status === "success"
        ? messages.subtitleSuccess
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
      activeField={activeField}
      isPasswordVisible={isPasswordVisible}
      hasPasswordValue={Boolean(password)}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>{messages.cardTitle}</CardTitle>
          <CardDescription>{messages.cardDescription}</CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="stack-sm">
          {token && state.status !== "success" ? (
            <form className="stack" onSubmit={handleSubmit}>
              <AuthPasswordField
                id="password"
                label={messages.passwordLabel}
                name="password"
                autoComplete="new-password"
                placeholder={messages.passwordPlaceholder}
                required
                hint={messages.passwordHint}
                value={password}
                error={fieldErrors.password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (fieldErrors.password || fieldErrors.confirmPassword) {
                    setFieldErrors({});
                  }
                  if (state.status === "error") {
                    setState({ status: "idle" });
                  }
                }}
                onFocus={() => setActiveField("password")}
                onBlur={() =>
                  setActiveField((current) =>
                    current === "password" ? null : current
                  )
                }
                showPasswordLabel={authMessages.common.showPassword}
                hidePasswordLabel={authMessages.common.hidePassword}
                onVisibilityChange={setIsPasswordVisible}
                disabled={state.status === "submitting"}
              />
              <AuthPasswordField
                id="confirm_password"
                label={messages.confirmPasswordLabel}
                name="confirm_password"
                autoComplete="new-password"
                placeholder={messages.confirmPasswordPlaceholder}
                required
                value={confirmPassword}
                error={fieldErrors.confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  if (fieldErrors.confirmPassword) {
                    setFieldErrors((prev) => ({
                      ...prev,
                      confirmPassword: undefined,
                    }));
                  }
                  if (state.status === "error") {
                    setState({ status: "idle" });
                  }
                }}
                onFocus={() => setActiveField("confirm_password")}
                onBlur={() =>
                  setActiveField((current) =>
                    current === "confirm_password" ? null : current
                  )
                }
                showPasswordLabel={authMessages.common.showPassword}
                hidePasswordLabel={authMessages.common.hidePassword}
                disabled={state.status === "submitting"}
              />
              <Button type="submit" disabled={state.status === "submitting"}>
                {state.status === "submitting"
                  ? messages.submitBusy
                  : messages.submitIdle}
              </Button>
            </form>
          ) : null}

          {state.status === "success" ? (
            <span className="text-muted">{messages.successState}</span>
          ) : null}
        </CardContent>
        <Separator />
        <CardFooter>
          <Link
            className={buttonClassNames({ variant: "ghost" })}
            href={buildLocalePath(locale, "/login")}
          >
            {messages.backToSignIn}
          </Link>

          {!token ? (
            <Link
              className={buttonClassNames({ variant: "secondary" })}
              href={buildLocalePath(locale, "/forgot-password")}
            >
              {messages.requestNewLink}
            </Link>
          ) : null}
        </CardFooter>
      </Card>
    </AuthSplitLayout>
  );
}
