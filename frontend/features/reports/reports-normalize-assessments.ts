import {
  REPORT_STAGE_SUMMARIES,
  STAGE_ORDER,
} from "./reports-normalize-constants";
import {
  isRecord,
  toDateString,
  toNumber,
  toOptionalString,
  toTrimmedString,
} from "./reports-normalize-helpers";
import {
  normalizeContextCard,
  normalizeValidationPlan,
} from "@/features/diagnosis/diagnosis-types";
import { normalizeArtifactLocale } from "@/lib/i18n/artifact-locale";
import type {
  ReportAssessmentSnapshot,
  ReportStageSummary,
} from "./reports-normalize-types";

type AssessmentSnapshotResponse = {
  id?: unknown;
  stage?: unknown;
  summary_text?: unknown;
  draft_summary_text?: unknown;
  draft_output_locale?: unknown;
  final_output_locale?: unknown;
  score_status?: unknown;
  total_score?: unknown;
  decision_band?: unknown;
  computed_at?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  context_card?: unknown;
  validation_plan?: unknown;
};

export const normalizeAssessments = (
  value: unknown
): ReportAssessmentSnapshot[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const normalized = value
    .filter(isRecord)
    .map((item) => {
      const response = item as AssessmentSnapshotResponse;
      const id = toTrimmedString(response.id);
      const stage = toTrimmedString(response.stage);
      if (!id || !stage) {
        return null;
      }
      return {
        id,
        stage,
        summaryText: toOptionalString(response.summary_text),
        draftSummaryText: toOptionalString(response.draft_summary_text),
        draftOutputLocale: normalizeArtifactLocale(response.draft_output_locale),
        finalOutputLocale: normalizeArtifactLocale(response.final_output_locale),
        scoreStatus: toOptionalString(response.score_status),
        totalScore: toNumber(response.total_score),
        decisionBand: toOptionalString(response.decision_band),
        computedAt: toDateString(response.computed_at),
        createdAt: toDateString(response.created_at),
        updatedAt: toDateString(response.updated_at),
        contextCard: normalizeContextCard(response.context_card),
        validationPlan: normalizeValidationPlan(response.validation_plan),
      };
    })
    .filter((item): item is ReportAssessmentSnapshot => Boolean(item));

  return normalized.sort((left, right) => {
    const leftOrder = STAGE_ORDER[left.stage.toLowerCase()] ?? 99;
    const rightOrder = STAGE_ORDER[right.stage.toLowerCase()] ?? 99;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.stage.localeCompare(right.stage);
  });
};

export const buildStageSummaries = (
  assessments: ReportAssessmentSnapshot[],
  userEditedPaths: Record<string, string[]> = {}
): ReportStageSummary[] => {
  const byStage = new Map(
    assessments.map((assessment) => [
      assessment.stage.toLowerCase(),
      assessment,
    ])
  );

  return REPORT_STAGE_SUMMARIES.map((definition) => {
    const assessment = byStage.get(definition.stage) ?? null;
    const summary =
      assessment?.summaryText ??
      assessment?.draftSummaryText ??
      definition.placeholder;
    const status = assessment?.summaryText
      ? "confirmed"
      : assessment?.draftSummaryText
      ? "draft"
      : "pending";
    const editedPaths = userEditedPaths[definition.stage] ?? [];

    return {
      stage: definition.stage,
      label: definition.label,
      title: definition.title,
      summary,
      status,
      assessment,
      userEditedPaths: editedPaths,
    };
  });
};
