import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const entryPath = path.join(
  frontendRoot,
  "tests",
  "fixtures",
  "ts-module-entry.ts"
);

test("loadTsModule resolves alias and .ts dependencies", () => {
  const moduleExports = loadTsModule(entryPath);

  assert.ok(moduleExports);
  assert.equal(moduleExports.loaded, true);
});
