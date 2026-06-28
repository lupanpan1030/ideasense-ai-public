import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { UserSession } from "@/features/auth/user-session";
import type {
  ProjectSummary,
  ProjectsArchivedFilter,
  ProjectsSortField,
} from "@/features/projects/projects";
import type { AppMessages } from "@/lib/i18n/messages";
import {
  LOADING_PLACEHOLDERS,
  STAGE_ORDER,
  formatOrgRoleLabel,
  highlightText,
  interpolate,
} from "./projects-workspace-utils";

type ProjectsWorkspaceMessages = AppMessages["projectsWorkspace"];
type CommonMessages = ProjectsWorkspaceMessages["common"];
type PageMessages = ProjectsWorkspaceMessages["page"];
type OrgPickerMessages = ProjectsWorkspaceMessages["orgPicker"];
type OrgChoice = UserSession["orgs"][number];

export function ProjectsWorkspaceHeader({
  isLoading,
  pageEyebrow,
  pageMessages,
  pageSubtitle,
  pageTitle,
  search,
  searchPlaceholder,
  onCreateProject,
  onSearchChange,
}: {
  isLoading: boolean;
  pageEyebrow: string;
  pageMessages: PageMessages;
  pageSubtitle: string;
  pageTitle: string;
  search: string;
  searchPlaceholder: string;
  onCreateProject: () => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <div className="page-header">
      <div className="stack-sm">
        <p className="eyebrow">{pageEyebrow}</p>
        <h1 className="page-title">{pageTitle}</h1>
        <p className="page-subtitle">{pageSubtitle}</p>
      </div>
      <div className="page-actions">
        <div className="page-search">
          <label className="sr-only" htmlFor="projects-search">
            {pageMessages.searchLabel}
          </label>
          <input
            id="projects-search"
            className="input input--sm"
            type="search"
            placeholder={searchPlaceholder}
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            disabled={isLoading}
          />
        </div>
        <Button type="button" onClick={onCreateProject}>
          {pageMessages.newProject}
        </Button>
      </div>
    </div>
  );
}

export function ProjectsWorkspaceTabs({
  allLabel,
  isReportsView,
  pageMessages,
  reportLabel,
  onTabChange,
}: {
  allLabel: string;
  isReportsView: boolean;
  pageMessages: PageMessages;
  reportLabel: string;
  onTabChange: (next: "all" | "report") => void;
}) {
  return (
    <div className="projects-tabs-row">
      <div
        className="projects-tabs"
        role="tablist"
        aria-label={pageMessages.tabsAriaLabel}
      >
        <button
          type="button"
          role="tab"
          aria-selected={!isReportsView}
          className={[
            "projects-tab",
            !isReportsView ? "projects-tab--active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onTabChange("all")}
        >
          {allLabel}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={isReportsView}
          className={[
            "projects-tab",
            isReportsView ? "projects-tab--active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onTabChange("report")}
        >
          {reportLabel}
        </button>
      </div>
    </div>
  );
}

export function ProjectsWorkspaceFilters({
  archivedFilter,
  orderLabel,
  pageMessages,
  sortField,
  onArchivedChange,
  onOrderToggle,
  onSortChange,
}: {
  archivedFilter: ProjectsArchivedFilter;
  orderLabel: string;
  pageMessages: PageMessages;
  sortField: ProjectsSortField;
  onArchivedChange: (value: ProjectsArchivedFilter) => void;
  onOrderToggle: () => void;
  onSortChange: (value: ProjectsSortField) => void;
}) {
  return (
    <div className="projects-filters">
      <div className="projects-filters__group">
        <div className="field projects-filter">
          <label className="field__label" htmlFor="projects-archive-filter">
            {pageMessages.statusLabel}
          </label>
          <select
            id="projects-archive-filter"
            className="input input--sm"
            value={archivedFilter}
            onChange={(event) =>
              onArchivedChange(event.target.value as ProjectsArchivedFilter)
            }
          >
            <option value="active">{pageMessages.statusOptions.active}</option>
            <option value="archived">{pageMessages.statusOptions.archived}</option>
            <option value="all">{pageMessages.statusOptions.all}</option>
          </select>
        </div>
        <div className="field projects-filter">
          <label className="field__label" htmlFor="projects-sort-field">
            {pageMessages.sortByLabel}
          </label>
          <select
            id="projects-sort-field"
            className="input input--sm"
            value={sortField}
            onChange={(event) =>
              onSortChange(event.target.value as ProjectsSortField)
            }
          >
            <option value="updated_at">{pageMessages.sortOptions.updatedAt}</option>
            <option value="created_at">{pageMessages.sortOptions.createdAt}</option>
            <option value="title">{pageMessages.sortOptions.title}</option>
          </select>
        </div>
      </div>
      <div className="projects-filters__group">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={onOrderToggle}
          aria-label={pageMessages.toggleSortAriaLabel}
        >
          {orderLabel}
        </Button>
      </div>
    </div>
  );
}

export function ProjectsWorkspaceContent({
  commonMessages,
  emptyActionLabel,
  emptyDescription,
  emptyTitle,
  error,
  filteredProjects,
  getProjectHref,
  isArchivedView,
  isInitialLoading,
  isReportsView,
  pageMessages,
  search,
  showEmptyState,
  showErrorBanner,
  showErrorState,
  showNoResults,
  sortField,
  workspaceMessages,
  onArchiveToggle,
  onClearSearch,
  onCreateProject,
  onDelete,
  onRetry,
  onRename,
  onTabChange,
  onViewActive,
}: {
  commonMessages: CommonMessages;
  emptyActionLabel: string;
  emptyDescription: string;
  emptyTitle: string;
  error: string | null;
  filteredProjects: ProjectSummary[];
  getProjectHref: (project: ProjectSummary) => string;
  isArchivedView: boolean;
  isInitialLoading: boolean;
  isReportsView: boolean;
  pageMessages: PageMessages;
  search: string;
  showEmptyState: boolean;
  showErrorBanner: boolean;
  showErrorState: boolean;
  showNoResults: boolean;
  sortField: ProjectsSortField;
  workspaceMessages: ProjectsWorkspaceMessages;
  onArchiveToggle: (project: ProjectSummary) => void;
  onClearSearch: () => void;
  onCreateProject: () => void;
  onDelete: (project: ProjectSummary) => void;
  onRetry: () => void;
  onRename: (project: ProjectSummary) => void;
  onTabChange: (next: "all" | "report") => void;
  onViewActive: () => void;
}) {
  return (
    <>
      {showErrorBanner ? (
        <div className="alert projects-alert" role="status" aria-live="polite">
          <span className="projects-alert__message">{error}</span>
          <Button type="button" variant="secondary" onClick={onRetry}>
            {commonMessages.retry}
          </Button>
        </div>
      ) : null}

      {showErrorState ? (
        <Card variant="alert">
          <CardHeader>
            <CardTitle>{pageMessages.loadErrorTitle}</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="secondary" onClick={onRetry}>
              {commonMessages.retry}
            </Button>
          </CardContent>
        </Card>
      ) : isInitialLoading ? (
        <div className="projects-grid">
          {LOADING_PLACEHOLDERS.map((placeholder) => (
            <Card key={placeholder}>
              <CardHeader>
                <Skeleton className="skeleton--title" />
                <Skeleton className="skeleton--line" />
                <Skeleton className="skeleton--line" />
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : showEmptyState ? (
        <Card className="empty-state">
          <Badge variant="warning">{pageMessages.emptyBadge}</Badge>
          <CardTitle>{emptyTitle}</CardTitle>
          <CardDescription>{emptyDescription}</CardDescription>
          <div className="cluster">
            {isArchivedView ? (
              <Button type="button" variant="secondary" onClick={onViewActive}>
                {emptyActionLabel}
              </Button>
            ) : isReportsView ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => onTabChange("all")}
              >
                {emptyActionLabel}
              </Button>
            ) : (
              <Button type="button" onClick={onCreateProject}>
                {emptyActionLabel}
              </Button>
            )}
          </div>
        </Card>
      ) : showNoResults ? (
        <Card className="empty-state">
          <Badge variant="info">{pageMessages.noMatchesBadge}</Badge>
          <CardTitle>
            {isReportsView
              ? pageMessages.noMatchesReportTitle
              : pageMessages.noMatchesDefaultTitle}
          </CardTitle>
          <CardDescription>
            {pageMessages.noMatchesDescription}
          </CardDescription>
          <div className="cluster">
            <Button type="button" variant="secondary" onClick={onClearSearch}>
              {pageMessages.clearSearch}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => (
            <ProjectWorkspaceCard
              key={project.id}
              getProjectHref={getProjectHref}
              pageMessages={pageMessages}
              project={project}
              search={search}
              sortField={sortField}
              workspaceMessages={workspaceMessages}
              onArchiveToggle={onArchiveToggle}
              onDelete={onDelete}
              onRename={onRename}
            />
          ))}
        </div>
      )}
    </>
  );
}

function ProjectWorkspaceCard({
  getProjectHref,
  pageMessages,
  project,
  search,
  sortField,
  workspaceMessages,
  onArchiveToggle,
  onDelete,
  onRename,
}: {
  getProjectHref: (project: ProjectSummary) => string;
  pageMessages: PageMessages;
  project: ProjectSummary;
  search: string;
  sortField: ProjectsSortField;
  workspaceMessages: ProjectsWorkspaceMessages;
  onArchiveToggle: (project: ProjectSummary) => void;
  onDelete: (project: ProjectSummary) => void;
  onRename: (project: ProjectSummary) => void;
}) {
  const stageIndex = STAGE_ORDER.indexOf(project.stage.value);
  const progressLabel =
    stageIndex >= 0
      ? interpolate(pageMessages.stageProgress, {
          current: stageIndex + 1,
          total: STAGE_ORDER.length,
        })
      : pageMessages.stageProgressUnavailable;
  const dateLabel =
    sortField === "created_at" ? project.createdAtLabel : project.updatedAtLabel;

  return (
    <Card className="project-card">
      <CardHeader>
        <div className="project-card__top">
          <div className="project-meta">
            <div className="project-meta__badges">
              <Badge variant={project.stage.variant}>
                {highlightText(project.stage.label, search)}
              </Badge>
              {project.isArchived ? (
                <Badge variant="warning">
                  {pageMessages.statusOptions.archived}
                </Badge>
              ) : null}
            </div>
            <span className="text-muted">{dateLabel}</span>
          </div>
          <ProjectCardActions
            pageMessages={pageMessages}
            project={project}
            workspaceMessages={workspaceMessages}
            onArchiveToggle={onArchiveToggle}
            onDelete={onDelete}
            onRename={onRename}
          />
        </div>
        <Link className="project-card__link" href={getProjectHref(project)}>
          {stageIndex >= 0 ? (
            <div
              className="project-progress"
              role="img"
              aria-label={progressLabel}
            >
              {STAGE_ORDER.map((stage, index) => (
                <span
                  key={stage}
                  className={[
                    "project-progress__step",
                    index <= stageIndex ? "project-progress__step--active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                />
              ))}
            </div>
          ) : null}
          <CardTitle>{highlightText(project.title, search)}</CardTitle>
          <CardDescription>
            {highlightText(project.description, search)}
          </CardDescription>
        </Link>
      </CardHeader>
    </Card>
  );
}

function ProjectCardActions({
  pageMessages,
  project,
  workspaceMessages,
  onArchiveToggle,
  onDelete,
  onRename,
}: {
  pageMessages: PageMessages;
  project: ProjectSummary;
  workspaceMessages: ProjectsWorkspaceMessages;
  onArchiveToggle: (project: ProjectSummary) => void;
  onDelete: (project: ProjectSummary) => void;
  onRename: (project: ProjectSummary) => void;
}) {
  return (
    <details className="project-actions">
      <summary
        className="project-actions__summary"
        aria-label={interpolate(pageMessages.actionMenuAriaLabel, {
          projectTitle: project.title,
        })}
      >
        <span aria-hidden="true">...</span>
      </summary>
      <div className="project-actions__menu" role="menu">
        <button
          type="button"
          className="project-actions__item"
          role="menuitem"
          onClick={(event) => {
            closeActionMenu(event.currentTarget);
            onRename(project);
          }}
        >
          {workspaceMessages.renameModal.title}
        </button>
        <button
          type="button"
          className="project-actions__item"
          role="menuitem"
          onClick={(event) => {
            closeActionMenu(event.currentTarget);
            onArchiveToggle(project);
          }}
        >
          {project.isArchived ? pageMessages.unarchive : pageMessages.archive}
        </button>
        <div className="project-actions__divider" role="separator" />
        <button
          type="button"
          className="project-actions__item project-actions__item--danger"
          role="menuitem"
          onClick={(event) => {
            closeActionMenu(event.currentTarget);
            onDelete(project);
          }}
        >
          {workspaceMessages.deleteModal.title}
        </button>
      </div>
    </details>
  );
}

function closeActionMenu(target: HTMLElement) {
  const details = target.closest("details");
  if (details) {
    details.removeAttribute("open");
  }
}

export function ProjectsOrgPickerModal({
  commonMessages,
  currentOrgId,
  descriptionId,
  isSubmitting,
  orgChoices,
  orgPickerMessages,
  selectionError,
  selectionId,
  titleId,
  onConfirm,
  onSelectionChange,
}: {
  commonMessages: CommonMessages;
  currentOrgId: string | null;
  descriptionId: string;
  isSubmitting: boolean;
  orgChoices: OrgChoice[];
  orgPickerMessages: OrgPickerMessages;
  selectionError: string | null;
  selectionId: string | null;
  titleId: string;
  onConfirm: () => void;
  onSelectionChange: (orgId: string) => void;
}) {
  return (
    <div className="modal-overlay" role="presentation">
      <Card
        className="modal-card org-picker-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <CardHeader className="modal-header">
          <div className="stack-sm">
            <CardTitle id={titleId}>{orgPickerMessages.title}</CardTitle>
            <CardDescription id={descriptionId}>
              {orgPickerMessages.description}
            </CardDescription>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="modal-body">
          <fieldset className="org-picker-list">
            <legend className="sr-only">{orgPickerMessages.legend}</legend>
            {orgChoices.map((org) => {
              const isActive = org.status === "active";
              const isSelected = selectionId === org.id;
              const isCurrent = org.id === currentOrgId;
              return (
                <label
                  key={org.id}
                  className={[
                    "org-picker-option",
                    isSelected ? "org-picker-option--selected" : "",
                    !isActive ? "org-picker-option--disabled" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <input
                    type="radio"
                    name="org-selection"
                    value={org.id}
                    checked={isSelected}
                    onChange={() => onSelectionChange(org.id)}
                    disabled={!isActive}
                  />
                  <div className="org-picker-option__content">
                    <span className="org-picker-option__name">{org.name}</span>
                    {isCurrent ? (
                      <span className="org-picker-option__hint text-muted">
                        {commonMessages.currentOrganization}
                      </span>
                    ) : null}
                  </div>
                  <div className="org-picker-option__badges">
                    <Badge variant="secondary">
                      {formatOrgRoleLabel(org.orgRole, commonMessages.memberRole)}
                    </Badge>
                    {isCurrent ? (
                      <Badge variant="outline">{commonMessages.currentBadge}</Badge>
                    ) : null}
                    {!isActive ? (
                      <Badge variant="outline">{commonMessages.invitedBadge}</Badge>
                    ) : null}
                  </div>
                </label>
              );
            })}
          </fieldset>
          {selectionError ? (
            <div className="alert" role="alert">
              <span>{selectionError}</span>
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="modal-footer">
          <span className="text-muted">
            {orgPickerMessages.projectsLoadHint}
          </span>
          <Button
            onClick={onConfirm}
            disabled={isSubmitting || !selectionId}
          >
            {isSubmitting ? orgPickerMessages.switching : commonMessages.continue}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
