import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AppMessages } from "@/lib/i18n/messages";
import { ContextStageNav, ContextViewToggle } from "./live-context-controls";
import type { LiveContextMessages, StageKey, ViewMode } from "./live-context-formatters";

type StageNavItem = {
  key: StageKey;
};

type LiveContextBoardHeaderProps = {
  activeStage: StageKey;
  insightEnabled: boolean;
  messages: LiveContextMessages;
  progressIndex: number;
  showInsightNotification: boolean;
  stages: readonly StageNavItem[];
  updatedLabel: string;
  viewMode: ViewMode;
  onStageSelect: (stage: StageKey) => void;
  onViewModeChange: (mode: ViewMode) => void;
  resolveStageLabel: (stage: string | null | undefined) => string;
};

export function LiveContextBoardHeader({
  activeStage,
  insightEnabled,
  messages,
  progressIndex,
  showInsightNotification,
  stages,
  updatedLabel,
  viewMode,
  onStageSelect,
  onViewModeChange,
  resolveStageLabel,
}: LiveContextBoardHeaderProps) {
  return (
    <div className="context-panel__header">
      <div className="context-panel__header-row">
        <p className="sidebar-label">{messages.sectionLabels.stageNavigator}</p>
        <span className="context-panel__meta">{updatedLabel}</span>
      </div>
      <div className="context-panel__stack">
        <ContextStageNav
          stages={stages}
          activeStage={activeStage}
          progressIndex={progressIndex}
          onSelect={onStageSelect}
          messages={messages}
          resolveStageLabel={resolveStageLabel}
        />
        <div className="context-panel__divider" aria-hidden="true" />
        <ContextViewToggle
          viewMode={viewMode}
          insightEnabled={insightEnabled}
          showInsightNotification={showInsightNotification}
          onChange={onViewModeChange}
          messages={messages}
        />
      </div>
    </div>
  );
}

type LiveContextReviewPanelProps = {
  appMessages: AppMessages;
  hasPendingSuggestions: boolean;
  hasPendingUserEdits: boolean;
  isReviewSummaryFailed: boolean;
  isReviewSummaryPreparing: boolean;
  messages: LiveContextMessages;
  requiresVerification: boolean;
  reviewContextVersion: number | null;
  reviewError: string | null;
  reviewNextLabel: string;
  reviewStageLabel: string;
  reviewSummaryError: string | null;
  onReviewPending: () => void;
};

export function LiveContextReviewPanel({
  appMessages,
  hasPendingSuggestions,
  hasPendingUserEdits,
  isReviewSummaryFailed,
  isReviewSummaryPreparing,
  messages,
  requiresVerification,
  reviewContextVersion,
  reviewError,
  reviewNextLabel,
  reviewStageLabel,
  reviewSummaryError,
  onReviewPending,
}: LiveContextReviewPanelProps) {
  return (
    <div className="context-review context-review--sticky">
      <div className="context-review__header">
        <div>
          <p className="context-review__title">
            {messages.review.reviewTitle}
          </p>
          <p className="context-review__meta">
            {reviewStageLabel}
            {" -> "}
            {reviewNextLabel}
            {reviewContextVersion != null ? ` · v${reviewContextVersion}` : ""}
          </p>
        </div>
        <span className="context-review__tag">
          {messages.review.awaitingConfirmTag}
        </span>
      </div>
      <p className="context-review__copy">{messages.review.reviewCopy}</p>
      {requiresVerification ? (
        <div className="context-review__notice">
          <Badge variant="warning">
            {messages.review.emailVerificationRequired}
          </Badge>
          <p className="context-review__meta">
            {messages.review.emailVerificationContinue}
          </p>
        </div>
      ) : null}
      {isReviewSummaryPreparing ? (
        <div className="context-review__notice">
          <Badge variant="warning">
            {appMessages.stageGate.loading.titlePreparingSummary}
          </Badge>
          <p className="context-review__meta">
            {appMessages.stageGate.loading.descriptionPreparingSummary}
          </p>
        </div>
      ) : null}
      {isReviewSummaryFailed ? (
        <div className="context-review__notice">
          <Badge variant="warning">
            {appMessages.stageGate.modal.summaryPreparationFailedTitle}
          </Badge>
          <p className="context-review__meta">
            {reviewSummaryError ||
              appMessages.stageGate.modal.summaryPreparationFailedRetry}
          </p>
        </div>
      ) : null}
      {hasPendingUserEdits ? (
        <p className="context-review__meta">
          {messages.review.editsAppliedNotice}
        </p>
      ) : null}
      {hasPendingSuggestions ? (
        <div className="context-review__notice">
          <p className="context-review__meta">
            {messages.review.pendingSuggestionsNotice}
          </p>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={onReviewPending}
          >
            {messages.review.reviewPendingSuggestionsButton}
          </Button>
        </div>
      ) : null}
      {reviewError ? (
        <div className="context-review__error">{reviewError}</div>
      ) : null}
    </div>
  );
}

type LiveContextReviewCtaProps = {
  disabled: boolean;
  label: string;
  onConfirm: () => void;
};

export function LiveContextReviewCta({
  disabled,
  label,
  onConfirm,
}: LiveContextReviewCtaProps) {
  return (
    <div className="context-review__sticky">
      <Button
        type="button"
        onClick={onConfirm}
        disabled={disabled}
        className="context-review__cta"
      >
        {label}
      </Button>
    </div>
  );
}
