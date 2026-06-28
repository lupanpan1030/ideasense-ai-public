import { normalizeContextVersion } from "@/features/context/context-refresh";

export type StageGateSignal = {
  projectId: string | null;
  stage: string | null;
  nextStage: string | null;
  stageStatus: string | null;
  contextVersion: number | null;
  contextUpdatedAt: string | null;
  scoreStatus: string | null;
  totalScore: number | null;
  scores: Record<string, unknown> | null;
  open: boolean;
};

export const STAGE_GATE_AWAITING_CONFIRM = "awaiting_confirm";

type StageGatePayload = {
  project_id?: unknown;
  stage?: unknown;
  next_stage?: unknown;
  stage_status?: unknown;
  context_version?: unknown;
  context_updated_at?: unknown;
  score_status?: unknown;
  total_score?: unknown;
  scores_json?: unknown;
  scores?: unknown;
  open?: unknown;
};

const STAGE_GATE_EVENT = "ideasense:stage-gate";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const toTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const toLowerTrimmedString = (value: unknown): string | null => {
  const raw = toTrimmedString(value);
  return raw ? raw.toLowerCase() : null;
};

const toNumber = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const toBoolean = (value: unknown): boolean => value === true;

const normalizeStageGateSignal = (payload: unknown): StageGateSignal | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const response = payload as StageGatePayload;
  const projectId = toTrimmedString(response.project_id);
  const stage = toTrimmedString(response.stage);
  const nextStage = toTrimmedString(response.next_stage);
  const stageStatus = toLowerTrimmedString(response.stage_status);
  const contextVersion = normalizeContextVersion(response.context_version);
  const contextUpdatedAt =
    toTrimmedString(response.context_updated_at) ?? null;
  const scoreStatus = toLowerTrimmedString(response.score_status);
  const totalScore = toNumber(response.total_score);
  const open = toBoolean(response.open);

  const scoresPayload =
    (isRecord(response.scores_json) && response.scores_json) ||
    (isRecord(response.scores) && response.scores) ||
    null;

  return {
    projectId,
    stage,
    nextStage,
    stageStatus,
    contextVersion,
    contextUpdatedAt,
    scoreStatus,
    totalScore,
    scores: scoresPayload,
    open,
  };
};

export const emitStageGate = (payload: unknown): void => {
  if (typeof window === "undefined") {
    return;
  }

  const normalized = normalizeStageGateSignal(payload);
  if (!normalized) {
    return;
  }

  window.dispatchEvent(new CustomEvent(STAGE_GATE_EVENT, { detail: normalized }));
};

export const isAwaitingConfirmStageGateSignal = (
  signal: StageGateSignal | null,
  expectedProjectId?: string | null
): signal is StageGateSignal => {
  if (!signal || signal.stageStatus !== STAGE_GATE_AWAITING_CONFIRM) {
    return false;
  }
  const expected = expectedProjectId?.trim();
  if (!expected || !signal.projectId) {
    return true;
  }
  return signal.projectId === expected;
};

export const subscribeToStageGate = (
  listener: (payload: StageGateSignal) => void
): (() => void) => {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handler = (event: Event) => {
    const detail = (event as CustomEvent).detail;
    if (detail && typeof detail === "object") {
      listener(detail as StageGateSignal);
    }
  };

  window.addEventListener(STAGE_GATE_EVENT, handler as EventListener);
  return () => window.removeEventListener(STAGE_GATE_EVENT, handler as EventListener);
};

export { normalizeStageGateSignal };
