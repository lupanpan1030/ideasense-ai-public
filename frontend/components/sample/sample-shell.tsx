"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AppShellSidebar } from "@/components/layout/app-shell-sidebar";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { buttonClassNames } from "@/components/ui/button";
import type { ProjectSummary } from "@/features/projects/projects";
import { resolveWorkflowSteps } from "@/content/workflow-steps";
import { buildLocalePath, stripLocalePrefix } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

const STAGE_INDEX: Record<string, number> = {
  problem: 1,
  market: 2,
  tech: 3,
  report: 4,
};

export function SampleShell({
  children,
  projects,
}: {
  children: React.ReactNode;
  projects: ProjectSummary[];
}) {
  const router = useRouter();
  const locale = useAppLocale();
  const messages = useAppMessages();
  const appShellMessages = messages.appShell;
  const pathname = usePathname() ?? "";
  const searchParams = useSearchParams();
  const workflowBaseId = useId();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const sidebarProjectsListRef = useRef<HTMLDivElement | null>(null);
  const sidebarProjectsSentinelRef = useRef<HTMLDivElement | null>(null);
  const workflowSteps = useMemo(
    () => resolveWorkflowSteps(locale),
    [locale]
  );

  const navState = useMemo(() => {
    const normalizedPathname = stripLocalePrefix(pathname || "/");
    const segments = normalizedPathname.split("/").filter(Boolean);
    const isProjectsRoot = segments.length === 1 && segments[0] === "sample";
    const projectId =
      segments[0] === "sample" && segments[1] ? segments[1] : null;
    const section = segments[2] ?? null;
    return { isProjectsRoot, projectId, section };
  }, [pathname]);

  const isChatPage = navState.section === "chat";
  const isReportPage = navState.section === "report";
  const stageFilter = (searchParams?.get("stage") ?? "").toLowerCase();
  const isReportsView = navState.isProjectsRoot && stageFilter === "report";
  const isProjectsActive = navState.isProjectsRoot && !isReportsView;
  const showProjectList = Boolean(navState.projectId);
  const projectsHref = buildLocalePath(locale, "/sample");
  const reportsHref = buildLocalePath(locale, "/sample", "?stage=report");
  const chatHref = navState.projectId
    ? buildLocalePath(locale, `/sample/${navState.projectId}/chat`)
    : null;

  const navItemClass = (isActive: boolean) =>
    ["nav-item", isActive ? "nav-item--active" : ""].filter(Boolean).join(" ");
  const projectCardClass = (isActive: boolean) =>
    ["sidebar-project-card", isActive ? "sidebar-project-card--active" : ""]
      .filter(Boolean)
      .join(" ");

  const handleMobileSidebarToggle = useCallback(() => {
    setIsMobileSidebarOpen((prev) => !prev);
  }, []);

  const handleMobileSidebarClose = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  const handleSidebarToggle = useCallback(() => {
    setIsSidebarCollapsed((prev) => !prev);
  }, []);

  const handleCreateProject = useCallback(() => {
    router.push(buildLocalePath(locale, "/register"));
  }, [locale, router]);

  useEffect(() => {
    setIsMobileSidebarOpen(false);
  }, [pathname]);

  const appShellClassName = [
    "app-shell",
    "app-shell--sample",
    isSidebarCollapsed ? "app-shell--sidebar-collapsed" : "",
    navState.isProjectsRoot ? "app-shell--projects" : "",
    isChatPage ? "app-shell--chat" : "",
    isReportPage ? "app-shell--report" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const sidebarToggleLabel = isSidebarCollapsed
    ? appShellMessages.layout.expandSidebar
    : appShellMessages.layout.collapseSidebar;
  const formatStageBadge = useCallback(
    (project: ProjectSummary): string => {
      const index = STAGE_INDEX[project.stage.value];
      const label =
        messages.reportViewer.stageLabels[project.stage.value] ??
        project.stage.label;
      if (index) {
        return appShellMessages.layout.stageBadge
          .replace("{index}", String(index))
          .replace("{label}", label);
      }
      return label;
    },
    [appShellMessages.layout.stageBadge, messages.reportViewer.stageLabels]
  );

  return (
    <div
      className={[
        appShellClassName,
        isMobileSidebarOpen ? "app-shell--mobile-sidebar-open" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <button
        type="button"
        className="sidebar-mobile-toggle"
        aria-label={
          isMobileSidebarOpen
            ? appShellMessages.layout.closeMenu
            : appShellMessages.layout.openMenu
        }
        aria-expanded={isMobileSidebarOpen}
        onClick={handleMobileSidebarToggle}
      >
        <span className="sidebar-mobile-toggle__icon" aria-hidden="true">
          {isMobileSidebarOpen ? "✕" : "☰"}
        </span>
        <span className="sr-only">{appShellMessages.layout.menuLabel}</span>
      </button>
      <button
        type="button"
        className="sidebar-mobile-overlay"
        aria-hidden={!isMobileSidebarOpen}
        onClick={handleMobileSidebarClose}
      />
      <AppShellSidebar
        navState={navState}
        isChatPage={isChatPage}
        isSidebarCollapsed={isSidebarCollapsed}
        sidebarToggleLabel={sidebarToggleLabel}
        showProjectList={showProjectList}
        chatHref={chatHref}
        reportsHref={reportsHref}
        projectsHref={projectsHref}
        projectCardHrefBuilder={(projectId) =>
          buildLocalePath(locale, `/sample/${projectId}/chat`)
        }
        isProjectsActive={isProjectsActive}
        isReportsActive={isReportPage || isReportsView}
        navItemClass={navItemClass}
        projectCardClass={projectCardClass}
        formatStageBadge={formatStageBadge}
        workflowSteps={workflowSteps}
        workflowBaseId={workflowBaseId}
        sidebarProjects={projects}
        sidebarProjectsError={null}
        sidebarProjectsLoading={false}
        sidebarProjectsHasMore={false}
        sidebarProjectsListRef={sidebarProjectsListRef}
        sidebarProjectsSentinelRef={sidebarProjectsSentinelRef}
        onSidebarToggle={handleSidebarToggle}
        onCreateProject={handleCreateProject}
        onRetryProjects={() => {}}
        newProjectLabel={appShellMessages.layout.signInToCreateProject}
        onCloseSidebar={handleMobileSidebarClose}
      />

      <div
        className={[
          "app-shell__main",
          navState.isProjectsRoot ? "app-shell__main--sample-root" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <SampleTopbar />
        <main
          className={[
            "app-shell__content",
            navState.isProjectsRoot ? "app-shell__content--sample-root" : "",
            isChatPage ? "app-shell__content--chat" : "",
            isReportPage ? "app-shell__content--report" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

function SampleTopbar() {
  const locale = useAppLocale();
  const isZh = locale === "zh";

  return (
    <header className="app-shell__topbar sample-topbar">
      <nav
        className="sample-topbar__nav"
        aria-label={isZh ? "示例导航" : "Sample navigation"}
      >
        <Link className="sample-topbar__brand" href={buildLocalePath(locale, "/sample")}>
          IdeaSense Sample
        </Link>
        <Link className="sample-topbar__link" href={buildLocalePath(locale, "/sample")}>
          {isZh ? "工作区" : "Workspace"}
        </Link>
        <Link
          className="sample-topbar__link"
          href={buildLocalePath(locale, "/sample-report")}
        >
          {isZh ? "报告" : "Report"}
        </Link>
      </nav>
      <div className="sample-topbar__actions">
        <LanguageSwitcher compact className="sample-topbar__locale" />
        <Link
          className={buttonClassNames({ variant: "ghost", size: "sm" })}
          href={buildLocalePath(locale, "/login")}
        >
          {isZh ? "登录" : "Sign in"}
        </Link>
        <Link
          className={buttonClassNames({ size: "sm" })}
          href={buildLocalePath(locale, "/register")}
        >
          {isZh ? "注册" : "Create account"}
        </Link>
      </div>
    </header>
  );
}
