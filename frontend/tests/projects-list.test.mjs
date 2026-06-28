import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const projectsModulePath = path.join(
  frontendRoot,
  "features",
  "projects",
  "projects.ts"
);
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");

const { normalizeProjectsResponse, getProjectsErrorMessage } =
  loadTsModule(projectsModulePath);
const { ApiError } = loadTsModule(clientModulePath);

test("normalizeProjectsResponse applies fallbacks for missing fields", () => {
  const result = normalizeProjectsResponse({
    projects: [
      {
        id: "project-1",
        title: "",
        description: null,
        current_stage: null,
        updated_at: null,
      },
    ],
  });

  assert.equal(result.length, 1);
  assert.equal(result[0].title, "Untitled project");
  assert.equal(result[0].description, "No description yet.");
  assert.equal(result[0].stage.label, "Unknown");
  assert.equal(result[0].isArchived, false);
  assert.equal(result[0].createdAt, null);
  assert.equal(result[0].createdAtLabel, "Created unknown");
  assert.equal(result[0].updatedAt, null);
  assert.equal(result[0].updatedAtLabel, "Updated unknown");
});

test("normalizeProjectsResponse handles empty lists", () => {
  const result = normalizeProjectsResponse({ projects: [] });
  assert.deepEqual(result, []);
});

test("normalizeProjectsResponse tolerates malformed envelopes", () => {
  const result = normalizeProjectsResponse({ project: [] });
  assert.deepEqual(result, []);
});

test("getProjectsErrorMessage maps 401 responses", () => {
  const error = new ApiError({ status: 401, message: "Unauthorized" });
  assert.equal(
    getProjectsErrorMessage(error),
    "Your session expired. Please sign in again."
  );
});

test("getProjectsErrorMessage maps 500 responses", () => {
  const error = new ApiError({ status: 500, message: "Server error" });
  assert.equal(
    getProjectsErrorMessage(error),
    "Projects service is unavailable. Please try again soon."
  );
});

test("getProjectsErrorMessage maps 404 responses", () => {
  const error = new ApiError({ status: 404, message: "Project not found." });
  assert.equal(
    getProjectsErrorMessage(error),
    "Project not found or it was deleted."
  );
});
