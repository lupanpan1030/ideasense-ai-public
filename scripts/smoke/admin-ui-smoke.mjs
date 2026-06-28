#!/usr/bin/env node

import { createWriteStream } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const frontendRoot = path.join(repoRoot, "frontend");
const requireFromFrontend = createRequire(path.join(frontendRoot, "package.json"));
const { chromium, expect } = requireFromFrontend("@playwright/test");

const smokeStamp = new Date().toISOString().replace(/[:.]/g, "-");
const artifactDir = path.join(
  repoRoot,
  "artifacts",
  "smoke",
  `admin-ui-${smokeStamp}`
);

const orgId = "admin-smoke-org";
const userId = "admin-smoke-user";
const projectId = "11111111-1111-4111-8111-111111111111";
const cohortId = "22222222-2222-4222-8222-222222222222";
const reportId = "33333333-3333-4333-8333-333333333333";
const observationId = "44444444-4444-4444-8444-444444444444";
const now = "2026-06-05T10:00:00.000Z";

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

const routes = [
  { label: "admin-overview", path: "/en/admin", heading: "Organization overview" },
  { label: "admin-org", path: "/en/admin/org", heading: "Organization settings" },
  {
    label: "admin-prompts",
    path: "/en/admin/org/prompts",
    heading: "Prompt templates",
  },
  {
    label: "admin-question-banks",
    path: "/en/admin/org/question-banks",
    heading: "Question banks",
  },
  { label: "admin-cohorts", path: "/en/admin/cohorts", heading: "Cohorts" },
  {
    label: "admin-cohort-detail",
    path: `/en/admin/cohorts/${cohortId}`,
    heading: "Spring Startup Studio",
  },
  { label: "admin-projects", path: "/en/admin/projects", heading: "Projects" },
  {
    label: "admin-project-detail",
    path: `/en/admin/projects/${projectId}`,
    heading: "Validation Tool",
  },
  { label: "admin-members", path: "/en/admin/org/members", heading: "Members" },
  { label: "admin-invites", path: "/en/admin/org/invites", heading: "Invites" },
  {
    label: "admin-mentor-assignments",
    path: "/en/admin/org/mentor-assignments",
    heading: "Mentor assignments",
  },
  { label: "admin-reports", path: "/en/admin/reports", heading: "Reports" },
  {
    label: "admin-report-quality",
    path: "/en/admin/platform/report-quality",
    heading: "Report quality",
  },
  {
    label: "admin-platform-settings",
    path: "/en/admin/platform/settings",
    heading: "Platform settings",
  },
];

const localizedRoutes = [
  {
    label: "admin-overview-zh",
    path: "/zh/admin",
    heading: "组织概览",
  },
  {
    label: "admin-question-banks-zh",
    path: "/zh/admin/org/question-banks",
    heading: "题库",
  },
  {
    label: "admin-platform-settings-zh",
    path: "/zh/admin/platform/settings",
    heading: "平台设置",
  },
];

const navChecks = [
  {
    group: "Admin home",
    label: "Overview",
    path: "/en/admin",
    heading: "Organization overview",
  },
  {
    group: "Organization",
    label: "Organization",
    path: "/en/admin/org",
    heading: "Organization settings",
  },
  {
    group: "Organization",
    label: "Members",
    path: "/en/admin/org/members",
    heading: "Members",
  },
  {
    group: "Organization",
    label: "Invites",
    path: "/en/admin/org/invites",
    heading: "Invites",
  },
  {
    group: "Assessment ops",
    label: "Cohorts",
    path: "/en/admin/cohorts",
    heading: "Cohorts",
  },
  {
    group: "Assessment ops",
    label: "Mentor assignments",
    path: "/en/admin/org/mentor-assignments",
    heading: "Mentor assignments",
  },
  {
    group: "Assessment ops",
    label: "Projects",
    path: "/en/admin/projects",
    heading: "Projects",
  },
  {
    group: "Assessment ops",
    label: "Reports",
    path: "/en/admin/reports",
    heading: "Reports",
  },
  {
    group: "Methodology",
    label: "Prompts",
    path: "/en/admin/org/prompts",
    heading: "Prompt templates",
  },
  {
    group: "Methodology",
    label: "Question banks",
    path: "/en/admin/org/question-banks",
    heading: "Question banks",
  },
  {
    group: "Platform",
    label: "Report quality",
    path: "/en/admin/platform/report-quality",
    heading: "Report quality",
  },
  {
    group: "Platform",
    label: "Platform settings",
    path: "/en/admin/platform/settings",
    heading: "Platform settings",
  },
];

const sessionPayload = {
  user: {
    id: userId,
    email: "admin-smoke@ideasense.local",
    display_name: "Admin Smoke",
  },
  org: {
    id: orgId,
    name: "IdeaSense Smoke Organization",
    settings: {
      org_type: "institution",
      allow_cohorts: true,
      allow_mentor_assignments: true,
      default_mentor_visibility: "summaries_only",
    },
  },
  membership: {
    id: "membership-owner",
    org_role: "owner",
    status: "active",
  },
  capabilities: {
    is_org_admin: true,
    can_manage_org_settings: true,
    can_manage_prompts: true,
    can_manage_members: true,
    can_manage_invites: true,
    can_manage_cohorts: true,
    can_manage_assignments: true,
    can_manage_projects: true,
    can_manage_reports: true,
    can_manage_question_bank: true,
    can_transfer_ownership: true,
  },
  orgs: [
    {
      id: orgId,
      name: "IdeaSense Smoke Organization",
      org_role: "owner",
      status: "active",
    },
    {
      id: "admin-smoke-org-2",
      name: "Second Smoke Organization",
      org_role: "admin",
      status: "active",
    },
  ],
  actor_type: "user",
  is_platform_admin: true,
};

const cohorts = [
  {
    id: cohortId,
    name: "Spring Startup Studio",
    description: "Student founder cohort with active reviews.",
    start_at: "2026-06-01T00:00:00.000Z",
    end_at: "2026-08-30T00:00:00.000Z",
    is_archived: false,
    created_at: now,
    updated_at: now,
    students_count: 12,
    mentors_count: 3,
    projects_count: 8,
  },
];

const members = [
  {
    id: "membership-owner",
    org_role: "owner",
    status: "active",
    created_at: now,
    user: {
      id: userId,
      display_name: "Admin Smoke",
      email: "admin-smoke@ideasense.local",
    },
  },
  {
    id: "membership-mentor",
    org_role: "mentor",
    status: "active",
    created_at: now,
    user: {
      id: "mentor-1",
      display_name: "Mentor Reviewer",
      email: "mentor@ideasense.local",
    },
  },
  {
    id: "membership-student",
    org_role: "student",
    status: "active",
    created_at: now,
    user: {
      id: "student-1",
      display_name: "Student Founder",
      email: "student@ideasense.local",
    },
  },
];

const projects = [
  {
    id: projectId,
    title: "Validation Tool",
    description: "AI assessment workspace for student founders.",
    current_stage: "report",
    stage_status: "passed",
    is_archived: false,
    updated_at: now,
    created_at: now,
    owner: {
      id: "student-1",
      display_name: "Student Founder",
      email: "student@ideasense.local",
    },
    cohort: {
      id: cohortId,
      name: "Spring Startup Studio",
      is_archived: false,
    },
  },
];

const reports = [
  {
    id: reportId,
    report_version: 1,
    status: "final",
    confirmed: false,
    created_at: now,
    updated_at: now,
    project: {
      id: projectId,
      title: "Validation Tool",
      current_stage: "report",
      stage_status: "passed",
      is_archived: false,
      owner: {
        id: "student-1",
        display_name: "Student Founder",
        email: "student@ideasense.local",
      },
      cohort: {
        id: cohortId,
        name: "Spring Startup Studio",
        is_archived: false,
      },
    },
  },
];

const questionBankVersion = {
  id: "question-bank-v1",
  bank_key: "default",
  version: "v1",
  source: "admin-ui-smoke",
  org_id: orgId,
  is_active: true,
  created_at: now,
  activated_at: now,
};

const questionBankDraft = {
  version: questionBankVersion,
  questions: [
    {
      question_id: "S1Q1",
      stage: "problem",
      variant: "default",
      order_index: 1,
      title: "Idea snapshot",
      type_raw: "required",
      prompt: "Describe your idea.",
      standard_question: "Describe your idea.",
      consultant_tactic: "Keep the founder focused.",
      instruction: "Ask for a concise snapshot.",
      validation_rule: "Not empty",
      schema_paths: ["problem_user.idea.raw"],
      expected_key_points: ["What it is", "What it does"],
      prompt_meta: { source: "smoke" },
      notes: "Seeded by admin UI smoke.",
    },
    {
      question_id: "S1Q2",
      stage: "problem",
      variant: "default",
      order_index: 2,
      title: "Top problems",
      type_raw: "required",
      prompt: "List up to 3 problems.",
      standard_question: "List up to 3 problems.",
      consultant_tactic: "Force ranking.",
      instruction: "Ask for the #1 problem.",
      validation_rule: "At least one problem",
      schema_paths: ["problem.main_problems"],
      expected_key_points: ["Problem list", "Priority"],
      prompt_meta: { source: "smoke" },
      notes: "Seeded by admin UI smoke.",
    },
  ],
};

const promptTemplates = [
  {
    id: "prompt-1",
    template_key: "chat.problem.followup",
    version: "v1",
    content: "Ask one focused follow-up question.",
    purpose: "chat",
    stage: "problem",
    variant: "default",
    org_id: null,
    is_active: true,
    created_at: now,
    updated_at: now,
  },
  {
    id: "prompt-2",
    template_key: "report.final.summary",
    version: "v1",
    content: "Summarize the final assessment.",
    purpose: "report",
    stage: "report",
    variant: "default",
    org_id: orgId,
    is_active: true,
    created_at: now,
    updated_at: now,
  },
];

const assignments = [
  {
    id: "assignment-1",
    status: "active",
    can_view_messages: true,
    can_view_facts: true,
    can_comment: true,
    created_at: now,
    updated_at: now,
    mentor: {
      id: "mentor-1",
      display_name: "Mentor Reviewer",
      email: "mentor@ideasense.local",
    },
    student: {
      id: "student-1",
      display_name: "Student Founder",
      email: "student@ideasense.local",
    },
    cohort: {
      id: cohortId,
      name: "Spring Startup Studio",
    },
  },
];

const platformSettings = {
  settings: {
    report_quality_dashboard: true,
    admin_ui_smoke: "enabled",
  },
  entries: [
    {
      key: "report_quality_dashboard",
      value: true,
      updated_by: userId,
      updated_by_email: "admin-smoke@ideasense.local",
      updated_by_name: "Admin Smoke",
      created_at: now,
      updated_at: now,
    },
    {
      key: "admin_ui_smoke",
      value: "enabled",
      updated_by: userId,
      updated_by_email: "admin-smoke@ideasense.local",
      updated_by_name: "Admin Smoke",
      created_at: now,
      updated_at: now,
    },
  ],
};

const reportQualityObservation = {
  id: observationId,
  org_id: orgId,
  org_name: "IdeaSense Smoke Organization",
  org_slug: "ideasense-smoke",
  project_id: projectId,
  project_title: "Validation Tool",
  report_id: reportId,
  report_version: 1,
  generated_from_state_version: 6,
  observation_schema_version: "assessment_quality_observation_v1",
  status: "warn",
  failed_invariants: [],
  warning_invariants: ["canonical_score_boundary"],
  score_snapshot: {
    desirability: 78,
    viability: 68,
    feasibility: 74,
    total_score: 72,
  },
  evidence_counts: {
    unknowns: 2,
    evidence_gaps: 3,
  },
  canonical_boundaries: {
    within_any_score_boundary: false,
    nearest_case: { id: "technical_strong_market_weak" },
  },
  observation: {
    evidence: {
      counts: {
        unknowns: 2,
        evidence_gaps: 3,
      },
    },
    unknowns: {
      top_gaps: ["Buyer willingness to pay still needs proof."],
      items: ["Pricing proof"],
    },
    canonical_boundaries: {
      within_any_score_boundary: false,
      nearest_case: { id: "technical_strong_market_weak" },
    },
  },
  observed_at: now,
  created_at: now,
  updated_at: now,
};

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

function apiJson(route, payload, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function listResponse(items, page = 1, limit = 20, key = "items") {
  return {
    [key]: items,
    total: items.length,
    page,
    limit,
  };
}

async function installApiMocks(page, records, session = sessionPayload) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const pathname = url.pathname.replace(/^\/api\/v1/, "");

    if (method === "OPTIONS") {
      await route.fulfill({ status: 204 });
      return;
    }

    if (pathname === "/session" && method === "GET") {
      await apiJson(route, session);
      return;
    }

    if (pathname === "/admin-api/overview" && method === "GET") {
      await apiJson(route, {
        overview_metrics: [
          {
            label: "Active projects",
            value: "8",
            delta: "+2",
            tone: "primary",
            series: [4, 5, 6, 8],
          },
          {
            label: "Reports ready",
            value: "3",
            delta: "+1",
            tone: "success",
            series: [1, 2, 2, 3],
          },
        ],
        enrollment_trend: {
          label: "Enrollment trend",
          sublabel: "Last 30 days",
          total: "12",
          change: "+3",
          tone: "success",
          series: [2, 3, 4, 8, 12],
        },
        cohort_progress: [
          {
            id: cohortId,
            name: "Spring Startup Studio",
            progress: 62,
            meta: "8 projects",
          },
        ],
        pending_actions: [
          {
            title: "Review final reports",
            detail: "3 reports need confirmation.",
            tone: "warning",
          },
        ],
        upcoming_deadlines: [
          {
            title: "Mentor review window",
            due_at: "2026-06-20T10:00:00.000Z",
          },
        ],
        activity_feed: [
          {
            title: "Report confirmed",
            detail: "Validation Tool",
            created_at: now,
          },
        ],
        insight_highlights: [
          {
            title: "Evidence gaps",
            detail: "Pricing proof is still weak.",
          },
        ],
      });
      return;
    }

    if (pathname === "/admin-api/org/settings") {
      if (method === "PATCH") {
        await apiJson(route, { settings: sessionPayload.org.settings });
        return;
      }
      await apiJson(route, { settings: sessionPayload.org.settings });
      return;
    }

    if (pathname === "/admin-api/org/question-bank") {
      await apiJson(route, {
        bank_key: "default",
        version: "v1",
        source: "admin-ui-smoke",
        activated_at: now,
        created_at: now,
      });
      return;
    }

    if (pathname === "/admin-api/prompts" && method === "GET") {
      await apiJson(route, { templates: promptTemplates });
      return;
    }

    if (/^\/admin-api\/prompts\/[^/]+\/revert$/.test(pathname)) {
      await apiJson(route, {
        reverted: true,
        effective_template: promptTemplates[0],
      });
      return;
    }

    if (/^\/admin-api\/prompts\/[^/]+$/.test(pathname)) {
      await apiJson(route, promptTemplates[1]);
      return;
    }

    if (/^\/admin-api\/question-banks\/default\/active\/details$/.test(pathname)) {
      await apiJson(route, questionBankDraft);
      return;
    }

    if (/^\/admin-api\/question-banks\/default\/draft/.test(pathname)) {
      await apiJson(route, questionBankDraft);
      return;
    }

    if (pathname === "/admin-api/cohorts" && method === "POST") {
      const next = {
        ...cohorts[0],
        id: "cohort-created",
        name: "Created Smoke Cohort",
      };
      await apiJson(route, next);
      return;
    }

    if (pathname === "/admin-api/cohorts" && method === "GET") {
      await apiJson(route, listResponse(cohorts, 1, 20, "cohorts"));
      return;
    }

    if (pathname === `/admin-api/cohorts/${cohortId}` && method === "PATCH") {
      await apiJson(route, { ...cohorts[0], is_archived: true });
      return;
    }

    if (pathname === `/admin-api/cohorts/${cohortId}` && method === "GET") {
      const tab = url.searchParams.get("tab");
      if (tab === "projects") {
        await apiJson(route, {
          cohort: cohorts[0],
          list_type: "projects",
          items: projects,
          total: projects.length,
          page: 1,
          limit: 20,
        });
        return;
      }
      await apiJson(route, {
        cohort: cohorts[0],
        list_type: tab === "mentors" ? "mentors" : "members",
        items: [
          {
            membership_id: "membership-student",
            user_id: "student-1",
            display_name: "Student Founder",
            email: "student@ideasense.local",
            role_in_cohort: "student",
            status: "active",
            joined_at: now,
          },
          {
            membership_id: "membership-mentor",
            user_id: "mentor-1",
            display_name: "Mentor Reviewer",
            email: "mentor@ideasense.local",
            role_in_cohort: "mentor",
            status: "active",
            joined_at: now,
          },
        ],
        total: 2,
        page: 1,
        limit: 20,
      });
      return;
    }

    if (pathname === "/admin-api/projects" && method === "GET") {
      await apiJson(route, listResponse(projects, 1, 20, "projects"));
      return;
    }

    if (pathname === `/admin-api/projects/${projectId}`) {
      await apiJson(route, projects[0]);
      return;
    }

    if (pathname === `/admin-api/projects/${projectId}/reports`) {
      await apiJson(route, {
        reports: [
          {
            id: reportId,
            report_version: 1,
            status: "final",
            created_at: now,
            updated_at: now,
            confirmed: false,
            content_markdown: "Seeded final report.",
          },
        ],
      });
      return;
    }

    if (pathname === `/admin-api/projects/${projectId}/comments`) {
      if (method === "POST") {
        await apiJson(route, {
          id: "comment-created",
          content: "Smoke comment",
          visibility: "admin",
          created_at: now,
          author: members[0].user,
        });
        return;
      }
      await apiJson(route, {
        comments: [
          {
            id: "comment-1",
            content: "Review pricing evidence before final approval.",
            visibility: "admin",
            created_at: now,
            author: members[1].user,
          },
        ],
        total: 1,
        page: 1,
        limit: 20,
      });
      return;
    }

    if (new RegExp(`^/admin-api/projects/${projectId}/comments/[^/]+$`).test(pathname)) {
      await apiJson(route, null, 204);
      return;
    }

    if (pathname === "/admin-api/org/members" && method === "GET") {
      await apiJson(route, {
        members,
        total: members.length,
        limit: 20,
        offset: 0,
      });
      return;
    }

    if (/^\/admin-api\/org\/members\/[^/]+$/.test(pathname)) {
      await apiJson(route, { ...members[1], org_role: "admin" });
      return;
    }

    if (pathname === "/admin-api/org/invites" && method === "GET") {
      await apiJson(route, {
        invites: [
          {
            id: "invite-1",
            invitee_email: "pending@ideasense.local",
            invited_role: "student",
            status: "pending",
            token: "redacted-smoke-token",
            invite_link: "http://localhost/join?token=redacted-smoke-token",
            expires_at: "2026-06-20T10:00:00.000Z",
            created_at: now,
          },
        ],
        total: 1,
        page: 1,
        limit: 20,
      });
      return;
    }

    if (pathname === "/admin-api/org/invites" && method === "POST") {
      await apiJson(route, {
        status: "created",
        invite_link: "http://localhost/join?token=redacted-smoke-token",
        token: "redacted-smoke-token",
        user: null,
      });
      return;
    }

    if (/^\/admin-api\/org\/invites\/[^/]+$/.test(pathname)) {
      await apiJson(route, {
        id: "invite-1",
        invitee_email: "pending@ideasense.local",
        invited_role: "student",
        status: "revoked",
        token: "redacted-smoke-token",
        invite_link: "http://localhost/join?token=redacted-smoke-token",
        expires_at: "2026-06-20T10:00:00.000Z",
        created_at: now,
      });
      return;
    }

    if (pathname === "/admin-api/mentor-assignments" && method === "GET") {
      await apiJson(route, listResponse(assignments, 1, 20, "assignments"));
      return;
    }

    if (pathname === "/admin-api/mentor-assignments" && method === "POST") {
      await apiJson(route, assignments[0]);
      return;
    }

    if (/^\/admin-api\/mentor-assignments\/[^/]+$/.test(pathname)) {
      await apiJson(route, { ...assignments[0], status: "revoked" });
      return;
    }

    if (pathname === "/admin-api/reports" && method === "GET") {
      await apiJson(route, listResponse(reports, 1, 20, "reports"));
      return;
    }

    if (pathname === "/admin-api/reports/batch") {
      await apiJson(route, { updated_count: 1 });
      return;
    }

    if (/^\/admin-api\/reports\/[^/]+$/.test(pathname)) {
      await apiJson(route, { ...reports[0], confirmed: true });
      return;
    }

    if (pathname === "/admin-api/reports/export") {
      await route.fulfill({
        status: 200,
        contentType: "text/csv",
        headers: {
          "content-disposition": "attachment; filename=\"reports_export.csv\"",
        },
        body: `report_id,project_title,status\n${reportId},Validation Tool,final\n`,
      });
      return;
    }

    if (pathname === "/platform-api/settings") {
      await apiJson(route, platformSettings);
      return;
    }

    if (pathname === "/platform-api/report-quality/summary") {
      await apiJson(route, {
        total: 1,
        status_counts: [{ status: "warn", count: 1 }],
        invariant_counts: [
          {
            invariant_id: "canonical_score_boundary",
            severity: "warn",
            count: 1,
          },
        ],
      });
      return;
    }

    if (pathname === "/platform-api/report-quality/observations") {
      await apiJson(route, {
        observations: [reportQualityObservation],
        total: 1,
        limit: 20,
        offset: 0,
      });
      return;
    }

    if (pathname === `/platform-api/report-quality/observations/${observationId}`) {
      await apiJson(route, reportQualityObservation);
      return;
    }

    records.unhandled.push({ method, pathname });
    await apiJson(route, { detail: `Unhandled smoke API route: ${pathname}` }, 500);
  });
}

async function assertNoPageOverflow(page, label, records) {
  const metrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  records.routeResults.push({ label, ...metrics });
  expect(metrics.scrollWidth, `${label} horizontal overflow`).toBeLessThanOrEqual(
    metrics.clientWidth + 1
  );
}

async function gotoAndAssert(page, appBaseUrl, route, viewportName, records) {
  await page.goto(`${appBaseUrl}${route.path}`, { waitUntil: "domcontentloaded" });
  await page.addStyleTag({ content: devtoolsHideCss }).catch(() => {});
  await page.getByRole("heading", { level: 1 }).first().waitFor({
    state: "visible",
    timeout: 30_000,
  });
  await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
  await assertNoPageOverflow(page, `${route.label}-${viewportName}`, records);
  const screenshotPath = path.join(artifactDir, `${route.label}-${viewportName}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  records.screenshots.push(screenshotPath);
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const navLinkName = (label) => new RegExp(`^${escapeRegExp(label)}\\b`);

async function expectPathname(page, expectedPathname) {
  await page.waitForFunction(
    (pathname) => window.location.pathname === pathname,
    expectedPathname,
    { timeout: 10_000 }
  );
  const current = new URL(page.url());
  expect(current.pathname).toBe(expectedPathname);
}

async function exerciseAdminNavigation(page, appBaseUrl, records) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${appBaseUrl}/en/admin`, { waitUntil: "domcontentloaded" });
  await page.addStyleTag({ content: devtoolsHideCss }).catch(() => {});
  await expect(
    page.getByRole("link", { name: "Skip to admin content" })
  ).toHaveAttribute("href", "#admin-main-content");

  for (const group of ["Admin home", "Organization", "Assessment ops", "Methodology", "Platform"]) {
    await expect(
      page
        .locator(".admin-nav-group .sidebar-label")
        .filter({ hasText: new RegExp(`^${escapeRegExp(group)}$`) })
    ).toHaveCount(1);
  }

  for (const item of navChecks) {
    const nav = page.getByRole("navigation", {
      name: `Admin navigation: ${item.group}`,
    });
    await expect(nav).toBeVisible();
    const link = nav.getByRole("link", { name: navLinkName(item.label) });
    await expect(link).toBeVisible();
    await link.click();
    await page.addStyleTag({ content: devtoolsHideCss }).catch(() => {});
    await expectPathname(page, item.path);
    await expect(
      page.getByRole("heading", { level: 1, name: item.heading })
    ).toBeVisible();
    await expect(link).toHaveAttribute("aria-current", "page");
    records.navigationChecks.push({
      group: item.group,
      label: item.label,
      path: item.path,
    });
  }
}

async function exerciseRestrictedNavigation(page, appBaseUrl, records) {
  const restrictedSession = {
    ...sessionPayload,
    capabilities: {
      ...sessionPayload.capabilities,
      can_manage_prompts: false,
      can_manage_invites: false,
      can_manage_assignments: false,
      can_manage_reports: false,
      can_manage_question_bank: false,
    },
    is_platform_admin: false,
  };

  await page.unroute("**/api/v1/**");
  await installApiMocks(page, records, restrictedSession);
  await page.goto(`${appBaseUrl}/en/admin`, { waitUntil: "domcontentloaded" });
  await page.addStyleTag({ content: devtoolsHideCss }).catch(() => {});
  await expect(
    page.getByRole("heading", { level: 1, name: "Organization overview" })
  ).toBeVisible();

  for (const hiddenLabel of [
    "Prompts",
    "Question banks",
    "Invites",
    "Mentor assignments",
    "Reports",
    "Report quality",
    "Platform settings",
  ]) {
    await expect(
      page.getByRole("link", { name: navLinkName(hiddenLabel) })
    ).toHaveCount(0);
  }

  for (const hiddenGroup of ["Methodology", "Platform"]) {
    await expect(
      page
        .locator(".admin-nav-group .sidebar-label")
        .filter({ hasText: new RegExp(`^${escapeRegExp(hiddenGroup)}$`) })
    ).toHaveCount(0);
  }
  await expect(
    page.getByRole("link", { name: navLinkName("Members") })
  ).toBeVisible();

  for (const deniedPath of [
    "/en/admin/org/prompts",
    "/en/admin/org/invites",
    "/en/admin/reports",
    "/en/admin/platform/settings",
  ]) {
    await page.goto(`${appBaseUrl}${deniedPath}`, {
      waitUntil: "domcontentloaded",
    });
    await page.addStyleTag({ content: devtoolsHideCss }).catch(() => {});
    await expect(
      page.getByRole("heading", { level: 3, name: "403 - Access denied" })
    ).toBeVisible();
    records.restrictedChecks.push(deniedPath);
  }
}

async function exerciseReports(page, appBaseUrl, records) {
  await page.goto(`${appBaseUrl}/en/admin/reports`, { waitUntil: "domcontentloaded" });
  await page.locator("tbody input[type='checkbox']").first().check();
  await page.getByRole("button", { name: "Confirm selected", exact: true }).click();
  await expect(page.getByText("Confirmed 1 report(s).")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  const download = await downloadPromise;
  const downloadPath = path.join(artifactDir, await download.suggestedFilename());
  await download.saveAs(downloadPath);
  records.downloads.push(downloadPath);
}

async function exerciseInvites(page, appBaseUrl) {
  await page.goto(`${appBaseUrl}/en/admin/org/invites`, {
    waitUntil: "domcontentloaded",
  });
  await page.getByRole("button", { name: "Create invite" }).click();
  await page.getByLabel("Invitee email").fill("new-student@ideasense.local");
  await page.getByRole("button", { name: "Create invite" }).last().click();
  await expect(page.getByText("Invite link")).toBeVisible();
}

async function exerciseCohorts(page, appBaseUrl) {
  await page.goto(`${appBaseUrl}/en/admin/cohorts`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "New cohort" }).click();
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByText("Cohort name is required.")).toBeVisible();
  await page.getByLabel("Name").fill("Created Smoke Cohort");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByText("Cohort created")).toBeVisible();
}

async function exercisePrompts(page, appBaseUrl) {
  await page.goto(`${appBaseUrl}/en/admin/org/prompts`, {
    waitUntil: "domcontentloaded",
  });
  await page.getByLabel("Search").fill("no-template-matches-this-query");
  await expect(page.getByText("No prompt templates match the current filters.")).toBeVisible();
}

async function exerciseQuestionBanks(page, appBaseUrl) {
  await page.goto(`${appBaseUrl}/en/admin/org/question-banks`, {
    waitUntil: "domcontentloaded",
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Edit draft" }).click();
  await expect(page.getByText("Editing", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Import" }).click();
  await expect(page.getByLabel("Import payload")).toBeVisible();
  await page.getByRole("button", { name: "Reorder" }).click();
  await expect(page.getByLabel("Question id order")).toBeVisible();
}

async function main() {
  await mkdir(artifactDir, { recursive: true });
  const records = {
    routeResults: [],
    screenshots: [],
    downloads: [],
    navigationChecks: [],
    restrictedChecks: [],
    consoleEntries: [],
    networkErrors: [],
    pageErrors: [],
    unhandled: [],
  };

  const providedBaseUrl = process.env.SMOKE_APP_BASE_URL;
  const frontendPort = providedBaseUrl
    ? null
    : await findAvailablePort(Number(process.env.FRONTEND_PORT || "3023"));
  const appBaseUrl = providedBaseUrl || `http://localhost:${frontendPort}`;
  const frontendLog = path.join(artifactDir, "frontend.log");
  let frontend = null;

  if (!providedBaseUrl) {
    frontend = spawnLogged(
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
          NEXT_PUBLIC_API_BASE_URL: "",
          NEXT_PUBLIC_ENABLE_DEV_LOGIN: "1",
        },
      }
    );
  }

  const cleanup = () => {
    if (frontend && !frontend.killed) {
      frontend.kill("SIGTERM");
    }
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  try {
    await waitForHttp(`${appBaseUrl}/en/login`, "frontend");
    const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
    const context = await browser.newContext({
      acceptDownloads: true,
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
    await installApiMocks(page, records);
    await page.addInitScript(
      ({ token, activeOrgId }) => {
        window.localStorage.setItem("ideasense.auth.token", token);
        window.sessionStorage.setItem("ideasense.org.current", activeOrgId);
        document.cookie = `ideasense.auth.token=${encodeURIComponent(token)}; Path=/; SameSite=Lax`;
      },
      { token: "admin-ui-smoke-token", activeOrgId: orgId }
    );

    await page.setViewportSize({ width: 1440, height: 900 });
    await exerciseAdminNavigation(page, appBaseUrl, records);

    for (const route of routes) {
      await gotoAndAssert(page, appBaseUrl, route, "desktop", records);
    }

    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of routes) {
      await gotoAndAssert(page, appBaseUrl, route, "mobile", records);
    }

    for (const route of localizedRoutes) {
      await gotoAndAssert(page, appBaseUrl, route, "mobile", records);
    }

    await page.setViewportSize({ width: 1440, height: 900 });
    await exerciseReports(page, appBaseUrl, records);
    await exerciseInvites(page, appBaseUrl);
    await exerciseCohorts(page, appBaseUrl);
    await exercisePrompts(page, appBaseUrl);
    await exerciseQuestionBanks(page, appBaseUrl);
    await exerciseRestrictedNavigation(page, appBaseUrl, records);

    const video = page.video();
    await context.close();
    await browser.close();
    const videoPath = video ? await video.path() : null;
    const summaryPath = path.join(artifactDir, "smoke-summary.json");
    await writeFile(
      summaryPath,
      JSON.stringify(
        {
          ok: true,
          artifactDir,
          appBaseUrl,
          routeCount: routes.length,
          desktopMobileCombinations: routes.length * 2,
          localizedRouteCount: localizedRoutes.length,
          navigationCheckCount: records.navigationChecks.length,
          restrictedCheckCount: records.restrictedChecks.length,
          routeResults: records.routeResults,
          screenshots: records.screenshots,
          downloads: records.downloads,
          navigationChecks: records.navigationChecks,
          restrictedChecks: records.restrictedChecks,
          videoPath,
          frontendLog,
          consoleEntries: records.consoleEntries,
          pageErrors: records.pageErrors,
          networkErrors: records.networkErrors,
          unhandled: records.unhandled,
        },
        null,
        2
      ),
      "utf8"
    );

    if (
      records.consoleEntries.length ||
      records.pageErrors.length ||
      records.networkErrors.length ||
      records.unhandled.length
    ) {
      throw new Error(
        `Admin UI smoke found runtime issues. See ${summaryPath}`
      );
    }

    console.log(
      JSON.stringify(
        {
          ok: true,
          artifactDir,
          appBaseUrl,
          summaryPath,
          videoPath,
          routeCount: routes.length,
          desktopMobileCombinations: routes.length * 2,
          localizedRouteCount: localizedRoutes.length,
          navigationCheckCount: records.navigationChecks.length,
          restrictedCheckCount: records.restrictedChecks.length,
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
