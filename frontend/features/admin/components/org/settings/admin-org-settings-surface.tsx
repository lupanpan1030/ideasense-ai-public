import type { ChangeEventHandler } from "react";
import Image from "next/image";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { QuestionBankStatus } from "@/features/admin/org-settings";
import type {
  OrgSettingsMessageLocale,
  OrgSettingsMessages,
} from "@/features/admin/org-settings-messages";
import type { SelectOption } from "@/features/admin/org-settings-view-model";
import { formatTimestamp } from "@/features/admin/org-settings-view-model";

type AdminOrgSettingsSurfaceProps = {
  messages: OrgSettingsMessages;
  messageLocale: OrgSettingsMessageLocale;
  loadError: string | null;
  requestError: string | null;
  logoPreviewUrl: string | null;
  isLogoModalOpen: boolean;
  isReady: boolean;
  isSaving: boolean;
  orgName: string;
  orgNameError: string | null;
  orgSlug: string;
  orgType: string;
  orgTypeOptions: SelectOption[];
  questionBankStatus: QuestionBankStatus | null;
  questionBankError: string | null;
  allowCohorts: boolean;
  allowMentorAssignments: boolean;
  mentorVisibility: string;
  mentorVisibilityOptions: SelectOption[];
  mentorVisibilityLabelId: string;
  jsonDraft: string;
  jsonError: string | null;
  describedBy: string | undefined;
  hintId: string;
  errorId: string | undefined;
  statusNote: string;
  isDirty: boolean;
  onLogoModalOpen: () => void;
  onOrgNameChange: ChangeEventHandler<HTMLInputElement>;
  onSettingChange: (key: string, value: unknown) => void;
  onJsonChange: ChangeEventHandler<HTMLTextAreaElement>;
  onJsonFocus: () => void;
  onJsonBlur: () => void;
  onReset: () => void;
  onSave: () => void;
};

export function AdminOrgSettingsSurface({
  messages,
  messageLocale,
  loadError,
  requestError,
  logoPreviewUrl,
  isLogoModalOpen,
  isReady,
  isSaving,
  orgName,
  orgNameError,
  orgSlug,
  orgType,
  orgTypeOptions,
  questionBankStatus,
  questionBankError,
  allowCohorts,
  allowMentorAssignments,
  mentorVisibility,
  mentorVisibilityOptions,
  mentorVisibilityLabelId,
  jsonDraft,
  jsonError,
  describedBy,
  hintId,
  errorId,
  statusNote,
  isDirty,
  onLogoModalOpen,
  onOrgNameChange,
  onSettingChange,
  onJsonChange,
  onJsonFocus,
  onJsonBlur,
  onReset,
  onSave,
}: AdminOrgSettingsSurfaceProps) {
  return (
    <div className="page">
      <div className="page-header">
        <div className="stack-sm">
          <p className="eyebrow">{messages.page.eyebrow}</p>
          <h1 className="page-title">{messages.page.title}</h1>
          <p className="page-subtitle">{messages.page.subtitle}</p>
        </div>
      </div>

      {loadError ? (
        <div className="alert" role="alert">
          <span>{loadError}</span>
        </div>
      ) : null}
      {requestError ? (
        <div className="alert" role="alert">
          <span>{requestError}</span>
        </div>
      ) : null}

      <div className="admin-org-stack">
        <Card>
          <CardHeader className="stack-sm">
            <CardTitle>{messages.general.title}</CardTitle>
            <CardDescription>{messages.general.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="admin-org-profile">
              <button
                type="button"
                className="admin-org-logo admin-org-logo--button"
                onClick={onLogoModalOpen}
                aria-label={messages.general.logoAria}
                aria-haspopup="dialog"
                aria-expanded={isLogoModalOpen}
              >
                {logoPreviewUrl ? (
                  <Image
                    className="admin-org-logo__img"
                    src={logoPreviewUrl}
                    alt={messages.general.logoPreviewAlt}
                    fill
                    sizes="120px"
                    unoptimized
                  />
                ) : (
                  <span className="admin-org-logo__label">
                    {messages.general.logoLabel}
                  </span>
                )}
              </button>
              <div className="admin-org-fields">
                <Input
                  id="org-name"
                  label={messages.general.orgNameLabel}
                  value={orgName}
                  onChange={onOrgNameChange}
                  placeholder={
                    isReady ? messages.general.unavailable : messages.general.loading
                  }
                  disabled={!isReady || isSaving}
                  hint={messages.general.orgNameHint}
                  error={orgNameError ?? undefined}
                />
                <Input
                  id="org-slug"
                  label={messages.general.orgSlugLabel}
                  value={orgSlug}
                  placeholder={
                    isReady ? messages.general.unavailable : messages.general.loading
                  }
                  readOnly
                  aria-readonly="true"
                  disabled={!isReady}
                  hint={messages.general.orgSlugHint}
                />
                <div className="field">
                  <label className="field__label" htmlFor="org-type">
                    {messages.general.orgTypeLabel}
                  </label>
                  <select
                    id="org-type"
                    className="input"
                    value={orgType}
                    onChange={(event) =>
                      onSettingChange("org_type", event.target.value)
                    }
                    disabled={!isReady || isSaving}
                  >
                    {orgTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="field__hint">{messages.general.orgTypeHint}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="stack-sm">
            <CardTitle>{messages.questionBank.title}</CardTitle>
            <CardDescription>{messages.questionBank.description}</CardDescription>
          </CardHeader>
          <CardContent>
            {questionBankError ? (
              <p className="text-muted">{questionBankError}</p>
            ) : (
              <div className="admin-org-feature-grid">
                <div className="stack-sm">
                  <span className="eyebrow">{messages.questionBank.bankKey}</span>
                  <p>
                    {questionBankStatus?.bankKey ??
                      messages.questionBank.defaultBank}
                  </p>
                </div>
                <div className="stack-sm">
                  <span className="eyebrow">{messages.questionBank.version}</span>
                  <p>{questionBankStatus?.version ?? messages.status.unknown}</p>
                </div>
                <div className="stack-sm">
                  <span className="eyebrow">
                    {messages.questionBank.activated}
                  </span>
                  <p className="text-muted">
                    {formatTimestamp(
                      questionBankStatus?.activatedAt ??
                        questionBankStatus?.createdAt ??
                        null,
                      messageLocale,
                      messages.status.unknown
                    )}
                  </p>
                </div>
                <div className="stack-sm">
                  <span className="eyebrow">{messages.questionBank.source}</span>
                  <p className="text-muted">
                    {questionBankStatus?.source ?? messages.status.unknown}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="stack-sm">
            <CardTitle>{messages.features.title}</CardTitle>
            <CardDescription>{messages.features.description}</CardDescription>
          </CardHeader>
          <CardContent className="stack">
            <div className="admin-org-feature-grid">
              <div className="admin-org-feature-section">
                <div className="admin-toggle-list">
                  <label className="admin-toggle">
                    <span className="admin-toggle__text">
                      <span className="admin-toggle__label">
                        {messages.features.cohortsLabel}
                      </span>
                      <span className="admin-toggle__hint">
                        {messages.features.cohortsHint}
                      </span>
                    </span>
                    <span className="admin-switch">
                      <input
                        type="checkbox"
                        role="switch"
                        checked={allowCohorts}
                        onChange={(event) =>
                          onSettingChange("allow_cohorts", event.target.checked)
                        }
                        disabled={!isReady || isSaving}
                      />
                      <span className="admin-switch__track" aria-hidden="true">
                        <span className="admin-switch__thumb" />
                      </span>
                    </span>
                  </label>
                  <label className="admin-toggle">
                    <span className="admin-toggle__text">
                      <span className="admin-toggle__label">
                        {messages.features.mentorAssignmentsLabel}
                      </span>
                      <span className="admin-toggle__hint">
                        {messages.features.mentorAssignmentsHint}
                      </span>
                    </span>
                    <span className="admin-switch">
                      <input
                        type="checkbox"
                        role="switch"
                        checked={allowMentorAssignments}
                        onChange={(event) =>
                          onSettingChange(
                            "allow_mentor_assignments",
                            event.target.checked
                          )
                        }
                        disabled={!isReady || isSaving}
                      />
                      <span className="admin-switch__track" aria-hidden="true">
                        <span className="admin-switch__thumb" />
                      </span>
                    </span>
                  </label>
                </div>
              </div>

              <div className="admin-org-feature-section">
                <div className="field">
                  <span id={mentorVisibilityLabelId} className="field__label">
                    {messages.features.mentorVisibilityLabel}
                  </span>
                  <div
                    className="admin-radio-group"
                    role="radiogroup"
                    aria-labelledby={mentorVisibilityLabelId}
                  >
                    {mentorVisibilityOptions.map((option) => (
                      <label
                        key={option.value}
                        className={[
                          "admin-radio",
                          option.value === mentorVisibility
                            ? "admin-radio--active"
                            : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                      >
                        <input
                          type="radio"
                          name="mentor-visibility"
                          value={option.value}
                          checked={option.value === mentorVisibility}
                          onChange={(event) =>
                            onSettingChange(
                              "default_mentor_visibility",
                              event.target.value
                            )
                          }
                          disabled={!isReady || isSaving}
                        />
                        <span>
                          <span className="admin-radio__label">
                            {option.label}
                          </span>
                          {option.description ? (
                            <span className="admin-radio__hint">
                              {option.description}
                            </span>
                          ) : null}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <details className="admin-advanced">
              <summary className="admin-advanced__summary">
                <div className="stack-sm">
                  <span className="admin-advanced__title">
                    {messages.advanced.title}
                  </span>
                  <span className="text-muted">
                    {messages.advanced.description}
                  </span>
                </div>
                <span className="admin-advanced__chip">
                  {messages.advanced.chip}
                </span>
              </summary>
              <div className="admin-advanced__card">
                <div className="stack-sm">
                  <h3 className="card__title">{messages.advanced.jsonTitle}</h3>
                  <p className="card__description">
                    {messages.advanced.jsonDescription}
                  </p>
                </div>
                <div className="stack">
                  <div className="field">
                    <label className="field__label" htmlFor="org-settings-json">
                      {messages.advanced.jsonLabel}
                    </label>
                    <textarea
                      id="org-settings-json"
                      className={[
                        "textarea",
                        "admin-org-settings__editor",
                        jsonError ? "input--error" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      value={jsonDraft}
                      onChange={onJsonChange}
                      onFocus={onJsonFocus}
                      onBlur={onJsonBlur}
                      rows={16}
                      spellCheck={false}
                      autoCapitalize="off"
                      autoCorrect="off"
                      aria-describedby={describedBy}
                      aria-invalid={Boolean(jsonError) || undefined}
                      disabled={!isReady || isSaving}
                    />
                    <p id={hintId} className="field__hint">
                      {messages.advanced.jsonHint}
                    </p>
                    {jsonError ? (
                      <p id={errorId} className="field__error" role="alert">
                        {jsonError}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
            </details>
          </CardContent>
          <CardFooter className="admin-org-settings__footer">
            <span className="text-muted">{statusNote}</span>
            <div className="cluster">
              <Button
                type="button"
                variant="secondary"
                onClick={onReset}
                disabled={!isReady || isSaving || !isDirty}
              >
                {messages.actions.reset}
              </Button>
              <Button
                type="button"
                onClick={onSave}
                disabled={
                  !isReady ||
                  isSaving ||
                  !isDirty ||
                  Boolean(jsonError) ||
                  Boolean(orgNameError)
                }
              >
                {isSaving ? messages.actions.saving : messages.actions.save}
              </Button>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
