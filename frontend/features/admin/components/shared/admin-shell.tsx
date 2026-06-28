"use client";

import { useMemo, useState, type ChangeEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { Badge } from "@/components/ui/badge";
import { buttonClassNames } from "@/components/ui/button";
import type { AdminSession } from "@/features/admin/admin-session";
import { AdminSessionProvider } from "@/features/admin/admin-session-context";
import {
  getVisibleAdminNavGroups,
  isAdminNavItemActive,
} from "@/features/admin/admin-route-config";
import { buildLocalePath, stripLocalePrefix } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { orgStorage } from "@/lib/storage/org";

type AdminShellProps = {
  session: AdminSession;
  children: React.ReactNode;
};

const resolveInitials = (value: string): string => {
  const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, " ").trim();
  if (!cleaned) {
    return "IS";
  }
  const parts = cleaned.split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "IS";
};

const formatRole = (role: string, labels: Record<string, string>): string => {
  const normalized = role.trim().toLowerCase();
  if (labels[normalized]) {
    return labels[normalized];
  }
  return role
    .trim()
    .split("_")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
};

export function AdminShell({ session, children }: AdminShellProps) {
  const locale = useAppLocale();
  const messages = useAppMessages().adminShell;
  const pathname = usePathname() ?? "/admin";
  const routePathname = stripLocalePrefix(pathname);
  const router = useRouter();
  const [activeOrgId, setActiveOrgId] = useState(session.org.id);
  const displayName =
    session.user.display_name || session.user.email || messages.fallbackAdminUser;
  const initials = resolveInitials(displayName);
  const roleLabel = formatRole(session.membership.org_role, messages.roles);
  const roleVariant =
    session.membership.org_role === "owner"
      ? "success"
      : session.membership.org_role === "admin"
        ? "info"
        : "warning";

  const activeNavGroups = useMemo(
    () =>
      getVisibleAdminNavGroups(session).map((group) => ({
        key: group.key,
        label: messages.navGroups[group.key],
        items: group.items.map((item) => ({
          ...item,
          label: messages.nav[item.key].label,
          description: messages.nav[item.key].description,
          isActive: isAdminNavItemActive(routePathname, item),
        })),
      })),
    [messages.nav, messages.navGroups, routePathname, session]
  );

  const adminOrgs = useMemo(
    () =>
      session.orgs.filter(
        (org) =>
          org.status === "active" &&
          (org.org_role === "owner" || org.org_role === "admin")
      ),
    [session.orgs]
  );
  const showOrgSwitcher = adminOrgs.length > 1;

  const handleOrgChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextOrgId = event.target.value;
    if (!nextOrgId || nextOrgId === activeOrgId) {
      return;
    }
    const nextOrg = adminOrgs.find((org) => org.id === nextOrgId);
    if (!nextOrg) {
      return;
    }
    orgStorage.setOrgId(nextOrgId);
    setActiveOrgId(nextOrgId);
    router.replace(buildLocalePath(locale, "/admin"));
    router.refresh();
  };

  return (
    <AdminSessionProvider session={session}>
      <div className="admin-shell">
        <a className="admin-skip-link" href="#admin-main-content">
          {messages.skipToContent}
        </a>
        <aside className="admin-sidebar">
          <div className="admin-brand">
            <div className="brand">
              <div className="brand-mark">IS</div>
              <div className="stack-sm">
                <p className="brand-title">IdeaSense AI</p>
                <p className="brand-subtitle">{messages.brandSubtitle}</p>
              </div>
            </div>
          </div>

          <div className="admin-nav-card">
            {activeNavGroups.map((group) => (
              <div className="admin-nav-group" key={group.key}>
                <p className="sidebar-label">{group.label}</p>
                <nav
                  className="admin-nav"
                  aria-label={`${messages.navigationAriaLabel}: ${group.label}`}
                >
                  {group.items.map((item) => (
                    <Link
                      key={item.href}
                      className={[
                        "admin-nav-item",
                        item.isActive ? "admin-nav-item--active" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      href={buildLocalePath(locale, item.href)}
                      aria-current={item.isActive ? "page" : undefined}
                    >
                      <span className="admin-nav-item__label">
                        {item.label}
                      </span>
                      <span className="admin-nav-item__meta">
                        {item.description}
                      </span>
                    </Link>
                  ))}
                </nav>
              </div>
            ))}
          </div>

          <div className="admin-sidebar__footer">
            <div className="admin-sidebar__meta">
              <span className="text-muted">{messages.environment}</span>
              <strong>{messages.admin}</strong>
            </div>
            <Link
              className={buttonClassNames({ variant: "ghost", size: "sm" })}
              href={buildLocalePath(locale, "/projects")}
            >
              {messages.backToWorkspace}
            </Link>
          </div>
        </aside>

        <div className="admin-main">
          <header className="admin-topbar">
            <div className="admin-org">
              <span className="eyebrow">{messages.organization}</span>
              <div className="admin-org__name">
                {showOrgSwitcher ? (
                  <>
                    <label className="sr-only" htmlFor="admin-org-switcher">
                      {messages.switchOrganization}
                    </label>
                    <select
                      id="admin-org-switcher"
                      className="input input--sm admin-org__select"
                      value={activeOrgId}
                      onChange={handleOrgChange}
                      aria-label={messages.switchOrganization}
                    >
                      {adminOrgs.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.name}
                        </option>
                      ))}
                    </select>
                  </>
                ) : (
                  <span>{session.org.name}</span>
                )}
                <Badge variant={roleVariant}>{roleLabel}</Badge>
              </div>
            </div>

            <div className="cluster">
              <LanguageSwitcher compact className="shrink-0" />
              <details className="admin-user">
                <summary className="admin-user__summary">
                  <span className="admin-avatar" aria-hidden="true">
                    {initials}
                  </span>
                  <span className="admin-user__name">{displayName}</span>
                </summary>
                <div className="admin-user__menu">
                  <div className="admin-user__card">
                    <div>
                      <p className="admin-user__title">{displayName}</p>
                      <p className="text-muted">
                        {session.user.email ?? messages.noEmailOnFile}
                      </p>
                    </div>
                    <Badge variant={roleVariant}>{roleLabel}</Badge>
                  </div>
                  <div className="admin-user__actions">
                    <Link
                      className={buttonClassNames({
                        variant: "secondary",
                        size: "sm",
                      })}
                      href={buildLocalePath(locale, "/projects")}
                    >
                      {messages.workspaceAction}
                    </Link>
                    <Link
                      className={buttonClassNames({
                        variant: "ghost",
                        size: "sm",
                      })}
                      href={buildLocalePath(locale, "/logout", "?reason=switch")}
                    >
                      {messages.signOut}
                    </Link>
                  </div>
                </div>
              </details>
            </div>
          </header>

          <main id="admin-main-content" className="admin-content" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
    </AdminSessionProvider>
  );
}
