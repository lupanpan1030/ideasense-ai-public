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

const { handleSseControlEvent } = loadTsModule(modulePath);

test("handleSseControlEvent emits parsed payload", () => {
  const calls = [];
  const emit = (payload) => calls.push(payload);
  const logger = { warn() {} };

  const raw = JSON.stringify({
    type: "ai_message_id",
    context_version: 4,
    context_updated_at: "2024-02-01T10:30:00+00:00",
  });

  const result = handleSseControlEvent(raw, emit, logger);

  assert.equal(result, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].context_version, 4);
});

test("handleSseControlEvent ignores invalid JSON", () => {
  const calls = [];
  const emit = (payload) => calls.push(payload);
  const logger = { warn() {} };

  const result = handleSseControlEvent("{not-json", emit, logger);

  assert.equal(result, false);
  assert.equal(calls.length, 0);
});
