import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const reportModulePath = path.join(
  frontendRoot,
  "features",
  "reports",
  "reports-normalize.ts"
);

const { normalizeReportResponse, isReportEmpty, buildStageSummaries } =
  loadTsModule(reportModulePath);

test("normalizeReportResponse applies fallbacks for missing fields", () => {
  const result = normalizeReportResponse(
    {
      project_id: "project-1",
      generated_at: "2024-01-01T00:00:00Z",
      project: {
        id: "project-1",
        title: " ",
        description: null,
        current_stage: "problem",
        updated_at: "2024-01-01T00:00:00Z",
      },
      dvf_scoreboard: {
        desirability: "7",
        total_score: "8.5",
        decision_band: "Go",
      },
      key_risks: [
        {
          risk: "Market timing",
          severity: "High",
          likelihood: "Low",
          category: "Market",
        },
        {
          risk: "",
        },
      ],
      assessments: [
        {
          id: "assessment-1",
          stage: "Report",
          summary_text: "All set.",
          score_status: "complete",
        },
      ],
    },
    "project-1"
  );

  assert.ok(result);
  assert.equal(result.project.title, "Untitled project");
  assert.equal(result.project.description, null);
  assert.equal(result.artifactLocale, null);
  assert.equal(result.dvfScoreboard.desirability, 7);
  assert.equal(result.keyRisks.length, 1);
  assert.equal(result.assessments.length, 1);
  assert.deepEqual(result.validationPlan, []);
  assert.equal(Object.keys(result.diagnosis.contextCards).length, 0);
  assert.equal(isReportEmpty(result), false);
});

test("normalizeReportResponse preserves diagnosis and validation plan contracts", () => {
  const result = normalizeReportResponse(
    {
      project_id: "project-2",
      generated_at: "2024-01-01T00:00:00Z",
      diagnosis: {
        diagnosis_summary: "Evidence is directional, not externally verified.",
        context_cards: {
          problem: {
            stage: "problem",
            user_confirmed_inputs: [
              {
                path: "problem.one_line",
                label: "Problem",
                value: "Missed shuttles",
                claim_type: "fact",
                evidence_level: "E2",
                source: "user",
              },
            ],
            founder_assumptions: [],
            ai_inferences: [],
            unknowns: [],
            evidence_gaps: [],
          },
        },
        next_validation_steps: [
          {
            action: "Interview 5 users.",
            target: "P0 users",
            success_signal: "3 users describe the same pain.",
            linked_risk: "Problem evidence gap",
            priority: "high",
          },
        ],
      },
      validation_plan: [
        {
          action: "Run a buyer test.",
          success_signal: "2 buyers agree to a next step.",
        },
      ],
      assessments: [
        {
          id: "assessment-2",
          stage: "problem",
          context_card: {
            stage: "problem",
            user_confirmed_inputs: [
              {
                label: "Problem",
                value: "Missed shuttles",
              },
            ],
          },
          validation_plan: [{ action: "Resolve the unknown." }],
        },
      ],
    },
    "project-2"
  );

  assert.ok(result);
  assert.equal(result.diagnosis.summary, "Evidence is directional, not externally verified.");
  assert.equal(
    result.diagnosis.contextCards.problem.userConfirmedInputs[0].value,
    "Missed shuttles"
  );
  assert.equal(result.validationPlan[0].action, "Run a buyer test.");
  assert.equal(result.assessments[0].validationPlan[0].action, "Resolve the unknown.");
});

test("normalizeReportResponse preserves Report v2 artifact fields", () => {
  const result = normalizeReportResponse(
    {
      project_id: "project-v2",
      generated_at: "2026-06-02T12:00:00Z",
      artifact_schema_version: "report_v2",
      decision_snapshot: {
        verdict: "Validate first",
        total_score: "72",
        confidence: "medium",
        rationale: "Buyer urgency needs more proof.",
        top_findings: ["Student pain is clear."],
        top_gaps: ["Budget owner not confirmed."],
        next_action: "Run two buyer interviews.",
      },
      score_rationales: {
        desirability: {
          score: "76",
          rationale: "Repeated pain signal.",
          evidence_references: ["problem.one_line"],
          evidence_gaps: ["Segment size unknown."],
        },
      },
      risk_register: [
        {
          risk: "Buyer willingness to pay is unproven.",
          severity: "High",
          likelihood: "Medium",
          category: "Market",
          linked_evidence: "market_strategy.pricing",
          early_warning_signal: "No budget owner meeting.",
          mitigation_suggestion: "Run pricing interviews.",
        },
      ],
      experiment_plan: [
        {
          action: "Interview two program directors.",
          success_signal: "Both identify budget owner.",
          priority: "high",
          time_horizon: "7 days",
        },
      ],
      evidence_index: {
        counts: { user_confirmed_inputs: "2" },
        items: [
          {
            stage: "problem",
            layer: "user_confirmed_inputs",
            label: "Problem",
            path: "problem.one_line",
            value: "Founders build before validating demand.",
          },
        ],
      },
      assessments: [],
    },
    "project-v2"
  );

  assert.ok(result);
  assert.equal(result.artifactSchemaVersion, "report_v2");
  assert.equal(result.decisionSnapshot.verdict, "Validate first");
  assert.equal(result.decisionSnapshot.totalScore, 72);
  assert.equal(result.scoreRationales.desirability.score, 76);
  assert.equal(result.riskRegister[0].linkedEvidence, "market_strategy.pricing");
  assert.equal(result.experimentPlan[0].timeHorizon, "7 days");
  assert.equal(result.evidenceIndex.counts.user_confirmed_inputs, 2);
  assert.equal(result.evidenceIndex.items[0].path, "problem.one_line");
  assert.equal(isReportEmpty(result), false);
});

test("buildStageSummaries fills missing stages with placeholders", () => {
  const summaries = buildStageSummaries([
    {
      id: "assessment-1",
      stage: "problem",
      summaryText: "Problem summary.",
      draftSummaryText: null,
      draftOutputLocale: null,
      finalOutputLocale: "en",
      scoreStatus: "computed",
      totalScore: 72.4,
      decisionBand: null,
      computedAt: null,
      createdAt: null,
      updatedAt: null,
      contextCard: {
        stage: null,
        generatedAt: null,
        userConfirmedInputs: [],
        founderAssumptions: [],
        aiInferences: [],
        unknowns: [],
        evidenceGaps: [],
        verificationSummary: null,
      },
      validationPlan: [],
    },
  ]);

  assert.equal(summaries.length, 3);
  assert.equal(summaries[0].stage, "problem");
  assert.equal(summaries[0].summary, "Problem summary.");
  assert.equal(summaries[1].status, "pending");
  assert.equal(summaries[2].status, "pending");
});
