import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const tokenModulePath = path.join(frontendRoot, "lib", "storage", "token.ts");
const clientModulePath = path.join(frontendRoot, "lib", "api", "client.ts");
const oneTimeTokenUrlModulePath = path.join(
  frontendRoot,
  "lib",
  "auth",
  "one-time-token-url.ts"
);

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
  };
};

test("token storage reads/writes/clears via injected storage", () => {
  const { createTokenStorage, AUTH_TOKEN_STORAGE_KEY } =
    loadTsModule(tokenModulePath);
  const mockStorage = createMockStorage();
  const tokenStorage = createTokenStorage(mockStorage);

  assert.equal(tokenStorage.getToken(), null);

  tokenStorage.setToken("token-123");
  assert.equal(mockStorage.getItem(AUTH_TOKEN_STORAGE_KEY), "token-123");
  assert.equal(tokenStorage.getToken(), "token-123");

  tokenStorage.clearToken();
  assert.equal(mockStorage.getItem(AUTH_TOKEN_STORAGE_KEY), null);
});

test("token storage preserves session-only persistence on refresh", () => {
  const { createTokenStorage, AUTH_TOKEN_STORAGE_KEY } =
    loadTsModule(tokenModulePath);
  const mockStorage = createMockStorage();
  const mockSessionStorage = createMockStorage();
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;

  globalThis.window = {
    localStorage: mockStorage,
    sessionStorage: mockSessionStorage,
    location: { protocol: "http:" },
  };
  globalThis.document = { cookie: "" };

  try {
    const tokenStorage = createTokenStorage();

    tokenStorage.setToken("session-token", { persist: false });
    assert.equal(mockStorage.getItem(AUTH_TOKEN_STORAGE_KEY), null);
    assert.equal(
      mockSessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY),
      "session-token"
    );
    assert.match(globalThis.document.cookie, /ideasense\.auth\.token=session-token/);
    assert.doesNotMatch(globalThis.document.cookie, /Max-Age=/);

    tokenStorage.setTokenPreservingPersistence("refreshed-token");
    assert.equal(mockStorage.getItem(AUTH_TOKEN_STORAGE_KEY), null);
    assert.equal(
      mockSessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY),
      "refreshed-token"
    );
    assert.match(globalThis.document.cookie, /ideasense\.auth\.token=refreshed-token/);
    assert.doesNotMatch(globalThis.document.cookie, /Max-Age=/);
  } finally {
    if (previousWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = previousWindow;
    }
    if (previousDocument === undefined) {
      delete globalThis.document;
    } else {
      globalThis.document = previousDocument;
    }
  }
});

test("api client injects Authorization header", async () => {
  const { createApiClient } = loadTsModule(clientModulePath);

  let capturedAuthorization = null;
  const fetchMock = async (url, init = {}) => {
    const headers = new Headers(init.headers);
    capturedAuthorization = headers.get("Authorization");

    return new Response(JSON.stringify({ ok: true, url }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const tokenStore = {
    getToken: () => "token-abc",
    clearToken: () => {},
  };

  const client = createApiClient({
    fetch: fetchMock,
    tokenStore,
    baseUrl: "https://example.test/api",
  });

  await client.fetchJson("/projects");

  assert.equal(capturedAuthorization, "Bearer token-abc");
});

test("api client preserves token persistence when response refreshes token", async () => {
  const { createApiClient } = loadTsModule(clientModulePath);

  let refreshedToken = null;
  const tokenStore = {
    getToken: () => "token-old",
    setToken: () => {
      throw new Error("setToken should not be called when preserve API exists");
    },
    setTokenPreservingPersistence: (token) => {
      refreshedToken = token;
    },
    clearToken: () => {},
  };

  const fetchMock = async () =>
    new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "x-auth-token": "token-new",
      },
    });

  const client = createApiClient({
    fetch: fetchMock,
    tokenStore,
  });

  await client.fetchJson("/session");

  assert.equal(refreshedToken, "token-new");
});

test("api client clears token and triggers handler on 401", async () => {
  const { createApiClient, ApiError } = loadTsModule(clientModulePath);

  let cleared = 0;
  let unauthorizedCalls = 0;

  const tokenStore = {
    getToken: () => "token-xyz",
    clearToken: () => {
      cleared += 1;
    },
  };

  const fetchMock = async () =>
    new Response(JSON.stringify({ detail: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });

  const client = createApiClient({
    fetch: fetchMock,
    tokenStore,
    onUnauthorized: () => {
      unauthorizedCalls += 1;
    },
  });

  await assert.rejects(client.fetchJson("/projects"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 401);
    return true;
  });

  assert.equal(cleared, 1);
  assert.equal(unauthorizedCalls, 1);
});

test("one-time auth tokens are removed from the URL before network success", () => {
  const verifyPath = path.join(
    frontendRoot,
    "app",
    "(auth)",
    "verify-email",
    "verify-email-client.tsx"
  );
  const resetPath = path.join(
    frontendRoot,
    "app",
    "(auth)",
    "reset-password",
    "reset-password-client.tsx"
  );
  const verifySource = fs.readFileSync(verifyPath, "utf8");
  const resetSource = fs.readFileSync(resetPath, "utf8");
  const verifyEffectIndex = verifySource.indexOf("clearOneTimeTokenFromUrl();");
  const verifyRequestIndex = verifySource.indexOf('postJson("/auth/verify-email"');

  assert.ok(verifyEffectIndex > 0);
  assert.ok(verifyRequestIndex > verifyEffectIndex);
  assert.ok(
    resetSource.includes("useEffect(() =>") &&
      resetSource.includes("clearOneTimeTokenFromUrl();") &&
      resetSource.includes("}, [token]);"),
    "reset password must clear the token from the URL as soon as it is read"
  );
});

test("one-time email tokens can be carried in URL fragments", () => {
  const { readOneTimeTokenFromUrl, clearOneTimeTokenFromUrl } = loadTsModule(
    oneTimeTokenUrlModulePath
  );
  const previousWindow = globalThis.window;
  let replacedUrl = null;

  globalThis.window = {
    location: {
      href: "https://app.example.test/verify-email#token=fragment-secret&source=email",
      hash: "#token=fragment-secret&source=email",
    },
    history: {
      state: null,
      replaceState(_state, _title, url) {
        replacedUrl = url;
      },
    },
  };

  try {
    assert.equal(
      readOneTimeTokenFromUrl({
        get: () => null,
      }),
      "fragment-secret"
    );
    assert.equal(
      readOneTimeTokenFromUrl({
        get: (name) => (name === "token" ? "query-secret" : null),
      }),
      "query-secret"
    );

    clearOneTimeTokenFromUrl();
    assert.equal(replacedUrl, "/verify-email#source=email");
  } finally {
    if (previousWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = previousWindow;
    }
  }
});

test("email verification resend paths respect captcha-protected production UX", () => {
  const verifyPath = path.join(
    frontendRoot,
    "app",
    "(auth)",
    "verify-email",
    "verify-email-client.tsx"
  );
  const bannerPath = path.join(
    frontendRoot,
    "components",
    "layout",
    "email-verification-banner.tsx"
  );
  const verifySource = fs.readFileSync(verifyPath, "utf8");
  const bannerSource = fs.readFileSync(bannerPath, "utf8");

  assert.ok(
    verifySource.includes('state.status === "loading" || state.status === "idle"') &&
      verifySource.includes("readOneTimeTokenFromUrl(searchParams)") &&
      verifySource.includes("messages.subtitleLoading"),
    "verify page must not mount resend captcha controls while a token is being auto-verified"
  );
  assert.ok(
    bannerSource.includes("const captchaEnabled = isCaptchaEnabled();") &&
      bannerSource.includes("captchaEnabled ? null") &&
      bannerSource.includes('href={buildLocalePath(locale, "/verify-email")}'),
    "app shell banner must route captcha-protected resend through the full verify page"
  );
});
