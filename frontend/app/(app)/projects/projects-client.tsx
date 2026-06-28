"use client";

import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Separator } from "@/components/ui/separator";
import { useUserSession } from "@/features/auth/user-session";
import {
  deleteProject,
  fetchProjects,
  getProjectsErrorMessage,
  getProjectUpdateErrorMessage,
  updateProject,
  type ProjectsArchivedFilter,
  type ProjectsSortField,
  type ProjectsSortOrder,
  type ProjectCreateResult,
  type ProjectSummary,
} from "@/features/projects/projects";
import { CreateProjectModal } from "@/features/projects/create-project-modal";
import {
  DeleteProjectModal,
  RenameProjectModal,
} from "@/features/projects/project-action-modals";
import {
  ARCHIVED_FILTERS,
  DEFAULT_ARCHIVED_FILTER,
  DEFAULT_SORT_FIELD,
  DEFAULT_SORT_ORDER,
  ORG_SELECTION_SESSION_KEY,
  SORT_FIELDS,
  SORT_ORDERS,
  filterProjects,
  interpolate,
} from "@/features/projects/projects-workspace-utils";
import {
  ProjectsOrgPickerModal,
  ProjectsWorkspaceContent,
  ProjectsWorkspaceFilters,
  ProjectsWorkspaceHeader,
  ProjectsWorkspaceTabs,
} from "@/features/projects/projects-workspace-panels";
import { INVITE_ERROR_QUERY_KEY } from "@/features/invitations/invite-accept";
import { buildLocalePath, stripLocalePrefix } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { orgStorage } from "@/lib/storage/org";

export default function ProjectsClient() {
  const locale = useAppLocale();
  const workspaceMessages = useAppMessages().projectsWorkspace;
  const commonMessages = workspaceMessages.common;
  const pageMessages = workspaceMessages.page;
  const orgPickerMessages = workspaceMessages.orgPicker;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, status: sessionStatus, refresh } = useUserSession();
  const inviteError = searchParams.get(INVITE_ERROR_QUERY_KEY);
  const stageFilter = (searchParams.get("stage") ?? "").toLowerCase();
  const isReportsView = stageFilter === "report";
  const stageParam = isReportsView ? "report" : undefined;
  const archivedParam = (
    searchParams.get("archived") ?? DEFAULT_ARCHIVED_FILTER
  ).toLowerCase();
  const archivedFilter = ARCHIVED_FILTERS.includes(
    archivedParam as ProjectsArchivedFilter
  )
    ? (archivedParam as ProjectsArchivedFilter)
    : DEFAULT_ARCHIVED_FILTER;
  const sortParam = (searchParams.get("sort") ?? DEFAULT_SORT_FIELD).toLowerCase();
  const sortField = SORT_FIELDS.includes(sortParam as ProjectsSortField)
    ? (sortParam as ProjectsSortField)
    : DEFAULT_SORT_FIELD;
  const orderParam = (
    searchParams.get("order") ?? DEFAULT_SORT_ORDER
  ).toLowerCase();
  const sortOrder = SORT_ORDERS.includes(orderParam as ProjectsSortOrder)
    ? (orderParam as ProjectsSortOrder)
    : DEFAULT_SORT_ORDER;
  const queryParam = searchParams.get("q") ?? "";
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [search, setSearch] = useState(queryParam);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [allCount, setAllCount] = useState<number | null>(null);
  const [reportCount, setReportCount] = useState<number | null>(null);
  const [showOrgPicker, setShowOrgPicker] = useState(false);
  const [orgSelectionId, setOrgSelectionId] = useState<string | null>(null);
  const [orgSelectionError, setOrgSelectionError] = useState<string | null>(null);
  const [isOrgSelectionSubmitting, setIsOrgSelectionSubmitting] = useState(false);
  const orgPickerTitleId = useId();
  const orgPickerDescriptionId = useId();
  const [renameTarget, setRenameTarget] = useState<ProjectSummary | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null);
  const retryControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setSearch(queryParam);
  }, [queryParam]);

  const activeOrgs = useMemo(() => {
    if (!session) {
      return [];
    }
    const seen = new Set<string>();
    const active = session.orgs.filter((org) => {
      if (org.status !== "active") {
        return false;
      }
      if (seen.has(org.id)) {
        return false;
      }
      seen.add(org.id);
      return true;
    });
    if (!seen.has(session.org.id)) {
      active.push({
        id: session.org.id,
        name: session.org.name,
        orgRole: session.membership.orgRole,
        status: "active",
      });
    }
    return active;
  }, [session]);

  const invitedOrgs = useMemo(() => {
    if (!session) {
      return [];
    }
    const activeIds = new Set(activeOrgs.map((org) => org.id));
    return session.orgs.filter(
      (org) => org.status !== "active" && !activeIds.has(org.id)
    );
  }, [session, activeOrgs]);

  const orgChoices = useMemo(
    () => [...activeOrgs, ...invitedOrgs],
    [activeOrgs, invitedOrgs]
  );

  const loadProjects = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setError(null);

      try {
        const { projects: data, total } = await fetchProjects({
          signal,
          stage: stageParam,
          archived: archivedFilter,
          sort: sortField,
          order: sortOrder,
        });
        if (signal?.aborted) {
          return;
        }
        setProjects(data);
        if (stageParam === "report") {
          setReportCount(total);
        } else {
          setAllCount(total);
        }
      } catch (err) {
        if (signal?.aborted) {
          return;
        }
        setError(getProjectsErrorMessage(err));
      } finally {
        if (!signal?.aborted) {
          setIsLoading(false);
        }
      }
    },
    [archivedFilter, sortField, sortOrder, stageParam]
  );

  const handleRetry = useCallback(() => {
    retryControllerRef.current?.abort();
    const controller = new AbortController();
    retryControllerRef.current = controller;
    loadProjects(controller.signal);
  }, [loadProjects]);

  const handleOrgSelectionConfirm = useCallback(async () => {
    if (!orgSelectionId) {
      setOrgSelectionError(commonMessages.selectOrganizationError);
      return;
    }
    if (isOrgSelectionSubmitting) {
      return;
    }
    setIsOrgSelectionSubmitting(true);
    setOrgSelectionError(null);
    try {
      orgStorage.setOrgId(orgSelectionId);
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(ORG_SELECTION_SESSION_KEY, "1");
      }
      await refresh();
      setShowOrgPicker(false);
      setAllCount(null);
      setReportCount(null);
      await loadProjects();
    } catch {
      setOrgSelectionError(commonMessages.switchOrganizationError);
    } finally {
      setIsOrgSelectionSubmitting(false);
    }
  }, [
    isOrgSelectionSubmitting,
    loadProjects,
    orgSelectionId,
    refresh,
    setAllCount,
    setReportCount,
    commonMessages.selectOrganizationError,
    commonMessages.switchOrganizationError,
  ]);

  useEffect(() => {
    if (sessionStatus !== "ready" || !session) {
      return;
    }
    if (activeOrgs.length <= 1) {
      setShowOrgPicker(false);
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const selectionDone =
      window.sessionStorage.getItem(ORG_SELECTION_SESSION_KEY) === "1";
    if (selectionDone) {
      setShowOrgPicker(false);
      return;
    }
    const storedOrgId = orgStorage.getOrgId();
    const defaultOrgId =
      storedOrgId && activeOrgs.some((org) => org.id === storedOrgId)
        ? storedOrgId
        : session.org.id;
    setOrgSelectionId(defaultOrgId);
    setShowOrgPicker(true);
  }, [activeOrgs, session, sessionStatus]);

  useEffect(() => {
    if (!showOrgPicker) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [showOrgPicker]);

  useEffect(() => {
    const controller = new AbortController();
    loadProjects(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadProjects]);

  useEffect(() => {
    setAllCount(null);
    setReportCount(null);
  }, [archivedFilter]);

  useEffect(
    () => () => {
      retryControllerRef.current?.abort();
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    const loadCounts = async () => {
      try {
        if (stageParam === "report") {
          if (allCount === null) {
            const { total } = await fetchProjects({
              signal,
              limit: 1,
              offset: 0,
              archived: archivedFilter,
            });
            setAllCount(total);
          }
        } else if (reportCount === null) {
          const { total } = await fetchProjects({
            signal,
            stage: "report",
            limit: 1,
            offset: 0,
            archived: archivedFilter,
          });
          setReportCount(total);
        }
      } catch {
        if (signal.aborted) {
          return;
        }
      }
    };

    void loadCounts();
    return () => {
      controller.abort();
    };
  }, [allCount, archivedFilter, reportCount, stageParam]);

  useEffect(() => {
    if (!inviteError) {
      return;
    }
    setToastMessage(inviteError);
    const url = new URL(window.location.href);
    url.searchParams.delete(INVITE_ERROR_QUERY_KEY);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }, [inviteError]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [toastMessage]);

  const filteredProjects = useMemo(
    () => filterProjects(projects, search),
    [projects, search]
  );

  const isInitialLoading = isLoading && projects.length === 0;
  const showErrorBanner = Boolean(error) && projects.length > 0;
  const showErrorState = Boolean(error) && projects.length === 0;
  const showEmptyState = !isInitialLoading && !error && projects.length === 0;
  const showNoResults =
    !isInitialLoading &&
    !error &&
    projects.length > 0 &&
    filteredProjects.length === 0;

  const handleCreateProject = useCallback(() => {
    setIsCreateOpen(true);
  }, []);

  const handleCreateClose = useCallback(() => {
    setIsCreateOpen(false);
  }, []);

  const handleCreateSuccess = useCallback(
    (result: ProjectCreateResult) => {
      const matchesStage =
        stageParam === "report" ? result.project.stage.value === "report" : true;
      const matchesArchive =
        archivedFilter === "all"
          ? true
          : archivedFilter === "archived"
            ? result.project.isArchived
            : !result.project.isArchived;

      if (matchesStage && matchesArchive) {
        setProjects((prev) => [result.project, ...prev]);
      }

      if (archivedFilter !== "archived") {
        setAllCount((prev) => (prev === null ? null : prev + 1));
        if (result.project.stage.value === "report") {
          setReportCount((prev) => (prev === null ? null : prev + 1));
        }
      }
      setIsCreateOpen(false);
      router.push(buildLocalePath(locale, `/projects/${result.project.id}/chat`));
    },
    [archivedFilter, locale, router, stageParam]
  );

  const updateQueryParams = useCallback(
    (updates: {
      stage?: string | null;
      archived?: ProjectsArchivedFilter | null;
      sort?: ProjectsSortField | null;
      order?: ProjectsSortOrder | null;
    }) => {
      const url = new URL(window.location.href);
      const setParam = (key: string, value: string | null, fallback: string) => {
        if (!value || value === fallback) {
          url.searchParams.delete(key);
          return;
        }
        url.searchParams.set(key, value);
      };

      if ("stage" in updates) {
        const nextStage = updates.stage;
        if (nextStage) {
          url.searchParams.set("stage", nextStage);
        } else {
          url.searchParams.delete("stage");
        }
      }
      if ("archived" in updates) {
        setParam("archived", updates.archived ?? null, DEFAULT_ARCHIVED_FILTER);
      }
      if ("sort" in updates) {
        setParam("sort", updates.sort ?? null, DEFAULT_SORT_FIELD);
      }
      if ("order" in updates) {
        setParam("order", updates.order ?? null, DEFAULT_SORT_ORDER);
      }
      const nextPath = buildLocalePath(
        locale,
        stripLocalePrefix(url.pathname),
        url.search
      );
      router.push(`${nextPath}${url.hash}`);
    },
    [locale, router]
  );

  const handleTabChange = useCallback(
    (next: "all" | "report") => {
      updateQueryParams({ stage: next === "report" ? "report" : null });
    },
    [updateQueryParams]
  );

  const handleArchivedChange = useCallback(
    (nextValue: ProjectsArchivedFilter) => {
      updateQueryParams({ archived: nextValue });
    },
    [updateQueryParams]
  );

  const handleSortChange = useCallback(
    (nextValue: ProjectsSortField) => {
      updateQueryParams({ sort: nextValue });
    },
    [updateQueryParams]
  );

  const handleOrderToggle = useCallback(() => {
    const nextOrder: ProjectsSortOrder = sortOrder === "asc" ? "desc" : "asc";
    updateQueryParams({ order: nextOrder });
  }, [sortOrder, updateQueryParams]);

  const handleViewActive = useCallback(() => {
    updateQueryParams({ archived: "active" });
  }, [updateQueryParams]);

  const refreshProjects = useCallback(async () => {
    setAllCount(null);
    setReportCount(null);
    await loadProjects();
  }, [loadProjects]);

  const handleRenameSubmit = useCallback(
    async (projectId: string, title: string) => {
      await updateProject(projectId, { title });
      setToastMessage(commonMessages.renamedToast);
      await refreshProjects();
    },
    [commonMessages.renamedToast, refreshProjects]
  );

  const handleArchiveToggle = useCallback(
    async (project: ProjectSummary) => {
      try {
        await updateProject(project.id, { isArchived: !project.isArchived });
        setToastMessage(
          project.isArchived
            ? commonMessages.unarchivedToast
            : commonMessages.archivedToast
        );
        await refreshProjects();
      } catch (error) {
        setToastMessage(getProjectUpdateErrorMessage(error));
      }
    },
    [
      commonMessages.archivedToast,
      commonMessages.unarchivedToast,
      refreshProjects,
    ]
  );

  const handleDeleteSubmit = useCallback(
    async (projectId: string) => {
      await deleteProject(projectId);
      setToastMessage(commonMessages.deletedToast);
      await refreshProjects();
    },
    [commonMessages.deletedToast, refreshProjects]
  );

  const getProjectHref = useCallback(
    (project: ProjectSummary) =>
      isReportsView
        ? buildLocalePath(locale, `/projects/${project.id}/report`)
        : buildLocalePath(locale, `/projects/${project.id}/chat`),
    [isReportsView, locale]
  );

  const pageTitle = pageMessages.title;
  const pageEyebrow = pageMessages.eyebrow;
  const archiveSubtitle =
    archivedFilter === "archived"
      ? pageMessages.archivedOnly
      : archivedFilter === "all"
        ? pageMessages.includingArchived
        : pageMessages.activeOnly;
  const pageSubtitle = isReportsView
    ? interpolate(pageMessages.reportSubtitle, { archiveSubtitle })
    : interpolate(pageMessages.defaultSubtitle, { archiveSubtitle });
  const searchPlaceholder = isReportsView
    ? pageMessages.searchReportsPlaceholder
    : pageMessages.searchPlaceholder;
  const allLabel =
    allCount === null
      ? pageMessages.all
      : `${pageMessages.all} (${allCount})`;
  const reportLabel =
    reportCount === null
      ? pageMessages.reports
      : `${pageMessages.reports} (${reportCount})`;
  const orderLabel =
    sortField === "title"
      ? sortOrder === "asc"
        ? pageMessages.orderLabels.titleAsc
        : pageMessages.orderLabels.titleDesc
      : sortOrder === "asc"
        ? sortField === "created_at"
          ? pageMessages.orderLabels.createdAsc
          : pageMessages.orderLabels.updatedAsc
        : sortField === "created_at"
          ? pageMessages.orderLabels.createdDesc
          : pageMessages.orderLabels.updatedDesc;
  const isArchivedView = archivedFilter === "archived";
  const emptyTitle = isReportsView
    ? isArchivedView
      ? pageMessages.emptyTitles.archivedReport
      : pageMessages.emptyTitles.report
    : isArchivedView
      ? pageMessages.emptyTitles.archived
      : pageMessages.emptyTitles.active;
  const emptyDescription = isArchivedView
    ? pageMessages.emptyDescriptions.archived
    : isReportsView
      ? pageMessages.emptyDescriptions.report
      : pageMessages.emptyDescriptions.active;
  const emptyActionLabel = isArchivedView
    ? isReportsView
      ? pageMessages.emptyActions.activeReports
      : pageMessages.emptyActions.activeProjects
    : isReportsView
      ? pageMessages.emptyActions.allProjects
      : pageMessages.emptyActions.newProject;

  return (
    <div className="page">
      <ProjectsWorkspaceHeader
        isLoading={isLoading}
        pageEyebrow={pageEyebrow}
        pageMessages={pageMessages}
        pageSubtitle={pageSubtitle}
        pageTitle={pageTitle}
        search={search}
        searchPlaceholder={searchPlaceholder}
        onCreateProject={handleCreateProject}
        onSearchChange={setSearch}
      />

      <ProjectsWorkspaceTabs
        allLabel={allLabel}
        isReportsView={isReportsView}
        pageMessages={pageMessages}
        reportLabel={reportLabel}
        onTabChange={handleTabChange}
      />

      <ProjectsWorkspaceFilters
        archivedFilter={archivedFilter}
        orderLabel={orderLabel}
        pageMessages={pageMessages}
        sortField={sortField}
        onArchivedChange={handleArchivedChange}
        onOrderToggle={handleOrderToggle}
        onSortChange={handleSortChange}
      />

      <Separator />

      <ProjectsWorkspaceContent
        commonMessages={commonMessages}
        emptyActionLabel={emptyActionLabel}
        emptyDescription={emptyDescription}
        emptyTitle={emptyTitle}
        error={error}
        filteredProjects={filteredProjects}
        getProjectHref={getProjectHref}
        isArchivedView={isArchivedView}
        isInitialLoading={isInitialLoading}
        isReportsView={isReportsView}
        pageMessages={pageMessages}
        search={search}
        showEmptyState={showEmptyState}
        showErrorBanner={showErrorBanner}
        showErrorState={showErrorState}
        showNoResults={showNoResults}
        sortField={sortField}
        workspaceMessages={workspaceMessages}
        onArchiveToggle={(project) => void handleArchiveToggle(project)}
        onClearSearch={() => setSearch("")}
        onCreateProject={handleCreateProject}
        onDelete={setDeleteTarget}
        onRetry={handleRetry}
        onRename={setRenameTarget}
        onTabChange={handleTabChange}
        onViewActive={handleViewActive}
      />

      {showOrgPicker ? (
        <ProjectsOrgPickerModal
          commonMessages={commonMessages}
          currentOrgId={session?.org.id ?? null}
          descriptionId={orgPickerDescriptionId}
          isSubmitting={isOrgSelectionSubmitting}
          orgChoices={orgChoices}
          orgPickerMessages={orgPickerMessages}
          selectionError={orgSelectionError}
          selectionId={orgSelectionId}
          titleId={orgPickerTitleId}
          onConfirm={handleOrgSelectionConfirm}
          onSelectionChange={(orgId) => {
            setOrgSelectionId(orgId);
            if (orgSelectionError) {
              setOrgSelectionError(null);
            }
          }}
        />
      ) : null}

      {isCreateOpen ? (
        <CreateProjectModal
          onClose={handleCreateClose}
          onCreate={handleCreateSuccess}
        />
      ) : null}

      {renameTarget ? (
        <RenameProjectModal
          project={renameTarget}
          onClose={() => setRenameTarget(null)}
          onSubmit={handleRenameSubmit}
        />
      ) : null}

      {deleteTarget ? (
        <DeleteProjectModal
          project={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handleDeleteSubmit}
        />
      ) : null}

      {toastMessage ? (
        <div className="admin-toast" role="status" aria-live="polite">
          <span className="admin-toast__title">{toastMessage}</span>
        </div>
      ) : null}
    </div>
  );
}
