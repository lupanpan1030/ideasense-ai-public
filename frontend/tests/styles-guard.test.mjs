import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");

const requiredCssFiles = [
  path.join(frontendRoot, "styles", "base.css"),
  path.join(frontendRoot, "styles", "utilities.css"),
  path.join(frontendRoot, "styles", "primitives.css"),
  path.join(frontendRoot, "styles", "layout.css"),
];

test("split css files exist", () => {
  for (const filePath of requiredCssFiles) {
    assert.ok(fs.existsSync(filePath), `Missing ${filePath}`);
  }
});

test("globals.css import order is stable", () => {
  const globalsPath = path.join(frontendRoot, "app", "globals.css");
  const globals = fs.readFileSync(globalsPath, "utf8");
  const importOrder = [
    '@import "tailwindcss";',
    '@import "../styles/tokens.css";',
    '@import "../styles/base.css";',
    '@import "../styles/utilities.css";',
    '@import "../styles/primitives.css";',
    '@import "../styles/layout.css";',
  ];

  let lastIndex = -1;
  for (const statement of importOrder) {
    const index = globals.indexOf(statement);
    assert.ok(index !== -1, `globals.css missing ${statement}`);
    assert.ok(
      index > lastIndex,
      `globals.css import order is incorrect for ${statement}`
    );
    lastIndex = index;
  }
});

test("layout.css includes split-view grid classes", () => {
  const layoutPath = path.join(frontendRoot, "styles", "layout-workspace.css");
  const layout = fs.readFileSync(layoutPath, "utf8");
  const requiredMarkers = [
    ".split-view",
    ".split-view__left",
    ".split-view__center",
    ".split-view__right",
  ];

  for (const marker of requiredMarkers) {
    assert.ok(layout.includes(marker), `layout.css missing ${marker}`);
  }
});
