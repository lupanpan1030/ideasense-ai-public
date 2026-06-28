import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadTsModule } from "./helpers/load-ts-module.mjs";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const exportModulePath = path.join(
  frontendRoot,
  "features",
  "reports",
  "report-export.ts"
);

const { exportJson, exportMarkdown, buildReportFilename } =
  loadTsModule(exportModulePath);

test("report exports create blob downloads with expected metadata", () => {
  let seenBlob = null;
  let revokedUrl = null;
  let anchor = null;

  const deps = {
    createObjectUrl: (blob) => {
      seenBlob = blob;
      return "blob:report";
    },
    revokeObjectUrl: (url) => {
      revokedUrl = url;
    },
    createAnchor: () => {
      anchor = {
        href: "",
        download: "",
        click: () => {
          anchor.clicked = true;
        },
        remove: () => {
          anchor.removed = true;
        },
      };
      return anchor;
    },
  };

  const filename = buildReportFilename(
    "project-1",
    "json",
    new Date("2024-01-02T12:00:00Z")
  );
  exportJson({ hello: "world" }, filename, deps);

  assert.equal(filename, "ideasense-report_project-1_2024-01-02.json");
  assert.equal(seenBlob.type, "application/json");
  assert.equal(anchor.download, filename);
  assert.equal(anchor.href, "blob:report");
  assert.equal(anchor.clicked, true);
  assert.equal(anchor.removed, true);
  assert.equal(revokedUrl, "blob:report");

  exportMarkdown("# Report", "ideasense-report.md", deps);
  assert.equal(seenBlob.type, "text/markdown");
  assert.equal(anchor.download, "ideasense-report.md");
});
