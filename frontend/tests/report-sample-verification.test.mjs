import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const modulePath = path.join(
  frontendRoot,
  "features",
  "reports",
  "report-sample-verification.ts"
);

const { buildSampleVerificationSnapshot } = loadTsModule(modulePath);

test("buildSampleVerificationSnapshot returns null without a source report", () => {
  assert.equal(buildSampleVerificationSnapshot(null), null);
});

test("buildSampleVerificationSnapshot maps supported sample entries", () => {
  const snapshot = buildSampleVerificationSnapshot({
    projectId: "sample-project",
    assessments: [
      {
        stage: "problem",
        contextCard: {
          userConfirmedInputs: [
            {
              path: "problem.target_user",
              label: "Target user",
              value: "Student founders",
              evidenceLevel: "user_confirmed",
            },
          ],
          founderAssumptions: [],
          evidenceGaps: [],
        },
      },
    ],
  });

  assert.equal(snapshot.projectId, "sample-project");
  assert.equal(snapshot.stages[0].stage, "problem");
  assert.equal(snapshot.stages[0].supported, 1);
  assert.equal(snapshot.stages[0].verified, 1);
  assert.equal(snapshot.stages[0].questions[0].questionId, "problem.target_user");
  assert.equal(snapshot.stages[0].questions[0].status, "supported");
  assert.equal(
    snapshot.stages[0].questions[0].sources[0].snippet,
    "Student founders"
  );
});

test("buildSampleVerificationSnapshot maps assumptions and gaps as uncertain", () => {
  const snapshot = buildSampleVerificationSnapshot({
    projectId: "sample-project",
    assessments: [
      {
        stage: "market",
        contextCard: {
          userConfirmedInputs: [],
          founderAssumptions: [
            {
              path: "market.frequency",
              label: "Usage frequency",
              value: "Weekly",
            },
          ],
          evidenceGaps: [
            {
              path: "market.willingness_to_pay",
              label: "Willingness to pay",
              reason: "Needs pricing evidence",
            },
          ],
        },
      },
    ],
  });

  const stage = snapshot.stages[0];

  assert.equal(stage.total, 2);
  assert.equal(stage.uncertain, 2);
  assert.deepEqual(
    stage.questions.map((question) => question.status),
    ["uncertain", "uncertain"]
  );
  assert.deepEqual(
    stage.questions.map((question) => question.questionId),
    [
      "market.frequency-assumption-0",
      "market.willingness_to_pay-gap-0",
    ]
  );
  assert.equal(stage.questions[1].sources[0].snippet, "Needs pricing evidence");
});
