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

const AUTH_TOKEN_KEY = "ideasense.auth.token";
const CURRENT_ORG_STORAGE_KEY = "ideasense.org.current";

const createMockStorage = () => {
  const entries = new Map();
  return {
    getItem(key) {
      return entries.has(key) ? entries.get(key) : null;
    },
    setItem(key, value) {
      entries.set(key, value);
    },
    removeItem(key) {
      entries.delete(key);
    },
    clear() {
      entries.clear();
    },
  };
};

const localStorage = createMockStorage();
const sessionStorage = createMockStorage();
const unauthorizedEvents = [];

globalThis.window = {
  localStorage,
  sessionStorage,
  dispatchEvent(event) {
    unauthorizedEvents.push(event);
    return true;
  },
};

if (typeof globalThis.CustomEvent === "undefined") {
  globalThis.CustomEvent = class CustomEvent extends Event {
    constructor(type, init = {}) {
      super(type);
      this.detail = init.detail;
    }
  };
}

const { streamChatResponse } = loadTsModule(modulePath);

const resetAuthState = () => {
  localStorage.clear();
  sessionStorage.clear();
  unauthorizedEvents.length = 0;
  localStorage.setItem(AUTH_TOKEN_KEY, "token-123");
};

test("stream start 403 keeps auth token and surfaces request error", async () => {
  resetAuthState();
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Project access denied" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    streamChatResponse("project-1", "hello", {}, { idleTimeoutMs: 0 }),
    /You do not have access to this chat/
  );

  assert.equal(localStorage.getItem(AUTH_TOKEN_KEY), "token-123");
  assert.equal(unauthorizedEvents.length, 0);
});

test("stream start 401 clears auth token and emits unauthorized event", async () => {
  resetAuthState();
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    streamChatResponse("project-1", "hello", {}, { idleTimeoutMs: 0 }),
    /Your session expired/
  );

  assert.equal(localStorage.getItem(AUTH_TOKEN_KEY), null);
  assert.equal(unauthorizedEvents.length, 1);
});

test("stream refresh preserves session-only token persistence", async () => {
  resetAuthState();
  localStorage.clear();
  sessionStorage.setItem(AUTH_TOKEN_KEY, "session-token-old");
  const encoder = new TextEncoder();

  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('event: done\ndata: {"status":"ok"}\n\n')
          );
          controller.close();
        },
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "x-auth-token": "session-token-new",
        },
      }
    );

  await streamChatResponse("project-1", "hello", {}, { idleTimeoutMs: 0 });

  assert.equal(localStorage.getItem(AUTH_TOKEN_KEY), null);
  assert.equal(sessionStorage.getItem(AUTH_TOKEN_KEY), "session-token-new");
});

test("stream request includes selected organization context", async () => {
  resetAuthState();
  sessionStorage.setItem(CURRENT_ORG_STORAGE_KEY, "org-123");
  let observedHeaders = null;
  const encoder = new TextEncoder();

  globalThis.fetch = async (_url, init = {}) => {
    observedHeaders = new Headers(init.headers);
    return new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('event: done\ndata: {"status":"ok"}\n\n')
          );
          controller.close();
        },
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
        },
      }
    );
  };

  await streamChatResponse("project-1", "hello", {}, { idleTimeoutMs: 0 });

  assert.equal(observedHeaders.get("X-Org-ID"), "org-123");
});
