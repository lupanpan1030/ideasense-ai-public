import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  QuestionBankDraft,
  QuestionBankVersion,
} from "@/features/admin/question-banks";
import type { QuestionBankMessages } from "@/features/admin/question-bank-messages";
import {
  formatQuestionBankStageValue,
  formatQuestionBankTimestamp,
} from "@/features/admin/question-bank-view-model";

export type ImportFormat = "yaml" | "json";
export type ImportMode = "replace" | "merge";
export type QuestionTabKey = "overview" | "questions" | "import" | "reorder";

type QuestionBankStatusAlertsProps = {
  actionError: string | null;
  actionNotice: string | null;
  loadError: string | null;
  messages: QuestionBankMessages;
};

export function QuestionBankStatusAlerts({
  actionError,
  actionNotice,
  loadError,
  messages,
}: QuestionBankStatusAlertsProps) {
  return (
    <>
      {loadError ? (
        <Card variant="alert" role="alert">
          <CardHeader>
            <CardTitle>{messages.bank.loadErrorTitle}</CardTitle>
            <CardDescription>{loadError}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {actionNotice ? (
        <Card variant="soft" role="status" aria-live="polite">
          <CardHeader>
            <CardTitle>{messages.alerts.success}</CardTitle>
            <CardDescription>{actionNotice}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {actionError ? (
        <Card variant="alert" role="alert">
          <CardHeader>
            <CardTitle>{messages.alerts.actionFailed}</CardTitle>
            <CardDescription>{actionError}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}
    </>
  );
}

type QuestionBankModeBannerProps = {
  activeDetail: QuestionBankDraft | null;
  activeTab: QuestionTabKey;
  isEditing: boolean;
  isWorking: boolean;
  messages: QuestionBankMessages;
  onEnterEdit: () => void;
  onExitEdit: () => void;
  onPublish: () => void;
};

export function QuestionBankModeBanner({
  activeDetail,
  activeTab,
  isEditing,
  isWorking,
  messages,
  onEnterEdit,
  onExitEdit,
  onPublish,
}: QuestionBankModeBannerProps) {
  if (activeTab === "overview") {
    return null;
  }

  return (
    <Card variant={isEditing ? "soft" : "default"} className="question-bank-banner">
      <CardContent className="question-bank-banner__content">
        <div className="stack-sm">
          <p className="eyebrow">
            {isEditing ? messages.mode.draftMode : messages.mode.readonly}
          </p>
          <p className="text-muted">
            {isEditing
              ? messages.mode.descriptionEditing
              : messages.mode.descriptionReadonly}
          </p>
        </div>
        {isEditing ? (
          <div className="cluster">
            <Button onClick={onPublish} disabled={isWorking}>
              {messages.actions.publishDraft}
            </Button>
            <Button variant="ghost" onClick={onExitEdit} disabled={isWorking}>
              {messages.actions.exitEdit}
            </Button>
          </div>
        ) : (
          <Button onClick={onEnterEdit} disabled={isWorking || !activeDetail}>
            {messages.actions.editDraft}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

type QuestionBankTabsProps = {
  activeTab: QuestionTabKey;
  isEditing: boolean;
  messages: QuestionBankMessages;
  onTabChange: (tab: QuestionTabKey) => void;
};

export function QuestionBankTabs({
  activeTab,
  isEditing,
  messages,
  onTabChange,
}: QuestionBankTabsProps) {
  const tabs: QuestionTabKey[] = ["overview", "questions", "import", "reorder"];

  return (
    <div
      className="question-bank-tabs"
      role="group"
      aria-label={messages.tabs.sections}
    >
      <div className="question-bank-tabs__items">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            aria-pressed={activeTab === tab}
            className={
              activeTab === tab
                ? "question-bank-tab question-bank-tab--active"
                : "question-bank-tab"
            }
            onClick={() => onTabChange(tab)}
          >
            {messages.tabs[tab]}
          </button>
        ))}
      </div>
      <Badge variant="secondary">
        {isEditing ? messages.mode.editing : messages.mode.readonly}
      </Badge>
    </div>
  );
}

type QuestionBankOverviewPanelProps = {
  activeDetail: QuestionBankDraft | null;
  activeVersion: QuestionBankVersion | null;
  draft: QuestionBankDraft | null;
  isEditing: boolean;
  isWorking: boolean;
  messageLocale: "en" | "zh";
  messages: QuestionBankMessages;
  onEnterEdit: () => void;
  onExitEdit: () => void;
  onPublish: () => void;
};

export function QuestionBankOverviewPanel({
  activeDetail,
  activeVersion,
  draft,
  isEditing,
  isWorking,
  messageLocale,
  messages,
  onEnterEdit,
  onExitEdit,
  onPublish,
}: QuestionBankOverviewPanelProps) {
  return (
    <div className="question-bank-panel stack-lg">
      <Card>
        <CardHeader>
          <CardTitle>{messages.overview.activeTitle}</CardTitle>
          <CardDescription>{messages.overview.activeDescription}</CardDescription>
        </CardHeader>
        <CardContent className="question-bank-meta">
          {activeVersion ? (
            <>
              <div>
                <p className="text-muted">{messages.overview.version}</p>
                <strong>{activeVersion.version}</strong>
              </div>
              <div>
                <p className="text-muted">{messages.overview.source}</p>
                <strong>{activeVersion.source ?? messages.unknown}</strong>
              </div>
              <div>
                <p className="text-muted">{messages.overview.activated}</p>
                <strong>
                  {formatQuestionBankTimestamp(
                    activeVersion.activatedAt,
                    messageLocale,
                    messages.unknown
                  )}
                </strong>
              </div>
            </>
          ) : (
            <p className="text-muted">{messages.overview.noActive}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{messages.overview.draftStatus}</CardTitle>
          <CardDescription>{messages.overview.draftDescription}</CardDescription>
        </CardHeader>
        <CardContent className="question-bank-actions">
          {isEditing && draft ? (
            <>
              <div className="stack-sm">
                <p className="text-muted">{messages.overview.editingDraft}</p>
                <strong>{draft.version.version}</strong>
              </div>
              <div className="cluster">
                <Button onClick={onPublish} disabled={isWorking}>
                  {messages.actions.publishDraft}
                </Button>
                <Button variant="ghost" onClick={onExitEdit} disabled={isWorking}>
                  {messages.actions.exitEdit}
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="stack-sm">
                <p className="text-muted">{messages.overview.viewingActive}</p>
                <strong>
                  {activeVersion
                    ? messages.mode.readonly
                    : messages.overview.unavailable}
                </strong>
              </div>
              <Button onClick={onEnterEdit} disabled={isWorking || !activeDetail}>
                {messages.actions.editDraft}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

type QuestionBankImportPanelProps = {
  draft: QuestionBankDraft | null;
  importBody: string;
  importFormat: ImportFormat;
  importMode: ImportMode;
  isEditing: boolean;
  isWorking: boolean;
  messages: QuestionBankMessages;
  onImport: () => void;
  setImportBody: (value: string) => void;
  setImportFormat: (value: ImportFormat) => void;
  setImportMode: (value: ImportMode) => void;
};

export function QuestionBankImportPanel({
  draft,
  importBody,
  importFormat,
  importMode,
  isEditing,
  isWorking,
  messages,
  onImport,
  setImportBody,
  setImportFormat,
  setImportMode,
}: QuestionBankImportPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{messages.import.title}</CardTitle>
        <CardDescription>{messages.import.description}</CardDescription>
      </CardHeader>
      <CardContent className="question-bank-import">
        {isEditing && draft ? (
          <>
            <div className="cluster">
              <label className="field">
                <span className="field__label">{messages.import.format}</span>
                <select
                  className="input"
                  value={importFormat}
                  onChange={(event) =>
                    setImportFormat(event.target.value as ImportFormat)
                  }
                >
                  <option value="yaml">YAML</option>
                  <option value="json">JSON</option>
                </select>
              </label>
              <label className="field">
                <span className="field__label">{messages.import.mode}</span>
                <select
                  className="input"
                  value={importMode}
                  onChange={(event) =>
                    setImportMode(event.target.value as ImportMode)
                  }
                >
                  <option value="replace">{messages.import.replace}</option>
                  <option value="merge">{messages.import.merge}</option>
                </select>
              </label>
            </div>
            <label className="field" htmlFor="question-bank-import-body">
              <span className="field__label">{messages.import.bodyLabel}</span>
              <textarea
                id="question-bank-import-body"
                className="textarea question-bank-textarea"
                rows={12}
                value={importBody}
                onChange={(event) => setImportBody(event.target.value)}
                placeholder={
                  importFormat === "yaml"
                    ? messages.import.yamlPlaceholder
                    : messages.import.jsonPlaceholder
                }
              />
            </label>
            <Button onClick={onImport} disabled={isWorking}>
              {messages.actions.import}
            </Button>
          </>
        ) : (
          <p className="text-muted">{messages.import.switchToEdit}</p>
        )}
      </CardContent>
    </Card>
  );
}

type QuestionBankReorderPanelProps = {
  draft: QuestionBankDraft | null;
  isEditing: boolean;
  isWorking: boolean;
  messages: QuestionBankMessages;
  onReorder: () => void;
  reorderError: string | null;
  reorderList: string;
  reorderStage: string;
  reorderStages: string[];
  reorderVariant: string;
  reorderVariants: string[];
  setReorderList: (value: string) => void;
  setReorderStage: (value: string) => void;
  setReorderVariant: (value: string) => void;
};

export function QuestionBankReorderPanel({
  draft,
  isEditing,
  isWorking,
  messages,
  onReorder,
  reorderError,
  reorderList,
  reorderStage,
  reorderStages,
  reorderVariant,
  reorderVariants,
  setReorderList,
  setReorderStage,
  setReorderVariant,
}: QuestionBankReorderPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{messages.reorder.title}</CardTitle>
        <CardDescription>{messages.reorder.description}</CardDescription>
      </CardHeader>
      <CardContent className="question-bank-reorder">
        {isEditing && draft ? (
          <>
            <div className="cluster">
              <label className="field">
                <span className="field__label">{messages.reorder.stage}</span>
                <select
                  className="input"
                  value={reorderStage}
                  onChange={(event) => setReorderStage(event.target.value)}
                >
                  {reorderStages.map((stage) => (
                    <option key={stage} value={stage}>
                      {formatQuestionBankStageValue(stage, messages.stages)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field__label">{messages.reorder.variant}</span>
                <select
                  className="input"
                  value={reorderVariant}
                  onChange={(event) => setReorderVariant(event.target.value)}
                >
                  {reorderVariants.map((variant) => (
                    <option key={variant} value={variant}>
                      {variant}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field" htmlFor="question-bank-reorder-body">
              <span className="field__label">{messages.reorder.bodyLabel}</span>
              <textarea
                id="question-bank-reorder-body"
                className="textarea question-bank-textarea"
                rows={10}
                value={reorderList}
                onChange={(event) => setReorderList(event.target.value)}
                placeholder={messages.reorder.placeholder}
                aria-describedby={
                  reorderError ? "question-bank-reorder-error" : undefined
                }
                aria-invalid={Boolean(reorderError) || undefined}
              />
            </label>
            {reorderError ? (
              <p
                id="question-bank-reorder-error"
                className="field__error"
                role="alert"
              >
                {reorderError}
              </p>
            ) : null}
            <Button onClick={onReorder} disabled={isWorking}>
              {messages.actions.updateOrder}
            </Button>
          </>
        ) : (
          <p className="text-muted">{messages.reorder.switchToEdit}</p>
        )}
      </CardContent>
    </Card>
  );
}
