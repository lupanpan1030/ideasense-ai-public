import Link from "next/link";
import { type RefObject, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProjectSummary } from "@/features/projects/projects";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

type WorkflowStep = {
  key: string;
  index: string;
  label: string;
  meta: string;
  description: string;
};

type NavState = {
  isProjectsRoot: boolean;
  projectId: string | null;
  section: string | null;
};

type AppShellSidebarProps = {
  navState: NavState;
  isChatPage: boolean;
  isSidebarCollapsed: boolean;
  sidebarToggleLabel: string;
  showProjectList: boolean;
  chatHref: string | null;
  reportsHref: string | null;
  projectsHref?: string;
  projectCardHrefBuilder?: (projectId: string) => string;
  isProjectsActive: boolean;
  isReportsActive: boolean;
  showReportsNav?: boolean;
  navItemClass: (isActive: boolean) => string;
  projectCardClass: (isActive: boolean) => string;
  formatStageBadge: (project: ProjectSummary) => string;
  workflowSteps: WorkflowStep[];
  workflowBaseId: string;
  sidebarProjects: ProjectSummary[];
  sidebarProjectsError: string | null;
  sidebarProjectsLoading: boolean;
  sidebarProjectsHasMore: boolean;
  sidebarProjectsListRef: RefObject<HTMLDivElement | null>;
  sidebarProjectsSentinelRef: RefObject<HTMLDivElement | null>;
  onSidebarToggle: () => void;
  onCloseSidebar: () => void;
  onCreateProject: () => void;
  onRetryProjects: () => void;
  newProjectLabel: string;
};

export function AppShellSidebar({
  navState,
  isChatPage,
  isSidebarCollapsed,
  sidebarToggleLabel,
  showProjectList,
  chatHref,
  reportsHref,
  projectsHref = "/projects",
  projectCardHrefBuilder = (projectId: string) => `/projects/${projectId}/chat`,
  isProjectsActive,
  isReportsActive,
  showReportsNav = true,
  navItemClass,
  projectCardClass,
  formatStageBadge,
  workflowSteps,
  workflowBaseId,
  sidebarProjects,
  sidebarProjectsError,
  sidebarProjectsLoading,
  sidebarProjectsHasMore,
  sidebarProjectsListRef,
  sidebarProjectsSentinelRef,
  onSidebarToggle,
  onCloseSidebar,
  onCreateProject,
  onRetryProjects,
  newProjectLabel,
}: AppShellSidebarProps) {
  const locale = useAppLocale();
  const sidebarMessages = useAppMessages().appShell.sidebar;
  const workflowContainerRef = useRef<HTMLDivElement | null>(null);
  const [workflowDensity, setWorkflowDensity] = useState<
    "expanded" | "compact" | "condensed"
  >("compact");

  useEffect(() => {
    if (showProjectList) {
      return;
    }

    const container = workflowContainerRef.current;
    if (!container) {
      return;
    }

    const updateDensity = (height: number, width: number) => {
      if (height <= 420 || width <= 280) {
        setWorkflowDensity("condensed");
        return;
      }

      if (height <= 520 || width <= 360) {
        setWorkflowDensity("compact");
        return;
      }

      setWorkflowDensity("expanded");
    };

    if (typeof ResizeObserver === "undefined") {
      const rect = container.getBoundingClientRect();
      updateDensity(rect.height, rect.width);
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      updateDensity(entry.contentRect.height, entry.contentRect.width);
    });

    observer.observe(container);
    const rect = container.getBoundingClientRect();
    updateDensity(rect.height, rect.width);

    return () => observer.disconnect();
  }, [showProjectList]);

  const workflowCardClassName = [
    "workflow-card",
    navState.isProjectsRoot ? "workflow-card--static" : "",
    workflowDensity === "expanded" ? "workflow-card--expanded" : "",
    workflowDensity === "compact" ? "workflow-card--compact" : "",
    workflowDensity === "condensed" ? "workflow-card--condensed" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const isWorkflowExpanded =
    workflowDensity === "expanded" || navState.isProjectsRoot;

  return (
    <aside className="app-shell__sidebar" id="workspace-sidebar">
      <div className="sidebar-header">
        <Link
          className="brand"
          href={buildLocalePath(locale, "/")}
          aria-label={sidebarMessages.home}
          onClick={onCloseSidebar}
        >
          <div className="brand-mark">IS</div>
          <div className="stack-sm">
            <p className="brand-title">IdeaSense AI</p>
          </div>
        </Link>
        <button
          type="button"
          className="sidebar-close"
          onClick={onCloseSidebar}
          aria-label={sidebarMessages.closeSidebar}
        >
          <span className="sidebar-close__icon" aria-hidden="true">
            ✕
          </span>
        </button>
        {isChatPage && !isSidebarCollapsed ? (
          <button
            type="button"
            className="sidebar-toggle"
            onClick={onSidebarToggle}
            aria-controls="workspace-sidebar"
            aria-expanded={!isSidebarCollapsed}
            aria-label={sidebarToggleLabel}
            title={sidebarToggleLabel}
          >
            <span className="sidebar-toggle__icon" aria-hidden="true">
              {isSidebarCollapsed ? ">" : "<"}
            </span>
            <span className="sr-only">{sidebarToggleLabel}</span>
          </button>
        ) : null}
      </div>
      <div className="sidebar-section">
        <p className="sidebar-label">{sidebarMessages.workspace}</p>
        {isChatPage && isSidebarCollapsed ? (
          <button
            type="button"
            className="sidebar-toggle sidebar-toggle--nav"
            onClick={onSidebarToggle}
            aria-controls="workspace-sidebar"
            aria-expanded={!isSidebarCollapsed}
            aria-label={sidebarToggleLabel}
            title={sidebarToggleLabel}
          >
            <span className="sidebar-toggle__icon" aria-hidden="true">
              {isSidebarCollapsed ? ">" : "<"}
            </span>
            <span className="sr-only">{sidebarToggleLabel}</span>
          </button>
        ) : null}
        <nav className="nav" aria-label={sidebarMessages.primaryNavigation}>
          <Link
            className={navItemClass(isProjectsActive)}
            href={projectsHref}
            aria-current={isProjectsActive ? "page" : undefined}
            onClick={onCloseSidebar}
          >
            <span className="nav-item__icon" aria-hidden="true">
              P
            </span>
            <span className="nav-item__label">{sidebarMessages.projects}</span>
          </Link>
          {chatHref ? (
            <Link
              className={navItemClass(navState.section === "chat")}
              href={chatHref}
              aria-current={navState.section === "chat" ? "page" : undefined}
              onClick={onCloseSidebar}
            >
              <span className="nav-item__icon" aria-hidden="true">
                C
              </span>
              <span className="nav-item__label">{sidebarMessages.chat}</span>
            </Link>
          ) : null}
          {showReportsNav ? (
            reportsHref ? (
              <Link
                className={navItemClass(isReportsActive)}
                href={reportsHref}
                aria-current={isReportsActive ? "page" : undefined}
                onClick={onCloseSidebar}
              >
                <span className="nav-item__icon" aria-hidden="true">
                  R
                </span>
                <span className="nav-item__label">{sidebarMessages.reports}</span>
              </Link>
            ) : (
              <span className="nav-item nav-item--disabled" aria-disabled="true">
                <span className="nav-item__icon" aria-hidden="true">
                  R
                </span>
                <span className="nav-item__label">{sidebarMessages.reports}</span>
              </span>
            )
          ) : null}
        </nav>
      </div>

      <div
        className={["sidebar-section", "sidebar-section--grow"].join(" ")}
        ref={workflowContainerRef}
      >
        <div className="sidebar-section__header">
          <p className="sidebar-label">
            {showProjectList
              ? sidebarMessages.recentProjects
              : sidebarMessages.workflow}
          </p>
          {showProjectList ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="sidebar-action"
              onClick={onCreateProject}
              aria-label={newProjectLabel}
              title={newProjectLabel}
            >
              <span className="sidebar-action__icon" aria-hidden="true">
                +
              </span>
              <span className="sr-only">{newProjectLabel}</span>
            </Button>
          ) : null}
        </div>
        {showProjectList ? (
          <div className="sidebar-projects" ref={sidebarProjectsListRef}>
            {sidebarProjects.map((project) => {
              const isActive = project.id === navState.projectId;
              return (
                <Link
                  key={project.id}
                  className={projectCardClass(isActive)}
                  href={projectCardHrefBuilder(project.id)}
                  aria-current={isActive ? "page" : undefined}
                  onClick={onCloseSidebar}
                >
                  <span className="sidebar-project-title">{project.title}</span>
                  <Badge
                    variant={project.stage.variant}
                    className="sidebar-project-stage"
                  >
                    {formatStageBadge(project)}
                  </Badge>
                  <span className="sidebar-project-updated">
                    {project.updatedAtLabel}
                  </span>
                </Link>
              );
            })}
            {sidebarProjectsLoading && sidebarProjects.length === 0 ? (
              <span className="sidebar-project-state">
                {sidebarMessages.loadingProjects}
              </span>
            ) : null}
            {sidebarProjectsError ? (
              <div className="sidebar-project-state">
                <span>{sidebarProjectsError}</span>
                <button
                  type="button"
                  className="sidebar-project-retry"
                  onClick={onRetryProjects}
                >
                  {sidebarMessages.retry}
                </button>
              </div>
            ) : null}
            {!sidebarProjectsLoading &&
            !sidebarProjectsError &&
            sidebarProjects.length === 0 ? (
              <span className="sidebar-project-state">
                {sidebarMessages.noProjects}
              </span>
            ) : null}
            {sidebarProjectsHasMore ? (
              <div
                ref={sidebarProjectsSentinelRef}
                className="sidebar-projects__sentinel"
                aria-hidden="true"
              />
            ) : null}
            {sidebarProjectsLoading && sidebarProjects.length > 0 ? (
              <span className="sidebar-project-state">
                {sidebarMessages.loadingMore}
              </span>
            ) : null}
          </div>
        ) : (
          <div className={workflowCardClassName}>
            <div className="workflow-scan" aria-hidden="true" />
            <div className="workflow-header">
              <div className="workflow-header__stack">
                <div className="workflow-title">{sidebarMessages.overview}</div>
                <p className="workflow-subtitle">
                  {sidebarMessages.workflowSubtitle}
                </p>
                <div className="workflow-status workflow-status--inline">
                  <span className="workflow-pulse" aria-hidden="true" />
                  <span>{sidebarMessages.workflowStepsCount}</span>
                </div>
              </div>
            </div>
            <ol
              className="workflow-steps"
              aria-label={sidebarMessages.workflowAriaLabel}
            >
              {workflowSteps.map((step) => {
                const tooltipId = `${workflowBaseId}-workflow-${step.key}`;
                return (
                  <li
                    key={step.key}
                    className="workflow-step"
                    tabIndex={0}
                    aria-describedby={isWorkflowExpanded ? undefined : tooltipId}
                  >
                    <span className="workflow-index">{step.index}</span>
                    <div className="workflow-content">
                      <span className="workflow-label">{step.label}</span>
                      <span className="workflow-meta">{step.meta}</span>
                      <span className="workflow-detail">
                        {step.description}
                      </span>
                      <span
                        id={tooltipId}
                        role="tooltip"
                        className="workflow-tooltip"
                      >
                        {step.description}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ol>
            <p className="workflow-hint">
              {sidebarMessages.workflowHint}
            </p>
            <div className="workflow-actions">
              <Button type="button" size="sm" onClick={onCreateProject}>
                {sidebarMessages.startProject}
              </Button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
