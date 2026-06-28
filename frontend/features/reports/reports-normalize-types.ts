import type {
  ContextCard,
  ReportDiagnosis,
  ValidationPlanItem,
} from "@/features/diagnosis/diagnosis-types";

export type {
  ContextCard,
  ReportDiagnosis,
  ValidationPlanItem,
} from "@/features/diagnosis/diagnosis-types";

export type ReportProjectMeta = {
  id: string;
  title: string;
  description: string | null;
  currentStage: string;
  updatedAt: string | null;
};

export type ReportLeanCanvas = {
  problem: string | null;
  customerSegments: string | null;
  uniqueValueProposition: string | null;
  solution: string | null;
  channels: string | null;
  revenueStreams: string | null;
  costStructure: string | null;
  keyMetrics: string | null;
  unfairAdvantage: string | null;
};

export type ReportMarketEvidence = {
  signals: string | null;
  channelTests: string | null;
  channelTestSuccess: string | null;
};

export type ReportScoreboard = {
  desirability: number | null;
  viability: number | null;
  feasibility: number | null;
  totalScore: number | null;
  decisionBand: string | null;
};

export type ReportJobStatusValue =
  | "not_started"
  | "queued"
  | "running"
  | "finalizing"
  | "ready"
  | "failed"
  | "stale";

export type ReportJobStatus = {
  projectId: string;
  currentStage: string | null;
  stageStatus: string | null;
  jobType: string | null;
  status: ReportJobStatusValue;
  retryable: boolean;
  reportId: string | null;
  reportVersion: number | null;
  generatedAt: string | null;
  contextVersion: number | null;
  nextPollMs: number;
};

export type ReportDvfConfidence = {
  coverage: number | null;
  level: string | null;
  dimensions: Record<string, number> | null;
};

export type ReportDvfDimension = {
  score: number | null;
  comment: string | null;
  subscores: Record<string, number> | null;
};

export type ReportDvfAssessment = {
  desirability: ReportDvfDimension | null;
  viability: ReportDvfDimension | null;
  feasibility: ReportDvfDimension | null;
  totalScore: number | null;
};

export type ReportRiskItem = {
  risk: string;
  severity: string;
  likelihood: string;
  category: string;
  mitigationSuggestion: string | null;
};

export type ReportArchitectureDiagram = {
  type: string;
  code: string;
};

export type ReportDataQualityItem = {
  questionId: string;
  title: string | null;
};

export type ReportDataQuality = {
  missingCount: number;
  missingPaths: string[];
  missingQuestions: ReportDataQualityItem[];
  skippedCount: number | null;
};

export type ReportDecisionSnapshot = {
  verdict: string | null;
  totalScore: number | null;
  confidence: string | null;
  rationale: string | null;
  topFindings: string[];
  topGaps: string[];
  nextAction: string | null;
};

export type ReportScoreRationale = {
  score: number | null;
  confidence: string | null;
  rationale: string | null;
  evidenceReferences: string[];
  evidenceGaps: string[];
};

export type ReportScoreRationales = {
  desirability: ReportScoreRationale | null;
  viability: ReportScoreRationale | null;
  feasibility: ReportScoreRationale | null;
};

export type ReportRiskRegisterItem = {
  risk: string;
  severity: string;
  likelihood: string;
  category: string;
  linkedEvidence: string | null;
  earlyWarningSignal: string | null;
  mitigationSuggestion: string | null;
};

export type ReportExperimentPlanItem = {
  action: string;
  target: string | null;
  successSignal: string | null;
  linkedRisk: string | null;
  priority: string;
  timeHorizon: string | null;
};

export type ReportEvidenceIndexItem = {
  stage: string | null;
  layer: string | null;
  label: string | null;
  path: string | null;
  value: string | null;
};

export type ReportEvidenceIndex = {
  counts: Record<string, number>;
  items: ReportEvidenceIndexItem[];
};

export type ReportAssessmentSnapshot = {
  id: string;
  stage: string;
  summaryText: string | null;
  draftSummaryText: string | null;
  draftOutputLocale: "en" | "zh" | null;
  finalOutputLocale: "en" | "zh" | null;
  scoreStatus: string | null;
  totalScore: number | null;
  decisionBand: string | null;
  computedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  contextCard: ContextCard;
  validationPlan: ValidationPlanItem[];
};

export type ReportStageSummary = {
  stage: string;
  label: string;
  title: string;
  summary: string;
  status: "confirmed" | "draft" | "pending";
  assessment: ReportAssessmentSnapshot | null;
  userEditedPaths: string[];
};

export type ReportSnapshot = {
  projectId: string;
  generatedAt: string;
  artifactLocale: "en" | "zh" | null;
  artifactSchemaVersion: string | null;
  project: ReportProjectMeta;
  leanCanvas: ReportLeanCanvas;
  marketEvidence: ReportMarketEvidence;
  dvfConfidence: ReportDvfConfidence | null;
  dvfScoreboard: ReportScoreboard;
  dvfAssessment: ReportDvfAssessment | null;
  keyRisks: ReportRiskItem[];
  architectureDiagram: ReportArchitectureDiagram | null;
  overallSummary: string | null;
  diagnosis: ReportDiagnosis;
  validationPlan: ValidationPlanItem[];
  dataQuality: ReportDataQuality | null;
  decisionSnapshot: ReportDecisionSnapshot | null;
  scoreRationales: ReportScoreRationales | null;
  riskRegister: ReportRiskRegisterItem[];
  experimentPlan: ReportExperimentPlanItem[];
  evidenceIndex: ReportEvidenceIndex | null;
  userEditedPaths: Record<string, string[]>;
  assessments: ReportAssessmentSnapshot[];
};
