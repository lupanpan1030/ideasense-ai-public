import { Badge } from "@/components/ui/badge";
import type { ProjectVerificationSnapshot } from "@/features/assessments/api";
import type { AppLocale } from "@/lib/i18n/config";
import type { AppMessages } from "@/lib/i18n/messages";
import {
  ArchitectureDiagramCard,
  DataQualityCard,
  DiagnosisCard,
  DvfAssessmentCard,
  DvfScoreboardCard,
  KeyRisksCard,
  LeanCanvasCard,
  MarketEvidenceCard,
  OverallSummaryCard,
  ReportSnapshotCard,
  ReportV2ArtifactCard,
  ValidationPlanCard,
  VerificationSummaryCard,
} from "./report-viewer-cards";
import { ReportStageSummaries } from "./report-viewer-stage-summaries";
import type { ReportSnapshot, ReportStageSummary } from "./reports-normalize";
import { formatDateTime } from "./report-viewer-helpers";

type BadgeVariant =
  | "default"
  | "outline"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info";

type ReportDocumentProps = {
  confirmedStages: number;
  currentStageLabel: string | null;
  decisionBand: string | null;
  decisionVariant: BadgeVariant;
  interpolate: (
    template: string,
    values: Record<string, string | number>
  ) => string;
  isSample: boolean;
  isVerificationLoading: boolean;
  locale: AppLocale;
  messages: AppMessages["reportViewer"];
  overallSummary: string;
  report: ReportSnapshot;
  riskCount: number;
  stageSummaries: ReportStageSummary[];
  totalScore: string;
  verificationError: string | null;
  verificationSnapshot: ProjectVerificationSnapshot | null;
};

export function ReportDocument({
  confirmedStages,
  currentStageLabel,
  decisionBand,
  decisionVariant,
  interpolate,
  isSample,
  isVerificationLoading,
  locale,
  messages,
  overallSummary,
  report,
  riskCount,
  stageSummaries,
  totalScore,
  verificationError,
  verificationSnapshot,
}: ReportDocumentProps) {
  return (
    <div className="report-doc">
      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">
              {messages.shell.sections.executiveSummaryEyebrow}
            </p>
            <h2 className="section-title">
              {messages.shell.sections.decisionOverviewTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.decisionOverviewDescription}
            </p>
          </div>
        </div>
        {overallSummary ? (
          <OverallSummaryCard report={report} className="report-panel" />
        ) : (
          <p className="text-muted">{messages.shell.states.noOverallSummary}</p>
        )}
        <div className="report-decision">
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.decisionBand}</span>
            <Badge variant={decisionVariant}>
              {decisionBand ?? messages.shell.states.notScored}
            </Badge>
          </div>
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.totalDvfScore}</span>
            <span className="report-decision__value">{totalScore}</span>
          </div>
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.risksFlagged}</span>
            <span className="report-decision__value">{riskCount}</span>
          </div>
        </div>
        <div className="report-score-stack">
          <DvfScoreboardCard report={report} className="report-panel" />
          <DvfAssessmentCard report={report} className="report-panel" />
        </div>
        <ReportV2ArtifactCard report={report} className="report-panel" />
        <div className="report-score-stack">
          <DiagnosisCard report={report} className="report-panel" />
          <ValidationPlanCard report={report} className="report-panel" />
        </div>
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">{messages.shell.sections.contextEyebrow}</p>
            <h2 className="section-title">
              {messages.shell.sections.scopeAndInputsTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.scopeAndInputsDescription}
            </p>
          </div>
        </div>
        <div className="report-meta">
          <div className="report-meta__item stack-sm">
            <span className="eyebrow">{messages.snapshot.projectLabel}</span>
            <p className="report-meta__title">{report.project.title}</p>
            <p className="text-muted">
              {report.project.description ?? messages.snapshot.noDescriptionYet}
            </p>
          </div>
          <div className="report-meta__item stack-sm">
            <span className="eyebrow">{messages.shell.labels.coverage}</span>
            <p>
              {confirmedStages} / {stageSummaries.length}{" "}
              {messages.shell.labels.confirmedSuffix}
            </p>
            <p className="text-muted">
              {messages.shell.labels.currentStage}: {currentStageLabel}
            </p>
          </div>
          <div className="report-meta__item stack-sm">
            <span className="eyebrow">{messages.shell.labels.timeline}</span>
            <p>
              {messages.shell.labels.generatedPrefix}{" "}
              {formatDateTime(report.generatedAt, {
                locale,
                fallback: messages.shell.states.unknownTime,
              })}
            </p>
            <p className="text-muted">
              {messages.shell.labels.updatedPrefix}{" "}
              {formatDateTime(report.project.updatedAt, {
                locale,
                fallback: messages.shell.states.unknownTime,
              })}
            </p>
          </div>
        </div>
        <DataQualityCard report={report} className="report-panel" />
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">{messages.shell.sections.findingsEyebrow}</p>
            <h2 className="section-title">
              {messages.shell.sections.stageEvidenceTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.stageEvidenceDescription}
            </p>
          </div>
          <Badge variant="info">
            {stageSummaries.length} {messages.shell.labels.stagesCountSuffix}
          </Badge>
        </div>
        <ReportStageSummaries stageSummaries={stageSummaries} />
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">
              {messages.shell.sections.verificationEyebrow}
            </p>
            <h2 className="section-title">
              {messages.shell.sections.evidenceChecksTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.evidenceChecksDescription}
            </p>
          </div>
        </div>
        <VerificationSummaryCard
          verification={verificationSnapshot}
          isLoading={isVerificationLoading}
          errorMessage={verificationError}
          className="report-panel"
        />
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">
              {messages.shell.sections.validationEyebrow}
            </p>
            <h2 className="section-title">
              {messages.shell.sections.marketEvidenceTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.marketEvidenceDescription}
            </p>
          </div>
        </div>
        <MarketEvidenceCard report={report} className="report-panel" />
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">
              {messages.shell.sections.businessModelEyebrow}
            </p>
            <h2 className="section-title">
              {messages.shell.sections.leanCanvasTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.leanCanvasDescription}
            </p>
          </div>
        </div>
        <LeanCanvasCard report={report} className="report-panel" />
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">{messages.shell.sections.risksEyebrow}</p>
            <h2 className="section-title">
              {messages.shell.sections.executionRealityCheckTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.executionRealityCheckDescription}
            </p>
          </div>
        </div>
        <div className="report-score-stack">
          <KeyRisksCard report={report} className="report-panel" />
          <ArchitectureDiagramCard
            report={report}
            className="report-panel"
            showSource={!isSample}
          />
        </div>
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">
              {messages.shell.sections.conclusionEyebrow}
            </p>
            <h2 className="section-title">
              {messages.shell.sections.recommendationTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.recommendationDescription}
            </p>
          </div>
        </div>
        <div className="report-decision">
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.recommendation}</span>
            <Badge variant={decisionVariant}>
              {decisionBand ?? messages.shell.states.notScored}
            </Badge>
          </div>
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.priorityRisks}</span>
            <span className="report-decision__value">{riskCount}</span>
          </div>
          <div className="report-decision__item">
            <span className="eyebrow">{messages.shell.labels.decisionScore}</span>
            <span className="report-decision__value">{totalScore}</span>
          </div>
        </div>
        <div className="report-next-steps stack-sm">
          <span className="eyebrow">{messages.shell.labels.nextSteps}</span>
          <ul>
            <li>{messages.shell.nextSteps.reviewStageSummaries}</li>
            <li>
              {riskCount > 0
                ? interpolate(messages.shell.nextSteps.prioritizeRisks, {
                    count: riskCount,
                  })
                : messages.shell.nextSteps.captureRisks}
            </li>
            <li>{messages.shell.nextSteps.confirmDecisionBand}</li>
          </ul>
        </div>
      </section>

      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <p className="eyebrow">{messages.shell.sections.appendixEyebrow}</p>
            <h2 className="section-title">
              {messages.shell.sections.reportMetadataTitle}
            </h2>
            <p className="report-lede text-muted">
              {messages.shell.sections.reportMetadataDescription}
            </p>
          </div>
        </div>
        <ReportSnapshotCard report={report} className="report-panel" />
      </section>
    </div>
  );
}
