"use client";

import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { fetchAdminSession } from "@/features/admin/admin-session";
import {
  fetchOrgSettings,
  fetchQuestionBankStatus,
  getQuestionBankErrorMessage,
  getOrgSettingsErrorMessage,
  type QuestionBankStatus,
  updateOrgSettings,
  type OrgSettings,
} from "@/features/admin/org-settings";
import { useAppLocale } from "@/lib/i18n/provider";
import {
  ORG_SETTINGS_MESSAGES,
  type OrgSettingsMessageLocale,
} from "@/features/admin/org-settings-messages";
import {
  DEFAULT_SETTINGS,
  LOGO_MIME_TYPES,
  MAX_LOGO_BYTES,
  ensureOption,
  formatSettings,
  isPlainRecord,
  resolveOrgSlug,
  toBoolean,
  toStringValue,
} from "@/features/admin/org-settings-view-model";
import { AdminOrgLogoModal } from "./admin-org-logo-modal";
import { AdminOrgSettingsSurface } from "./admin-org-settings-surface";

type LoadStatus = "loading" | "ready" | "error";

export function AdminOrgSettingsClient() {
  const locale = useAppLocale();
  const messageLocale: OrgSettingsMessageLocale = locale === "zh" ? "zh" : "en";
  const messages = ORG_SETTINGS_MESSAGES[messageLocale];
  const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savedSettings, setSavedSettings] = useState<OrgSettings>({});
  const [draftSettings, setDraftSettings] = useState<OrgSettings>({});
  const [jsonDraft, setJsonDraft] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isJsonFocused, setIsJsonFocused] = useState(false);
  const [isLogoModalOpen, setIsLogoModalOpen] = useState(false);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null);
  const [logoNotice, setLogoNotice] = useState<string | null>(null);
  const [savedOrgName, setSavedOrgName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [orgNameError, setOrgNameError] = useState<string | null>(null);
  const [orgSlug, setOrgSlug] = useState("");
  const [questionBankStatus, setQuestionBankStatus] =
    useState<QuestionBankStatus | null>(null);
  const [questionBankError, setQuestionBankError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    fetchOrgSettings()
      .then((response) => {
        if (!isActive) {
          return;
        }
        setSavedSettings(response);
        setDraftSettings(response);
        setJsonDraft(formatSettings(response));
        setLoadStatus("ready");
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(
          getOrgSettingsErrorMessage(error, messages.errors.orgSettings)
        );
        setLoadStatus("error");
      });
    return () => {
      isActive = false;
    };
  }, [messages.errors.orgSettings]);

  useEffect(() => {
    let isActive = true;
    fetchQuestionBankStatus()
      .then((status) => {
        if (!isActive) {
          return;
        }
        setQuestionBankStatus(status);
        setQuestionBankError(null);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setQuestionBankError(
          getQuestionBankErrorMessage(error, messages.errors.questionBank)
        );
        setQuestionBankStatus(null);
      });
    return () => {
      isActive = false;
    };
  }, [messages.errors.questionBank]);

  useEffect(() => {
    let isActive = true;
    fetchAdminSession()
      .then((session) => {
        if (!isActive) {
          return;
        }
        setSavedOrgName(session.org.name);
        setOrgName(session.org.name);
        setOrgSlug(resolveOrgSlug(session));
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setSavedOrgName("");
        setOrgName("");
        setOrgSlug("");
      });
    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (isJsonFocused) {
      return;
    }
    const formatted = formatSettings(draftSettings);
    setJsonDraft((prev) => (prev === formatted ? prev : formatted));
  }, [draftSettings, isJsonFocused]);

  useEffect(() => {
    if (!logoFile) {
      setLogoPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(logoFile);
    setLogoPreviewUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [logoFile]);

  const savedSnapshot = useMemo(
    () => formatSettings(savedSettings),
    [savedSettings]
  );
  const draftSnapshot = useMemo(
    () => formatSettings(draftSettings),
    [draftSettings]
  );

  const normalizedOrgName = orgName.trim();
  const normalizedSavedOrgName = savedOrgName.trim();
  const isNameDirty = normalizedOrgName !== normalizedSavedOrgName;
  const isDirty = draftSnapshot !== savedSnapshot || isNameDirty;
  const isReady = loadStatus === "ready";

  const allowCohorts = toBoolean(
    draftSettings["allow_cohorts"],
    DEFAULT_SETTINGS.allow_cohorts
  );
  const allowMentorAssignments = toBoolean(
    draftSettings["allow_mentor_assignments"],
    DEFAULT_SETTINGS.allow_mentor_assignments
  );
  const orgType = toStringValue(
    draftSettings["org_type"],
    DEFAULT_SETTINGS.org_type
  );
  const mentorVisibility = toStringValue(
    draftSettings["default_mentor_visibility"],
    DEFAULT_SETTINGS.default_mentor_visibility
  );

  const orgTypeOptions = useMemo(
    () =>
      ensureOption(
        [
          {
            value: "institution",
            label: messages.options.orgType.institution,
          },
          {
            value: "private",
            label: messages.options.orgType.private,
          },
        ],
        orgType,
        messages.options.currentPrefix
      ),
    [messages, orgType]
  );
  const mentorVisibilityOptions = useMemo(
    () =>
      ensureOption(
        [
          {
            value: "summaries_only",
            label: messages.options.mentorVisibility.summaries_only.label,
            description:
              messages.options.mentorVisibility.summaries_only.description,
          },
          {
            value: "full",
            label: messages.options.mentorVisibility.full.label,
            description: messages.options.mentorVisibility.full.description,
          },
          {
            value: "private",
            label: messages.options.mentorVisibility.private.label,
            description: messages.options.mentorVisibility.private.description,
          },
        ],
        mentorVisibility,
        messages.options.currentPrefix
      ),
    [mentorVisibility, messages]
  );

  const statusNote = useMemo(() => {
    if (loadStatus === "loading") {
      return messages.status.loading;
    }
    if (loadStatus === "error") {
      return messages.status.unavailable;
    }
    if (isSaving) {
      return messages.status.saving;
    }
    if (saveNotice) {
      return saveNotice;
    }
    if (isDirty) {
      return messages.status.unsaved;
    }
    return messages.status.upToDate;
  }, [isDirty, isSaving, loadStatus, messages, saveNotice]);

  const updateSetting = (key: string, value: unknown) => {
    setDraftSettings((prev) => ({ ...prev, [key]: value }));
    setRequestError(null);
    setSaveNotice(null);
  };

  const handleOrgNameChange = (event: ChangeEvent<HTMLInputElement>) => {
    setOrgName(event.target.value);
    setOrgNameError(null);
    setRequestError(null);
    setSaveNotice(null);
  };

  const handleLogoModalOpen = () => {
    setIsLogoModalOpen(true);
    setLogoNotice(null);
  };

  const handleLogoModalClose = () => {
    setIsLogoModalOpen(false);
  };

  const handleLogoFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      setLogoFile(null);
      setLogoNotice(null);
      return;
    }
    if (!LOGO_MIME_TYPES.has(file.type)) {
      setLogoFile(null);
      setLogoNotice(messages.logo.unsupported);
      event.target.value = "";
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      setLogoFile(null);
      setLogoNotice(messages.logo.tooLarge);
      event.target.value = "";
      return;
    }
    setLogoFile(file);
    setLogoNotice(null);
  };

  const handleLogoUpload = () => {
    if (!logoFile) {
      setLogoNotice(messages.logo.selectFile);
      return;
    }
    setLogoNotice(messages.logo.ready);
    setIsLogoModalOpen(false);
  };

  const handleReset = () => {
    setDraftSettings(savedSettings);
    setJsonDraft(formatSettings(savedSettings));
    setOrgName(savedOrgName);
    setOrgNameError(null);
    setJsonError(null);
    setRequestError(null);
    setSaveNotice(null);
  };

  const handleSave = async () => {
    if (jsonError) {
      return;
    }
    setRequestError(null);
    setOrgNameError(null);
    setSaveNotice(null);

    if (!normalizedOrgName && normalizedSavedOrgName) {
      setOrgNameError(messages.errors.orgNameRequired);
      return;
    }

    const payload = {
      settings: draftSettings,
      ...(normalizedOrgName ? { name: normalizedOrgName } : {}),
    };

    setIsSaving(true);
    try {
      const updated = await updateOrgSettings(payload);
      setSavedSettings(updated);
      setDraftSettings(updated);
      setJsonDraft(formatSettings(updated));
      setJsonError(null);
      if (normalizedOrgName) {
        setSavedOrgName(normalizedOrgName);
        setOrgName(normalizedOrgName);
      }
      setSaveNotice(messages.status.saved);
    } catch (error) {
      setRequestError(
        getOrgSettingsErrorMessage(error, messages.errors.orgSettings)
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleJsonChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const value = event.target.value;
    setJsonDraft(value);
    setRequestError(null);
    setSaveNotice(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(value);
    } catch {
      setJsonError(messages.errors.jsonInvalid);
      return;
    }

    if (!isPlainRecord(parsed)) {
      setJsonError(messages.errors.jsonObject);
      return;
    }

    setJsonError(null);
    setDraftSettings(parsed);
  };

  const handleJsonFocus = () => {
    setIsJsonFocused(true);
  };

  const handleJsonBlur = () => {
    setIsJsonFocused(false);
    if (!jsonError) {
      setJsonDraft(formatSettings(draftSettings));
    }
  };

  const hintId = "org-settings-hint";
  const errorId = jsonError ? "org-settings-error" : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const logoModalDescriptionId = "logo-modal-description";
  const mentorVisibilityLabelId = "mentor-visibility-label";

  return (
    <>
      <AdminOrgSettingsSurface
        messages={messages}
        messageLocale={messageLocale}
        loadError={loadError}
        requestError={requestError}
        logoPreviewUrl={logoPreviewUrl}
        isLogoModalOpen={isLogoModalOpen}
        isReady={isReady}
        isSaving={isSaving}
        orgName={orgName}
        orgNameError={orgNameError}
        orgSlug={orgSlug}
        orgType={orgType}
        orgTypeOptions={orgTypeOptions}
        questionBankStatus={questionBankStatus}
        questionBankError={questionBankError}
        allowCohorts={allowCohorts}
        allowMentorAssignments={allowMentorAssignments}
        mentorVisibility={mentorVisibility}
        mentorVisibilityOptions={mentorVisibilityOptions}
        mentorVisibilityLabelId={mentorVisibilityLabelId}
        jsonDraft={jsonDraft}
        jsonError={jsonError}
        describedBy={describedBy}
        hintId={hintId}
        errorId={errorId}
        statusNote={statusNote}
        isDirty={isDirty}
        onLogoModalOpen={handleLogoModalOpen}
        onOrgNameChange={handleOrgNameChange}
        onSettingChange={updateSetting}
        onJsonChange={handleJsonChange}
        onJsonFocus={handleJsonFocus}
        onJsonBlur={handleJsonBlur}
        onReset={handleReset}
        onSave={handleSave}
      />

      {isLogoModalOpen ? (
        <AdminOrgLogoModal
          messages={messages}
          logoModalDescriptionId={logoModalDescriptionId}
          logoPreviewUrl={logoPreviewUrl}
          logoFileName={logoFile?.name ?? null}
          logoNotice={logoNotice}
          hasLogoFile={Boolean(logoFile)}
          onClose={handleLogoModalClose}
          onLogoFileChange={handleLogoFileChange}
          onLogoUpload={handleLogoUpload}
        />
      ) : null}
    </>
  );
}
