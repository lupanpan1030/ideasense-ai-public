export type DiagnosisEntry = {
  path: string | null;
  label: string;
  value: string;
  resolutionStatus: string;
  claimType: string;
  evidenceLevel: string;
  source: string;
  note: string | null;
  pending: boolean;
};

export type EvidenceGapEntry = {
  path: string | null;
  label: string;
  reason: string;
  evidenceLevel: string;
};

export type VerificationSummary = {
  status: string;
  supportedClaims: number;
  unsupportedClaims: number;
  uncertainClaims: number;
  supportedRatio: number | null;
  items: Array<{
    claim: string;
    verdict: string;
    confidence: number | null;
    section: string | null;
  }>;
};

export type ContextCard = {
  stage: string | null;
  generatedAt: string | null;
  userConfirmedInputs: DiagnosisEntry[];
  founderAssumptions: DiagnosisEntry[];
  aiInferences: DiagnosisEntry[];
  unknowns: DiagnosisEntry[];
  evidenceGaps: EvidenceGapEntry[];
  verificationSummary: VerificationSummary | null;
};

export type ValidationPlanItem = {
  action: string;
  target: string | null;
  successSignal: string | null;
  linkedRisk: string | null;
  priority: string | null;
};

export type ReportDiagnosis = {
  generatedAt: string | null;
  summary: string | null;
  contextCards: Record<string, ContextCard>;
  dvfConfidence: Record<string, unknown>;
  riskRegister: Record<string, unknown>[];
  stageValidationPlans: Record<string, ValidationPlanItem[]>;
  nextValidationSteps: ValidationPlanItem[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toOptionalString = (value: unknown): string | null => {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (value === null || value === undefined) {
    return null;
  }
  return String(value);
};

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const toBoolean = (value: unknown): boolean => value === true;

const normalizeEntry = (value: unknown): DiagnosisEntry | null => {
  if (!isRecord(value)) {
    return null;
  }
  const label =
    toTrimmedString(value.label) ??
    toTrimmedString(value.path) ??
    toTrimmedString(value.name);
  const rawValue =
    toOptionalString(value.value) ??
    toOptionalString(value.text) ??
    toOptionalString(value.answer);
  if (!label || !rawValue) {
    return null;
  }
  return {
    path: toTrimmedString(value.path),
    label,
    value: rawValue,
    resolutionStatus:
      toTrimmedString(value.resolution_status) ??
      toTrimmedString(value.resolutionStatus) ??
      "answered",
    claimType:
      toTrimmedString(value.claim_type) ??
      toTrimmedString(value.claimType) ??
      "hypothesis",
    evidenceLevel:
      toTrimmedString(value.evidence_level) ??
      toTrimmedString(value.evidenceLevel) ??
      "E1",
    source: toTrimmedString(value.source) ?? "user",
    note: toOptionalString(value.note),
    pending: toBoolean(value.pending),
  };
};

const normalizeEvidenceGap = (value: unknown): EvidenceGapEntry | null => {
  if (!isRecord(value)) {
    return null;
  }
  const label = toTrimmedString(value.label) ?? toTrimmedString(value.path);
  if (!label) {
    return null;
  }
  return {
    path: toTrimmedString(value.path),
    label,
    reason:
      toTrimmedString(value.reason) ??
      toTrimmedString(value.note) ??
      "Evidence gap",
    evidenceLevel:
      toTrimmedString(value.evidence_level) ??
      toTrimmedString(value.evidenceLevel) ??
      "E0",
  };
};

const normalizeEntryArray = (value: unknown): DiagnosisEntry[] =>
  Array.isArray(value)
    ? value
        .map((entry) => normalizeEntry(entry))
        .filter((entry): entry is DiagnosisEntry => Boolean(entry))
    : [];

const normalizeEvidenceGapArray = (value: unknown): EvidenceGapEntry[] =>
  Array.isArray(value)
    ? value
        .map((entry) => normalizeEvidenceGap(entry))
        .filter((entry): entry is EvidenceGapEntry => Boolean(entry))
    : [];

export const normalizeVerificationSummary = (
  value: unknown
): VerificationSummary | null => {
  if (!isRecord(value)) {
    return null;
  }
  const items = Array.isArray(value.items)
    ? value.items
        .map((item) => {
          if (!isRecord(item)) {
            return null;
          }
          const claim = toTrimmedString(item.claim);
          if (!claim) {
            return null;
          }
          return {
            claim,
            verdict: toTrimmedString(item.verdict) ?? "uncertain",
            confidence: toNumber(item.confidence),
            section: toOptionalString(item.section),
          };
        })
        .filter(
          (item): item is VerificationSummary["items"][number] => Boolean(item)
        )
    : [];

  return {
    status: toTrimmedString(value.status) ?? "not_checked",
    supportedClaims: toNumber(value.supported_claims) ?? 0,
    unsupportedClaims: toNumber(value.unsupported_claims) ?? 0,
    uncertainClaims: toNumber(value.uncertain_claims) ?? 0,
    supportedRatio: toNumber(value.supported_ratio),
    items,
  };
};

export const normalizeContextCard = (value: unknown): ContextCard => {
  const record = isRecord(value) ? value : {};
  return {
    stage: toTrimmedString(record.stage),
    generatedAt:
      toTrimmedString(record.generated_at) ?? toTrimmedString(record.generatedAt),
    userConfirmedInputs: normalizeEntryArray(record.user_confirmed_inputs),
    founderAssumptions: normalizeEntryArray(record.founder_assumptions),
    aiInferences: normalizeEntryArray(record.ai_inferences),
    unknowns: normalizeEntryArray(record.unknowns),
    evidenceGaps: normalizeEvidenceGapArray(record.evidence_gaps),
    verificationSummary: normalizeVerificationSummary(record.verification_summary),
  };
};

export const hasContextCardContent = (card: ContextCard | null | undefined) =>
  Boolean(
    card &&
      (card.userConfirmedInputs.length ||
        card.founderAssumptions.length ||
        card.aiInferences.length ||
        card.unknowns.length ||
        card.evidenceGaps.length ||
        (card.verificationSummary &&
          (card.verificationSummary.supportedClaims ||
            card.verificationSummary.unsupportedClaims ||
            card.verificationSummary.uncertainClaims ||
            card.verificationSummary.items.length)))
  );

export const normalizeValidationPlan = (
  value: unknown
): ValidationPlanItem[] => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (!isRecord(item)) {
        return null;
      }
      const action = toTrimmedString(item.action);
      if (!action) {
        return null;
      }
      return {
        action,
        target: toOptionalString(item.target),
        successSignal:
          toOptionalString(item.success_signal) ??
          toOptionalString(item.successSignal),
        linkedRisk:
          toOptionalString(item.linked_risk) ??
          toOptionalString(item.linkedRisk),
        priority: toOptionalString(item.priority),
      };
    })
    .filter((item): item is ValidationPlanItem => Boolean(item));
};

export const normalizeReportDiagnosis = (value: unknown): ReportDiagnosis => {
  const record = isRecord(value) ? value : {};
  const rawCards = isRecord(record.context_cards) ? record.context_cards : {};
  const contextCards = Object.entries(rawCards).reduce<Record<string, ContextCard>>(
    (acc, [stage, card]) => {
      const stageKey = stage.trim().toLowerCase();
      if (stageKey) {
        acc[stageKey] = normalizeContextCard(card);
      }
      return acc;
    },
    {}
  );
  const rawStagePlans = isRecord(record.stage_validation_plans)
    ? record.stage_validation_plans
    : {};
  const stageValidationPlans = Object.entries(rawStagePlans).reduce<
    Record<string, ValidationPlanItem[]>
  >((acc, [stage, plan]) => {
    const stageKey = stage.trim().toLowerCase();
    const normalized = normalizeValidationPlan(plan);
    if (stageKey && normalized.length) {
      acc[stageKey] = normalized;
    }
    return acc;
  }, {});

  return {
    generatedAt:
      toTrimmedString(record.generated_at) ?? toTrimmedString(record.generatedAt),
    summary:
      toOptionalString(record.summary) ??
      toOptionalString(record.diagnosis_summary) ??
      toOptionalString(record.diagnosisSummary),
    contextCards,
    dvfConfidence: isRecord(record.dvf_confidence)
      ? record.dvf_confidence
      : {},
    riskRegister: Array.isArray(record.risk_register)
      ? record.risk_register.filter(isRecord)
      : [],
    stageValidationPlans,
    nextValidationSteps: normalizeValidationPlan(
      record.next_validation_steps ?? record.nextValidationSteps
    ),
  };
};
