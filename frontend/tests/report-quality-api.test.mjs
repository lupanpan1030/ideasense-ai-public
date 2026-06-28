import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const apiModulePath = path.join(frontendRoot, "lib", "api", "client.ts");
const reportQualityModulePath = path.join(
  frontendRoot,
  "features",
  "admin",
  "report-quality.ts"
);

const apiModule = loadTsModule(apiModulePath);
const reportQuality = loadTsModule(reportQualityModulePath);

test("fetchReportQualityObservations builds filters and normalizes rows", async () => {
  let requestedPath = "";
  apiModule.apiClient.fetchJson = async (pathValue) => {
    requestedPath = pathValue;
    return {
      observations: [
        {
          id: "obs-1",
          org_id: "org-1",
          org_name: "IdeaSense Lab",
          org_slug: "ideasense-lab",
          project_id: "project-1",
          project_title: "Validation Tool",
          report_id: "report-1",
          report_version: "2",
          generated_from_state_version: 6,
          observation_schema_version: "assessment_quality_observation_v1",
          status: "fail",
          failed_invariants: ["score_rationales_complete"],
          warning_invariants: ["canonical_score_boundary"],
          score_snapshot: { total_score: 72 },
          evidence_counts: { unknowns: 2 },
          canonical_boundaries: { within_any_score_boundary: false },
          observed_at: "2026-06-04T00:00:00Z",
          created_at: "2026-06-04T00:00:00Z",
          updated_at: "2026-06-04T00:00:00Z",
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    };
  };

  const response = await reportQuality.fetchReportQualityObservations({
    status: "fail",
    q: "Validation Tool",
  });

  assert.match(requestedPath, /status=fail/);
  assert.match(requestedPath, /q=Validation\+Tool/);
  assert.equal(response.total, 1);
  assert.equal(response.observations[0].status, "fail");
  assert.equal(response.observations[0].reportVersion, 2);
  assert.deepEqual(response.observations[0].failedInvariants, [
    "score_rationales_complete",
  ]);
});

test("fetchReportQualityObservation normalizes detail payload", async () => {
  apiModule.apiClient.fetchJson = async (pathValue) => {
    assert.equal(
      pathValue,
      "/platform-api/report-quality/observations/obs-2"
    );
    return {
      id: "obs-2",
      org_id: "org-1",
      project_id: "project-1",
      report_id: "report-1",
      report_version: 1,
      generated_from_state_version: 4,
      observation_schema_version: "assessment_quality_observation_v1",
      status: "warn",
      failed_invariants: [],
      warning_invariants: ["canonical_score_boundary"],
      score_snapshot: {},
      evidence_counts: {},
      canonical_boundaries: {},
      observation: { summary: { status: "warn" } },
    };
  };

  const response = await reportQuality.fetchReportQualityObservation("obs-2");

  assert.equal(response.status, "warn");
  assert.deepEqual(response.observation, { summary: { status: "warn" } });
});

test("getReportQualityErrorMessage maps platform access errors", () => {
  const message = reportQuality.getReportQualityErrorMessage(
    new apiModule.ApiError({
      status: 403,
      message: "Insufficient platform permissions",
    }),
    {
      accessDenied: "No platform access",
      default: "Default",
      sessionExpired: "Expired",
      unavailable: "Unavailable",
    }
  );

  assert.equal(message, "No platform access");
});
