"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthSplitLayout } from "@/components/auth/auth-split-layout";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  fetchInvitationDetails,
  getInviteDetailsErrorMessage,
} from "@/features/invitations/invite-details";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { inviteTokenStorage } from "@/lib/storage/invite";

const APP_NAME = "IdeaSense AI";

export default function JoinClient() {
  const locale = useAppLocale();
  const joinMessages = useAppMessages().auth.join;
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    setIsReady(false);
    setInviteEmail(null);
    if (!token) {
      setError(joinMessages.errors.missingInvite);
      setIsReady(true);
      return;
    }
    inviteTokenStorage.setToken(token);
    setError(null);

    const loadDetails = async () => {
      try {
        const details = await fetchInvitationDetails(token);
        if (!isActive) {
          return;
        }
        setInviteEmail(details.invitee_email);
      } catch (err) {
        if (!isActive) {
          return;
        }
        setError(getInviteDetailsErrorMessage(err));
      } finally {
        if (isActive) {
          setIsReady(true);
        }
      }
    };

    void loadDetails();

    return () => {
      isActive = false;
    };
  }, [joinMessages.errors.missingInvite, token]);

  const handleContinue = (path: "/login" | "/register") => {
    if (token) {
      inviteTokenStorage.setToken(token);
    }
    if (path === "/register" && inviteEmail) {
      const params = new URLSearchParams({ email: inviteEmail });
      router.push(buildLocalePath(locale, path, params.toString()));
      return;
    }
    router.push(buildLocalePath(locale, path));
  };

  return (
    <AuthSplitLayout
      badge={`${APP_NAME} ${joinMessages.badgeSuffix}`}
      title={`${joinMessages.titlePrefix} ${APP_NAME}`}
      subtitle={joinMessages.subtitle}
      visualTitle={joinMessages.cardTitle}
      visualDescription={joinMessages.cardDescription}
      visualNoteTitle={inviteEmail ? `${joinMessages.inviteSentPrefix} ${inviteEmail}.` : undefined}
      visualNoteDescription={joinMessages.footerHelp}
      mode="neutral"
      visualVariant="simple"
      simpleTone={error ? "warning" : "info"}
    >
      <Card className="auth-card">
        <CardHeader>
          <CardTitle>{joinMessages.cardTitle}</CardTitle>
          <CardDescription>{joinMessages.cardDescription}</CardDescription>
        </CardHeader>
        <Separator />
        <CardContent className="stack">
          {error ? (
            <div className="alert" role="alert">
              <span>{error}</span>
            </div>
          ) : null}
          {inviteEmail ? (
            <p className="text-muted">
              {joinMessages.inviteSentPrefix} {inviteEmail}.
            </p>
          ) : null}
          <div className="stack-sm">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleContinue("/login")}
              disabled={!isReady}
            >
              {joinMessages.existingUserAction}
            </Button>
            <Button
              type="button"
              onClick={() => handleContinue("/register")}
              disabled={!isReady}
            >
              {joinMessages.newUserPrefix} {APP_NAME}?{" "}
              {joinMessages.newUserAction}
            </Button>
          </div>
        </CardContent>
        <Separator />
        <CardFooter>
          <span className="text-muted">{joinMessages.footerHelp}</span>
        </CardFooter>
      </Card>
    </AuthSplitLayout>
  );
}
