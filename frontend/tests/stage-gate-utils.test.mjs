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
  "components",
  "stage-gate-utils.ts"
);

const { hasVisibleStageDraftSummary, renderMarkdown } = loadTsModule(modulePath);

test("hasVisibleStageDraftSummary requires non-empty draft text", () => {
  assert.equal(hasVisibleStageDraftSummary(null), false);
  assert.equal(hasVisibleStageDraftSummary({ draftSummaryText: "" }), false);
  assert.equal(hasVisibleStageDraftSummary({ draftSummaryText: "   " }), false);
  assert.equal(
    hasVisibleStageDraftSummary({ draftSummaryText: "Problem summary" }),
    true
  );
});

test("renderMarkdown escapes html before formatting", () => {
  const html = renderMarkdown("**Safe** <script>alert('x')</script>");

  assert.match(html, /<strong>Safe<\/strong>/);
  assert.match(html, /&lt;script&gt;alert/);
  assert.doesNotMatch(html, /<script>/);
});
