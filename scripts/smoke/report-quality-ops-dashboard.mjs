#!/usr/bin/env node

import { createWriteStream, readFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const backendRoot = path.join(repoRoot, "backend");
const frontendRoot = path.join(repoRoot, "frontend");
const requireFromFrontend = createRequire(path.join(frontendRoot, "package.json"));
const { chromium } = requireFromFrontend("playwright");

const smokeStamp = new Date().toISOString().replace(/[:.]/g, "-");
const artifactDir = path.join(
  repoRoot,
  "artifacts",
  "smoke",
  `report-quality-ops-dashboard-${smokeStamp}`
);
const orgId = "92929292-1111-4111-8111-111111111111";
const userId = "92929292-2222-4222-8222-222222222222";
const identityId = "92929292-7777-4777-8777-777777777777";
const bankId = "92929292-6666-4666-8666-666666666666";
const projectId = "92929292-3333-4333-8333-333333333333";
const reportId = "92929292-4444-4444-8444-444444444444";
const observationId = "92929292-5555-4555-8555-555555555555";
const smokeEmail = "report-quality-smoke@ideasense.local";

const devtoolsHideCss = `
  nextjs-portal,
  [data-nextjs-toast],
  [data-nextjs-dialog-overlay],
  [data-nextjs-dev-tools-button],
  [aria-label="Next.js Dev Tools"] {
    display: none !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }
`;

const seedPython = String.raw`
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json


def normalize_dsn(value: str) -> str:
    return value.replace("postgresql+psycopg2://", "postgresql://", 1)


dsn = normalize_dsn(os.environ["SMOKE_DATABASE_URL"])
migration_path = Path(os.environ["SMOKE_MIGRATION_PATH"])

org_id = os.environ["SMOKE_ORG_ID"]
user_id = os.environ["SMOKE_USER_ID"]
identity_id = os.environ["SMOKE_IDENTITY_ID"]
bank_id = os.environ["SMOKE_BANK_ID"]
project_id = os.environ["SMOKE_PROJECT_ID"]
report_id = os.environ["SMOKE_REPORT_ID"]
observation_id = os.environ["SMOKE_OBSERVATION_ID"]
email = os.environ["SMOKE_EMAIL"]

decision_snapshot = {
    "verdict": "validate_first",
    "total_score": 72,
    "confidence": "medium",
    "rationale": "The report is intentionally seeded with one missing rationale invariant for dashboard smoke.",
    "top_findings": ["Problem evidence is directionally clear."],
    "top_gaps": ["Buyer willingness to pay still needs proof."],
    "next_action": "Run two buyer interviews.",
}
score_rationales = {
    "desirability": {
        "score": 78,
        "confidence": 0.72,
        "rationale": "Repeated founder pain is visible.",
        "evidence_references": [{"path": "problem.one_line"}],
        "evidence_gaps": [],
    },
    "viability": {
        "score": 68,
        "confidence": 0.58,
        "rationale": "Buyer proof is not complete.",
        "evidence_references": [],
        "evidence_gaps": [{"path": "market_strategy.pricing"}],
    },
    "feasibility": {
        "score": 74,
        "confidence": 0.65,
        "rationale": "MVP scope is plausible.",
        "evidence_references": [{"path": "tech_execution.product_scope.mvp_definition"}],
        "evidence_gaps": [],
    },
}
evidence_index = {
    "counts": {
        "user_confirmed_inputs": 4,
        "founder_assumptions": 2,
        "ai_inferences": 1,
        "unknowns": 2,
        "evidence_gaps": 3,
        "verification_summary": 0,
    },
    "items": [
        {
            "stage": "market",
            "layer": "unknowns",
            "path": "market_strategy.pricing",
            "label": "Pricing proof",
            "source": "user",
        }
    ],
}
observation = {
    "artifact_schema_version": "assessment_quality_observation_v1",
    "source": {"source": "report-quality-ops-dashboard-smoke"},
    "report": {
        "project_id": project_id,
        "report_id": report_id,
        "report_version": 1,
        "status": "final",
        "artifact_schema_version": "report_v2",
        "scores": {
            "desirability": 78,
            "viability": 68,
            "feasibility": 74,
            "total_score": 72,
        },
        "decision_confidence": "medium",
    },
    "dimensions": {},
    "evidence": {
        "counts": evidence_index["counts"],
        "items_by_layer": {"unknowns": evidence_index["items"]},
        "promoted_paths": [],
        "total_items": 1,
    },
    "unknowns": {
        "count": 2,
        "items": evidence_index["items"],
        "top_gaps": ["Buyer willingness to pay still needs proof."],
    },
    "canonical_boundaries": {
        "within_any_score_boundary": False,
        "matched_cases": [],
        "nearest_case": {
            "id": "technical_strong_market_weak",
            "categories": ["technical_strong", "market_weak"],
            "score_distance": 6,
        },
    },
    "invariants": [
        {
            "id": "score_rationales_complete",
            "status": "fail",
            "details": {"incomplete_dimensions": ["viability"]},
        },
        {
            "id": "canonical_score_boundary",
            "status": "warn",
            "details": {"within_any_score_boundary": False},
        },
    ],
    "summary": {
        "status": "fail",
        "failed": ["score_rationales_complete"],
        "warnings": ["canonical_score_boundary"],
    },
}

with psycopg2.connect(dsn) as conn:
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.report_quality_observations')")
        if cur.fetchone()[0] is None:
            cur.execute(migration_path.read_text(encoding="utf-8"))
        else:
            cur.execute(
                "ALTER TABLE report_quality_observations "
                "ADD COLUMN IF NOT EXISTS project_title TEXT NULL"
            )

        cur.execute(
            """
            SELECT set_config('app.actor_type', 'system', false);
            SELECT set_config('app.org_id', %(org_id)s, false);
            SELECT set_config('app.user_id', %(user_id)s, false);

            INSERT INTO organizations (id, name, slug, settings)
            VALUES (
              %(org_id)s,
              'Report Quality Smoke Lab',
              'report-quality-smoke-lab',
              '{"org_type":"institution","allow_cohorts":false,"allow_mentor_assignments":false,"default_mentor_visibility":"summaries_only","allow_admin_transfer_ownership":false}'::jsonb
            )
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                settings = EXCLUDED.settings,
                deleted_at = NULL,
                updated_at = now();

            INSERT INTO users (id, email, display_name, primary_org_id, email_verified_at, is_active, deleted_at)
            VALUES (
              %(user_id)s,
              %(email)s,
              'Report Quality Smoke Admin',
              %(org_id)s,
              now(),
              true,
              NULL
            )
            ON CONFLICT (id) DO UPDATE
            SET email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                primary_org_id = EXCLUDED.primary_org_id,
                email_verified_at = COALESCE(users.email_verified_at, now()),
                is_active = true,
                deleted_at = NULL,
                updated_at = now();

            INSERT INTO user_identities (
              id, user_id, provider, provider_subject, email, password_hash,
              status, deleted_at
            )
            VALUES (
              %(identity_id)s,
              %(user_id)s,
              'local',
              NULL,
              %(email)s,
              crypt('report-quality-smoke-password', gen_salt('bf')),
              'active',
              NULL
            )
            ON CONFLICT (id) DO UPDATE
            SET user_id = EXCLUDED.user_id,
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                status = 'active',
                deleted_at = NULL,
                updated_at = now();

            INSERT INTO organization_memberships (org_id, user_id, org_role, status, created_by, deleted_at)
            VALUES (%(org_id)s, %(user_id)s, 'owner', 'active', NULL, NULL)
            ON CONFLICT (org_id, user_id) WHERE deleted_at IS NULL
            DO UPDATE SET org_role = 'owner', status = 'active', updated_at = now();

            INSERT INTO platform_admins (user_id, role, status, created_by, deleted_at)
            VALUES (%(user_id)s, 'admin', 'active', %(user_id)s, NULL)
            ON CONFLICT (user_id) WHERE deleted_at IS NULL
            DO UPDATE SET role = 'admin', status = 'active', updated_at = now();

            INSERT INTO question_bank_versions (
              id, org_id, bank_key, version, source, raw_json, is_active, deleted_at
            )
            VALUES (
              %(bank_id)s,
              %(org_id)s,
              'report-quality-smoke',
              'v1',
              'report-quality-ops-dashboard-smoke',
              '{"stages":["problem","market","tech","report"],"variants":["default"]}'::jsonb,
              false,
              NULL
            )
            ON CONFLICT (id) DO UPDATE
            SET org_id = EXCLUDED.org_id,
                bank_key = EXCLUDED.bank_key,
                version = EXCLUDED.version,
                source = EXCLUDED.source,
                raw_json = EXCLUDED.raw_json,
                is_active = false,
                deleted_at = NULL,
                updated_at = now();

            INSERT INTO projects (
              id, org_id, owner_user_id, title, description,
              question_bank_version_id, current_stage, current_variant, stage_status,
              settings, deleted_at
            )
            VALUES (
              %(project_id)s,
              %(org_id)s,
              %(user_id)s,
              'Validation Tool',
              'Seeded project for report quality dashboard smoke.',
              %(bank_id)s,
              'report',
              'default',
              'passed',
              '{}'::jsonb,
              NULL
            )
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                description = EXCLUDED.description,
                question_bank_version_id = EXCLUDED.question_bank_version_id,
                current_stage = EXCLUDED.current_stage,
                current_variant = EXCLUDED.current_variant,
                stage_status = EXCLUDED.stage_status,
                deleted_at = NULL,
                updated_at = now();

            INSERT INTO project_reports (
              id, org_id, project_id, report_version, status, content_markdown,
              content_json, diagnosis_json, validation_plan_json,
              artifact_schema_version, decision_snapshot_json,
              score_rationales_json, risk_register_json, experiment_plan_json,
              evidence_index_json, generated_from_state_version,
              generator_model, confirmed
            )
            VALUES (
              %(report_id)s,
              %(org_id)s,
              %(project_id)s,
              1,
              'final',
              'Seeded report for report quality dashboard smoke.',
              %(content_json)s,
              '{}'::jsonb,
              '[]'::jsonb,
              'report_v2',
              %(decision_snapshot)s,
              %(score_rationales)s,
              '[]'::jsonb,
              '[]'::jsonb,
              %(evidence_index)s,
              6,
              'smoke-seed',
              true
            )
            ON CONFLICT (id) DO UPDATE
            SET content_json = EXCLUDED.content_json,
                decision_snapshot_json = EXCLUDED.decision_snapshot_json,
                score_rationales_json = EXCLUDED.score_rationales_json,
                evidence_index_json = EXCLUDED.evidence_index_json,
                deleted_at = NULL,
                updated_at = now();
            """,
            {
                "org_id": org_id,
                "user_id": user_id,
                "identity_id": identity_id,
                "bank_id": bank_id,
                "email": email,
                "project_id": project_id,
                "report_id": report_id,
                "content_json": Json(
                    {
                        "artifact_schema_version": "report_v2",
                        "decision_snapshot": decision_snapshot,
                        "score_rationales": score_rationales,
                        "evidence_index": evidence_index,
                    }
                ),
                "decision_snapshot": Json(decision_snapshot),
                "score_rationales": Json(score_rationales),
                "evidence_index": Json(evidence_index),
            },
        )
        cur.execute(
            """
            INSERT INTO report_quality_observations (
              id, org_id, project_id, project_title, report_id, report_version,
              generated_from_state_version, observation_schema_version, status,
              failed_invariants_json, warning_invariants_json, score_snapshot_json,
              evidence_counts_json, canonical_boundaries_json, observation_json
            )
            VALUES (
              %(observation_id)s,
              %(org_id)s,
              %(project_id)s,
              'Validation Tool',
              %(report_id)s,
              1,
              6,
              'assessment_quality_observation_v1',
              'fail',
              %(failed_invariants)s,
              %(warning_invariants)s,
              %(score_snapshot)s,
              %(evidence_counts)s,
              %(canonical_boundaries)s,
              %(observation)s
            )
            ON CONFLICT (report_id, generated_from_state_version)
            WHERE deleted_at IS NULL
            DO UPDATE SET
              project_title = EXCLUDED.project_title,
              status = EXCLUDED.status,
              failed_invariants_json = EXCLUDED.failed_invariants_json,
              warning_invariants_json = EXCLUDED.warning_invariants_json,
              score_snapshot_json = EXCLUDED.score_snapshot_json,
              evidence_counts_json = EXCLUDED.evidence_counts_json,
              canonical_boundaries_json = EXCLUDED.canonical_boundaries_json,
              observation_json = EXCLUDED.observation_json,
              observed_at = now(),
              updated_at = now(),
              deleted_at = NULL;
            """,
            {
                "observation_id": observation_id,
                "org_id": org_id,
                "project_id": project_id,
                "report_id": report_id,
                "failed_invariants": Json(["score_rationales_complete"]),
                "warning_invariants": Json(["canonical_score_boundary"]),
                "score_snapshot": Json(observation["report"]["scores"]),
                "evidence_counts": Json(evidence_index["counts"]),
                "canonical_boundaries": Json(observation["canonical_boundaries"]),
                "observation": Json(observation),
            },
        )
    conn.commit()

print(json.dumps({"org_id": org_id, "user_id": user_id, "project_id": project_id, "report_id": report_id, "observation_id": observation_id}))
`;

function loadEnvFile(filePath) {
  if (!existsSync(filePath)) {
    return {};
  }
  const text = readFileSync(filePath, "utf8");
  const values = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) {
      continue;
    }
    const [key, ...rest] = line.split("=");
    values[key.trim()] = rest.join("=").trim().replace(/^['"]|['"]$/g, "");
  }
  return values;
}

function runSeed(databaseUrl) {
  const result = spawnSync("python3", ["-c", seedPython], {
    cwd: repoRoot,
    env: {
      ...process.env,
      SMOKE_DATABASE_URL: databaseUrl,
      SMOKE_MIGRATION_PATH: path.join(
        repoRoot,
        "database",
        "migrations",
        "059_add_report_quality_observations_20260604143000.sql"
      ),
      SMOKE_ORG_ID: orgId,
      SMOKE_USER_ID: userId,
      SMOKE_IDENTITY_ID: identityId,
      SMOKE_BANK_ID: bankId,
      SMOKE_PROJECT_ID: projectId,
      SMOKE_REPORT_ID: reportId,
      SMOKE_OBSERVATION_ID: observationId,
      SMOKE_EMAIL: smokeEmail,
    },
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
  });
  if (result.status !== 0) {
    throw new Error(
      [
        "Failed to seed report quality smoke data.",
        result.stdout,
        result.stderr,
      ]
        .filter(Boolean)
        .join("\n")
    );
  }
  return JSON.parse(result.stdout.trim());
}

function findAvailablePort(startPort) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on("error", () => {
      resolve(findAvailablePort(startPort + 1));
    });
  });
}

async function waitForHttp(url, label, timeoutMs = 120_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // Retry until timeout.
    }
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  throw new Error(`Timed out waiting for ${label}: ${url}`);
}

function spawnLogged(command, args, options) {
  const stdout = createWriteStream(options.stdoutPath, { flags: "a" });
  const stderr = createWriteStream(options.stderrPath, { flags: "a" });
  const child = spawn(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.stdout.pipe(stdout);
  child.stderr.pipe(stderr);
  return child;
}

async function assertNoPageOverflow(page, label, records) {
  const metrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  records.routeResults.push({ label, ...metrics });
  if (metrics.scrollWidth > metrics.clientWidth + 1) {
    throw new Error(
      `${label} has horizontal overflow: ${metrics.scrollWidth}px > ${metrics.clientWidth}px`
    );
  }
}

async function devLogin(apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/auth/dev-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: smokeEmail }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload?.access_token) {
    throw new Error(
      `Dev login failed: ${response.status} ${JSON.stringify(payload)}`
    );
  }
  return payload.access_token;
}

async function main() {
  await mkdir(artifactDir, { recursive: true });
  const records = {
    routeResults: [],
    screenshots: [],
    consoleEntries: [],
    networkErrors: [],
    pageErrors: [],
  };
  const backendEnv = loadEnvFile(path.join(backendRoot, ".env"));
  const databaseUrl =
    process.env.DATABASE_URL_ADMIN ||
    process.env.DATABASE_URL ||
    backendEnv.DATABASE_URL_ADMIN ||
    backendEnv.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL_ADMIN or DATABASE_URL is required for smoke.");
  }
  const seeded = runSeed(databaseUrl);
  const backendPort = await findAvailablePort(
    Number(process.env.BACKEND_PORT || "8013")
  );
  const frontendPort = await findAvailablePort(
    Number(process.env.FRONTEND_PORT || "3013")
  );
  const apiBaseUrl = `http://localhost:${backendPort}/api/v1`;
  const appBaseUrl = `http://localhost:${frontendPort}`;
  const backendLog = path.join(artifactDir, "backend.log");
  const frontendLog = path.join(artifactDir, "frontend.log");

  const backend = spawnLogged(
    process.env.PYTHON || "python3",
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(backendPort)],
    {
      cwd: backendRoot,
      stdoutPath: backendLog,
      stderrPath: backendLog,
      env: {
        ...process.env,
        APP_ENV: "development",
        ADMIN_API_ENABLED: "1",
        ADMIN_ENABLED: "1",
        DEV_AUTH_BYPASS: "0",
        DEV_LOGIN_ENABLED: "1",
        JWT_SECRET: process.env.JWT_SECRET || "report-quality-smoke-secret",
        JWT_EXPIRES_MINUTES: "120",
        DATABASE_URL: databaseUrl,
        DATABASE_URL_ADMIN: databaseUrl,
        CORS_ALLOW_ORIGINS: `${appBaseUrl},http://127.0.0.1:${frontendPort}`,
      },
    }
  );
  const frontend = spawnLogged(
    "npm",
    [
      "--prefix",
      frontendRoot,
      "run",
      "dev",
      "--",
      "--hostname",
      "localhost",
      "--port",
      String(frontendPort),
    ],
    {
      cwd: repoRoot,
      stdoutPath: frontendLog,
      stderrPath: frontendLog,
      env: {
        ...process.env,
        NEXT_PUBLIC_ADMIN_ENABLED: "1",
        NEXT_PUBLIC_API_BASE_URL: apiBaseUrl,
        NEXT_PUBLIC_ENABLE_DEV_LOGIN: "1",
      },
    }
  );

  const cleanup = () => {
    for (const child of [backend, frontend]) {
      if (!child.killed) {
        child.kill("SIGTERM");
      }
    }
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  try {
    await waitForHttp(`http://localhost:${backendPort}/health`, "backend");
    await waitForHttp(`${appBaseUrl}/en/login`, "frontend");
    const token = await devLogin(apiBaseUrl);
    const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      recordVideo: {
        dir: artifactDir,
        size: { width: 1440, height: 900 },
      },
    });
    const page = await context.newPage();
    page.on("console", (message) => {
      if (message.type() === "error") {
        records.consoleEntries.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      records.pageErrors.push(error.message);
    });
    page.on("response", (response) => {
      const status = response.status();
      if (status >= 400 && response.url().includes("/api/v1/")) {
        records.networkErrors.push({
          status,
          url: response.url(),
          method: response.request().method(),
        });
      }
    });
    await page.goto(`${appBaseUrl}/en/login`, { waitUntil: "domcontentloaded" });
    await page.addStyleTag({ content: devtoolsHideCss });
    await page.evaluate(
      ({ authToken, activeOrgId }) => {
        localStorage.setItem("ideasense.auth.token", authToken);
        sessionStorage.setItem("ideasense.org.current", activeOrgId);
        document.cookie = `ideasense.auth.token=${encodeURIComponent(authToken)}; Path=/; SameSite=Lax`;
      },
      { authToken: token, activeOrgId: orgId }
    );
    const dashboardUrl = `${appBaseUrl}/en/admin/platform/report-quality`;
    await page.goto(dashboardUrl, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: devtoolsHideCss });
    await page
      .getByRole("heading", { level: 1, name: "Report quality" })
      .waitFor({
        state: "visible",
        timeout: 30_000,
      });
    await page.getByText("Validation Tool").first().waitFor({
      state: "visible",
      timeout: 30_000,
    });
    await page.getByRole("button", { name: "Inspect" }).first().click();
    await page.getByText("score_rationales_complete").first().waitFor({
      state: "visible",
      timeout: 30_000,
    });
    await page.getByText("Canonical boundary").first().waitFor({
      state: "visible",
      timeout: 30_000,
    });
    const screenshotPath = path.join(artifactDir, "dashboard.png");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    records.screenshots.push(screenshotPath);
    await assertNoPageOverflow(page, "report-quality-desktop", records);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(dashboardUrl, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: devtoolsHideCss });
    await page
      .getByRole("heading", { level: 1, name: "Report quality" })
      .waitFor({
        state: "visible",
        timeout: 30_000,
      });
    await page.getByText("Validation Tool").first().waitFor({
      state: "visible",
      timeout: 30_000,
    });
    const mobileScreenshotPath = path.join(artifactDir, "dashboard-mobile.png");
    await page.screenshot({ path: mobileScreenshotPath, fullPage: true });
    records.screenshots.push(mobileScreenshotPath);
    await assertNoPageOverflow(page, "report-quality-mobile", records);

    const video = page.video();
    await context.close();
    await browser.close();
    const videoPath = video ? await video.path() : null;
    const summaryPath = path.join(artifactDir, "smoke-summary.json");
    await writeFile(
      summaryPath,
      JSON.stringify(
        {
          dashboardUrl,
          orgId,
          userId,
          projectId,
          reportId,
          observationId,
          seeded,
          screenshotPath,
          mobileScreenshotPath,
          routeResults: records.routeResults,
          screenshots: records.screenshots,
          videoPath,
          backendLog,
          frontendLog,
          consoleEntries: records.consoleEntries,
          pageErrors: records.pageErrors,
          networkErrors: records.networkErrors,
        },
        null,
        2
      ),
      "utf8"
    );
    if (
      records.consoleEntries.length ||
      records.pageErrors.length ||
      records.networkErrors.length
    ) {
      throw new Error(
        `Report quality smoke found runtime issues. See ${summaryPath}`
      );
    }
    console.log(
      JSON.stringify(
        {
          ok: true,
          artifactDir,
          dashboardUrl,
          screenshotPath,
          mobileScreenshotPath,
          videoPath,
          summaryPath,
        },
        null,
        2
      )
    );
  } finally {
    cleanup();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
