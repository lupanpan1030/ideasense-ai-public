import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { renderMarkdown } from "@/features/assessments/components/stage-gate-utils";
import type { ProjectVerificationSnapshot } from "@/features/assessments/api";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import type { AppMessages } from "@/lib/i18n/messages";
import type { ReportSnapshot } from "./reports-normalize";
import { formatDateTime } from "./report-viewer-helpers";

type ReportSnapshotCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function ReportSnapshotCard({ report, className = "" }: ReportSnapshotCardProps) {
  const locale = useAppLocale();
  const messages = useAppMessages().reportViewer;
  return (
    <Card className={className}>
      <CardHeader className="workspace-panel__header">
        <div className="stack-sm">
          <CardTitle>{messages.snapshot.title}</CardTitle>
          <CardDescription>
            {messages.snapshot.generatedPrefix}{" "}
            {formatDateTime(report.generatedAt, {
              locale,
              fallback: messages.shell.states.unknownTime,
            })}
          </CardDescription>
        </div>
        <Badge variant="info">{report.project.currentStage}</Badge>
      </CardHeader>
      <CardContent className="stack-sm">
        <div className="stack-sm">
          <span className="eyebrow">{messages.snapshot.projectLabel}</span>
          <p>{report.project.title}</p>
          <p className="text-muted">
            {report.project.description ?? messages.snapshot.noDescriptionYet}
          </p>
        </div>
        <div className="cluster-tight text-muted">
          <span>
            {messages.snapshot.updatedPrefix}{" "}
            {formatDateTime(report.project.updatedAt, {
              locale,
              fallback: messages.shell.states.unknownTime,
            })}
          </span>
          <span>-</span>
          <span>
            {messages.snapshot.idPrefix} {report.projectId}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

type DataQualityCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function DataQualityCard({ report, className = "" }: DataQualityCardProps) {
  const messages = useAppMessages().reportViewer;
  const dataQuality = report.dataQuality;
  const missingCount = dataQuality?.missingCount ?? 0;
  const skippedCount = dataQuality?.skippedCount;
  const missingQuestions = dataQuality?.missingQuestions ?? [];
  const missingPaths = dataQuality?.missingPaths ?? [];
  const confidence = report.dvfConfidence;
  const confidenceLevel = confidence?.level
    ? `${confidence.level.charAt(0).toUpperCase()}${confidence.level.slice(1)}`
    : null;
  const confidenceCoverage =
    typeof confidence?.coverage === "number"
      ? Math.round(confidence.coverage)
      : null;

  const renderMissingList = () => {
    if (!missingCount) {
      return <p className="text-muted">{messages.dataQuality.noMissingRequiredInputs}</p>;
    }
    if (missingQuestions.length) {
      return (
        <ul>
          {missingQuestions.map((item) => (
            <li key={item.questionId}>
              {item.title ?? `${messages.dataQuality.questionPrefix} ${item.questionId}`}
            </li>
          ))}
        </ul>
      );
    }
    if (missingPaths.length) {
      return (
        <ul>
          {missingPaths.map((path) => (
            <li key={path}>{path}</li>
          ))}
        </ul>
      );
    }
    return <p className="text-muted">{messages.dataQuality.missingDetailsUnavailable}</p>;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.dataQuality.title}</CardTitle>
        <CardDescription>{messages.dataQuality.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        <div className="cluster-tight text-muted">
          <span>
            {messages.dataQuality.missingRequiredInputs}: {missingCount}
          </span>
          <span>-</span>
          <span>
            {messages.dataQuality.skippedQuestions}:{" "}
            {typeof skippedCount === "number" ? skippedCount : messages.dataQuality.unknown}
          </span>
        </div>
        {confidenceLevel ? (
          <p className="text-muted">
            {messages.dataQuality.confidence}: {confidenceLevel}
            {confidenceCoverage !== null
              ? ` (${confidenceCoverage}% ${messages.dataQuality.inputsCoveredSuffix})`
              : ""}
          </p>
        ) : null}
        <div className="stack-sm">
          <span className="eyebrow">{messages.dataQuality.missingItems}</span>
          {renderMissingList()}
        </div>
      </CardContent>
    </Card>
  );
}

type LeanCanvasCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function LeanCanvasCard({ report, className = "" }: LeanCanvasCardProps) {
  const messages = useAppMessages().reportViewer;
  const canvasBlocks = [
    {
      key: "problem",
      label: messages.leanCanvas.blocks.problem,
      areaClass: "lean-canvas__cell--problem",
    },
    {
      key: "solution",
      label: messages.leanCanvas.blocks.solution,
      areaClass: "lean-canvas__cell--solution",
    },
    {
      key: "uniqueValueProposition",
      label: messages.leanCanvas.blocks.uniqueValueProposition,
      areaClass: "lean-canvas__cell--uvp",
    },
    {
      key: "unfairAdvantage",
      label: messages.leanCanvas.blocks.unfairAdvantage,
      areaClass: "lean-canvas__cell--unfair",
    },
    {
      key: "customerSegments",
      label: messages.leanCanvas.blocks.customerSegments,
      areaClass: "lean-canvas__cell--segments",
    },
    {
      key: "keyMetrics",
      label: messages.leanCanvas.blocks.keyMetrics,
      areaClass: "lean-canvas__cell--metrics",
    },
    {
      key: "channels",
      label: messages.leanCanvas.blocks.channels,
      areaClass: "lean-canvas__cell--channels",
    },
    {
      key: "costStructure",
      label: messages.leanCanvas.blocks.costStructure,
      areaClass: "lean-canvas__cell--cost",
    },
    {
      key: "revenueStreams",
      label: messages.leanCanvas.blocks.revenueStreams,
      areaClass: "lean-canvas__cell--revenue",
    },
  ] as const;

  const formatCanvasValue = (value: string | null | undefined) => {
    const trimmed = value?.trim();
    return trimmed ? trimmed : "-";
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.leanCanvas.title}</CardTitle>
        <CardDescription>{messages.leanCanvas.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="lean-canvas">
          {canvasBlocks.map((block) => {
            const value = formatCanvasValue(report.leanCanvas[block.key]);
            return (
              <div
                key={block.key}
                className={["lean-canvas__cell", block.areaClass].join(" ")}
              >
                <div className="lean-canvas__label">{block.label}</div>
                <div
                  className="lean-canvas__body"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(value) }}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

type MarketEvidenceCardProps = {
  report: ReportSnapshot;
  className?: string;
};

const splitEvidenceLines = (value: string | null | undefined) =>
  (value ?? "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);

type ReportViewerMessages = AppMessages["reportViewer"];

export function MarketEvidenceCard({
  report,
  className = "",
}: MarketEvidenceCardProps) {
  const messages = useAppMessages().reportViewer;
  const signals = splitEvidenceLines(report.marketEvidence.signals);
  const channelTests = splitEvidenceLines(report.marketEvidence.channelTests);
  const success = splitEvidenceLines(report.marketEvidence.channelTestSuccess);
  const hasAny = signals.length || channelTests.length || success.length;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.marketEvidence.title}</CardTitle>
        <CardDescription>{messages.marketEvidence.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        {hasAny ? (
          <div className="stack-md">
            <div className="stack-sm">
              <span className="eyebrow">{messages.marketEvidence.signals}</span>
              {signals.length ? (
                <ul>
                  {signals.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">{messages.marketEvidence.noSignals}</p>
              )}
            </div>
            <div className="stack-sm">
              <span className="eyebrow">{messages.marketEvidence.channelTests}</span>
              {channelTests.length ? (
                <ul>
                  {channelTests.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">{messages.marketEvidence.noChannelTests}</p>
              )}
            </div>
            <div className="stack-sm">
              <span className="eyebrow">{messages.marketEvidence.successCriteria}</span>
              {success.length ? (
                <ul>
                  {success.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">{messages.marketEvidence.noSuccessCriteria}</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-muted">{messages.marketEvidence.empty}</p>
        )}
      </CardContent>
    </Card>
  );
}

type VerificationSummaryCardProps = {
  verification: ProjectVerificationSnapshot | null;
  className?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
};

const resolveVerificationBadge = (
  status: string,
  messages: ReportViewerMessages
) => {
  switch (status) {
    case "supported":
      return { label: messages.verificationStatuses.supported, variant: "success" as const };
    case "verified":
      return { label: messages.verificationStatuses.verified, variant: "success" as const };
    case "contradicted":
      return {
        label: messages.verificationStatuses.contradicted,
        variant: "danger" as const,
      };
    case "uncertain":
      return {
        label: messages.verificationStatuses.uncertain,
        variant: "warning" as const,
      };
    case "verifying":
      return { label: messages.verificationStatuses.verifying, variant: "info" as const };
    case "not_applicable":
      return {
        label: messages.verificationStatuses.not_applicable,
        variant: "secondary" as const,
      };
    case "failed":
      return { label: messages.verificationStatuses.failed, variant: "danger" as const };
    case "stale":
      return { label: messages.verificationStatuses.stale, variant: "warning" as const };
    case "provider_unavailable":
      return {
        label: messages.verificationStatuses.provider_unavailable,
        variant: "secondary" as const,
      };
    case "no_evidence":
    case "not_checked":
    default:
      return { label: messages.verificationStatuses.not_checked, variant: "secondary" as const };
  }
};

export function VerificationSummaryCard({
  verification,
  className = "",
  isLoading = false,
  errorMessage = null,
}: VerificationSummaryCardProps) {
  const messages = useAppMessages().reportViewer;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.verification.title}</CardTitle>
        <CardDescription>{messages.verification.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-md">
        {errorMessage ? (
          <p className="text-muted">{errorMessage}</p>
        ) : isLoading ? (
          <div className="context-panel__skeleton">
            <span className="skeleton skeleton--line" />
            <span className="skeleton skeleton--line" />
          </div>
        ) : !verification || !verification.stages.length ? (
          <p className="text-muted">{messages.verification.empty}</p>
        ) : (
          <div className="stack-md">
            {verification.stages.map((stage) => {
              const label = messages.stageLabels[stage.stage] ?? stage.stage;
              const needsAttention =
                stage.contradicted +
                stage.uncertain +
                stage.failed +
                stage.stale +
                stage.providerUnavailable;
              const summary = `${messages.verification.summaryVerified} ${stage.supported}/${stage.total} · ${messages.verification.summaryNeedsAttention} ${needsAttention} · ${messages.verification.summaryNotApplicable} ${stage.notApplicable}`;
              return (
                <details key={stage.stage} className="verification-stage">
                  <summary className="verification-stage__summary">
                    <span className="eyebrow">{label}</span>
                    <span className="text-muted">{summary}</span>
                  </summary>
                  <div className="verification-list">
                    {stage.questions.length ? (
                      stage.questions.map((question) => {
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
                              <Badge variant={badge.variant}>
                                {badge.label}
                              </Badge>
                            </div>
                            {question.sources.length ? (
                              <div className="verification-sources">
                                {question.sources.map((source) => {
                                  const label =
                                    source.domain ?? source.url ?? messages.verification.sourceFallback;
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
                                {messages.verification.empty}
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="verification-item__empty">
                        {messages.verification.empty}
                      </div>
                    )}
                  </div>
                </details>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
