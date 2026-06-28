"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { apiClient } from "@/lib/api/client";
import { getSafeErrorMessage } from "@/lib/api/safe-error-message";
import { orgStorage } from "@/lib/storage/org";

export type UserSession = {
  user: {
    id: string;
    email: string | null;
    displayName: string | null;
    emailVerified: boolean;
  };
  org: {
    id: string;
    name: string;
    settings: Record<string, unknown>;
  };
  membership: {
    id: string;
    orgRole: string;
    status: string;
  };
  capabilities: {
    isOrgAdmin: boolean;
    canManageOrgSettings: boolean;
    canManagePrompts: boolean;
    canManageMembers: boolean;
    canManageInvites: boolean;
    canManageCohorts: boolean;
    canManageAssignments: boolean;
    canManageProjects: boolean;
    canManageReports: boolean;
  };
  orgs: Array<{
    id: string;
    name: string;
    orgRole: string;
    status: string;
  }>;
  actorType: string;
};

type SessionStatus = "loading" | "ready" | "error";

type UserSessionState = {
  status: SessionStatus;
  session: UserSession | null;
  error: string | null;
  refresh: () => Promise<void>;
};

const UserSessionContext = createContext<UserSessionState | null>(null);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const requireString = (value: unknown, label: string): string => {
  const resolved = toTrimmedString(value);
  if (!resolved) {
    throw new Error(`Invalid ${label}`);
  }
  return resolved;
};

const toOptionalString = (value: unknown): string | null =>
  toTrimmedString(value);

const toBoolean = (value: unknown, fallback: boolean): boolean =>
  typeof value === "boolean" ? value : fallback;

const normalizeSession = (payload: unknown): UserSession => {
  if (!isRecord(payload)) {
    throw new Error("Invalid session payload");
  }

  const user = isRecord(payload.user) ? payload.user : null;
  const org = isRecord(payload.org) ? payload.org : null;
  const membership = isRecord(payload.membership) ? payload.membership : null;

  if (!user || !org || !membership) {
    throw new Error("Session payload is incomplete");
  }

  const orgRole = requireString(membership.org_role, "membership.org_role");
  const isOrgAdmin = orgRole === "owner" || orgRole === "admin";
  const capabilitiesSource = isRecord(payload.capabilities)
    ? payload.capabilities
    : {};

  const capabilities = {
    isOrgAdmin: toBoolean(capabilitiesSource.is_org_admin, isOrgAdmin),
    canManageOrgSettings: toBoolean(
      capabilitiesSource.can_manage_org_settings,
      isOrgAdmin
    ),
    canManagePrompts: toBoolean(
      capabilitiesSource.can_manage_prompts,
      isOrgAdmin
    ),
    canManageMembers: toBoolean(
      capabilitiesSource.can_manage_members,
      isOrgAdmin
    ),
    canManageInvites: toBoolean(
      capabilitiesSource.can_manage_invites,
      isOrgAdmin
    ),
    canManageCohorts: toBoolean(
      capabilitiesSource.can_manage_cohorts,
      isOrgAdmin
    ),
    canManageAssignments: toBoolean(
      capabilitiesSource.can_manage_assignments,
      isOrgAdmin
    ),
    canManageProjects: toBoolean(
      capabilitiesSource.can_manage_projects,
      isOrgAdmin
    ),
    canManageReports: toBoolean(
      capabilitiesSource.can_manage_reports,
      isOrgAdmin
    ),
  };

  const orgs = Array.isArray(payload.orgs)
    ? payload.orgs
        .map((item) => {
          if (!isRecord(item)) {
            return null;
          }
          const id = toTrimmedString(item.id);
          const name = toTrimmedString(item.name);
          if (!id || !name) {
            return null;
          }
          return {
            id,
            name,
            orgRole: toOptionalString(item.org_role) ?? orgRole,
            status: toOptionalString(item.status) ?? "active",
          };
        })
        .filter(
          (item): item is UserSession["orgs"][number] => Boolean(item)
        )
    : [];

  return {
    user: {
      id: requireString(user.id, "user.id"),
      email: toOptionalString(user.email),
      displayName: toOptionalString(user.display_name),
      emailVerified: toBoolean(user.email_verified, false),
    },
    org: {
      id: requireString(org.id, "org.id"),
      name: requireString(org.name, "org.name"),
      settings: isRecord(org.settings) ? org.settings : {},
    },
    membership: {
      id: requireString(membership.id, "membership.id"),
      orgRole,
      status: requireString(membership.status, "membership.status"),
    },
    capabilities,
    orgs,
    actorType: toOptionalString(payload.actor_type) ?? "user",
  };
};

export const isOrgAdmin = (session: UserSession): boolean =>
  session.capabilities.isOrgAdmin ||
  session.membership.orgRole === "owner" ||
  session.membership.orgRole === "admin";

export function UserSessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [session, setSession] = useState<UserSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(
    () => {
      isMountedRef.current = true;
      return () => {
        isMountedRef.current = false;
      };
    },
    []
  );

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await apiClient.fetchJson<unknown>("/session");
      const nextSession = normalizeSession(response);
      if (!isMountedRef.current) {
        return;
      }
      orgStorage.setOrgId(nextSession.org.id);
      setSession(nextSession);
      setStatus("ready");
    } catch (err) {
      if (!isMountedRef.current) {
        return;
      }
      setSession(null);
      setStatus("error");
      setError(
        getSafeErrorMessage(err, {
          default: "Unable to load session.",
          network: "Session service is unavailable. Try again shortly.",
          sessionExpired: "Your session expired. Please sign in again.",
          unavailable: "Session service is unavailable. Try again shortly.",
        })
      );
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ status, session, error, refresh }),
    [status, session, error, refresh]
  );

  return (
    <UserSessionContext.Provider value={value}>
      {children}
    </UserSessionContext.Provider>
  );
}

export const useUserSession = (): UserSessionState => {
  const context = useContext(UserSessionContext);
  if (!context) {
    return {
      status: "loading",
      session: null,
      error: null,
      refresh: async () => {},
    };
  }
  return context;
};
