import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const stateModulePath = path.join(
  frontendRoot,
  "features",
  "chat",
  "chat-state.ts"
);
const handlersModulePath = path.join(
  frontendRoot,
  "features",
  "chat",
  "chat-stream-handlers.ts"
);

const {
  appendMessageDelta,
  createLocalMessage,
  updateMessageStreamStatus,
} = loadTsModule(stateModulePath);
const { createChatStreamHandlers } = loadTsModule(handlersModulePath);

test("appendMessageDelta appends stream tokens to the active message", () => {
  const message = createLocalMessage({
    id: "assistant-1",
    role: "assistant",
    content: "Hello",
    createdAt: null,
    status: "streaming",
  });

  const result = appendMessageDelta([message], "assistant-1", " world");

  assert.equal(result[0].content, "Hello world");
});

test("updateMessageStreamStatus stores transient status on active message", () => {
  const message = createLocalMessage({
    id: "assistant-1",
    role: "assistant",
    content: "",
    createdAt: null,
    status: "streaming",
  });

  const result = updateMessageStreamStatus(
    [message],
    "assistant-1",
    "Checking your answer"
  );

  assert.equal(result[0].streamStatus, "Checking your answer");
});

test("stream handlers trigger history refresh after done", () => {
  const calls = [];
  const { handlers, didReceiveDone } = createChatStreamHandlers({
    appendToken: (delta) => calls.push(`token:${delta}`),
    updateStatus: (label) => calls.push(`status:${label ?? "clear"}`),
    refreshHistory: () => calls.push("refresh"),
    markDone: () => calls.push("done"),
    reportError: () => calls.push("error"),
  });

  handlers.onStatus?.({ label: "Checking your answer" });
  handlers.onToken?.("hi");
  handlers.onDone?.({ status: "ok" });

  assert.equal(didReceiveDone(), true);
  assert.deepEqual(calls, [
    "status:Checking your answer",
    "status:clear",
    "token:hi",
    "status:clear",
    "done",
    "refresh",
  ]);
});

test("stream handlers clear transient status on error", () => {
  const calls = [];
  const { handlers } = createChatStreamHandlers({
    appendToken: (delta) => calls.push(`token:${delta}`),
    updateStatus: (label) => calls.push(`status:${label ?? "clear"}`),
    refreshHistory: () => calls.push("refresh"),
    reportError: () => calls.push("error"),
  });

  handlers.onStatus?.({ label: "Preparing project context" });
  handlers.onError?.({ status: "error" });

  assert.deepEqual(calls, [
    "status:Preparing project context",
    "status:clear",
    "error",
  ]);
});
