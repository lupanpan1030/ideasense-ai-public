import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");

const { buildApiUrl } = loadTsModule(clientModulePath);

test("buildApiUrl joins base + path without double slashes", () => {
  assert.equal(
    buildApiUrl("/api/v1/projects", "http://localhost:8000"),
    "http://localhost:8000/api/v1/projects"
  );
  assert.equal(
    buildApiUrl("/api/v1/projects", "http://localhost:8000/"),
    "http://localhost:8000/api/v1/projects"
  );
  assert.equal(buildApiUrl("/api/v1/projects", ""), "/api/v1/projects");
});

test("buildApiUrl prefixes /api/v1 when missing", () => {
  assert.equal(
    buildApiUrl("/projects", "http://localhost:8000"),
    "http://localhost:8000/api/v1/projects"
  );
});
