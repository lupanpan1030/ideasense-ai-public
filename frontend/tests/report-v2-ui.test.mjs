import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");

test("report viewer renders background status and Report v2 artifact surfaces", () => {
  const cardsPath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-viewer-v2-cards.tsx"
  );
  const documentPath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-document.tsx"
  );
  const surfacePath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-viewer-surface.tsx"
  );
  const surface = fs.readFileSync(surfacePath, "utf8");
  const cards = fs.readFileSync(cardsPath, "utf8");
  const reportDocument = fs.readFileSync(documentPath, "utf8");
  const cssPath = path.join(frontendRoot, "styles", "layout-reports.css");
  const css = fs.readFileSync(cssPath, "utf8");

  assert.ok(
    surface.includes("<ReportJobStatusCard"),
    "Report page must render report job status while generation is pending"
  );
  assert.ok(
    surface.includes("<ReportDocument") &&
      reportDocument.includes("<ReportV2ArtifactCard"),
    "Report page must render the Report v2 artifact card"
  );
  assert.ok(
    cards.includes("decisionSnapshot") &&
      cards.includes("scoreRationales") &&
      cards.includes("riskRegister") &&
      cards.includes("experimentPlan") &&
      cards.includes("evidenceIndex"),
    "Report v2 card must include all structured artifact sections"
  );
  assert.ok(
    cards.includes("report-v2-summary") &&
      cards.includes("report-v2-row") &&
      css.includes(".report-v2-artifact") &&
      css.includes("overflow-wrap: anywhere"),
    "Report v2 card must use responsive row layout with long-text wrapping"
  );
});

test("chat stage confirmation immediately carries report job status", () => {
  const hookPath = path.join(
    frontendRoot,
    "features",
    "context",
    "use-stage-gate-state.ts"
  );
  const chatHookPath = path.join(
    frontendRoot,
    "features",
    "chat",
    "use-chat-thread.ts"
  );
  const threadPath = path.join(
    frontendRoot,
    "features",
    "chat",
    "chat-thread.tsx"
  );
  const hook = fs.readFileSync(hookPath, "utf8");
  const chatHook = fs.readFileSync(chatHookPath, "utf8");
  const thread = fs.readFileSync(threadPath, "utf8");

  assert.ok(
    hook.includes("report_job_status: result?.reportJobStatus"),
    "stage confirmed event must broadcast the returned report job status"
  );
  assert.ok(
    chatHook.includes("normalizeReportJobStatus") &&
      chatHook.includes("payload.report_job_status"),
    "chat hook must consume report job status from the event immediately"
  );
  assert.ok(
    chatHook.includes('const reportReady = reportJobStatus?.status === "ready";'),
    "chat report navigation must not treat project stage_status=passed as report ready"
  );
  assert.ok(
    chatHook.includes("isReportJobPending") &&
      chatHook.includes("!isReportStage && !isReportJobPending"),
    "chat hook must keep polling pending report jobs before project detail refresh reaches report stage"
  );
  assert.ok(
    chatHook.includes("isStageWaitingForConfirmationError") &&
      chatHook.includes("setIsStageComplete(true)") &&
      chatHook.includes("fetchProjectDetail(projectId)"),
    "chat hook must recover from stale stage props when backend reports awaiting confirmation"
  );
  assert.ok(
    thread.includes('reportStatus === "queued"') &&
      thread.includes("isReportStatusUnavailable"),
    "chat composer must switch to report mode from job status before project refresh"
  );
});

test("report page prioritizes ready fetch errors and respects retryable", () => {
  const viewerPath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-viewer.tsx"
  );
  const viewer = fs.readFileSync(viewerPath, "utf8");
  const surfacePath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-viewer-surface.tsx"
  );
  const surface = fs.readFileSync(surfacePath, "utf8");
  const statusCardPath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-job-status-card.tsx"
  );
  const statusCard = fs.readFileSync(statusCardPath, "utf8");
  const pagePath = path.join(
    frontendRoot,
    "app",
    "(app)",
    "projects",
    "[projectId]",
    "report",
    "page.tsx"
  );
  const page = fs.readFileSync(pagePath, "utf8");

  assert.ok(
    viewer.includes("shouldShowReportFetchError") &&
      viewer.includes('activeReportStatus === "ready"'),
    "ready status with a missing report must show the report fetch error branch"
  );
  assert.ok(
    surface.includes("retryable={reportStatus?.retryable ?? false}") &&
      statusCard.includes("retryable &&") &&
      statusCard.includes("notRetryableDescription"),
    "retry button visibility must follow backend retryable status"
  );
  assert.ok(
    viewer.includes("outputLocale: locale"),
    "report and status requests must use the current UI locale"
  );
  assert.ok(
    page.includes('readSearchParam(resolvedSearchParams, "generate") === "1"') &&
      page.includes("autoStartReport={autoStartReport}"),
    "report page must pass generate=1 into the viewer"
  );
  assert.ok(
    viewer.includes("autoStartReport &&") &&
      viewer.includes('status === "not_started"') &&
      viewer.includes("startReportAttemptedRef.current"),
    "report page must only auto-start not_started jobs from generate=1"
  );
});

test("sample workspace reads one DB source and uses public sample chrome", () => {
  const sampleLayoutPath = path.join(
    frontendRoot,
    "app",
    "(marketing)",
    "sample",
    "layout.tsx"
  );
  const samplePagePath = path.join(
    frontendRoot,
    "app",
    "(marketing)",
    "sample",
    "page.tsx"
  );
  const sampleShellPath = path.join(
    frontendRoot,
    "components",
    "sample",
    "sample-shell.tsx"
  );
  const reportViewerPath = path.join(
    frontendRoot,
    "features",
    "reports",
    "report-viewer.tsx"
  );
  const sampleLayout = fs.readFileSync(sampleLayoutPath, "utf8");
  const samplePage = fs.readFileSync(samplePagePath, "utf8");
  const sampleShell = fs.readFileSync(sampleShellPath, "utf8");
  const reportViewer = fs.readFileSync(reportViewerPath, "utf8");

  assert.ok(
    sampleLayout.includes("getSampleProjectsCached") &&
      samplePage.includes("getSampleProjectsCached") &&
      !sampleLayout.includes("content/sample-workspace") &&
      !samplePage.includes("content/sample-workspace"),
    "sample pages must read from the single DB-backed cached source with no static bundled fallback"
  );
  assert.ok(
    !sampleShell.includes("AppShellTopbar") &&
      sampleShell.includes("SampleTopbar") &&
      sampleShell.includes("LanguageSwitcher"),
    "public sample pages must use public chrome instead of authenticated app chrome"
  );
  assert.ok(
    reportViewer.includes("buildSampleVerificationSnapshot") &&
      reportViewer.includes("setVerificationSnapshot(buildSampleVerificationSnapshot"),
    "sample reports must show bundled verification evidence instead of an empty live verification card"
  );
});
