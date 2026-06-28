import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const proxyModulePath = path.join(frontendRoot, "proxy.ts");
const require = createRequire(import.meta.url);

const { proxy } = loadTsModule(proxyModulePath);
const { NextRequest } = require(path.resolve(frontendRoot, "node_modules", "next", "server"));

const makeRequest = (pathname, headers = {}) =>
  new NextRequest(`http://localhost${pathname}`, { headers });

test("unprefixed user routes redirect to explicit english locale by default", () => {
  const response = proxy(makeRequest("/projects"));

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost/en/projects");
  assert.match(response.headers.get("set-cookie") ?? "", /ideasense\.locale=en/);
});

test("cookie locale is preserved when redirecting unprefixed public routes", () => {
  const response = proxy(
    makeRequest("/methodology", {
      cookie: "ideasense.locale=zh",
    })
  );

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost/zh/methodology");
  assert.match(response.headers.get("set-cookie") ?? "", /ideasense\.locale=zh/);
});

test("prefixed public routes rewrite internally without dropping locale", () => {
  const response = proxy(makeRequest("/zh/login"));

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("location"), null);
  assert.equal(
    response.headers.get("x-middleware-rewrite"),
    "http://localhost/login"
  );
  assert.match(response.headers.get("set-cookie") ?? "", /ideasense\.locale=zh/);
});

test("prefixed protected routes keep locale when redirecting to login", () => {
  const response = proxy(makeRequest("/zh/projects"));

  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "http://localhost/zh/login");
  assert.match(response.headers.get("set-cookie") ?? "", /ideasense\.locale=zh/);
});

test("prefixed protected routes allow browser-session auth cookies", () => {
  const response = proxy(
    makeRequest("/zh/projects", {
      cookie: "ideasense.auth.token=session-token; ideasense.locale=zh",
    })
  );

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("location"), null);
  assert.equal(
    response.headers.get("x-middleware-rewrite"),
    "http://localhost/projects"
  );
  assert.match(response.headers.get("set-cookie") ?? "", /ideasense\.locale=zh/);
});
