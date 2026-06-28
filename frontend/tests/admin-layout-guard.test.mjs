import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const adminCssPath = path.join(frontendRoot, "styles", "layout-admin.css");
const adminCss = fs.readFileSync(adminCssPath, "utf8");

test("admin shell constrains narrow viewport overflow", () => {
  assert.ok(
    adminCss.includes("max-width: 100vw"),
    "admin shell must not exceed the viewport width"
  );
  assert.ok(
    adminCss.includes(".admin-shell *") && adminCss.includes("min-width: 0"),
    "admin flex children must be allowed to shrink"
  );
  assert.ok(
    adminCss.includes(".admin-topbar .cluster") &&
      adminCss.includes("flex-wrap: wrap"),
    "admin topbar actions must wrap instead of pushing the viewport"
  );
  assert.ok(
    adminCss.includes(".admin-skip-link") &&
      adminCss.includes("transform: translateY(0)"),
    "admin shell must expose a skip link for keyboard users"
  );
  assert.ok(
    adminCss.includes(".admin-nav-group") &&
      adminCss.includes("gap: var(--space-2)"),
    "admin navigation must preserve visible information-architecture groups"
  );
});

test("admin data surfaces scroll locally and keep readable cells", () => {
  assert.ok(
    adminCss.includes("scrollbar-gutter: stable"),
    "admin table wrappers should reserve stable scroll gutters"
  );
  assert.ok(
    adminCss.includes(".admin-members-table") &&
      adminCss.includes(".admin-cohort-projects-table") &&
      adminCss.includes("min-width: 720px"),
    "admin tables must keep a stable table width inside their scroll wrapper"
  );
  assert.ok(
    adminCss.includes("overflow-wrap: anywhere"),
    "admin table and identity text must wrap long names, emails, and ids"
  );
  assert.ok(
    adminCss.includes(".admin-platform-table td::before") &&
      adminCss.includes("content: attr(data-label)") &&
      adminCss.includes(".admin-platform-table thead") &&
      adminCss.includes("clip: rect(0 0 0 0)"),
    "platform settings must switch to labeled rows on mobile instead of cramped columns"
  );
});

test("admin mobile interactions keep visible focus and overlays", () => {
  assert.ok(
    adminCss.includes(":focus-visible") &&
      adminCss.includes("outline: 2px solid var(--color-primary)"),
    "clickable admin rows must expose a keyboard focus indicator"
  );
  assert.ok(
    adminCss.includes(".admin-tab") && adminCss.includes("min-height: 44px"),
    "admin tabs must keep touch target sizing"
  );
  assert.ok(
    adminCss.includes("place-items: start center") &&
      adminCss.includes(".admin-toast") &&
      adminCss.includes("left: var(--space-4)"),
    "mobile admin modals and toasts must fit the viewport"
  );
});
