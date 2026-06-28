import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const repoRoot = path.resolve(frontendRoot, "..");

const requiredDirectories = [
  path.join(frontendRoot, "app"),
  path.join(frontendRoot, "app", "(app)"),
  path.join(frontendRoot, "app", "(auth)"),
  path.join(frontendRoot, "components"),
  path.join(frontendRoot, "components", "layout"),
  path.join(frontendRoot, "components", "ui"),
  path.join(frontendRoot, "styles"),
  path.join(frontendRoot, "public"),
  path.join(frontendRoot, "tests"),
];

const requiredFiles = [
  path.join(frontendRoot, "app", "layout.tsx"),
  path.join(frontendRoot, "app", "(marketing)", "page.tsx"),
  path.join(frontendRoot, "app", "(auth)", "login", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "layout.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "[projectId]", "chat", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "[projectId]", "report", "page.tsx"),
  path.join(frontendRoot, "components", "layout", "app-shell.tsx"),
  path.join(frontendRoot, "styles", "tokens.css"),
  path.join(repoRoot, "docs", "FRONTEND_DESIGN_CONTRACT.md"),
];

const assertDirectory = (dirPath) => {
  assert.ok(fs.existsSync(dirPath), `Missing directory ${dirPath}`);
  assert.ok(fs.statSync(dirPath).isDirectory(), `Not a directory ${dirPath}`);
};

const assertFile = (filePath) => {
  assert.ok(fs.existsSync(filePath), `Missing file ${filePath}`);
  assert.ok(fs.statSync(filePath).isFile(), `Not a file ${filePath}`);
};

test("phase 1 directories exist", () => {
  for (const dirPath of requiredDirectories) {
    assertDirectory(dirPath);
  }
});

test("phase 1 files exist", () => {
  for (const filePath of requiredFiles) {
    assertFile(filePath);
  }
});
