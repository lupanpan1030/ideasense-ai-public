import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const viewModelModulePath = path.join(
  frontendRoot,
  "features",
  "admin",
  "question-bank-view-model.ts"
);

const {
  formatQuestionBankQuestionLabel,
  formatQuestionBankStageValue,
  formatQuestionBankTimestamp,
  parseQuestionBankJson,
  questionBankListToText,
  questionBankTextToList,
  safeQuestionBankJsonStringify,
} = loadTsModule(viewModelModulePath);

test("formatQuestionBankTimestamp falls back for missing and invalid values", () => {
  assert.equal(formatQuestionBankTimestamp(null, "en", "Unknown"), "Unknown");
  assert.equal(
    formatQuestionBankTimestamp("not-a-date", "zh", "未知"),
    "未知"
  );
  assert.notEqual(
    formatQuestionBankTimestamp("2024-04-03T10:00:00Z", "en", "Unknown"),
    "Unknown"
  );
});

test("question bank newline helpers preserve one-item-per-line payloads", () => {
  assert.equal(questionBankListToText(["S1Q1", "S1Q2"]), "S1Q1\nS1Q2");
  assert.deepEqual(questionBankTextToList(" S1Q1 \n\n S1Q2 \n"), [
    "S1Q1",
    "S1Q2",
  ]);
});

test("parseQuestionBankJson accepts only JSON objects", () => {
  assert.deepEqual(parseQuestionBankJson("", "Object required"), {});
  assert.deepEqual(parseQuestionBankJson('{"weight":2}', "Object required"), {
    weight: 2,
  });
  assert.throws(
    () => parseQuestionBankJson("[]", "Object required"),
    /Object required/
  );
});

test("formatQuestionBankQuestionLabel prefers title and falls back to id", () => {
  assert.equal(
    formatQuestionBankQuestionLabel({
      orderIndex: 2,
      title: "Problem clarity",
      questionId: "S1Q2",
    }),
    "2. Problem clarity"
  );
  assert.equal(
    formatQuestionBankQuestionLabel({
      orderIndex: 3,
      title: "",
      questionId: "S1Q3",
    }),
    "3. S1Q3"
  );
});

test("formatQuestionBankStageValue maps known stages and preserves unknown values", () => {
  assert.equal(
    formatQuestionBankStageValue("problem", { problem: "Problem" }),
    "Problem"
  );
  assert.equal(
    formatQuestionBankStageValue("custom", { problem: "Problem" }),
    "custom"
  );
});

test("safeQuestionBankJsonStringify returns object JSON or an empty object fallback", () => {
  assert.equal(
    safeQuestionBankJsonStringify({ enabled: true }),
    '{\n  "enabled": true\n}'
  );
  const circular = {};
  circular.self = circular;
  assert.equal(safeQuestionBankJsonStringify(circular), "{}");
});
