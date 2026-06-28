import { LEAN_CANVAS_FIELDS } from "./reports-normalize-constants";
import { buildStageSummaries } from "./reports-normalize-assessments";
import type { ReportDvfDimension, ReportSnapshot } from "./reports-normalize-types";
import type { AppMessages } from "@/lib/i18n/messages";
import { normalizeLegacyAiAssistedCopy } from "@/lib/ai-assisted";

type ReportMarkdownMessages = Pick<AppMessages, "reportViewer" | "stageSummaries">;

const formatMarkdownSection = (
  title: string,
  body: string,
  emptyLabel: string
): string => {
  const trimmedBody = body.trim();
  if (!trimmedBody) {
    return `## ${title}\n\n${emptyLabel}\n`;
  }
  return `## ${title}\n\n${trimmedBody}\n`;
};

const splitEvidenceLines = (value: string | null | undefined): string[] =>
  (value ?? "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);

export const buildReportMarkdown = (
  report: ReportSnapshot,
  messages: ReportMarkdownMessages
): string => {
  const markdownMessages = messages.reportViewer.markdown;
  const stageMessages = messages.stageSummaries.stages;
  const lines: string[] = [];
  lines.push(`# ${report.project.title}`);
  lines.push("");
  lines.push(`${markdownMessages.projectId}: ${report.projectId}`);
  lines.push(`${markdownMessages.generated}: ${report.generatedAt}`);
  lines.push(
    `${markdownMessages.stage}: ${
      messages.reportViewer.stageLabels[report.project.currentStage] ??
      report.project.currentStage
    }`
  );
  if (report.project.description) {
    lines.push(`${markdownMessages.description}: ${report.project.description}`);
  }
  lines.push("");

  const leanLines = LEAN_CANVAS_FIELDS.map((field) => {
    const value = report.leanCanvas[field.label];
    const label =
      messages.reportViewer.leanCanvas.blocks[
        field.label as keyof typeof messages.reportViewer.leanCanvas.blocks
      ];
    return `- **${label}:** ${value ? value : "-"}`;
  }).join("\n");
  lines.push(
    formatMarkdownSection(
      markdownMessages.sections.leanCanvas,
      leanLines,
      markdownMessages.noDataAvailable
    )
  );

  const evidenceSignals = splitEvidenceLines(report.marketEvidence.signals);
  const evidenceTests = splitEvidenceLines(report.marketEvidence.channelTests);
  const evidenceSuccess = splitEvidenceLines(report.marketEvidence.channelTestSuccess);
  const evidenceLines = [
    `- **${markdownMessages.fields.signals}:** ${
      evidenceSignals.length ? evidenceSignals.join("; ") : "-"
    }`,
    `- **${markdownMessages.fields.channelTests}:** ${
      evidenceTests.length ? evidenceTests.join("; ") : "-"
    }`,
    `- **${markdownMessages.fields.successCriteria}:** ${
      evidenceSuccess.length ? evidenceSuccess.join("; ") : "-"
    }`,
  ].join("\n");
  lines.push(
    formatMarkdownSection(
      markdownMessages.sections.marketEvidence,
      evidenceLines,
      markdownMessages.noDataAvailable
    )
  );

  const scoreboardLines = [
    `- **${markdownMessages.fields.desirability}:** ${
      report.dvfScoreboard.desirability ?? "-"
    }`,
    `- **${markdownMessages.fields.viability}:** ${
      report.dvfScoreboard.viability ?? "-"
    }`,
    `- **${markdownMessages.fields.feasibility}:** ${
      report.dvfScoreboard.feasibility ?? "-"
    }`,
    `- **${markdownMessages.fields.totalScore}:** ${
      report.dvfScoreboard.totalScore ?? "-"
    }`,
    `- **${markdownMessages.fields.decisionBand}:** ${
      report.dvfScoreboard.decisionBand ?? "-"
    }`,
  ].join("\n");
  lines.push(
    formatMarkdownSection(
      markdownMessages.sections.dvfScoreboard,
      scoreboardLines,
      markdownMessages.noDataAvailable
    )
  );

  if (report.dvfAssessment) {
    const dimensionLines = (label: string, detail: ReportDvfDimension | null) =>
      detail
        ? `- **${label}**: ${detail.score ?? "-"}${
            detail.comment ? ` - ${detail.comment}` : ""
          }`
        : `- **${label}**: -`;
    const dvfLines = [
      dimensionLines(
        markdownMessages.fields.desirability,
        report.dvfAssessment.desirability
      ),
      dimensionLines(
        markdownMessages.fields.viability,
        report.dvfAssessment.viability
      ),
      dimensionLines(
        markdownMessages.fields.feasibility,
        report.dvfAssessment.feasibility
      ),
      `- **${markdownMessages.fields.totalScore}:** ${
        report.dvfAssessment.totalScore ?? "-"
      }`,
    ].join("\n");
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.dvfAssessment,
        dvfLines,
        markdownMessages.noDataAvailable
      )
    );
  }

  const riskLines = report.keyRisks.length
    ? report.keyRisks
        .map((risk) => {
          const mitigation = risk.mitigationSuggestion
            ? ` ${markdownMessages.fields.mitigation}: ${risk.mitigationSuggestion}`
            : "";
          return `- **${risk.risk}** (${risk.severity}/${risk.likelihood}, ${risk.category}).${mitigation}`;
        })
        .join("\n")
    : "";
  lines.push(
    formatMarkdownSection(
      markdownMessages.sections.keyRisks,
      riskLines,
      markdownMessages.noDataAvailable
    )
  );

  const diagnosisLines = Object.entries(report.diagnosis.contextCards)
    .flatMap(([stage, card]) => {
      const stageLabel = messages.reportViewer.stageLabels[stage] ?? stage;
      const counts = [
        `${card.userConfirmedInputs.length} confirmed inputs`,
        `${card.founderAssumptions.length} assumptions`,
        `${card.aiInferences.length} AI inferences`,
        `${card.unknowns.length} unknowns`,
        `${card.evidenceGaps.length} evidence gaps`,
      ].join("; ");
      return [`- **${stageLabel}:** ${counts}`];
    })
    .join("\n");
  if (diagnosisLines) {
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.diagnosis,
        diagnosisLines,
        markdownMessages.noDataAvailable
      )
    );
  }

  const plan = report.validationPlan.length
    ? report.validationPlan
    : report.diagnosis.nextValidationSteps;
  const validationPlanLines = plan
    .map((item) => {
      const target = item.target ? ` (${item.target})` : "";
      const success = item.successSignal
        ? ` ${markdownMessages.fields.successSignal}: ${item.successSignal}`
        : "";
      return `- **${item.action}**${target}.${success}`;
    })
    .join("\n");
  if (validationPlanLines) {
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.validationPlan,
        validationPlanLines,
        markdownMessages.noDataAvailable
      )
    );
  }

  if (report.architectureDiagram) {
    const diagram = [
      "```mermaid",
      report.architectureDiagram.code,
      "```",
    ].join("\n");
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.architectureDiagram,
        diagram,
        markdownMessages.noDataAvailable
      )
    );
  }

  const stageLines = buildStageSummaries(
    report.assessments,
    report.userEditedPaths
  )
    .map((stage) => {
      const stageMeta =
        stageMessages[stage.stage as keyof typeof stageMessages] ?? null;
      const editNote = stage.userEditedPaths.length
        ? ` (${markdownMessages.fields.userEdited})`
        : "";
      const stageLabel = stageMeta?.stepLabel ?? stage.label;
      const stageTitle = stageMeta?.title ?? stage.title;
      const rawSummary =
        stage.status === "pending" && !stage.assessment
          ? stageMeta?.placeholder ?? stage.summary
          : stage.summary;
      const summary = normalizeLegacyAiAssistedCopy(rawSummary) || rawSummary;
      return `- **${stageLabel} (${stageTitle})** (${stage.status})${editNote} - ${summary}`;
    })
    .join("\n");
  lines.push(
    formatMarkdownSection(
      markdownMessages.sections.stageSummaries,
      stageLines,
      markdownMessages.noDataAvailable
    )
  );

  if (report.overallSummary) {
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.overallSummary,
        report.overallSummary,
        markdownMessages.noDataAvailable
      )
    );
  }

  const editedLines = Object.entries(report.userEditedPaths)
    .flatMap(([stage, paths]) =>
      paths.map(
        (path) =>
          `- **${messages.reportViewer.stageLabels[stage] ?? stage}**: ${path}`
      )
    )
    .join("\n");
  if (editedLines) {
    lines.push(
      formatMarkdownSection(
        markdownMessages.sections.userEditedInputs,
        editedLines,
        markdownMessages.noDataAvailable
      )
    );
  }

  return lines.join("\n").trim() + "\n";
};
