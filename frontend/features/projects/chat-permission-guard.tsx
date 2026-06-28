"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchProjectPermissions } from "@/features/projects/project-permissions";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type ChatPermissionGuardProps = {
  projectId: string;
  children: React.ReactNode;
};

export function ChatPermissionGuard({
  projectId,
  children,
}: ChatPermissionGuardProps) {
  const router = useRouter();
  const locale = useAppLocale();
  const messages = useAppMessages().projectsWorkspace.permissionGuard;
  const [isAllowed, setIsAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let isActive = true;
    setIsAllowed(null);

    fetchProjectPermissions(projectId)
      .then((permissions) => {
        if (!isActive) {
          return;
        }
        if (!permissions.can_view_messages) {
          setIsAllowed(false);
          router.replace(buildLocalePath(locale, "/projects"));
          return;
        }
        setIsAllowed(true);
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setIsAllowed(false);
        router.replace(buildLocalePath(locale, "/projects"));
      });

    return () => {
      isActive = false;
    };
  }, [locale, projectId, router]);

  if (isAllowed === null) {
    return (
      <div className="page">
        <p className="text-muted">{messages.checking}</p>
      </div>
    );
  }

  if (isAllowed === false) {
    return null;
  }

  return <>{children}</>;
}
