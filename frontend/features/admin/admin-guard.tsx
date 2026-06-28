"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, ORG_CONTEXT_INVALID_EVENT } from "@/lib/api/client";
import { AdminShell } from "@/features/admin/components/shared/admin-shell";
import { fetchAdminSession, isOrgAdmin, type AdminSession } from "./admin-session";
import { hasAdminRouteAccess } from "./admin-route-config";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type GuardState =
  | { status: "loading" }
  | { status: "ready"; session: AdminSession }
  | { status: "denied" }
  | { status: "unauthorized" }
  | { status: "error"; message: string };

export const resolveAdminGuardErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminGuard"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.unauthorized;
    }
    if (error.status === 403) {
      return messages.errors.denied;
    }
    if (error.status >= 500) {
      return messages.errors.unavailable;
    }
  }
  return messages.errors.loadFailed;
};

const AdminGate = ({
  title,
  description,
  actions,
  tone = "default",
  role,
}: {
  title: string;
  description: string;
  actions?: React.ReactNode;
  tone?: "default" | "alert";
  role?: "alert" | "status";
}) => (
  <div className="admin-gate">
    <Card
      className="admin-gate__card"
      variant={tone === "alert" ? "alert" : "default"}
      role={role}
    >
      <CardHeader className="stack-sm">
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {actions ? (
        <CardFooter className="admin-gate__actions">{actions}</CardFooter>
      ) : null}
    </Card>
  </div>
);

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const locale = useAppLocale();
  const messages = useAppMessages().adminGuard;
  const [state, setState] = useState<GuardState>({ status: "loading" });
  const router = useRouter();
  const pathname = usePathname() ?? "/admin";

  useEffect(() => {
    let isActive = true;
    fetchAdminSession()
      .then((session) => {
        if (!isActive) {
          return;
        }
        if (!isOrgAdmin(session)) {
          setState({ status: "denied" });
          return;
        }
        setState({ status: "ready", session });
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "unauthorized" });
          return;
        }
        if (error instanceof ApiError && error.status === 403) {
          setState({ status: "denied" });
          return;
        }
        setState({
          status: "error",
          message: resolveAdminGuardErrorMessage(error, messages),
        });
      });
    return () => {
      isActive = false;
    };
  }, [messages]);

  useEffect(() => {
    const handleOrgContextInvalid = () => {
      router.replace(buildLocalePath(locale, "/projects"));
    };
    window.addEventListener(ORG_CONTEXT_INVALID_EVENT, handleOrgContextInvalid);
    return () => {
      window.removeEventListener(
        ORG_CONTEXT_INVALID_EVENT,
        handleOrgContextInvalid
      );
    };
  }, [locale, router]);

  const gateActions = useMemo(() => {
    return (
      <>
        <Link
          className={buttonClassNames({ variant: "secondary" })}
          href={buildLocalePath(locale, "/projects")}
        >
          {messages.actions.backToWorkspace}
        </Link>
        <Link
          className={buttonClassNames({ variant: "ghost" })}
          href={buildLocalePath(locale, "/login")}
        >
          {messages.actions.signIn}
        </Link>
      </>
    );
  }, [locale, messages.actions.backToWorkspace, messages.actions.signIn]);

  if (state.status === "loading") {
    return (
      <AdminGate
        title={messages.loading.title}
        description={messages.loading.description}
        role="status"
      />
    );
  }

  if (state.status === "unauthorized") {
    return (
      <AdminGate
        title={messages.unauthorized.title}
        description={messages.unauthorized.description}
        actions={
          <Link className={buttonClassNames()} href={buildLocalePath(locale, "/login")}>
            {messages.actions.goToSignIn}
          </Link>
        }
        tone="alert"
        role="alert"
      />
    );
  }

  if (state.status === "denied") {
    return (
      <AdminGate
        title={messages.denied.title}
        description={messages.denied.description}
        actions={gateActions}
        tone="alert"
        role="alert"
      />
    );
  }

  if (state.status === "error") {
    return (
      <AdminGate
        title={messages.error.title}
        description={state.message}
        actions={gateActions}
        tone="alert"
        role="alert"
      />
    );
  }

  if (!hasAdminRouteAccess(pathname, state.session)) {
    return (
      <AdminGate
        title={messages.denied.title}
        description={messages.denied.description}
        actions={gateActions}
        tone="alert"
        role="alert"
      />
    );
  }

  return <AdminShell session={state.session}>{children}</AdminShell>;
}
