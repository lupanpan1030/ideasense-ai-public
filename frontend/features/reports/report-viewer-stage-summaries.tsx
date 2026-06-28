import { Badge } from "@/components/ui/badge";
import type { ReportStageSummary } from "./reports-normalize";
import {
  formatScore,
  formatScoreStatus,
  formatNarrativeMarkdown,
  resolveStageStatus,
} from "./report-viewer-helpers";
import { renderMarkdown } from "@/features/assessments/components/stage-gate-utils";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { getLocaleDisplayName } from "@/lib/i18n/artifact-locale";
import {
  hasAiAssistedCopy,
  normalizeLegacyAiAssistedCopy,
} from "@/lib/ai-assisted";

type ReportStageSummariesProps = {
  stageSummaries: ReportStageSummary[];
};

export function ReportStageSummaries({ stageSummaries }: ReportStageSummariesProps) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.stageSummaries;
  if (!stageSummaries.length) {
    return <p className="text-muted">{messages.empty}</p>;
  }
  return (
    <div className="report-stage-list">
      {stageSummaries.map((stage) => {
        const hasPlaceholder = stage.status === "pending" && !stage.assessment;
        const statusVariant = stage.status === "confirmed" ? "success" : "warning";
        const scoreStatus = formatScoreStatus(
          stage.assessment?.scoreStatus ?? null,
          messages.scoreStatusFallback
        );
        const totalScore = stage.assessment?.totalScore ?? null;
        const hasAiAssist = hasAiAssistedCopy(stage.summary);
        const hasUserEdits = stage.userEditedPaths.length > 0;
        const stageMeta =
          messages.stages[stage.stage as keyof typeof messages.stages] ?? null;
        const activeLocale = stage.assessment?.summaryText
          ? stage.assessment.finalOutputLocale ?? stage.assessment.draftOutputLocale
          : stage.assessment?.draftSummaryText
            ? stage.assessment.draftOutputLocale ?? stage.assessment.finalOutputLocale
            : null;
        const activeLocaleLabel = getLocaleDisplayName(appMessages, activeLocale);
        const displayLabel = stageMeta?.stepLabel ?? stage.label;
        const displayTitle = stageMeta?.title ?? stage.title;
        const rawSummary = hasPlaceholder
          ? stageMeta?.placeholder ?? stage.summary
          : stage.summary;
        const summary = hasPlaceholder
          ? rawSummary
          : normalizeLegacyAiAssistedCopy(rawSummary) || rawSummary;
        const summaryHtml = renderMarkdown(formatNarrativeMarkdown(summary));
        const showLocaleNotice =
          activeLocale && activeLocale !== locale && activeLocaleLabel;
        const localeNote =
          showLocaleNotice
            ? messages.localeNotice.mismatchDescription.replace(
                "{locale}",
                activeLocaleLabel
              )
            : null;
        return (
          <article
            key={stage.stage}
            className={[
              "report-stage-item",
              hasPlaceholder ? "report-stage-item--pending" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <header className="report-stage-header stack-sm">
              <div className="cluster-tight">
                <Badge variant="info">{displayLabel}</Badge>
                {showLocaleNotice ? (
                  <Badge variant="outline">
                    {messages.localeNotice.badgePrefix}: {activeLocaleLabel}
                  </Badge>
                ) : null}
                {hasAiAssist ? (
                  <Badge variant="info">{messages.aiAssistedBadge}</Badge>
                ) : null}
                {hasUserEdits ? (
                  <Badge variant="info">{messages.userEditBadge}</Badge>
                ) : null}
                <Badge variant={statusVariant}>
                  {messages.badges[stage.status] ?? stage.status.toUpperCase()}
                </Badge>
              </div>
              <h3 className="report-stage-title">{displayTitle}</h3>
              <p className="text-muted">
                {resolveStageStatus(stage, messages.statusDescriptions)}
              </p>
              {localeNote ? (
                <p className="text-muted">{localeNote}</p>
              ) : null}
            </header>
            <div className="report-stage-body stack-sm">
              <div
                className={[
                  "markdown-preview",
                  hasPlaceholder ? "text-muted" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                dangerouslySetInnerHTML={{ __html: summaryHtml }}
              />
              <div className="cluster-tight text-muted">
                <span>{scoreStatus}</span>
                {totalScore !== null ? (
                  <>
                    <span>-</span>
                    <span>
                      {messages.stageScorePrefix} {formatScore(totalScore)}
                    </span>
                  </>
                ) : null}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
