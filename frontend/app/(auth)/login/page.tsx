"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthPasswordField } from "@/components/auth/auth-password-field";
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
import { devLoginWithEmail, loginWithEmail } from "@/features/auth/login";
import {
  acceptInvitationIfPresent,
  buildInviteErrorMessage,
  INVITE_ERROR_QUERY_KEY,
} from "@/features/invitations/invite-accept";
import { ApiError } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { isTokenUsable } from "@/lib/auth/token";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { tokenStorage } from "@/lib/storage/token";

const isDevLoginEnabled = process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === "1";

const resolveNotice = (
  reason: string | null,
  messages: ReturnType<typeof useAppMessages>["auth"]["login"]
) => {
  if (reason === "unauthorized") {
    return messages.reasons.unauthorized;
  }
  if (reason === "switch") {
    return messages.reasons.switch;
  }
  if (reason === "logout" || reason === "signout") {
    return messages.reasons.logout;
  }
  return null;
};

const getLoginErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["auth"]["login"]["errors"]
): string =>
  getSafeErrorMessage(error, {
    default: messages.signInDefault,
    network: messages.signInRetry,
    sessionExpired: messages.signInDefault,
    unavailable: messages.signInRetry,
  });

export default function LoginPage() {
  const locale = useAppLocale();
  const authMessages = useAppMessages().auth;
  const loginMessages = authMessages.login;
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDevLoginSubmitting, setIsDevLoginSubmitting] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaKey, setCaptchaKey] = useState(0);
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(true);
  const [activeField, setActiveField] =
    useState<AnimatedCharactersActiveField>(null);
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const captchaEnabled = isCaptchaEnabled();
  const isBusy = isSubmitting || isDevLoginSubmitting;

  const handlePostAuthRedirect = useCallback(async () => {
    const inviteResult = await acceptInvitationIfPresent();
    if (inviteResult.status === "accepted") {
      router.replace(buildLocalePath(locale, "/projects"));
      return;
    }
    if (inviteResult.status === "error") {
      const message = buildInviteErrorMessage(inviteResult.message);
      const searchParams = new URLSearchParams();
      searchParams.set(INVITE_ERROR_QUERY_KEY, message);
      router.replace(buildLocalePath(locale, "/projects", searchParams.toString()));
      return;
    }
    router.replace(buildLocalePath(locale, "/projects"));
  }, [locale, router]);

  useEffect(() => {
    const reason =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("reason")
        : null;
    setNotice(resolveNotice(reason, loginMessages));
  }, [loginMessages]);

  useEffect(() => {
    const token = tokenStorage.getToken();
    if (token && isTokenUsable(token)) {
      void handlePostAuthRedirect();
      return;
    }
    if (token) {
      tokenStorage.clearToken();
    }
    setIsCheckingAuth(false);
  }, [handlePostAuthRedirect]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isBusy) {
      return;
    }

    if (captchaRequired && captchaEnabled && !captchaToken) {
      setError(loginMessages.errors.captchaRequired);
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await loginWithEmail(
        {
          email,
          password,
          captcha_token: captchaToken ?? undefined,
        },
        { persist: rememberDevice }
      );
      setCaptchaRequired(false);
      await handlePostAuthRedirect();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403 && /captcha/i.test(err.message)) {
          setCaptchaRequired(true);
        }
        setError(getLoginErrorMessage(err, loginMessages.errors));
      } else {
        setError(getLoginErrorMessage(err, loginMessages.errors));
      }
    } finally {
      setIsSubmitting(false);
      if (captchaEnabled) {
        setCaptchaToken(null);
        setCaptchaKey((prev) => prev + 1);
      }
    }
  };

  const handleDevLogin = async () => {
    if (!isDevLoginEnabled || isBusy) {
      return;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError(loginMessages.errors.devLoginEmailRequired);
      return;
    }

    setError(null);
    setIsDevLoginSubmitting(true);

    try {
      await devLoginWithEmail(
        { email: trimmedEmail },
        { persist: rememberDevice }
      );
      await handlePostAuthRedirect();
    } catch (err) {
      setError(getLoginErrorMessage(err, loginMessages.errors));
    } finally {
      setIsDevLoginSubmitting(false);
    }
  };

  if (isCheckingAuth) {
    return null;
  }

  return (
    <AuthSplitLayout
      badge={loginMessages.badge}
      title={loginMessages.title}
      subtitle={loginMessages.subtitle}
      visualTitle={loginMessages.visualTitle}
      visualDescription={loginMessages.visualDescription}
      mode="login"
      activeField={activeField}
      isPasswordVisible={isPasswordVisible}
      hasPasswordValue={Boolean(password)}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>{loginMessages.cardTitle}</CardTitle>
          <CardDescription>{loginMessages.cardDescription}</CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <form
            className="stack"
            aria-label={loginMessages.formAriaLabel}
            onSubmit={handleSubmit}
          >
            <Input
              id="email"
              label={loginMessages.emailLabel}
              type="email"
              name="email"
              autoComplete="email"
              placeholder={loginMessages.emailPlaceholder}
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                if (error) {
                  setError(null);
                }
                if (notice) {
                  setNotice(null);
                }
              }}
              onFocus={() => setActiveField("email")}
              onBlur={() =>
                setActiveField((current) => (current === "email" ? null : current))
              }
              disabled={isBusy}
            />
            <AuthPasswordField
              id="password"
              label={loginMessages.passwordLabel}
              name="password"
              autoComplete="current-password"
              placeholder={loginMessages.passwordPlaceholder}
              required
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                if (error) {
                  setError(null);
                }
                if (notice) {
                  setNotice(null);
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
              disabled={isBusy}
            />
            {captchaEnabled && captchaRequired ? (
              <CaptchaWidget
                key={captchaKey}
                onToken={(token) => {
                  setCaptchaToken(token);
                  if (error) {
                    setError(null);
                  }
                }}
              />
            ) : null}
            <div className="auth-remember-row">
              <label className="auth-checkbox">
                <input
                  type="checkbox"
                  name="remember"
                  checked={rememberDevice}
                  onChange={(event) => setRememberDevice(event.target.checked)}
                  disabled={isBusy}
                />
                {loginMessages.rememberDevice}
              </label>
              <Link
                className="link-muted"
                href={buildLocalePath(locale, "/forgot-password")}
              >
                {loginMessages.forgotPassword}
              </Link>
            </div>
            {notice && !error ? (
              <div className="auth-status auth-status--info" role="status" aria-live="polite">
                <span>{notice}</span>
              </div>
            ) : null}
            {error ? (
              <div className="alert" role="alert">
                <span>{error}</span>
              </div>
            ) : null}
            <Button type="submit" disabled={isBusy}>
              {isSubmitting ? loginMessages.submitBusy : loginMessages.submitIdle}
            </Button>
            {isDevLoginEnabled ? (
              <div className="stack-sm">
                <span className="text-muted">{loginMessages.devLoginLabel}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleDevLogin}
                  disabled={isBusy}
                >
                  {isDevLoginSubmitting
                    ? loginMessages.devLoginBusy
                    : loginMessages.devLoginButton}
                </Button>
              </div>
            ) : null}
          </form>
        </CardContent>
        <Separator />
        <CardFooter className="auth-card__footer">
          <div className="auth-card__footer-block">
            <div className="cluster-tight">
              <span className="text-muted">{loginMessages.footerPrompt}</span>
              <Link
                className={buttonClassNames({ variant: "secondary", size: "sm" })}
                href={buildLocalePath(locale, "/register")}
              >
                {loginMessages.footerAction}
              </Link>
            </div>
          </div>
        </CardFooter>
      </Card>
    </AuthSplitLayout>
  );
}
