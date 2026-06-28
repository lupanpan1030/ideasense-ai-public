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
  "assessments",
  "stage-gate-channel.ts"
);

const {
  isAwaitingConfirmStageGateSignal,
  normalizeStageGateSignal,
} = loadTsModule(modulePath);

test("isAwaitingConfirmStageGateSignal accepts awaiting confirm for the project", () => {
  const signal = normalizeStageGateSignal({
    project_id: "project-1",
    stage: "problem",
    next_stage: "market",
    stage_status: "awaiting_confirm",
    context_version: "7",
  });

  assert.equal(isAwaitingConfirmStageGateSignal(signal, "project-1"), true);
});

test("isAwaitingConfirmStageGateSignal rejects missing or wrong stage status", () => {
  const missing = normalizeStageGateSignal({
    project_id: "project-1",
    stage: "problem",
  });
  const passed = normalizeStageGateSignal({
    project_id: "project-1",
    stage: "problem",
    stage_status: "passed",
  });

  assert.equal(isAwaitingConfirmStageGateSignal(missing, "project-1"), false);
  assert.equal(isAwaitingConfirmStageGateSignal(passed, "project-1"), false);
});

test("isAwaitingConfirmStageGateSignal rejects another project", () => {
  const signal = normalizeStageGateSignal({
    project_id: "project-2",
    stage: "problem",
    stage_status: "awaiting_confirm",
  });

  assert.equal(isAwaitingConfirmStageGateSignal(signal, "project-1"), false);
});
