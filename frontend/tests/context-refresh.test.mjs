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
  "context",
  "context-refresh.ts"
);

const {
  normalizeContextVersion,
  shouldRefreshContext,
  handleChatControlRefresh,
  resolvePollBackoffMs,
  shouldRunPollRefresh,
} = loadTsModule(modulePath);

test("normalizeContextVersion parses numeric inputs", () => {
  assert.equal(normalizeContextVersion(3), 3);
  assert.equal(normalizeContextVersion("4"), 4);
  assert.equal(normalizeContextVersion(" 5 "), 5);
  assert.equal(normalizeContextVersion(""), null);
  assert.equal(normalizeContextVersion(null), null);
});

test("shouldRefreshContext triggers only on version changes", () => {
  assert.equal(shouldRefreshContext(null, 0), true);
  assert.equal(shouldRefreshContext(1, 1), false);
  assert.equal(shouldRefreshContext(1, 2), true);
  assert.equal(shouldRefreshContext(2, "2"), false);
  assert.equal(shouldRefreshContext(2, "3"), true);
  assert.equal(shouldRefreshContext(2, null), false);
});

test("poll refresh skips hidden, in-flight, and backoff windows", () => {
  assert.equal(
    shouldRunPollRefresh({
      isDocumentHidden: true,
      inFlight: false,
      now: 100,
      nextRetryAt: 0,
    }),
    false
  );
  assert.equal(
    shouldRunPollRefresh({
      isDocumentHidden: false,
      inFlight: true,
      now: 100,
      nextRetryAt: 0,
    }),
    false
  );
  assert.equal(
    shouldRunPollRefresh({
      isDocumentHidden: false,
      inFlight: false,
      now: 100,
      nextRetryAt: 200,
    }),
    false
  );
  assert.equal(
    shouldRunPollRefresh({
      isDocumentHidden: false,
      inFlight: false,
      now: 250,
      nextRetryAt: 200,
    }),
    true
  );
});

test("poll backoff grows and caps", () => {
  assert.equal(resolvePollBackoffMs(0), 0);
  assert.equal(resolvePollBackoffMs(1), 12000);
  assert.equal(resolvePollBackoffMs(2), 24000);
  assert.equal(resolvePollBackoffMs(4), 60000);
  assert.equal(resolvePollBackoffMs(8), 60000);
});

test("handleChatControlRefresh triggers refresh for chat control/meta events", () => {
  let refreshCalls = 0;
  let latestVersion = null;
  const onRefresh = () => {
    refreshCalls += 1;
  };
  const updateLatest = (version) => {
    latestVersion = version;
  };

  const projectId = "project-123";

  const didRefreshMeta = handleChatControlRefresh({
    payload: { type: "meta", project_id: projectId },
    projectId,
    currentVersion: 1,
    onRefresh,
    onUpdateLatestVersion: updateLatest,
  });

  assert.equal(didRefreshMeta, true);
  assert.equal(refreshCalls, 1);

  const didRefreshSameVersion = handleChatControlRefresh({
    payload: {
      type: "control",
      project_id: projectId,
      context_version: 2,
    },
    projectId,
    currentVersion: 2,
    onRefresh,
    onUpdateLatestVersion: updateLatest,
  });

  assert.equal(didRefreshSameVersion, false);
  assert.equal(refreshCalls, 1);
  assert.equal(latestVersion, 2);

  const didRefreshStageComplete = handleChatControlRefresh({
    payload: { type: "stage_complete", project_id: projectId },
    projectId,
    currentVersion: 2,
    onRefresh,
    onUpdateLatestVersion: updateLatest,
  });

  assert.equal(didRefreshStageComplete, true);
  assert.equal(refreshCalls, 2);

  const didSkipOtherProject = handleChatControlRefresh({
    payload: { type: "meta", project_id: "other" },
    projectId,
    currentVersion: 2,
    onRefresh,
    onUpdateLatestVersion: updateLatest,
  });

  assert.equal(didSkipOtherProject, false);
  assert.equal(refreshCalls, 2);
});
