import { Check, Lock, Zap } from "lucide-react";
import type { AppMessages } from "@/lib/i18n/messages";

type LiveContextMessages = AppMessages["liveContext"];
type ViewMode = "draft" | "insight" | "diagnosis";

type ContextStageNavProps<Stage extends string> = {
  stages: readonly { key: Stage }[];
  activeStage: Stage;
  progressIndex: number;
  onSelect: (stage: Stage) => void;
  messages: LiveContextMessages;
  resolveStageLabel: (stage: string | null | undefined) => string;
};

export function ContextStageNav<Stage extends string>({
  stages,
  activeStage,
  progressIndex,
  onSelect,
  messages,
  resolveStageLabel,
}: ContextStageNavProps<Stage>) {
  return (
    <div className="context-tabs context-tabs--stages">
      {stages.map((stage, index) => {
        const isCompleted = index < progressIndex;
        const isLocked = index > progressIndex;
        const isSelected = activeStage === stage.key;
        const disabled = isLocked;
        const statusLabel = isCompleted
          ? messages.tabs.completed
          : isLocked
            ? messages.tabs.locked
            : messages.tabs.active;
        const statusIcon = isCompleted ? (
          <Check className="context-tab__status-icon" />
        ) : isLocked ? (
          <Lock className="context-tab__status-icon context-tab__status-icon--compact" />
        ) : (
          <Zap className="context-tab__status-icon context-tab__status-icon--compact" />
        );
        const statusClass = isCompleted
          ? "context-tab__meta--done"
          : isLocked
            ? "context-tab__meta--locked"
            : "context-tab__meta--active";
        const stageClass = `context-tab--${stage.key}`;

        return (
          <button
            key={stage.key}
            type="button"
            onClick={() => (disabled ? undefined : onSelect(stage.key))}
            className={[
              "context-tab",
              stageClass,
              isSelected ? "context-tab--active" : "",
              disabled ? "context-tab--disabled" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            disabled={disabled}
            aria-current={isSelected ? "step" : undefined}
          >
            <span className="context-tab__label">
              {resolveStageLabel(stage.key)}
            </span>
            <span className={`context-tab__meta ${statusClass}`}>
              {statusIcon}
              <span className="context-tab__status-label">{statusLabel}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

type ContextViewToggleProps = {
  viewMode: ViewMode;
  insightEnabled: boolean;
  showInsightNotification: boolean;
  onChange: (mode: ViewMode) => void;
  messages: LiveContextMessages;
};

export function ContextViewToggle({
  viewMode,
  insightEnabled,
  showInsightNotification,
  onChange,
  messages,
}: ContextViewToggleProps) {
  const insightStatus = !insightEnabled
    ? messages.tabs.locked
    : viewMode === "insight"
      ? messages.tabs.active
      : messages.tabs.ready;
  const insightStatusClass = !insightEnabled
    ? "context-tab__meta--locked"
    : viewMode === "insight"
      ? "context-tab__meta--active"
      : "context-tab__meta--ready";

  return (
    <div
      role="tablist"
      aria-label={messages.tabs.viewAriaLabel}
      className="context-tabs-block"
    >
      <p className="context-tabs__title">{messages.tabs.viewTitle}</p>
      <div className="context-tabs context-tabs--views">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "draft"}
          className={[
            "context-tab",
            viewMode === "draft" ? "context-tab--active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onChange("draft")}
        >
          <span className="context-tab__label">{messages.tabs.liveContext}</span>
          <span className="context-tab__meta context-tab__meta--active">
            {viewMode === "draft" ? messages.tabs.active : messages.tabs.ready}
          </span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "insight"}
          className={[
            "context-tab",
            viewMode === "insight" ? "context-tab--active" : "",
            insightEnabled ? "" : "context-tab--disabled",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => (insightEnabled ? onChange("insight") : undefined)}
          disabled={!insightEnabled}
        >
          <span className="context-tab__label">
            {messages.tabs.stageOverview}
          </span>
          <span className={`context-tab__meta ${insightStatusClass}`}>
            {showInsightNotification ? (
              <span className="context-tab__indicator" aria-hidden="true" />
            ) : null}
            {insightStatus}
          </span>
        </button>
      </div>
    </div>
  );
}
