"use client";

import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
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
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { useUserSession } from "@/features/auth/user-session";
import {
  fetchUserSettings,
  getUserProfileErrorMessage,
  getUserSettingsErrorMessage,
  updateUserProfile,
  updateUserSettings,
  type UserSettings,
  type UserSettingsUpdate,
} from "@/features/settings/user-settings";
import { getUserProfile, getUserProfileFromToken } from "@/lib/auth/user-profile";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { tokenStorage } from "@/lib/storage/token";

type ProfileStatus = "idle" | "saving" | "saved" | "error";
type SettingsStatus = "loading" | "idle" | "saving" | "saved" | "error";

const normalizeDisplayName = (value: string): string => value.trim();

const normalizeTimeZone = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const resolveBrowserTimeZone = (): string | null => {
  try {
    const resolved = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return resolved ? resolved : null;
  } catch {
    return null;
  }
};

const resolveSupportedTimeZones = (): string[] => {
  if (typeof Intl === "undefined") {
    return [];
  }
  const supportedValuesOf = (
    Intl as typeof Intl & { supportedValuesOf?: (key: string) => string[] }
  ).supportedValuesOf;
  if (typeof supportedValuesOf !== "function") {
    return [];
  }
  try {
    const values = supportedValuesOf("timeZone");
    return Array.isArray(values) ? values : [];
  } catch {
    return [];
  }
};

export default function SettingsPage() {
  const locale = useAppLocale();
  const settingsMessages = useAppMessages().settings;
  const { session, status: sessionStatus, refresh } = useUserSession();
  const [fallbackProfile] = useState(() => {
    const token = tokenStorage.getToken();
    return getUserProfileFromToken(token);
  });
  const profile = session
    ? getUserProfile({
        displayName: session.user.displayName,
        email: session.user.email,
      })
    : fallbackProfile;

  const emailVerified = session?.user.emailVerified;
  const isEmailKnown = typeof emailVerified === "boolean";
  const showVerifyLink = emailVerified === false;
  const statusBadge =
    emailVerified === true ? (
      <Badge variant="success">{settingsMessages.statusBadges.verified}</Badge>
    ) : emailVerified === false ? (
      <Badge variant="warning">{settingsMessages.statusBadges.unverified}</Badge>
    ) : (
      <Badge variant="secondary">{settingsMessages.statusBadges.checking}</Badge>
    );
  const statusNote = !isEmailKnown
    ? settingsMessages.statusNotes.checking
    : emailVerified
      ? settingsMessages.statusNotes.verified
      : settingsMessages.statusNotes.unverified;

  const [displayNameDraft, setDisplayNameDraft] = useState<string | null>(null);
  const [profileStatus, setProfileStatus] = useState<ProfileStatus>("idle");
  const [profileError, setProfileError] = useState<string | null>(null);
  const sessionDisplayName = session?.user.displayName ?? "";
  const effectiveDisplayName = displayNameDraft ?? sessionDisplayName;
  const isProfileDirty =
    profileStatus === "saved"
      ? false
      : normalizeDisplayName(effectiveDisplayName) !==
        normalizeDisplayName(sessionDisplayName);
  const profileDisabled = profileStatus === "saving";
  const profileStatusNote = profileError
    ? profileError
    : profileStatus === "saving"
      ? settingsMessages.profileStatus.saving
      : profileStatus === "saved"
        ? settingsMessages.profileStatus.saved
        : isProfileDirty
          ? settingsMessages.profileStatus.unsaved
          : settingsMessages.profileStatus.upToDate;

  const handleDisplayNameChange = (event: ChangeEvent<HTMLInputElement>) => {
    setDisplayNameDraft(event.target.value);
    if (profileStatus !== "idle") {
      setProfileStatus("idle");
    }
    setProfileError(null);
  };

  const handleProfileReset = () => {
    setDisplayNameDraft(null);
    setProfileError(null);
    setProfileStatus("idle");
  };

  const handleProfileSave = async () => {
    if (!isProfileDirty || profileDisabled) {
      return;
    }
    setProfileStatus("saving");
    setProfileError(null);
    try {
      const normalizedName = normalizeDisplayName(effectiveDisplayName);
      const updated = await updateUserProfile({
        display_name: normalizedName ? normalizedName : null,
      });
      const nextName = updated.display_name ?? "";
      setDisplayNameDraft(nextName);
      setProfileStatus("saved");
      await refresh();
      setDisplayNameDraft(null);
    } catch (error) {
      setProfileStatus("error");
      setProfileError(
        getUserProfileErrorMessage(error, settingsMessages.errors.profile)
      );
    }
  };

  const browserTimeZone = useMemo(() => resolveBrowserTimeZone(), []);
  const supportedTimeZones = useMemo(() => resolveSupportedTimeZones(), []);
  const timeZoneOptions = useMemo(() => {
    if (!supportedTimeZones.length) {
      return browserTimeZone ? [browserTimeZone] : [];
    }
    if (!browserTimeZone) {
      return supportedTimeZones;
    }
    return supportedTimeZones.filter((tz) => tz !== browserTimeZone);
  }, [browserTimeZone, supportedTimeZones]);

  const [settingsBase, setSettingsBase] = useState<UserSettings | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<UserSettings | null>(null);
  const [settingsStatus, setSettingsStatus] =
    useState<SettingsStatus>("loading");
  const [settingsError, setSettingsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadSettings = async () => {
      setSettingsStatus("loading");
      setSettingsError(null);
      try {
        const data = await fetchUserSettings();
        if (cancelled) {
          return;
        }
        setSettingsBase(data);
        setSettingsDraft(data);
        setSettingsStatus("idle");
      } catch (error) {
        if (cancelled) {
          return;
        }
        setSettingsStatus("error");
        setSettingsError(
          getUserSettingsErrorMessage(error, settingsMessages.errors.preferences)
        );
      }
    };

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, [settingsMessages.errors.preferences]);

  const isSettingsDirty = Boolean(
    settingsBase &&
      settingsDraft &&
      (settingsBase.email_notifications !==
        settingsDraft.email_notifications ||
        settingsBase.weekly_summary !== settingsDraft.weekly_summary ||
        normalizeTimeZone(settingsBase.time_zone) !==
          normalizeTimeZone(settingsDraft.time_zone))
  );
  const settingsDisabled =
    settingsStatus === "loading" || settingsStatus === "saving";
  const settingsStatusNote = settingsError
    ? settingsError
    : settingsStatus === "loading"
      ? settingsMessages.preferencesStatus.loading
      : settingsStatus === "saving"
        ? settingsMessages.preferencesStatus.saving
        : settingsStatus === "saved"
          ? settingsMessages.preferencesStatus.saved
          : isSettingsDirty
            ? settingsMessages.preferencesStatus.unsaved
            : settingsMessages.preferencesStatus.upToDate;

  const updateDraft = <K extends keyof UserSettings>(
    key: K,
    value: UserSettings[K]
  ) => {
    setSettingsDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
    if (settingsStatus !== "idle") {
      setSettingsStatus("idle");
    }
    setSettingsError(null);
  };

  const handleSettingsReset = () => {
    if (!settingsBase) {
      return;
    }
    setSettingsDraft(settingsBase);
    setSettingsStatus("idle");
    setSettingsError(null);
  };

  const handleSettingsSave = async () => {
    if (!settingsBase || !settingsDraft || settingsDisabled) {
      return;
    }
    const payload: UserSettingsUpdate = {};
    if (
      settingsBase.email_notifications !== settingsDraft.email_notifications
    ) {
      payload.email_notifications = settingsDraft.email_notifications;
    }
    if (settingsBase.weekly_summary !== settingsDraft.weekly_summary) {
      payload.weekly_summary = settingsDraft.weekly_summary;
    }
    const baseTimeZone = normalizeTimeZone(settingsBase.time_zone);
    const draftTimeZone = normalizeTimeZone(settingsDraft.time_zone);
    if (baseTimeZone !== draftTimeZone) {
      payload.time_zone = draftTimeZone;
    }
    if (!Object.keys(payload).length) {
      return;
    }
    setSettingsStatus("saving");
    setSettingsError(null);
    try {
      const updated = await updateUserSettings(payload);
      setSettingsBase(updated);
      setSettingsDraft(updated);
      setSettingsStatus("saved");
    } catch (error) {
      setSettingsStatus("error");
      setSettingsError(
        getUserSettingsErrorMessage(error, settingsMessages.errors.preferences)
      );
    }
  };

  const timeZoneValue = settingsDraft?.time_zone ?? "auto";
  const timeZoneLabel = browserTimeZone
    ? settingsMessages.preferences.autoTimeZone.replace(
        "{timeZone}",
        browserTimeZone
      )
    : settingsMessages.preferences.autoTimeZone.replace(
        "{timeZone}",
        settingsMessages.preferences.autoTimeZoneBrowserFallback
      );

  return (
    <div className="page page--settings">
      <div className="settings-shell">
        <div className="page-header settings-header">
          <div className="stack-sm">
            <p className="eyebrow">{settingsMessages.page.eyebrow}</p>
            <h1 className="page-title">{settingsMessages.page.title}</h1>
            <p className="page-subtitle">{settingsMessages.page.subtitle}</p>
          </div>
          <div className="page-actions">
            <Link
              className={buttonClassNames({ variant: "secondary", size: "sm" })}
              href={buildLocalePath(locale, "/projects")}
            >
              {settingsMessages.page.backToProjects}
            </Link>
          </div>
        </div>

        <Separator />

        <div className="settings-stack">
          <Card className="settings-hero">
            <CardHeader className="settings-hero__header">
              <div className="stack-sm">
                <p className="eyebrow">{settingsMessages.profile.eyebrow}</p>
                <CardTitle>{settingsMessages.profile.title}</CardTitle>
                <CardDescription>{settingsMessages.profile.description}</CardDescription>
              </div>
              {statusBadge}
            </CardHeader>
            <CardContent className="settings-hero__content">
              <div className="settings-hero__identity">
                <div className="settings-hero__avatar">{profile.initials}</div>
                <div>
                  <p className="settings-hero__name">{profile.label}</p>
                  {profile.email ? (
                    <p className="settings-hero__email text-muted">
                      {profile.email}
                    </p>
                  ) : (
                    <p className="settings-hero__email text-muted">
                      {settingsMessages.profile.noEmailOnFile}
                    </p>
                  )}
                </div>
              </div>
              <div className="settings-hero__form">
                <Input
                  id="display-name"
                  label={settingsMessages.profile.displayNameLabel}
                  hint={settingsMessages.profile.displayNameHint}
                  value={effectiveDisplayName}
                  onChange={handleDisplayNameChange}
                  disabled={profileDisabled || sessionStatus === "loading"}
                  autoComplete="name"
                />
              </div>
            </CardContent>
            <CardFooter className="settings-card__footer">
              <span
                className={
                  profileStatus === "error" ? "field__error" : "text-muted"
                }
              >
                {profileStatusNote}
              </span>
              <div className="cluster">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleProfileReset}
                  disabled={!isProfileDirty || profileDisabled}
                >
                  {settingsMessages.profile.reset}
                </Button>
                <Button
                  type="button"
                  onClick={handleProfileSave}
                  disabled={!isProfileDirty || profileDisabled}
                >
                  {profileStatus === "saving"
                    ? settingsMessages.profile.saving
                    : settingsMessages.profile.save}
                </Button>
              </div>
            </CardFooter>
          </Card>

          <Card className="settings-section">
            <CardHeader>
              <CardTitle>{settingsMessages.security.title}</CardTitle>
              <CardDescription>{settingsMessages.security.description}</CardDescription>
            </CardHeader>
            <CardContent className="stack-sm">
              <div className="cluster">
                <Link
                  className={buttonClassNames({
                    variant: "secondary",
                    size: "sm",
                  })}
                  href={buildLocalePath(locale, "/forgot-password")}
                >
                  {settingsMessages.security.changePassword}
                </Link>
                {showVerifyLink ? (
                  <Link
                    className={buttonClassNames({
                      variant: "ghost",
                      size: "sm",
                    })}
                    href={buildLocalePath(locale, "/verify-email")}
                  >
                    {settingsMessages.security.verifyEmail}
                  </Link>
                ) : null}
              </div>
              <span className="text-muted">{statusNote}</span>
            </CardContent>
          </Card>

          <Card className="settings-section">
            <CardHeader>
              <CardTitle>{settingsMessages.preferences.title}</CardTitle>
              <CardDescription>{settingsMessages.preferences.description}</CardDescription>
            </CardHeader>
            <CardContent className="stack">
              <div className="settings-toggle-list">
                <label className="settings-toggle">
                  <span className="settings-toggle__text">
                    <span className="settings-toggle__label">
                      {settingsMessages.preferences.emailNotificationsLabel}
                    </span>
                    <span className="settings-toggle__hint">
                      {settingsMessages.preferences.emailNotificationsHint}
                    </span>
                  </span>
                  <span className="settings-switch">
                    <input
                      type="checkbox"
                      role="switch"
                      checked={Boolean(settingsDraft?.email_notifications)}
                      onChange={(event) =>
                        updateDraft(
                          "email_notifications",
                          event.target.checked
                        )
                      }
                      disabled={settingsDisabled}
                    />
                    <span className="settings-switch__track" aria-hidden>
                      <span className="settings-switch__thumb" />
                    </span>
                  </span>
                </label>
                <label className="settings-toggle">
                  <span className="settings-toggle__text">
                    <span className="settings-toggle__label">
                      {settingsMessages.preferences.weeklySummaryLabel}
                    </span>
                    <span className="settings-toggle__hint">
                      {settingsMessages.preferences.weeklySummaryHint}
                    </span>
                  </span>
                  <span className="settings-switch">
                    <input
                      type="checkbox"
                      role="switch"
                      checked={Boolean(settingsDraft?.weekly_summary)}
                      onChange={(event) =>
                        updateDraft("weekly_summary", event.target.checked)
                      }
                      disabled={settingsDisabled}
                    />
                    <span className="settings-switch__track" aria-hidden>
                      <span className="settings-switch__thumb" />
                    </span>
                  </span>
                </label>
              </div>

              <div className="field">
                <span className="field__label">
                  {settingsMessages.preferences.languageLabel}
                </span>
                <div>
                  <LanguageSwitcher
                    ariaLabel={settingsMessages.preferences.languageLabel}
                  />
                </div>
                <p className="field__hint">
                  {settingsMessages.preferences.languageHint}
                </p>
              </div>

              <div className="field">
                <label className="field__label" htmlFor="time-zone">
                  {settingsMessages.preferences.timeZoneLabel}
                </label>
                {timeZoneOptions.length ? (
                  <select
                    id="time-zone"
                    className="input"
                    value={timeZoneValue}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateDraft(
                        "time_zone",
                        value === "auto" ? null : value
                      );
                    }}
                    disabled={settingsDisabled}
                  >
                    <option value="auto">{timeZoneLabel}</option>
                    {timeZoneOptions.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id="time-zone"
                    className="input"
                    value={settingsDraft?.time_zone ?? ""}
                    placeholder={settingsMessages.preferences.timeZonePlaceholder}
                    onChange={(event) =>
                      updateDraft("time_zone", event.target.value)
                    }
                    disabled={settingsDisabled}
                  />
                )}
                <p className="field__hint">
                  {settingsMessages.preferences.timeZoneHint}
                </p>
              </div>
            </CardContent>
            <CardFooter className="settings-card__footer">
              <span
                className={settingsError ? "field__error" : "text-muted"}
              >
                {settingsStatusNote}
              </span>
              <div className="cluster">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleSettingsReset}
                  disabled={!isSettingsDirty || settingsDisabled}
                >
                  {settingsMessages.preferences.reset}
                </Button>
                <Button
                  type="button"
                  onClick={handleSettingsSave}
                  disabled={!isSettingsDirty || settingsDisabled}
                >
                  {settingsStatus === "saving"
                    ? settingsMessages.preferences.saving
                    : settingsMessages.preferences.save}
                </Button>
              </div>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
