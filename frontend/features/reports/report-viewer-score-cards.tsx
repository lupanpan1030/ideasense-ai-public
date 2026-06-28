import type { CSSProperties } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ReportDvfDimension, ReportSnapshot } from "./reports-normalize";
import { formatScore, resolveDecisionVariant } from "./report-viewer-helpers";
import { useAppMessages } from "@/lib/i18n/provider";

type DvfScoreboardCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function DvfScoreboardCard({
  report,
  className = "",
}: DvfScoreboardCardProps) {
  const messages = useAppMessages().reportViewer;
  const buildMeterStyle = (value: number | null, emphasis: boolean): CSSProperties => {
    const normalized =
      typeof value === "number" ? Math.min(Math.max(value, 0), 100) : null;
    const radius = 42;
    const circumference = 2 * Math.PI * radius;
    const offset =
      normalized === null ? circumference : circumference * (1 - normalized / 100);
    return {
      "--meter-length": `${circumference}`,
      "--meter-offset": `${offset}`,
      "--meter-color": emphasis
        ? "var(--color-primary-strong)"
        : "var(--color-primary)",
    } as CSSProperties;
  };

  const buildMeterValue = (value: number | null) =>
    typeof value === "number" ? Math.min(Math.max(value, 0), 100) : null;

  const totalValue = buildMeterValue(report.dvfScoreboard.totalScore);
  const metricItems: Array<[string, number | null]> = [
    [messages.scoreboard.metricLabels.desirability, report.dvfScoreboard.desirability],
    [messages.scoreboard.metricLabels.viability, report.dvfScoreboard.viability],
    [messages.scoreboard.metricLabels.feasibility, report.dvfScoreboard.feasibility],
  ];
  const confidence = report.dvfConfidence;
  const confidenceLevel = confidence?.level
    ? `${confidence.level.charAt(0).toUpperCase()}${confidence.level.slice(1)}`
    : messages.scoreboard.unknown;
  const confidenceCoverage =
    typeof confidence?.coverage === "number"
      ? Math.round(confidence.coverage)
      : null;

  return (
    <Card className={className}>
      <CardHeader className="workspace-panel__header">
        <div className="stack-sm">
          <CardTitle>{messages.scoreboard.title}</CardTitle>
          <CardDescription>{messages.scoreboard.description}</CardDescription>
          {confidence ? (
            <span className="text-muted">
              {messages.scoreboard.confidence}: {confidenceLevel}
              {confidenceCoverage !== null
                ? ` (${confidenceCoverage}% ${messages.dataQuality.inputsCoveredSuffix})`
                : ""}
            </span>
          ) : null}
        </div>
        {report.dvfScoreboard.decisionBand ? (
          <Badge variant={resolveDecisionVariant(report.dvfScoreboard.decisionBand)}>
            {report.dvfScoreboard.decisionBand}
          </Badge>
        ) : null}
      </CardHeader>
      <CardContent className="scoreboard-grid">
        <div className="scoreboard-hero">
          <div
            className="score-meter score-meter--hero"
            style={buildMeterStyle(totalValue, true)}
          >
            <svg
              className="score-meter__ring"
              viewBox="0 0 100 100"
              role="img"
              aria-label={`${messages.scoreboard.totalScore} ${formatScore(totalValue)}`}
            >
              <circle className="score-meter__track" cx="50" cy="50" r="42" />
              <circle className="score-meter__progress" cx="50" cy="50" r="42" />
            </svg>
            <div className="score-meter__content">
              <span className="score-meter__value">
                {formatScore(totalValue)}
              </span>
              <span className="score-meter__label">{messages.scoreboard.totalScore}</span>
            </div>
          </div>
          <p className="text-muted">
            {messages.scoreboard.compositeDescription}
          </p>
        </div>
        <div className="scoreboard-mini-grid">
          {metricItems.map(([label, value]) => {
            const normalized = buildMeterValue(value);
            return (
              <div
                key={label}
                className="score-meter score-meter--compact"
                style={buildMeterStyle(normalized, false)}
              >
                <svg
                  className="score-meter__ring"
                  viewBox="0 0 100 100"
                  role="img"
                  aria-label={`${label} ${formatScore(normalized)}`}
                >
                  <circle className="score-meter__track" cx="50" cy="50" r="42" />
                  <circle className="score-meter__progress" cx="50" cy="50" r="42" />
                </svg>
                <div className="score-meter__content">
                  <span className="score-meter__value">
                    {formatScore(normalized)}
                  </span>
                  <span className="score-meter__label">{label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

type DvfAssessmentCardProps = {
  report: ReportSnapshot;
  className?: string;
};

export function DvfAssessmentCard({ report, className = "" }: DvfAssessmentCardProps) {
  const messages = useAppMessages().reportViewer;
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{messages.assessment.title}</CardTitle>
        <CardDescription>{messages.assessment.description}</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        {report.dvfAssessment ? (
          <>
            {(
              [
                [messages.assessment.metricLabels.desirability, report.dvfAssessment.desirability],
                [messages.assessment.metricLabels.viability, report.dvfAssessment.viability],
                [messages.assessment.metricLabels.feasibility, report.dvfAssessment.feasibility],
              ] as Array<[string, ReportDvfDimension | null]>
            ).map(([label, detail]) => (
              <div key={label} className="stack-sm">
                <span className="eyebrow">{label}</span>
                <p>
                  {messages.assessment.scorePrefix}: {formatScore(detail?.score ?? null)}
                  {detail?.comment ? ` - ${detail.comment}` : ""}
                </p>
              </div>
            ))}
            <div className="stack-sm">
              <span className="eyebrow">{messages.assessment.totalScore}</span>
              <p>{formatScore(report.dvfAssessment.totalScore)}</p>
            </div>
          </>
        ) : (
          <p className="text-muted">{messages.assessment.empty}</p>
        )}
      </CardContent>
    </Card>
  );
}
