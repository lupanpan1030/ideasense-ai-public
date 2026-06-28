"use client";

import { useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUserSession } from "@/features/auth/user-session";
import { getUserProfile, getUserProfileFromToken } from "@/lib/auth/user-profile";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { orgStorage } from "@/lib/storage/org";
import { tokenStorage } from "@/lib/storage/token";
import { Check, Search } from "lucide-react";

export function AppShellTopbar() {
  const locale = useAppLocale();
  const messages = useAppMessages().appShell;
  const topbarMessages = messages.topbar;
  const router = useRouter();
  const { session } = useUserSession();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const orgOptions = useMemo(() => session?.orgs ?? [], [session?.orgs]);
  const activeOrgId = selectedOrgId ?? session?.org.id ?? "";
  const userProfile = useMemo(() => {
    if (session) {
      return getUserProfile({
        displayName: session.user.displayName,
        email: session.user.email,
      });
    }
    const token = tokenStorage.getToken();
    return getUserProfileFromToken(token);
  }, [session]);
  const emailVerified = session?.user.emailVerified;
  const showUnverifiedBadge = emailVerified === false;
  const showOrgSwitcher = useMemo(() => {
    if (orgOptions.length > 1) {
      return true;
    }
    return orgOptions.some((org) => org.status === "invited");
  }, [orgOptions]);

  const handleOrgChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextOrgId = event.target.value;
    if (!nextOrgId || nextOrgId === activeOrgId) {
      return;
    }
    const selectedOrg = orgOptions.find((org) => org.id === nextOrgId);
    if (!selectedOrg || selectedOrg.status !== "active") {
      return;
    }
    orgStorage.setOrgId(nextOrgId);
    setSelectedOrgId(nextOrgId);
    router.replace(buildLocalePath(locale, "/projects"));
    router.refresh();
  };

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      router.push(buildLocalePath(locale, "/projects"));
      return;
    }
    const params = new URLSearchParams({ q: query });
    router.push(buildLocalePath(locale, "/projects", params.toString()));
  };

  return (
    <header className="app-shell__topbar">
      <form className="topbar-search" onSubmit={handleSearchSubmit}>
        <label className="sr-only" htmlFor="workspace-search">
          {topbarMessages.searchLabel}
        </label>
        <input
          id="workspace-search"
          className="input input--sm topbar-search__input"
          type="search"
          placeholder={topbarMessages.searchPlaceholder}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
        <Button
          type="submit"
          variant="secondary"
          size="sm"
          className="topbar-search__submit"
          aria-label={topbarMessages.searchSubmit}
          title={topbarMessages.searchSubmit}
        >
          <Search className="h-4 w-4" />
        </Button>
      </form>
      <div className="cluster topbar-actions">
        <LanguageSwitcher compact className="shrink-0" />
        {showOrgSwitcher ? (
          <div className="topbar-org-switcher">
            <label className="sr-only" htmlFor="org-switcher">
              {topbarMessages.switchOrganization}
            </label>
            <select
              id="org-switcher"
              className="input input--sm topbar-org-switcher__select"
              value={activeOrgId ?? ""}
              onChange={handleOrgChange}
              aria-label={topbarMessages.switchOrganization}
            >
              {orgOptions.map((org) => {
                const suffix =
                  org.status === "invited" ? topbarMessages.invitedSuffix : "";
                return (
                  <option
                    key={org.id}
                    value={org.id}
                    disabled={org.status !== "active"}
                  >
                    {org.name}
                    {suffix}
                  </option>
                );
              })}
            </select>
          </div>
        ) : null}
        <Badge variant="success" className="topbar-status-badge">
          {topbarMessages.synced}
        </Badge>
        {showUnverifiedBadge ? (
          <Link
            className="topbar-verify"
            href={buildLocalePath(locale, "/verify-email")}
            title={topbarMessages.verifyYourEmail}
            aria-label={topbarMessages.verifyYourEmail}
          >
            <Badge variant="warning">{topbarMessages.emailUnverified}</Badge>
          </Link>
        ) : null}
        <details className="topbar-user-menu">
          <summary
            className="topbar-user__summary"
            aria-label={topbarMessages.accountLabel.replace(
              "{name}",
              userProfile.label
            )}
            title={userProfile.label}
          >
            <span className="topbar-user">
              <span className="topbar-user__text">{userProfile.initials}</span>
              {emailVerified ? (
                <span
                  className="topbar-user__status"
                  aria-label={topbarMessages.emailVerified}
                  title={topbarMessages.emailVerified}
                >
                  <Check
                    className="topbar-user__status-icon"
                    aria-hidden="true"
                  />
                </span>
              ) : null}
            </span>
          </summary>
          <div className="topbar-user__panel" role="menu">
            <div className="topbar-user__identity">
              <p className="topbar-user__name">{userProfile.label}</p>
              {userProfile.email ? (
                <p className="topbar-user__email text-muted">
                  {userProfile.email}
                </p>
              ) : null}
            </div>
            <div className="topbar-user__divider" aria-hidden="true" />
            <div className="topbar-user__actions">
              <Link
                className="topbar-user__action"
                href={buildLocalePath(locale, "/settings")}
              >
                {topbarMessages.personalSettings}
              </Link>
              <Link
                className="topbar-user__action topbar-user__action--danger"
                href={buildLocalePath(locale, "/logout", "?reason=signout")}
              >
                {topbarMessages.signOut}
              </Link>
            </div>
          </div>
        </details>
      </div>
    </header>
  );
}
