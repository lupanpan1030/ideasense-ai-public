"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ShellLayoutProvider } from "@/components/layout/shell-layout-context";
import { AppShellSidebar } from "@/components/layout/app-shell-sidebar";
import { AppShellTopbar } from "@/components/layout/app-shell-topbar";
import { EmailVerificationBanner } from "@/components/layout/email-verification-banner";
import {
  fetchProjects,
  getProjectsErrorMessage,
  ProjectCreateResult,
  ProjectSummary,
} from "@/features/projects/projects";
import { fetchProjectPermissions } from "@/features/projects/project-permissions";
import { CreateProjectModal } from "@/features/projects/create-project-modal";
import { subscribeToChatControl } from "@/features/chat/control-channel";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { buildLocalePath, stripLocalePrefix } from "@/lib/i18n/config";
import { resolveWorkflowSteps } from "../../content/workflow-steps";

const PROJECT_PAGE_SIZE = 8;
const SIDEBAR_COLLAPSE_KEY = "ideasense.sidebarCollapsed";
const STAGE_INDEX: Record<string, number> = {
  problem: 1,
  market: 2,
  tech: 3,
  report: 4,
};

const mergeSidebarProjects = (
  prev: ProjectSummary[],
  next: ProjectSummary[],
  reset: boolean
): ProjectSummary[] => {
  const merged = reset ? [] : [...prev];
  const indexById = new Map<string, number>();
  merged.forEach((item, index) => {
    indexById.set(item.id, index);
  });

  next.forEach((item) => {
    const existingIndex = indexById.get(item.id);
    if (existingIndex === undefined) {
      indexById.set(item.id, merged.length);
      merged.push(item);
      return;
    }
    merged[existingIndex] = item;
  });

  return merged;
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const locale = useAppLocale();
  const messages = useAppMessages();
  const appShellMessages = messages.appShell;
  const workflowBaseId = useId();
  const pathname = usePathname() ?? "";
  const searchParams = useSearchParams();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const navState = useMemo(() => {
    const normalizedPathname = stripLocalePrefix(pathname || "/");
    const segments = normalizedPathname.split("/").filter(Boolean);
    const isProjectsRoot = segments.length === 1 && segments[0] === "projects";
    const projectId =
      segments[0] === "projects" && segments[1] ? segments[1] : null;
    const section = segments[2] ?? null;

    return {
      isProjectsRoot,
      projectId,
      section,
    };
  }, [pathname]);
  const isChatPage = navState.section === "chat";
  const isReportPage = navState.section === "report";
  const stageFilter = (searchParams?.get("stage") ?? "").toLowerCase();
  const isReportsView =
    navState.isProjectsRoot && stageFilter === "report";
  const isProjectsActive = navState.isProjectsRoot;
  const [canViewMessages, setCanViewMessages] = useState<boolean | null>(null);

  const [sidebarProjects, setSidebarProjects] = useState<ProjectSummary[]>([]);
  const [sidebarProjectsError, setSidebarProjectsError] = useState<string | null>(
    null
  );
  const [sidebarProjectsLoading, setSidebarProjectsLoading] = useState(false);
  const [sidebarProjectsHasMore, setSidebarProjectsHasMore] = useState(true);
  const sidebarProjectsListRef = useRef<HTMLDivElement | null>(null);
  const sidebarProjectsSentinelRef = useRef<HTMLDivElement | null>(null);
  const sidebarProjectsLoadingRef = useRef(false);
  const sidebarProjectsHasMoreRef = useRef(true);
  const sidebarProjectsCountRef = useRef(0);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [summaryVisible, setSummaryVisible] = useState(false);
  const [sidebarPreference, setSidebarPreference] = useState<boolean | null>(
    null
  );
  const workflowSteps = useMemo(
    () => resolveWorkflowSteps(locale),
    [locale]
  );

  useEffect(() => {
    sidebarProjectsHasMoreRef.current = sidebarProjectsHasMore;
  }, [sidebarProjectsHasMore]);

  useEffect(() => {
    sidebarProjectsCountRef.current = sidebarProjects.length;
  }, [sidebarProjects]);

  const loadSidebarProjects = useCallback(
    async ({ reset = false }: { reset?: boolean } = {}) => {
      if (sidebarProjectsLoadingRef.current) {
        return;
      }
      if (!sidebarProjectsHasMoreRef.current && !reset) {
        return;
      }

      sidebarProjectsLoadingRef.current = true;
      setSidebarProjectsLoading(true);
      setSidebarProjectsError(null);

      const offset = reset ? 0 : sidebarProjectsCountRef.current;

      try {
        const { projects: next, total } = await fetchProjects({
          offset,
          limit: PROJECT_PAGE_SIZE,
        });
        setSidebarProjects((prev) => mergeSidebarProjects(prev, next, reset));
        setSidebarProjectsHasMore(offset + next.length < total);
      } catch (error) {
        setSidebarProjectsError(getProjectsErrorMessage(error));
      } finally {
        sidebarProjectsLoadingRef.current = false;
        setSidebarProjectsLoading(false);
      }
    },
    []
  );

  const showProjectList = Boolean(navState.projectId);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const stored = window.localStorage.getItem(SIDEBAR_COLLAPSE_KEY);
    if (stored === "1") {
      setSidebarPreference(true);
    } else if (stored === "0") {
      setSidebarPreference(false);
    }
  }, []);

  useEffect(() => {
    if (!showProjectList) {
      return;
    }
    if (sidebarProjectsCountRef.current === 0) {
      loadSidebarProjects({ reset: true });
    }
  }, [loadSidebarProjects, showProjectList]);

  useEffect(() => {
    setIsMobileSidebarOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!showProjectList) {
      return;
    }
    return subscribeToChatControl((payload) => {
      if (payload.project_id && payload.project_id !== navState.projectId) {
        return;
      }
      const type =
        typeof payload.type === "string" ? payload.type.trim().toLowerCase() : "";
      if (type !== "stage_confirmed") {
        return;
      }
      void loadSidebarProjects({ reset: true });
    });
  }, [loadSidebarProjects, navState.projectId, showProjectList]);

  useEffect(() => {
    let isActive = true;
    if (!navState.projectId) {
      setCanViewMessages(null);
      return () => {
        isActive = false;
      };
    }

    setCanViewMessages(null);
    fetchProjectPermissions(navState.projectId)
      .then((permissions) => {
        if (!isActive) {
          return;
        }
        setCanViewMessages(permissions.can_view_messages);
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setCanViewMessages(false);
      });

    return () => {
      isActive = false;
    };
  }, [navState.projectId]);

  useEffect(() => {
    if (!showProjectList) {
      return;
    }

    const list = sidebarProjectsListRef.current;
    const sentinel = sidebarProjectsSentinelRef.current;
    if (!list || !sentinel || typeof IntersectionObserver === "undefined") {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          loadSidebarProjects();
        }
      },
      { root: list, rootMargin: "120px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadSidebarProjects, showProjectList]);

  const navItemClass = (isActive: boolean) =>
    ["nav-item", isActive ? "nav-item--active" : ""].filter(Boolean).join(" ");
  const projectCardClass = (isActive: boolean) =>
    ["sidebar-project-card", isActive ? "sidebar-project-card--active" : ""]
      .filter(Boolean)
      .join(" ");
  const isSidebarCollapsed = isChatPage ? (sidebarPreference ?? false) : false;
  const appShellClassName = [
    "app-shell",
    isSidebarCollapsed ? "app-shell--sidebar-collapsed" : "",
    navState.isProjectsRoot ? "app-shell--projects" : "",
    isChatPage ? "app-shell--chat" : "",
    isReportPage ? "app-shell--report" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const projectsHref = buildLocalePath(locale, "/projects");
  const reportsHref = buildLocalePath(locale, "/projects", "?stage=report");
  const chatHref =
    !isChatPage && navState.projectId && canViewMessages
      ? buildLocalePath(locale, `/projects/${navState.projectId}/chat`)
      : null;

  const handleSidebarToggle = useCallback(() => {
    const current = sidebarPreference ?? summaryVisible;
    const next = !current;
    setSidebarPreference(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SIDEBAR_COLLAPSE_KEY, next ? "1" : "0");
    }
  }, [sidebarPreference, summaryVisible]);

  const handleMobileSidebarToggle = useCallback(() => {
    setIsMobileSidebarOpen((prev) => !prev);
  }, []);

  const handleMobileSidebarClose = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  const handleCreateProject = useCallback(() => {
    setIsCreateOpen(true);
  }, []);

  const handleCreateClose = useCallback(() => {
    setIsCreateOpen(false);
  }, []);

  const handleCreateSuccess = useCallback(
    (result: ProjectCreateResult) => {
      setSidebarProjects((prev) => {
        const next = prev.filter((item) => item.id !== result.project.id);
        return [result.project, ...next];
      });
      setIsCreateOpen(false);
      router.push(buildLocalePath(locale, `/projects/${result.project.id}/chat`));
    },
    [locale, router]
  );

  const shellLayoutValue = useMemo(
    () => ({ setSummaryVisible }),
    [setSummaryVisible]
  );
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
  const sidebarToggleLabel = isSidebarCollapsed
    ? appShellMessages.layout.expandSidebar
    : appShellMessages.layout.collapseSidebar;
  const newProjectLabel = appShellMessages.layout.newProject;

  return (
    <ShellLayoutProvider value={shellLayoutValue}>
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
          buildLocalePath(locale, `/projects/${projectId}/chat`)
        }
        isProjectsActive={isProjectsActive}
        isReportsActive={isReportPage || isReportsView}
        showReportsNav={!navState.isProjectsRoot}
        navItemClass={navItemClass}
        projectCardClass={projectCardClass}
        formatStageBadge={formatStageBadge}
          workflowSteps={workflowSteps}
          workflowBaseId={workflowBaseId}
          sidebarProjects={sidebarProjects}
          sidebarProjectsError={sidebarProjectsError}
          sidebarProjectsLoading={sidebarProjectsLoading}
          sidebarProjectsHasMore={sidebarProjectsHasMore}
          sidebarProjectsListRef={sidebarProjectsListRef}
          sidebarProjectsSentinelRef={sidebarProjectsSentinelRef}
          onSidebarToggle={handleSidebarToggle}
          onCreateProject={handleCreateProject}
          onRetryProjects={() => loadSidebarProjects({ reset: true })}
          newProjectLabel={newProjectLabel}
          onCloseSidebar={handleMobileSidebarClose}
        />

      <div className="app-shell__main">
        <AppShellTopbar />
        <main
          className={[
            "app-shell__content",
            isChatPage ? "app-shell__content--chat" : "",
            isReportPage ? "app-shell__content--report" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <EmailVerificationBanner />
          {children}
        </main>
      </div>
      {isCreateOpen ? (
        <CreateProjectModal
          onClose={handleCreateClose}
          onCreate={handleCreateSuccess}
        />
      ) : null}
    </div>
    </ShellLayoutProvider>
  );
}
