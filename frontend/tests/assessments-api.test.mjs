import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const apiModulePath = path.join(
  frontendRoot,
  "features",
  "assessments",
  "api.ts"
);
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");

const {
  normalizeConfirmResponse,
  normalizeStageDraftResponse,
  getStageGateErrorMessage,
} =
  loadTsModule(apiModulePath);
const { ApiError } = loadTsModule(clientModulePath);

test("normalizeConfirmResponse parses computed scores", () => {
  const payload = {
    score_status: "computed",
    scores: { D: 22, V: 31, F: 19, total: 72 },
    total_score: 72.4,
    next_stage: "market",
    updated_project: { stage_status: "passed" },
    context_card: {
      stage: "problem",
      user_confirmed_inputs: [
        {
          label: "Problem",
          value: "Missed shuttles",
          claim_type: "fact",
          evidence_level: "E2",
          source: "user",
        },
      ],
    },
    validation_plan: [
      {
        action: "Interview 5 users.",
        success_signal: "3 users describe the same pain.",
      },
    ],
  };

  const result = normalizeConfirmResponse(payload);

  assert.ok(result);
  assert.equal(result.scoreStatus, "computed");
  assert.equal(result.totalScore, 72.4);
  assert.equal(result.scores.desirability, 22);
  assert.equal(result.scores.viability, 31);
  assert.equal(result.scores.feasibility, 19);
  assert.equal(result.contextCard.userConfirmedInputs[0].value, "Missed shuttles");
  assert.equal(result.validationPlan[0].action, "Interview 5 users.");
});

test("normalizeConfirmResponse handles needs_retry responses", () => {
  const payload = {
    score_status: "needs_retry",
    error: "LLM timeout",
    scores: null,
  };

  const result = normalizeConfirmResponse(payload);

  assert.ok(result);
  assert.equal(result.scoreStatus, "needs_retry");
  assert.equal(result.error, "LLM timeout");
  assert.equal(result.scores, null);
});

test("normalizeStageDraftResponse parses ready draft status", () => {
  const result = normalizeStageDraftResponse(
    {
      assessment_id: "assessment-1",
      project_id: "project-1",
      stage: "problem",
      stage_status: "awaiting_confirm",
      draft_summary_text: "Draft summary",
      draft_output_locale: "en",
      context_version: 5,
      generation_status: "ready",
      retryable: false,
    },
    "fallback-project",
    "fallback-stage"
  );

  assert.ok(result);
  assert.equal(result.projectId, "project-1");
  assert.equal(result.stage, "problem");
  assert.equal(result.generationStatus, "ready");
  assert.equal(result.retryable, false);
  assert.equal(result.draftSummaryText, "Draft summary");
});

test("normalizeStageDraftResponse maps queued draft status", () => {
  const result = normalizeStageDraftResponse(
    {
      project_id: "project-1",
      stage: "market",
      draft_summary_text: "",
      context_version: 6,
      generation_status: "queued",
    },
    "fallback-project",
    "fallback-stage"
  );

  assert.ok(result);
  assert.equal(result.generationStatus, "queued");
  assert.equal(result.retryable, false);
  assert.equal(result.draftSummaryText, "");
});

test("normalizeStageDraftResponse makes failed drafts retryable", () => {
  const result = normalizeStageDraftResponse(
    {
      project_id: "project-1",
      stage: "tech",
      draft_summary_text: "",
      generation_status: "failed",
      last_error: "Provider unavailable",
    },
    "fallback-project",
    "fallback-stage"
  );

  assert.ok(result);
  assert.equal(result.generationStatus, "failed");
  assert.equal(result.retryable, true);
  assert.equal(result.lastError, "Provider unavailable");
});

test("getStageGateErrorMessage maps 409 to refresh prompt", () => {
  const error = new ApiError({ status: 409, message: "Conflict" });
  const details = getStageGateErrorMessage(error);

  assert.equal(details.shouldRefresh, true);
  assert.match(details.message, /refresh/i);
});

test("getStageGateErrorMessage preserves stage summary timeout detail", () => {
  const error = new ApiError({
    status: 503,
    message: "Stage summary generation timed out. Try again in a moment.",
  });
  const details = getStageGateErrorMessage(error);

  assert.equal(details.shouldRefresh, false);
  assert.equal(
    details.message,
    "Stage summary generation timed out. Try again in a moment."
  );
});

test("normalizeConfirmResponse preserves valid report job status", () => {
  const result = normalizeConfirmResponse({
    score_status: "computed",
    report_job_status: {
      project_id: "project-1",
      current_stage: "report",
      status: "running",
      retryable: false,
    },
  });

  assert.equal(result.reportJobStatus.projectId, "project-1");
  assert.equal(result.reportJobStatus.status, "running");
});

test("normalizeConfirmResponse drops unknown report job status values", () => {
  const result = normalizeConfirmResponse({
    score_status: "computed",
    report_job_status: {
      project_id: "project-1",
      current_stage: "report",
      status: "waiting_on_worker",
      retryable: false,
    },
  });

  assert.equal(result.reportJobStatus, null);
});
