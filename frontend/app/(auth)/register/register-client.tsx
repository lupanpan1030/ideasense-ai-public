"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
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
import { registerWithEmail } from "@/features/auth/login";
import {
  acceptInvitationIfPresent,
  buildInviteErrorMessage,
  INVITE_ERROR_QUERY_KEY,
} from "@/features/invitations/invite-accept";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { isTokenUsable } from "@/lib/auth/token";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { tokenStorage } from "@/lib/storage/token";

type FieldErrors = {
  email?: string;
  password?: string;
  confirmPassword?: string;
};

const isValidEmail = (value: string) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

const getRegisterErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["auth"]["register"]["errors"]
): string =>
  getSafeErrorMessage(error, {
    default: messages.createAccountDefault,
    network: messages.createAccountRetry,
    sessionExpired: messages.createAccountDefault,
    unavailable: messages.createAccountRetry,
  });

export default function RegisterClient() {
  const locale = useAppLocale();
  const authMessages = useAppMessages().auth;
  const registerMessages = authMessages.register;
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [hasPrefilledEmail, setHasPrefilledEmail] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaKey, setCaptchaKey] = useState(0);
  const [activeField, setActiveField] =
    useState<AnimatedCharactersActiveField>(null);
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const captchaEnabled = isCaptchaEnabled();

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

  useEffect(() => {
    if (hasPrefilledEmail) {
      return;
    }
    const emailParam = searchParams.get("email");
    if (!emailParam) {
      return;
    }
    const normalized = emailParam.trim();
    if (!normalized) {
      return;
    }
    setEmail(normalized);
    setHasPrefilledEmail(true);
  }, [hasPrefilledEmail, searchParams]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const trimmedEmail = email.trim();
    const trimmedName = fullName.trim();
    const nextErrors: FieldErrors = {};

    if (!trimmedEmail) {
      nextErrors.email = registerMessages.errors.emailRequired;
    } else if (/\s/.test(trimmedEmail)) {
      nextErrors.email = registerMessages.errors.emailNoSpaces;
    } else if (!isValidEmail(trimmedEmail)) {
      nextErrors.email = registerMessages.errors.emailInvalid;
    }

    if (!password) {
      nextErrors.password = registerMessages.errors.passwordRequired;
    } else if (password.length < 8 || password.length > 128) {
      nextErrors.password = registerMessages.errors.passwordLength;
    }

    if (!confirmPassword) {
      nextErrors.confirmPassword =
        registerMessages.errors.confirmPasswordRequired;
    } else if (confirmPassword !== password) {
      nextErrors.confirmPassword =
        registerMessages.errors.confirmPasswordMismatch;
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setError(null);
      return;
    }

    setFieldErrors({});

    if (captchaEnabled && !captchaToken) {
      setError(registerMessages.errors.captchaRequired);
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await registerWithEmail({
        email: trimmedEmail,
        password,
        full_name: trimmedName || undefined,
        captcha_token: captchaToken ?? undefined,
      });
      await handlePostAuthRedirect();
    } catch (err) {
      setError(getRegisterErrorMessage(err, registerMessages.errors));
    } finally {
      setIsSubmitting(false);
      if (captchaEnabled) {
        setCaptchaToken(null);
        setCaptchaKey((prev) => prev + 1);
      }
    }
  };

  if (isCheckingAuth) {
    return null;
  }

  return (
    <AuthSplitLayout
      badge={registerMessages.badge}
      title={registerMessages.title}
      subtitle={registerMessages.subtitle}
      visualTitle={registerMessages.visualTitle}
      visualDescription={registerMessages.visualDescription}
      mode="register"
      activeField={activeField}
      isPasswordVisible={isPasswordVisible}
      hasPasswordValue={Boolean(password)}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>{registerMessages.cardTitle}</CardTitle>
          <CardDescription>{registerMessages.cardDescription}</CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <form
            className="stack"
            aria-label={registerMessages.formAriaLabel}
            onSubmit={handleSubmit}
          >
            <Input
              id="email"
              label={registerMessages.emailLabel}
              type="email"
              name="email"
              autoComplete="email"
              placeholder={registerMessages.emailPlaceholder}
              required
              value={email}
              error={fieldErrors.email}
              onChange={(event) => {
                setEmail(event.target.value);
                if (fieldErrors.email) {
                  setFieldErrors((prev) => ({ ...prev, email: undefined }));
                }
                if (error) {
                  setError(null);
                }
              }}
              onFocus={() => setActiveField("email")}
              onBlur={() =>
                setActiveField((current) => (current === "email" ? null : current))
              }
              disabled={isSubmitting}
            />
            <Input
              id="full_name"
              label={registerMessages.fullNameLabel}
              type="text"
              name="full_name"
              autoComplete="name"
              placeholder={registerMessages.fullNamePlaceholder}
              hint={registerMessages.fullNameHint}
              value={fullName}
              onChange={(event) => {
                setFullName(event.target.value);
                if (error) {
                  setError(null);
                }
              }}
              onFocus={() => setActiveField("full_name")}
              onBlur={() =>
                setActiveField((current) =>
                  current === "full_name" ? null : current
                )
              }
              disabled={isSubmitting}
            />
            <AuthPasswordField
              id="password"
              label={registerMessages.passwordLabel}
              name="password"
              autoComplete="new-password"
              placeholder={registerMessages.passwordPlaceholder}
              required
              hint={registerMessages.passwordHint}
              value={password}
              error={fieldErrors.password}
              onChange={(event) => {
                setPassword(event.target.value);
                if (fieldErrors.password) {
                  setFieldErrors((prev) => ({ ...prev, password: undefined }));
                }
                if (fieldErrors.confirmPassword) {
                  setFieldErrors((prev) => ({
                    ...prev,
                    confirmPassword: undefined,
                  }));
                }
                if (error) {
                  setError(null);
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
              disabled={isSubmitting}
            />
            <AuthPasswordField
              id="confirm_password"
              label={registerMessages.confirmPasswordLabel}
              name="confirm_password"
              autoComplete="new-password"
              placeholder={registerMessages.confirmPasswordPlaceholder}
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
                if (error) {
                  setError(null);
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
              disabled={isSubmitting}
            />
            {captchaEnabled ? (
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
            {error ? (
              <div className="alert" role="alert">
                <span>{error}</span>
              </div>
            ) : null}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? registerMessages.submitBusy
                : registerMessages.submitIdle}
            </Button>
          </form>
        </CardContent>
        <Separator />
        <CardFooter className="auth-card__footer">
          <div className="auth-card__footer-block">
            <div className="cluster-tight">
              <span className="text-muted">{registerMessages.footerPrompt}</span>
              <Link
                className={buttonClassNames({ variant: "secondary", size: "sm" })}
                href={buildLocalePath(locale, "/login")}
              >
                {registerMessages.footerAction}
              </Link>
            </div>
          </div>
        </CardFooter>
      </Card>
    </AuthSplitLayout>
  );
}
