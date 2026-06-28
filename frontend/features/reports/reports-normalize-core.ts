import { normalizeProjectId } from "@/features/projects/project-id";
import { normalizeArtifactLocale } from "@/lib/i18n/artifact-locale";
import { LEAN_CANVAS_FIELDS } from "./reports-normalize-constants";
import {
  isRecord,
  toDateString,
  toNumber,
  toOptionalString,
  toTrimmedString,
} from "./reports-normalize-helpers";
import { normalizeAssessments } from "./reports-normalize-assessments";
import {
  normalizeReportDiagnosis,
  normalizeValidationPlan,
} from "@/features/diagnosis/diagnosis-types";
import type {
  ReportArchitectureDiagram,
  ReportDataQuality,
  ReportDecisionSnapshot,
  ReportDvfConfidence,
  ReportDvfAssessment,
  ReportDvfDimension,
  ReportEvidenceIndex,
  ReportEvidenceIndexItem,
  ReportExperimentPlanItem,
  ReportLeanCanvas,
  ReportMarketEvidence,
  ReportProjectMeta,
  ReportRiskRegisterItem,
  ReportRiskItem,
  ReportScoreRationale,
  ReportScoreRationales,
  ReportScoreboard,
  ReportSnapshot,
} from "./reports-normalize-types";

type ReportResponse = {
  project_id?: unknown;
  generated_at?: unknown;
  artifact_locale?: unknown;
  artifact_schema_version?: unknown;
  project?: unknown;
  lean_canvas?: unknown;
  market_evidence?: unknown;
  dvf_confidence?: unknown;
  dvf_scoreboard?: unknown;
  dvf_assessment?: unknown;
  key_risks?: unknown;
  architecture_diagram?: unknown;
  overall_summary?: unknown;
  overallSummary?: unknown;
  data_quality?: unknown;
  diagnosis?: unknown;
  validation_plan?: unknown;
  decision_snapshot?: unknown;
  score_rationales?: unknown;
  risk_register?: unknown;
  experiment_plan?: unknown;
  evidence_index?: unknown;
  user_edited_paths?: unknown;
  assessments?: unknown;
};

type ReportProjectMetaResponse = {
  id?: unknown;
  title?: unknown;
  description?: unknown;
  current_stage?: unknown;
  updated_at?: unknown;
};

type MarketEvidenceResponse = {
  signals?: unknown;
  channel_tests?: unknown;
  channel_test_success?: unknown;
};

type DvfScoreboardResponse = {
  desirability?: unknown;
  viability?: unknown;
  feasibility?: unknown;
  total_score?: unknown;
  decision_band?: unknown;
};

type DvfConfidenceResponse = {
  coverage?: unknown;
  level?: unknown;
  dimensions?: unknown;
};

type DvfDimensionResponse = {
  score?: unknown;
  comment?: unknown;
  subscores?: unknown;
};

type DvfAssessmentResponse = {
  desirability?: unknown;
  viability?: unknown;
  feasibility?: unknown;
  total_score?: unknown;
};

type RiskItemResponse = {
  risk?: unknown;
  severity?: unknown;
  likelihood?: unknown;
  category?: unknown;
  mitigation_suggestion?: unknown;
  mitigationSuggestion?: unknown;
};

type ArchitectureDiagramResponse = {
  type?: unknown;
  code?: unknown;
};

type DataQualityResponse = {
  missing_paths?: unknown;
  missing_questions?: unknown;
  missing_count?: unknown;
  skipped_questions?: unknown;
};

type MissingQuestionResponse = {
  question_id?: unknown;
  title?: unknown;
};

type DecisionSnapshotResponse = {
  verdict?: unknown;
  total_score?: unknown;
  totalScore?: unknown;
  confidence?: unknown;
  rationale?: unknown;
  top_findings?: unknown;
  topFindings?: unknown;
  top_gaps?: unknown;
  topGaps?: unknown;
  next_action?: unknown;
  nextAction?: unknown;
};

type ScoreRationaleResponse = {
  score?: unknown;
  confidence?: unknown;
  rationale?: unknown;
  evidence_references?: unknown;
  evidenceReferences?: unknown;
  evidence_gaps?: unknown;
  evidenceGaps?: unknown;
};

type RiskRegisterItemResponse = {
  risk?: unknown;
  severity?: unknown;
  likelihood?: unknown;
  category?: unknown;
  linked_evidence?: unknown;
  linkedEvidence?: unknown;
  early_warning_signal?: unknown;
  earlyWarningSignal?: unknown;
  mitigation_suggestion?: unknown;
  mitigationSuggestion?: unknown;
};

type ExperimentPlanItemResponse = {
  action?: unknown;
  target?: unknown;
  success_signal?: unknown;
  successSignal?: unknown;
  linked_risk?: unknown;
  linkedRisk?: unknown;
  priority?: unknown;
  time_horizon?: unknown;
  timeHorizon?: unknown;
};

type EvidenceIndexItemResponse = {
  stage?: unknown;
  layer?: unknown;
  label?: unknown;
  path?: unknown;
  value?: unknown;
};

type EvidenceIndexResponse = {
  counts?: unknown;
  items?: unknown;
};

const normalizeStringList = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => toOptionalString(item))
    .filter((item): item is string => Boolean(item));
};

const normalizeDataQuality = (value: unknown): ReportDataQuality | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as DataQualityResponse;
  const missingPaths = Array.isArray(response.missing_paths)
    ? response.missing_paths
        .map((item) => toTrimmedString(item))
        .filter((item): item is string => Boolean(item))
    : [];
  const missingQuestions = Array.isArray(response.missing_questions)
    ? response.missing_questions
        .map((item) => {
          if (!isRecord(item)) {
            return null;
          }
          const record = item as MissingQuestionResponse;
          const questionId = toTrimmedString(record.question_id) ?? "";
          if (!questionId) {
            return null;
          }
          return {
            questionId,
            title: toOptionalString(record.title),
          };
        })
        .filter((item): item is { questionId: string; title: string | null } =>
          Boolean(item)
        )
    : [];
  const skippedCount = isRecord(response.skipped_questions)
    ? toNumber(response.skipped_questions.count)
    : toNumber(response.skipped_questions);
  const missingCount =
    toNumber(response.missing_count) ?? missingPaths.length;

  return {
    missingCount,
    missingPaths,
    missingQuestions,
    skippedCount,
  };
};

const normalizeDecisionSnapshot = (
  value: unknown
): ReportDecisionSnapshot | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as DecisionSnapshotResponse;
  const snapshot = {
    verdict: toOptionalString(response.verdict),
    totalScore: toNumber(response.total_score) ?? toNumber(response.totalScore),
    confidence: toOptionalString(response.confidence),
    rationale: toOptionalString(response.rationale),
    topFindings: normalizeStringList(
      response.top_findings ?? response.topFindings
    ),
    topGaps: normalizeStringList(response.top_gaps ?? response.topGaps),
    nextAction:
      toOptionalString(response.next_action) ??
      toOptionalString(response.nextAction),
  };
  const hasContent =
    Boolean(snapshot.verdict) ||
    snapshot.totalScore !== null ||
    Boolean(snapshot.confidence) ||
    Boolean(snapshot.rationale) ||
    snapshot.topFindings.length > 0 ||
    snapshot.topGaps.length > 0 ||
    Boolean(snapshot.nextAction);
  return hasContent ? snapshot : null;
};

const normalizeScoreRationale = (
  value: unknown
): ReportScoreRationale | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as ScoreRationaleResponse;
  const rationale = {
    score: toNumber(response.score),
    confidence: toOptionalString(response.confidence),
    rationale: toOptionalString(response.rationale),
    evidenceReferences: normalizeStringList(
      response.evidence_references ?? response.evidenceReferences
    ),
    evidenceGaps: normalizeStringList(
      response.evidence_gaps ?? response.evidenceGaps
    ),
  };
  const hasContent =
    rationale.score !== null ||
    Boolean(rationale.confidence) ||
    Boolean(rationale.rationale) ||
    rationale.evidenceReferences.length > 0 ||
    rationale.evidenceGaps.length > 0;
  return hasContent ? rationale : null;
};

const normalizeScoreRationales = (
  value: unknown
): ReportScoreRationales | null => {
  if (!isRecord(value)) {
    return null;
  }
  const rationales = {
    desirability: normalizeScoreRationale(value.desirability),
    viability: normalizeScoreRationale(value.viability),
    feasibility: normalizeScoreRationale(value.feasibility),
  };
  return rationales.desirability || rationales.viability || rationales.feasibility
    ? rationales
    : null;
};

const normalizeRiskRegister = (value: unknown): ReportRiskRegisterItem[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter(isRecord)
    .map((item) => {
      const response = item as RiskRegisterItemResponse;
      const risk = toTrimmedString(response.risk);
      if (!risk) {
        return null;
      }
      return {
        risk,
        severity: toTrimmedString(response.severity) ?? "medium",
        likelihood: toTrimmedString(response.likelihood) ?? "medium",
        category: toTrimmedString(response.category) ?? "General",
        linkedEvidence:
          toOptionalString(response.linked_evidence) ??
          toOptionalString(response.linkedEvidence),
        earlyWarningSignal:
          toOptionalString(response.early_warning_signal) ??
          toOptionalString(response.earlyWarningSignal),
        mitigationSuggestion:
          toOptionalString(response.mitigation_suggestion) ??
          toOptionalString(response.mitigationSuggestion),
      };
    })
    .filter((item): item is ReportRiskRegisterItem => Boolean(item));
};

const normalizeExperimentPlan = (
  value: unknown
): ReportExperimentPlanItem[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter(isRecord)
    .map((item) => {
      const response = item as ExperimentPlanItemResponse;
      const action = toTrimmedString(response.action);
      if (!action) {
        return null;
      }
      return {
        action,
        target: toOptionalString(response.target),
        successSignal:
          toOptionalString(response.success_signal) ??
          toOptionalString(response.successSignal),
        linkedRisk:
          toOptionalString(response.linked_risk) ??
          toOptionalString(response.linkedRisk),
        priority: toTrimmedString(response.priority) ?? "medium",
        timeHorizon:
          toOptionalString(response.time_horizon) ??
          toOptionalString(response.timeHorizon),
      };
    })
    .filter((item): item is ReportExperimentPlanItem => Boolean(item));
};

const normalizeEvidenceIndexItem = (
  value: unknown
): ReportEvidenceIndexItem | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as EvidenceIndexItemResponse;
  const item = {
    stage: toOptionalString(response.stage),
    layer: toOptionalString(response.layer),
    label: toOptionalString(response.label),
    path: toOptionalString(response.path),
    value: toOptionalString(response.value),
  };
  return item.stage || item.layer || item.label || item.path || item.value
    ? item
    : null;
};

const normalizeEvidenceIndex = (value: unknown): ReportEvidenceIndex | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as EvidenceIndexResponse;
  const counts = isRecord(response.counts)
    ? Object.entries(response.counts).reduce<Record<string, number>>(
        (acc, [key, count]) => {
          const numeric = toNumber(count);
          if (numeric !== null) {
            acc[key] = numeric;
          }
          return acc;
        },
        {}
      )
    : {};
  const items = Array.isArray(response.items)
    ? response.items
        .map(normalizeEvidenceIndexItem)
        .filter((item): item is ReportEvidenceIndexItem => Boolean(item))
    : [];
  return Object.keys(counts).length || items.length ? { counts, items } : null;
};

const normalizeProjectMeta = (
  value: unknown,
  fallbackProjectId: string
): ReportProjectMeta => {
  if (!isRecord(value)) {
    return {
      id: fallbackProjectId,
      title: "Untitled project",
      description: null,
      currentStage: "unknown",
      updatedAt: null,
    };
  }

  const response = value as ReportProjectMetaResponse;
  const id = normalizeProjectId(toTrimmedString(response.id)) ?? fallbackProjectId;
  const title = toTrimmedString(response.title) ?? "Untitled project";
  const description = toOptionalString(response.description);
  const currentStage = toTrimmedString(response.current_stage) ?? "unknown";
  const updatedAt = toDateString(response.updated_at);

  return {
    id,
    title,
    description,
    currentStage,
    updatedAt,
  };
};

const normalizeLeanCanvas = (value: unknown): ReportLeanCanvas => {
  const canvas: Record<string, string | null> = {};
  const record = isRecord(value) ? value : null;

  for (const field of LEAN_CANVAS_FIELDS) {
    if (record && field.key in record) {
      canvas[field.label] = toOptionalString(record[field.key]);
    } else {
      canvas[field.label] = null;
    }
  }

  return canvas as ReportLeanCanvas;
};

const normalizeMarketEvidence = (value: unknown): ReportMarketEvidence => {
  if (!isRecord(value)) {
    return { signals: null, channelTests: null, channelTestSuccess: null };
  }
  const response = value as MarketEvidenceResponse;
  return {
    signals: toOptionalString(response.signals),
    channelTests: toOptionalString(response.channel_tests),
    channelTestSuccess: toOptionalString(response.channel_test_success),
  };
};

const normalizeScoreboard = (value: unknown): ReportScoreboard => {
  if (!isRecord(value)) {
    return {
      desirability: null,
      viability: null,
      feasibility: null,
      totalScore: null,
      decisionBand: null,
    };
  }
  const response = value as DvfScoreboardResponse;
  return {
    desirability: toNumber(response.desirability),
    viability: toNumber(response.viability),
    feasibility: toNumber(response.feasibility),
    totalScore: toNumber(response.total_score),
    decisionBand: toOptionalString(response.decision_band),
  };
};

const normalizeDvfConfidence = (value: unknown): ReportDvfConfidence | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as DvfConfidenceResponse;
  const dimensions = isRecord(response.dimensions)
    ? Object.entries(response.dimensions).reduce<Record<string, number>>(
        (acc, [key, score]) => {
          const numeric = toNumber(score);
          if (numeric !== null) {
            acc[key] = numeric;
          }
          return acc;
        },
        {}
      )
    : null;

  return {
    coverage: toNumber(response.coverage),
    level: toOptionalString(response.level),
    dimensions: dimensions && Object.keys(dimensions).length ? dimensions : null,
  };
};

const normalizeDvfDimension = (value: unknown): ReportDvfDimension | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as DvfDimensionResponse;
  const subscores = isRecord(response.subscores)
    ? Object.entries(response.subscores).reduce<Record<string, number>>(
        (acc, [key, score]) => {
          const numeric = toNumber(score);
          if (numeric !== null) {
            acc[key] = numeric;
          }
          return acc;
        },
        {}
      )
    : null;

  return {
    score: toNumber(response.score),
    comment: toOptionalString(response.comment),
    subscores: subscores && Object.keys(subscores).length ? subscores : null,
  };
};

const normalizeDvfAssessment = (value: unknown): ReportDvfAssessment | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as DvfAssessmentResponse;
  const assessment = {
    desirability: normalizeDvfDimension(response.desirability),
    viability: normalizeDvfDimension(response.viability),
    feasibility: normalizeDvfDimension(response.feasibility),
    totalScore: toNumber(response.total_score),
  };

  if (
    !assessment.desirability &&
    !assessment.viability &&
    !assessment.feasibility &&
    assessment.totalScore === null
  ) {
    return null;
  }

  return assessment;
};

const normalizeRiskItems = (value: unknown): ReportRiskItem[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((item) => {
      const response = item as RiskItemResponse;
      const risk = toTrimmedString(response.risk);
      const severity = toTrimmedString(response.severity) ?? "Unknown";
      const likelihood = toTrimmedString(response.likelihood) ?? "Unknown";
      const category = toTrimmedString(response.category) ?? "General";
      const mitigation =
        toOptionalString(response.mitigation_suggestion) ??
        toOptionalString(response.mitigationSuggestion);

      if (!risk) {
        return null;
      }

      return {
        risk,
        severity,
        likelihood,
        category,
        mitigationSuggestion: mitigation,
      };
    })
    .filter((item): item is ReportRiskItem => Boolean(item));
};

const normalizeArchitectureDiagram = (
  value: unknown
): ReportArchitectureDiagram | null => {
  if (!isRecord(value)) {
    return null;
  }
  const response = value as ArchitectureDiagramResponse;
  const code = toTrimmedString(response.code);
  if (!code) {
    return null;
  }
  const type = toTrimmedString(response.type) ?? "mermaid";
  return { type, code };
};

const normalizeStagePathMap = (
  value: unknown
): Record<string, string[]> => {
  if (!isRecord(value)) {
    return {};
  }

  return Object.entries(value).reduce<Record<string, string[]>>(
    (acc, [stage, paths]) => {
      if (typeof stage !== "string" || !Array.isArray(paths)) {
        return acc;
      }
      const cleaned = paths.filter(
        (path): path is string => typeof path === "string" && path.trim().length > 0
      );
      if (cleaned.length) {
        acc[stage.trim().toLowerCase()] = cleaned;
      }
      return acc;
    },
    {}
  );
};

export const normalizeReportResponse = (
  payload: unknown,
  fallbackProjectId: string
): ReportSnapshot | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as ReportResponse;
  const projectId =
    normalizeProjectId(toTrimmedString(response.project_id)) ??
    normalizeProjectId(fallbackProjectId);
  if (!projectId) {
    return null;
  }

  const generatedAt = toDateString(response.generated_at) ?? new Date().toISOString();
  const artifactLocale = normalizeArtifactLocale(response.artifact_locale);
  const artifactSchemaVersion = toOptionalString(response.artifact_schema_version);
  const project = normalizeProjectMeta(response.project, projectId);
  const leanCanvas = normalizeLeanCanvas(response.lean_canvas);
  const marketEvidence = normalizeMarketEvidence(response.market_evidence);
  const dvfConfidence = normalizeDvfConfidence(response.dvf_confidence);
  const dvfScoreboard = normalizeScoreboard(response.dvf_scoreboard);
  const dvfAssessment = normalizeDvfAssessment(response.dvf_assessment);
  const keyRisks = normalizeRiskItems(response.key_risks);
  const architectureDiagram = normalizeArchitectureDiagram(
    response.architecture_diagram
  );
  const assessments = normalizeAssessments(response.assessments);
  const diagnosis = normalizeReportDiagnosis(response.diagnosis);
  const validationPlan = normalizeValidationPlan(response.validation_plan);
  const overallSummary =
    toOptionalString(response.overall_summary) ??
    toOptionalString(response.overallSummary);
  const userEditedPaths = normalizeStagePathMap(response.user_edited_paths);
  const dataQuality = normalizeDataQuality(response.data_quality);
  const decisionSnapshot = normalizeDecisionSnapshot(response.decision_snapshot);
  const scoreRationales = normalizeScoreRationales(response.score_rationales);
  const riskRegister = normalizeRiskRegister(response.risk_register);
  const experimentPlan = normalizeExperimentPlan(response.experiment_plan);
  const evidenceIndex = normalizeEvidenceIndex(response.evidence_index);

  return {
    projectId,
    generatedAt,
    artifactLocale,
    artifactSchemaVersion,
    project,
    leanCanvas,
    marketEvidence,
    dvfConfidence,
    dvfScoreboard,
    dvfAssessment,
    keyRisks,
    architectureDiagram,
    overallSummary,
    diagnosis,
    validationPlan,
    dataQuality,
    decisionSnapshot,
    scoreRationales,
    riskRegister,
    experimentPlan,
    evidenceIndex,
    userEditedPaths,
    assessments,
  };
};

export const isReportEmpty = (report: ReportSnapshot | null): boolean => {
  if (!report) {
    return true;
  }

  const leanCanvasValues = Object.values(report.leanCanvas).filter(
    (value) => typeof value === "string" && value.trim()
  );
  const hasLeanCanvas = leanCanvasValues.length > 0;
  const scoreboardValues = [
    report.dvfScoreboard.desirability,
    report.dvfScoreboard.viability,
    report.dvfScoreboard.feasibility,
    report.dvfScoreboard.totalScore,
  ].some((value) => typeof value === "number");
  const hasDecisionBand = Boolean(report.dvfScoreboard.decisionBand);
  const hasDvfAssessment = Boolean(report.dvfAssessment);
  const hasRisks = report.keyRisks.length > 0;
  const hasDiagram = Boolean(report.architectureDiagram?.code);
  const hasAssessments = report.assessments.length > 0;
  const hasOverallSummary = Boolean(report.overallSummary);
  const hasDiagnosis =
    Object.keys(report.diagnosis.contextCards).length > 0 ||
    Boolean(report.diagnosis.summary);
  const hasValidationPlan =
    report.validationPlan.length > 0 ||
    report.diagnosis.nextValidationSteps.length > 0;
  const hasReportV2Artifact =
    Boolean(report.decisionSnapshot) ||
    Boolean(report.scoreRationales) ||
    report.riskRegister.length > 0 ||
    report.experimentPlan.length > 0 ||
    Boolean(report.evidenceIndex);
  const hasMarketEvidence = Boolean(
    report.marketEvidence.signals ||
      report.marketEvidence.channelTests ||
      report.marketEvidence.channelTestSuccess
  );

  return !(
    hasLeanCanvas ||
    scoreboardValues ||
    hasDecisionBand ||
    hasDvfAssessment ||
    hasRisks ||
    hasDiagram ||
    hasAssessments ||
    hasMarketEvidence ||
    hasOverallSummary ||
    hasDiagnosis ||
    hasValidationPlan ||
    hasReportV2Artifact
  );
};
