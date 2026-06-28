import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDir, "..");
const repoRoot = path.resolve(frontendRoot, "..");

const requiredFiles = [
  path.join(repoRoot, "docs", "FRONTEND_DESIGN_CONTRACT.md"),
  path.join(frontendRoot, "styles", "tokens.css"),
  path.join(frontendRoot, "app", "globals.css"),
  path.join(frontendRoot, "components", "ui", "button.tsx"),
  path.join(frontendRoot, "components", "ui", "input.tsx"),
  path.join(frontendRoot, "components", "ui", "card.tsx"),
  path.join(frontendRoot, "components", "ui", "badge.tsx"),
  path.join(frontendRoot, "components", "ui", "separator.tsx"),
  path.join(frontendRoot, "components", "ui", "skeleton.tsx"),
  path.join(frontendRoot, "components", "layout", "app-shell.tsx"),
  path.join(frontendRoot, "app", "(auth)", "login", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "layout.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "[projectId]", "chat", "page.tsx"),
  path.join(frontendRoot, "app", "(app)", "projects", "[projectId]", "report", "page.tsx"),
];

test("required design system files exist", () => {
  for (const filePath of requiredFiles) {
    assert.ok(fs.existsSync(filePath), `Missing ${filePath}`);
  }
});

test("globals imports tokens and tokens define core palette", () => {
  const globalsPath = path.join(frontendRoot, "app", "globals.css");
  const tokensPath = path.join(frontendRoot, "styles", "tokens.css");

  const globals = fs.readFileSync(globalsPath, "utf8");
  assert.ok(
    globals.includes('@import "../styles/tokens.css";'),
    "globals.css must import tokens.css"
  );

  const tokens = fs.readFileSync(tokensPath, "utf8");
  const requiredTokens = [
    "--font-sans:",
    "--color-primary:",
    "--color-cta:",
    "--color-bg:",
    "--color-border:",
    "--space-4:",
    "--radius-md:",
    "--shadow-sm:",
  ];

  for (const token of requiredTokens) {
    assert.ok(tokens.includes(token), `Missing token ${token}`);
  }

  assert.ok(
    tokens.includes(":root.dark") && tokens.includes("data-theme=\"dark\""),
    "tokens.css must include dark theme overrides"
  );
});

test("layout avoids external font hosts", () => {
  const layoutPath = path.join(frontendRoot, "app", "layout.tsx");
  const layoutContent = fs.readFileSync(layoutPath, "utf8");

  assert.ok(
    !layoutContent.includes("next/font/google"),
    "layout.tsx should not import external fonts"
  );
  assert.ok(
    !layoutContent.includes("fonts.googleapis.com"),
    "external font hosts are not allowed"
  );
});

test("mobile app surfaces keep safe touch targets and text wrapping", () => {
  const shellCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-shell.css"),
    "utf8"
  );
  const modalCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-modals.css"),
    "utf8"
  );
  const projectsCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-projects.css"),
    "utf8"
  );
  const chatCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-chat.css"),
    "utf8"
  );
  const reportsCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-reports.css"),
    "utf8"
  );
  const workspaceCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-workspace.css"),
    "utf8"
  );
  const adminCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-admin.css"),
    "utf8"
  );
  const baseCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-base.css"),
    "utf8"
  );
  const sidebarCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-sidebar.css"),
    "utf8"
  );
  const workflowCardCss = fs.readFileSync(
    path.join(frontendRoot, "styles", "layout-workflow-card.css"),
    "utf8"
  );
  const homePage = fs.readFileSync(
    path.join(frontendRoot, "components", "marketing", "HomePage.tsx"),
    "utf8"
  );
  const homePageSectionShell = fs.readFileSync(
    path.join(frontendRoot, "components", "marketing", "HomePageSectionShell.tsx"),
    "utf8"
  );
  const methodologyPage = fs.readFileSync(
    path.join(frontendRoot, "components", "marketing", "MethodologyPageView.tsx"),
    "utf8"
  );
  const methodologyPageUtils = fs.readFileSync(
    path.join(frontendRoot, "components", "marketing", "methodology-page-utils.tsx"),
    "utf8"
  );
  const methodologySections = [
    "MethodologyIntroSections.tsx",
    "MethodologyOutputSections.tsx",
    "MethodologyReviewSection.tsx",
  ]
    .map((fileName) =>
      fs.readFileSync(
        path.join(frontendRoot, "components", "marketing", fileName),
        "utf8"
      )
    )
    .join("\n");
  const languageSwitcher = fs.readFileSync(
    path.join(frontendRoot, "components", "layout", "language-switcher.tsx"),
    "utf8"
  );

  assert.ok(
    modalCss.includes("z-index: 100"),
    "modals must sit above the mobile sidebar toggle"
  );
  assert.ok(
    shellCss.includes("width: 44px") &&
      shellCss.includes(".app-shell__topbar .btn") &&
      shellCss.includes(".app-shell__main") &&
      shellCss.includes("color-mix(in srgb, var(--color-bg) 82%, var(--color-surface) 18%)") &&
      shellCss.includes(".app-shell__main--sample-root") &&
      shellCss.includes("min-height: 44px"),
    "mobile shell controls and backgrounds must stay consistent"
  );
  assert.ok(
    projectsCss.includes(".project-actions__summary") &&
      projectsCss.includes("height: 44px") &&
      projectsCss.includes(".projects-tab") &&
      projectsCss.includes("min-height: 44px"),
    "project cards and filters must keep 44px mobile touch targets"
  );
  assert.ok(
    chatCss.includes(".message-content") &&
      chatCss.includes("overflow-wrap: anywhere"),
    "chat messages must wrap long tokens and URLs"
  );
  assert.ok(
    reportsCss.includes(".report-details pre") &&
      reportsCss.includes("white-space: pre-wrap") &&
      reportsCss.includes(".markdown-preview") &&
      reportsCss.includes("overflow-wrap: anywhere"),
    "report markdown and source blocks must wrap or scroll long content"
  );
  assert.ok(
    workspaceCss.includes(".verification-item__header") &&
      workspaceCss.includes("flex-wrap: wrap") &&
      workspaceCss.includes(".context-tab") &&
      workspaceCss.includes("min-height: 44px"),
    "verification and context controls must remain readable on mobile"
  );
  assert.ok(
    languageSwitcher.includes("min-h-[2.75rem]"),
    "language switcher options must keep 44px touch targets"
  );
  assert.ok(
    adminCss.includes(".admin-nav-item") &&
      adminCss.includes("min-height: 44px") &&
      adminCss.includes(".admin-main") &&
      adminCss.includes(".admin-gate") &&
      adminCss.includes("color-mix(in srgb, var(--color-bg) 82%, var(--color-surface) 18%)") &&
      adminCss.includes("flex: 0 0 auto") &&
      adminCss.includes(".admin-nav-item__meta") &&
      adminCss.includes("display: none") &&
    adminCss.includes(".admin-members__toolbar") &&
      adminCss.includes(".admin-invites__toolbar") &&
      adminCss.includes(".admin-checkbox-target") &&
      adminCss.includes("overflow-x: auto"),
    "admin mobile navigation, tables, and checkboxes must avoid narrow-screen overflow"
  );
  assert.ok(
    baseCss.includes(".settings-card__footer .btn") &&
      baseCss.includes(".settings-shell .input") &&
      baseCss.includes("min-height: 44px") &&
      baseCss.includes(".settings-switch") &&
      baseCss.includes("height: 44px"),
    "settings page controls must keep 44px touch targets"
  );
  assert.ok(
    sidebarCss.includes(".brand") &&
      sidebarCss.includes(".nav-item") &&
      sidebarCss.includes("min-height: 44px"),
    "workspace sidebar brand and nav controls must keep 44px touch targets"
  );
  assert.ok(
    workflowCardCss.includes(".workflow-actions .btn") &&
      workflowCardCss.includes("min-height: 44px"),
    "workflow card actions must keep 44px touch targets"
  );
  assert.ok(
    homePage.includes("bg-[linear-gradient(180deg,#f8fafc_0%,#f5f5f7_48%,#eef2f7_100%)]") &&
      homePageSectionShell.includes("py-14 md:scroll-mt-28 md:py-28") &&
      homePageSectionShell.includes("initial={{ y: 18 }}") &&
      !homePage.includes("initial={{ opacity: 0") &&
      !homePageSectionShell.includes("initial={{ opacity: 0") &&
      !homePage.includes("useScroll") &&
      !homePage.includes("useTransform") &&
      !homePageSectionShell.includes("useScroll") &&
      !homePageSectionShell.includes("useTransform"),
    "marketing homepage must keep continuous backgrounds without hidden section gaps"
  );
  assert.ok(
    methodologyPage.includes("bg-[linear-gradient(180deg,#f8fafc_0%,#f5f5f7_48%,#eef2f7_100%)]") &&
      methodologyPage.includes("px-5 py-8 md:px-6 md:py-14") &&
      methodologySections.includes("py-14 md:py-24") &&
      methodologyPageUtils.includes("initial={{ y: 18 }}") &&
      !methodologyPage.includes("initial={{ opacity: 0") &&
      !methodologyPageUtils.includes("initial={{ opacity: 0"),
    "methodology page must keep continuous backgrounds without hidden section gaps"
  );
});
