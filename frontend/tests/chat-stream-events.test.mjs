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
  "chat",
  "chat-stream.ts"
);

const { dispatchSseEvent } = loadTsModule(modulePath);

test("dispatchSseEvent emits control payloads via emitControl", () => {
  const calls = [];
  const emitControl = (payload) => calls.push(payload);

  dispatchSseEvent(
    { event: "control", data: JSON.stringify({ context_version: 2 }) },
    { emitControl, logger: { warn() {} } },
    "project-1"
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, "control");
  assert.equal(calls[0].context_version, 2);
});

test("dispatchSseEvent emits meta payloads via emitControl", () => {
  const calls = [];
  const emitControl = (payload) => calls.push(payload);

  dispatchSseEvent(
    { event: "meta", data: JSON.stringify({ context_version: 3 }) },
    { emitControl, logger: { warn() {} } },
    "project-2"
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, "meta");
  assert.equal(calls[0].project_id, "project-2");
});

test("dispatchSseEvent forces meta type and fills empty project_id", () => {
  const calls = [];
  const emitControl = (payload) => calls.push(payload);

  dispatchSseEvent(
    {
      event: "meta",
      data: JSON.stringify({ type: "control", project_id: "   " }),
    },
    { emitControl, logger: { warn() {} } },
    "project-3"
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, "meta");
  assert.equal(calls[0].project_id, "project-3");
});

test("dispatchSseEvent sends status payload to status handler", () => {
  const calls = [];

  dispatchSseEvent(
    {
      event: "status",
      data: JSON.stringify({
        phase: "checking_answer",
        label: "Checking your answer",
      }),
    },
    { onStatus: (payload) => calls.push(payload), logger: { warn() {} } },
    "project-4"
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].phase, "checking_answer");
  assert.equal(calls[0].label, "Checking your answer");
});
