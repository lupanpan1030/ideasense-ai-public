import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const configModulePath = path.join(frontendRoot, "lib", "i18n", "config.ts");

const {
  buildLocalePath,
  extractLocaleFromPathname,
  normalizeAppLocale,
  stripLocalePrefix,
} = loadTsModule(configModulePath);

test("locale config extracts and strips locale prefixes", () => {
  assert.equal(extractLocaleFromPathname("/en/projects"), "en");
  assert.equal(extractLocaleFromPathname("/zh/projects/123"), "zh");
  assert.equal(extractLocaleFromPathname("/projects"), null);

  assert.equal(stripLocalePrefix("/en/projects"), "/projects");
  assert.equal(stripLocalePrefix("/zh"), "/");
  assert.equal(stripLocalePrefix("/projects"), "/projects");
});

test("locale config builds explicit locale paths", () => {
  assert.equal(buildLocalePath("en", "/projects", ""), "/en/projects");
  assert.equal(buildLocalePath("zh", "/projects/abc", "tab=report"), "/zh/projects/abc?tab=report");
  assert.equal(buildLocalePath("zh", "/en/settings", "?section=profile"), "/zh/settings?section=profile");
});

test("normalizeAppLocale falls back to english", () => {
  assert.equal(normalizeAppLocale("zh"), "zh");
  assert.equal(normalizeAppLocale("en"), "en");
  assert.equal(normalizeAppLocale("fr"), "en");
  assert.equal(normalizeAppLocale(undefined), "en");
});
