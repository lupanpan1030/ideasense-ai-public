"use client";

import { createPortal } from "react-dom";
import { useId } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useModalFocusTrap } from "@/components/ui/modal-focus";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useUserSession } from "@/features/auth/user-session";
import {
  ContextCardSummary,
  ValidationPlanList,
} from "@/features/diagnosis/diagnosis-panels";
import { hasContextCardContent } from "@/features/diagnosis/diagnosis-types";
import { type StageConfirmResult, type StageSummarySnapshot } from "../api";
import { StageGateScoreCard } from "./stage-gate-score-card";
import { StageSummaryList } from "./stage-summary-list";
import { renderMarkdown } from "./stage-gate-utils";
import { useStageGateModalState } from "./use-stage-gate-modal";
import { useAppMessages } from "@/lib/i18n/provider";

type StageGateModalProps = {
  onClose: () => void;
  projectId: string;
  stage: string;
  nextStage?: string | null;
  contextVersion: number | null;
  contextUpdatedAt?: string | null;
  stageSummaries?: StageSummarySnapshot[];
  onConfirmed?: (result: StageConfirmResult) => Promise<void> | void;
  onRequestRefresh?: () => Promise<void> | void;
  showPendingOverrideHint?: boolean;
  onReviewPending?: () => void;
};

export function StageGateModal({
  onClose,
  projectId,
  stage,
  nextStage,
  contextVersion: initialContextVersion,
  contextUpdatedAt: initialContextUpdatedAt,
  stageSummaries = [],
  onConfirmed,
  onRequestRefresh,
  showPendingOverrideHint = false,
  onReviewPending,
}: StageGateModalProps) {
  const appMessages = useAppMessages();
  const messages = appMessages.stageGate;
  const diagnosisMessages = appMessages.liveContext.diagnosis;
  const titleId = useId();
  const descriptionId = useId();
  const dialogId = useId();
  const handleModalKeyDown = useModalFocusTrap(dialogId);
  const isFinalReport = stage.trim().toLowerCase() === "report";
  const { session } = useUserSession();
  const emailVerified = session?.user.emailVerified;
  const requiresVerification = emailVerified === false;
  const {
    actionLabel,
    headerBadge,
    headerDescription,
    headerTitle,
    confirmError,
    confirmResult,
    draftSummary,
    hasDraftSummary,
    isSubmitting,
    isComputed,
    isSummaryPreparing,
    isSummaryFailed,
    nextStageLabel,
    primaryDisabled,
    resolvedContextVersion,
    scoreSummary,
    summaryError,
    totalScore,
    updatedLabel,
    handleClose,
    handlePrimaryAction,
    handleReviewPending,
  } = useStageGateModalState({
    projectId,
    stage,
    nextStage,
    isFinalReport,
    contextVersion: initialContextVersion,
    contextUpdatedAt: initialContextUpdatedAt,
    onClose,
    onConfirmed,
    onRequestRefresh,
    onReviewPending,
  });

  if (typeof document === "undefined") {
    return null;
  }

  const showConfirmError = Boolean(confirmError);
  const canReviewPending = Boolean(onReviewPending);
  const loadingTitle = isFinalReport
    ? messages.loading.titleReport
    : messages.loading.titleSummary;
  const loadingDescription = isFinalReport
    ? messages.loading.descriptionReport
    : messages.loading.descriptionSummary;
  const summaryPreparingTitle = messages.loading.titlePreparingSummary;
  const summaryPreparingDescription =
    messages.loading.descriptionPreparingSummary;
  const primaryLabel = requiresVerification
    ? messages.modal.verifyEmailToContinue
    : actionLabel;
  const handlePrimaryClick = () => {
    if (requiresVerification) {
      return;
    }
    handlePrimaryAction();
  };
  const stageCards = stageSummaries.filter((summary) =>
    hasContextCardContent(summary.contextCard)
  );
  const stageValidationPlans = stageSummaries.flatMap(
    (summary) => summary.validationPlan
  );
  const draftSummaryHtml = hasDraftSummary
    ? renderMarkdown(draftSummary?.draftSummaryText ?? "")
    : "";

  return createPortal(
    <div className="modal-overlay" role="presentation" onClick={handleClose}>
      <Card
        id={dialogId}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleModalKeyDown}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <div className="cluster-tight">
              <CardTitle id={titleId}>{headerTitle}</CardTitle>
              <Badge variant={headerBadge.variant}>{headerBadge.label}</Badge>
            </div>
            <CardDescription id={descriptionId}>
              {headerDescription}
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            {messages.modal.close}
          </Button>
        </CardHeader>
        <Separator />
        <CardContent className="modal-body">
          {requiresVerification ? (
            <Card variant="alert" role="alert">
              <CardHeader>
                <CardTitle>{messages.modal.emailVerificationRequiredTitle}</CardTitle>
                <CardDescription>
                  {messages.modal.emailVerificationRequiredDescription}
                </CardDescription>
              </CardHeader>
            </Card>
          ) : null}
          {showConfirmError ? (
            <Card variant="alert" role="alert">
              <CardHeader>
                <CardTitle>{messages.modal.confirmationFailedTitle}</CardTitle>
                <CardDescription>{confirmError}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted">{messages.modal.confirmationFailedRetry}</p>
              </CardContent>
            </Card>
          ) : null}

          {showPendingOverrideHint ? (
            <Card variant="soft">
              <CardHeader className="stack-sm">
                <CardTitle>{messages.modal.pendingSuggestionsTitle}</CardTitle>
                <CardDescription>
                  {messages.modal.pendingSuggestionsDescription}
                </CardDescription>
              </CardHeader>
              {canReviewPending ? (
                <CardContent>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={handleReviewPending}
                    disabled={isSubmitting}
                  >
                    {messages.modal.pendingSuggestionsButton}
                  </Button>
                </CardContent>
              ) : null}
            </Card>
          ) : null}

          <div className="stack-lg">
            {isSummaryPreparing ? (
              <Card variant="soft" className="stage-gate-progress">
                <CardHeader className="stack-sm">
                  <CardTitle>
                    {summaryPreparingTitle}
                    <span className="loading-dots" aria-hidden="true">
                      <span className="loading-dot" />
                      <span className="loading-dot" />
                      <span className="loading-dot" />
                    </span>
                  </CardTitle>
                  <CardDescription>{summaryPreparingDescription}</CardDescription>
                </CardHeader>
                <CardContent className="stage-gate-progress__lines">
                  <span className="skeleton skeleton--line" />
                  <span className="skeleton skeleton--line" />
                  <span className="skeleton skeleton--line" />
                </CardContent>
              </Card>
            ) : null}
            {isSummaryFailed ? (
              <Card variant="alert" role="alert">
                <CardHeader>
                  <CardTitle>
                    {messages.modal.summaryPreparationFailedTitle}
                  </CardTitle>
                  <CardDescription>
                    {summaryError || messages.modal.summaryPreparationFailedRetry}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted">
                    {messages.modal.summaryPreparationFailedRetry}
                  </p>
                </CardContent>
              </Card>
            ) : null}
            {isSubmitting ? (
              <Card variant="soft" className="stage-gate-progress">
                <CardHeader className="stack-sm">
                  <CardTitle>
                    {loadingTitle}
                    <span className="loading-dots" aria-hidden="true">
                      <span className="loading-dot" />
                      <span className="loading-dot" />
                      <span className="loading-dot" />
                    </span>
                  </CardTitle>
                  <CardDescription>{loadingDescription}</CardDescription>
                </CardHeader>
                <CardContent className="stage-gate-progress__lines">
                  <span className="skeleton skeleton--line" />
                  <span className="skeleton skeleton--line" />
                  <span className="skeleton skeleton--line" />
                </CardContent>
              </Card>
            ) : null}
            {isComputed && confirmResult ? (
              <StageGateScoreCard
                nextStageLabel={nextStageLabel}
                totalScore={totalScore}
                scoreSummary={scoreSummary}
              />
            ) : null}

            {isComputed && confirmResult ? (
              <Card variant="soft">
                <CardHeader className="stack-sm">
                  <CardTitle>{diagnosisMessages.title}</CardTitle>
                  <CardDescription>{diagnosisMessages.description}</CardDescription>
                </CardHeader>
                <CardContent className="stack-md">
                  <ContextCardSummary
                    card={confirmResult.contextCard}
                    messages={diagnosisMessages}
                  />
                  <div className="stack-sm">
                    <span className="eyebrow">
                      {diagnosisMessages.validationPlanTitle}
                    </span>
                    <ValidationPlanList
                      plan={confirmResult.validationPlan}
                      messages={diagnosisMessages}
                    />
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {isFinalReport ? (
              <div className="stack-md">
                <StageSummaryList
                  summaries={stageSummaries}
                  title={messages.modal.stageSummariesTitle}
                  stages={["problem", "market", "tech"]}
                />
                {stageCards.length || stageValidationPlans.length ? (
                  <Card variant="soft">
                    <CardHeader className="stack-sm">
                      <CardTitle>{diagnosisMessages.title}</CardTitle>
                      <CardDescription>
                        {diagnosisMessages.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="stack-md">
                      {stageCards.map((summary) => (
                        <div key={summary.stage} className="stack-sm">
                          <span className="eyebrow">{summary.stage}</span>
                          <ContextCardSummary
                            card={summary.contextCard}
                            messages={diagnosisMessages}
                          />
                        </div>
                      ))}
                      <div className="stack-sm">
                        <span className="eyebrow">
                          {diagnosisMessages.validationPlanTitle}
                        </span>
                        <ValidationPlanList
                          plan={stageValidationPlans}
                          messages={diagnosisMessages}
                        />
                      </div>
                    </CardContent>
                  </Card>
                ) : null}
              </div>
            ) : (
              <Card variant="soft">
                <CardHeader className="stack-sm">
                  <CardTitle>{messages.modal.autoGeneratedSummaryTitle}</CardTitle>
                  <CardDescription>
                    {messages.modal.autoGeneratedSummaryDescription}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {hasDraftSummary ? (
                    <div
                      className="stage-gate-draft-summary"
                      dangerouslySetInnerHTML={{ __html: draftSummaryHtml }}
                    />
                  ) : (
                    <p className="text-muted">
                      {messages.modal.autoGeneratedSummaryPending}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </CardContent>
        <Separator />
        <CardFooter className="modal-footer">
          <div className="cluster-tight">
            {resolvedContextVersion !== null ? (
              <Badge variant="info">Context v{resolvedContextVersion}</Badge>
            ) : (
              <Badge variant="warning">{messages.modal.contextUnknown}</Badge>
            )}
            <span className="text-muted">{updatedLabel}</span>
          </div>
          <div className="cluster">
            {!isComputed ? (
              <Button
                type="button"
                variant="ghost"
                onClick={handleClose}
                disabled={isSubmitting}
              >
                {messages.modal.cancel}
              </Button>
            ) : null}
            <Button
              type="button"
              onClick={handlePrimaryClick}
              disabled={primaryDisabled || requiresVerification}
            >
              {primaryLabel}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>,
    document.body
  );
}
