import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatScore,
  formatUpdatedAt,
  renderMarkdown,
} from "@/features/assessments/components/stage-gate-utils";
import { useStageGateModalState } from "@/features/assessments/components/use-stage-gate-modal";
import type {
  ProjectVerificationSnapshot,
  StageSummarySnapshot,
} from "@/features/assessments/api";
import type { StageGateSnapshot } from "./use-stage-gate-state";
import {
  type LiveContextMessages,
  type StageKey,
  ListeningIndicator,
  normalizeStageKey,
  resolveStageLabel,
  resolveVerificationBadge,
} from "./live-context-formatters";

type StageInsightViewProps = {
  projectId: string;
  activeStage: StageKey;
  stageSummaries: StageSummarySnapshot[];
  stageGateState: StageGateSnapshot | null;
  stageVerification: ProjectVerificationSnapshot | null;
  stageVerificationError: string | null;
  isVerificationLoading: boolean;
  refreshStageVerificationData: () => Promise<void>;
  requestStageVerificationRefresh: (stage?: string) => Promise<void>;
  showPendingOverrideHint: boolean;
  onReviewPending: () => void;
  onConfirmed: () => Promise<void>;
  onRequestRefresh: () => Promise<void>;
  messages: LiveContextMessages;
};

export function StageInsightView({
  projectId,
  activeStage,
  stageSummaries,
  stageGateState,
  stageVerification,
  stageVerificationError,
  isVerificationLoading,
  refreshStageVerificationData,
  requestStageVerificationRefresh,
  showPendingOverrideHint,
  onReviewPending,
  onConfirmed,
  onRequestRefresh,
  messages,
}: StageInsightViewProps) {
  const stageSummaryMap = useMemo(
    () =>
      new Map(
        stageSummaries.map((entry) => [entry.stage.trim().toLowerCase(), entry])
      ),
    [stageSummaries]
  );

  const gateStageKey = normalizeStageKey(stageGateState?.stage);
  const isReportGate = stageGateState?.stage?.toLowerCase() === "report";
  const isGateActive = Boolean(
    stageGateState && (isReportGate || gateStageKey === activeStage)
  );
  const isFinalReport = Boolean(stageGateState && isReportGate);
  const stageLabel = resolveStageLabel(activeStage, messages);

  const {
    confirmError,
    headerTitle,
    isSubmitting,
    nextStageLabel,
    resolvedContextVersion,
    scoreSummary,
    totalScore,
    updatedLabel,
    stageLabel: gateStageLabel,
  } = useStageGateModalState({
    projectId,
    stage: stageGateState?.stage ?? activeStage,
    nextStage: stageGateState?.nextStage ?? null,
    isFinalReport,
    contextVersion: stageGateState?.contextVersion ?? null,
    contextUpdatedAt: stageGateState?.contextUpdatedAt ?? null,
    onClose: () => {},
    onConfirmed,
    onRequestRefresh,
    onReviewPending,
    autoCloseOnConfirm: false,
    lockBodyScroll: false,
  });

  const stagesToRender = [activeStage];

  const renderSummary = (stageKey: string) => {
    const summary = stageSummaryMap.get(stageKey) ?? null;
    const markdown =
      (summary?.finalSummaryMarkdown || summary?.draftSummaryMarkdown || "").trim();
    const statusLabel = summary
      ? summary.confirmed
        ? messages.labels.final
        : messages.labels.draft
      : messages.labels.pending;
    const summaryUpdated = summary?.updatedAt
      ? formatUpdatedAt(summary.updatedAt)
      : null;
    const summaryMeta = [statusLabel, summaryUpdated].filter(Boolean).join(" · ");
    const hasUserEdits = Boolean(summary?.userEditedPaths?.length);
    const verificationSummary =
      stageVerification?.stages.find((item) => item.stage === stageKey) ?? null;
    const verificationQuestions = verificationSummary?.questions ?? [];
    const verificationAttentionCount = verificationSummary
      ? verificationSummary.contradicted +
        verificationSummary.uncertain +
        verificationSummary.failed +
        verificationSummary.stale +
        verificationSummary.providerUnavailable
      : 0;
    const verificationMeta = verificationSummary
      ? `${messages.verificationStatuses.supported} ${verificationSummary.supported}/${verificationSummary.total} · ${messages.labels.verificationNeedsAttention} ${verificationAttentionCount}`
      : messages.labels.verificationPending;

    return (
      <section key={stageKey} className="context-panel__section">
        <div className="context-panel__section-header">
          <div className="cluster-tight">
            <p className="sidebar-label">
              {resolveStageLabel(stageKey, messages)}
            </p>
            {hasUserEdits ? <Badge variant="info">{messages.labels.userEdit}</Badge> : null}
          </div>
          <span className="context-panel__meta">{summaryMeta}</span>
        </div>
        {markdown ? (
          <div
            className="markdown-preview context-panel__report"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(markdown) }}
          />
        ) : isSubmitting && isGateActive ? (
          <div className="context-panel__skeleton">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-3/5" />
          </div>
        ) : (
          <ListeningIndicator label={messages.listening} />
        )}

        <div className="context-panel__verification">
          <div className="context-panel__section-header">
            <p className="sidebar-label">{messages.sectionLabels.verification}</p>
            <div className="cluster-tight">
              <span className="context-panel__meta">{verificationMeta}</span>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  void requestStageVerificationRefresh(stageKey);
                  void refreshStageVerificationData();
                }}
                disabled={isVerificationLoading}
              >
                {messages.insight.recheck}
              </Button>
            </div>
          </div>
          {stageVerificationError ? (
            <div className="context-panel__notice">
              {messages.insight.verificationUnavailablePrefix} {stageVerificationError}
            </div>
          ) : isVerificationLoading && !verificationSummary ? (
            <div className="context-panel__skeleton">
              <Skeleton className="h-3 w-4/5" />
              <Skeleton className="h-3 w-3/5" />
            </div>
          ) : verificationQuestions.length ? (
            <div className="verification-list">
              {verificationQuestions.map((question) => {
                const badge = resolveVerificationBadge(question.status, messages);
                return (
                  <div
                    key={question.questionId}
                    className="verification-item"
                  >
                    <div className="verification-item__header">
                      <div className="verification-item__title">
                        {question.questionTitle ?? question.questionId}
                      </div>
                      <Badge variant={badge.variant}>{badge.label}</Badge>
                    </div>
                    {question.sources.length ? (
                      <div className="verification-sources">
                        {question.sources.map((source) => {
                          const label =
                            source.domain ?? source.url ?? messages.labels.sourceFallback;
                          return (
                            <div
                              key={`${source.url ?? label}`}
                              className="verification-source"
                            >
                              <div className="verification-source__meta">
                                {label}
                              </div>
                              {source.title ? (
                                <div className="verification-source__title">
                                  {source.url ? (
                                    <a
                                      href={source.url}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {source.title}
                                    </a>
                                  ) : (
                                    source.title
                                  )}
                                </div>
                              ) : null}
                              {source.snippet ? (
                                <div className="verification-source__snippet">
                                  {source.snippet}
                                </div>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="verification-item__empty">
                        {messages.insight.verificationEmpty}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="verification-item__empty">
              {messages.insight.verificationEmpty}
            </div>
          )}
        </div>
      </section>
    );
  };

  const showScore = Boolean(scoreSummary || totalScore !== null);

  const headerTitleText = isGateActive
    ? headerTitle
    : isFinalReport
      ? messages.insight.finalReportTitle
      : `${stageLabel} ${messages.insight.stageOverviewSuffix}`;
  const headerDescriptionText = isGateActive
    ? isFinalReport
      ? messages.insight.reportReadyDescription
      : messages.insight.summaryReadyDescription
    : isFinalReport
      ? messages.insight.finalReportDescription
      : messages.insight.stageOverviewDescription;

  return (
    <div className="context-panel__section">
      <div className="context-panel__section-header">
        <p className="sidebar-label">{headerTitleText}</p>
      </div>
      <p className="context-panel__meta">{headerDescriptionText}</p>

      {showPendingOverrideHint && isGateActive ? (
        <div className="context-panel__notice">
          <p className="sidebar-label context-panel__accent">
            {messages.insight.pendingSuggestionsTitle}
          </p>
          <p className="context-panel__meta">
            {messages.insight.pendingSuggestionsDescription}
          </p>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={onReviewPending}
            className="mt-3"
          >
            {messages.insight.pendingSuggestionsButton}
          </Button>
        </div>
      ) : null}

      {confirmError ? (
        <div className="context-panel__notice">
          {messages.insight.confirmationFailedPrefix} {confirmError}
        </div>
      ) : null}

      <div className="context-panel__sections">
        {stagesToRender.map((stageKey) => renderSummary(stageKey))}
      </div>

      {showScore ? (
        <div className="context-panel__section">
          <div className="context-panel__section-header">
            <p className="sidebar-label">{messages.sectionLabels.scorecard}</p>
          </div>
          <div className="context-table context-table--compact">
            <div className="context-table__row">
              <span className="context-table__cell">{messages.labels.total}</span>
              <span className="context-table__status">
                {formatScore(totalScore)}
              </span>
            </div>
            <div className="context-table__row">
              <span className="context-table__cell">{messages.labels.desirability}</span>
              <span className="context-table__status">
                {formatScore(scoreSummary?.desirability ?? null)}
              </span>
            </div>
            <div className="context-table__row">
              <span className="context-table__cell">{messages.labels.viability}</span>
              <span className="context-table__status">
                {formatScore(scoreSummary?.viability ?? null)}
              </span>
            </div>
            <div className="context-table__row">
              <span className="context-table__cell">{messages.labels.feasibility}</span>
              <span className="context-table__status">
                {formatScore(scoreSummary?.feasibility ?? null)}
              </span>
            </div>
          </div>
        </div>
      ) : null}

      {isGateActive ? (
        <div className="context-panel__footer">
          <div className="context-panel__meta">
            {resolvedContextVersion !== null
              ? `v${resolvedContextVersion}`
              : messages.insight.footerContextUnknown}{" "}
            {updatedLabel}
            {gateStageLabel && stageGateState?.nextStage
              ? ` · ${gateStageLabel} -> ${nextStageLabel}`
              : gateStageLabel
                ? ` · ${gateStageLabel}`
                : ""}
          </div>
        </div>
      ) : null}
    </div>
  );
}
