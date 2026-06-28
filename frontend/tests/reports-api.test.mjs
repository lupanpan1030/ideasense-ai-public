import { test, after } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const reportsApiPath = path.join(
  frontendRoot,
  "features",
  "reports",
  "reports-api.ts"
);
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");

const clientModule = loadTsModule(clientModulePath);
const { ApiError } = clientModule;
const { fetchProjectReport, fetchProjectReportStatus, normalizeReportJobStatus } =
  loadTsModule(reportsApiPath);
const originalFetchJson = clientModule.apiClient.fetchJson;

after(() => {
  clientModule.apiClient.fetchJson = originalFetchJson;
});

test("fetchProjectReport returns null only for missing reports", async () => {
  clientModule.apiClient.fetchJson = async () => {
    throw new ApiError({ status: 404, message: "Report not found." });
  };

  await assert.doesNotReject(async () => {
    const report = await fetchProjectReport("project-1");
    assert.equal(report, null);
  });
});

test("fetchProjectReport preserves missing project errors", async () => {
  clientModule.apiClient.fetchJson = async () => {
    throw new ApiError({ status: 404, message: "Project not found." });
  };

  await assert.rejects(
    () => fetchProjectReport("project-1"),
    (error) =>
      error instanceof ApiError &&
      error.status === 404 &&
      error.message === "Project not found."
  );
});

test("fetchProjectReport preserves report access errors", async () => {
  clientModule.apiClient.fetchJson = async () => {
    throw new ApiError({ status: 403, message: "Report access denied." });
  };

  await assert.rejects(
    () => fetchProjectReport("project-1"),
    (error) =>
      error instanceof ApiError &&
      error.status === 403 &&
      error.message === "Report access denied."
  );
});

test("fetchProjectReportStatus normalizes report job status payloads", async () => {
  clientModule.apiClient.fetchJson = async (path) => {
    assert.equal(path, "/projects/project-1/report/status");
    return {
      project_id: "project-1",
      current_stage: "report",
      stage_status: "awaiting_confirm",
      job_type: "report_generation_v0",
      status: "finalizing",
      retryable: false,
      report_id: "report-1",
      report_version: "3",
      generated_at: "2026-06-02T12:00:00Z",
      context_version: "8",
      next_poll_ms: "1500",
    };
  };

  const status = await fetchProjectReportStatus("project-1");

  assert.equal(status.projectId, "project-1");
  assert.equal(status.status, "finalizing");
  assert.equal(status.jobType, "report_generation_v0");
  assert.equal(status.reportVersion, 3);
  assert.equal(status.contextVersion, 8);
  assert.equal(status.nextPollMs, 1500);
});

test("report APIs pass requested output locale when provided", async () => {
  const paths = [];
  clientModule.apiClient.fetchJson = async (path) => {
    paths.push(path);
    if (path.includes("/report/status")) {
      return {
        project_id: "project-1",
        current_stage: "report",
        stage_status: "awaiting_confirm",
        job_type: "report_generation_v0",
        status: "queued",
        retryable: false,
        context_version: 8,
      };
    }
    throw new ApiError({ status: 404, message: "Report not found." });
  };

  const report = await fetchProjectReport("project-1", { outputLocale: "zh" });
  const status = await fetchProjectReportStatus("project-1", {
    outputLocale: "zh",
  });

  assert.equal(report, null);
  assert.equal(status.status, "queued");
  assert.deepEqual(paths, [
    "/projects/project-1/report?output_locale=zh",
    "/projects/project-1/report/status?output_locale=zh",
  ]);
});

test("normalizeReportJobStatus preserves explicit retryable false", () => {
  const status = normalizeReportJobStatus(
    {
      project_id: "project-1",
      current_stage: "report",
      status: "failed",
      retryable: false,
      next_poll_ms: 100,
    },
    "fallback-project"
  );

  assert.equal(status.projectId, "project-1");
  assert.equal(status.status, "failed");
  assert.equal(status.retryable, false);
  assert.equal(status.nextPollMs, 500);
});

test("normalizeReportJobStatus rejects unknown status values", () => {
  const status = normalizeReportJobStatus(
    {
      project_id: "project-1",
      current_stage: "report",
      status: "waiting_on_worker",
      retryable: false,
    },
    "fallback-project"
  );

  assert.equal(status, null);
});

test("fetchProjectReportStatus rejects unknown status payloads", async () => {
  clientModule.apiClient.fetchJson = async () => ({
    project_id: "project-1",
    current_stage: "report",
    status: "waiting_on_worker",
  });

  await assert.rejects(
    () => fetchProjectReportStatus("project-1"),
    /Invalid report status payload\./
  );
});
