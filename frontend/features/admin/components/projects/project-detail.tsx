"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, apiClient } from "@/lib/api/client";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import {
  DeleteProjectCommentModal,
  EditProjectModal,
} from "./project-detail-dialogs";
import {
  ProjectDetailSurface,
  interpolate,
  resolveIntlLocale,
} from "./project-detail-surface";
import type {
  DetailTab,
  ProjectCommentItem,
  ProjectCommentsResponse,
  ProjectDetailResponse,
  ProjectReportItem,
  ProjectReportsResponse,
  Stage,
  StageStatus,
} from "./project-detail-types";

const DEFAULT_LIMIT = 20;

const STATUS_VARIANTS: Record<StageStatus, "warning" | "info" | "success"> = {
  in_progress: "warning",
  awaiting_confirm: "info",
  passed: "success",
};

const getProjectErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminProjectDetail"]
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status >= 500) {
      return messages.errors.unavailable;
    }
  }
  return messages.errors.loadFailed;
};

const fetchProjectDetail = async (
  projectId: string
): Promise<ProjectDetailResponse> =>
  apiClient.fetchJson<ProjectDetailResponse>(`/admin-api/projects/${projectId}`);

const fetchProjectReports = async (
  projectId: string
): Promise<ProjectReportsResponse> =>
  apiClient.fetchJson<ProjectReportsResponse>(
    `/admin-api/projects/${projectId}/reports`
  );

const fetchProjectComments = async (
  projectId: string,
  page: number
): Promise<ProjectCommentsResponse> => {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(DEFAULT_LIMIT),
  });
  return apiClient.fetchJson<ProjectCommentsResponse>(
    `/admin-api/projects/${projectId}/comments?${params.toString()}`
  );
};

const updateProject = async (
  projectId: string,
  payload: {
    title?: string;
    description?: string;
    current_stage?: Stage;
    stage_status?: StageStatus;
  }
): Promise<ProjectDetailResponse> =>
  apiClient.postJson<ProjectDetailResponse>(
    `/admin-api/projects/${projectId}`,
    payload,
    { method: "PATCH" }
  );

const createProjectComment = async (
  projectId: string,
  payload: { content: string }
): Promise<ProjectCommentItem> =>
  apiClient.postJson<ProjectCommentItem>(
    `/admin-api/projects/${projectId}/comments`,
    payload
  );

const deleteProjectComment = async (
  projectId: string,
  commentId: string
): Promise<void> => {
  await apiClient.fetchJson(
    `/admin-api/projects/${projectId}/comments/${commentId}`,
    {
      method: "DELETE",
    }
  );
};

type ProjectDetailProps = {
  projectId: string;
};

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminProjectDetail;
  const intlLocale = resolveIntlLocale(locale);
  const searchParams = useSearchParams();
  const [project, setProject] = useState<ProjectDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>(() => {
    const requested = searchParams?.get("tab");
    if (requested === "reports" || requested === "comments") {
      return requested;
    }
    return "summary";
  });
  const [reports, setReports] = useState<ProjectReportItem[]>([]);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [isReportsLoading, setIsReportsLoading] = useState(false);
  const [comments, setComments] = useState<ProjectCommentItem[]>([]);
  const [commentsTotal, setCommentsTotal] = useState(0);
  const [commentsPage, setCommentsPage] = useState(1);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [isCommentsLoading, setIsCommentsLoading] = useState(false);
  const [commentDraft, setCommentDraft] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [commentFormError, setCommentFormError] = useState<string | null>(null);
  const [commentToDelete, setCommentToDelete] =
    useState<ProjectCommentItem | null>(null);
  const [isDeletingComment, setIsDeletingComment] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editDraft, setEditDraft] = useState({
    title: "",
    description: "",
    current_stage: "problem" as Stage,
    stage_status: "in_progress" as StageStatus,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const commentTotalPages = Math.max(
    1,
    Math.ceil(commentsTotal / DEFAULT_LIMIT)
  );
  const commentPageStart =
    commentsTotal === 0 ? 0 : (commentsPage - 1) * DEFAULT_LIMIT + 1;
  const commentPageEnd = Math.min(
    commentsTotal,
    commentsPage * DEFAULT_LIMIT
  );
  const canCommentBack = commentsPage > 1;
  const canCommentForward = commentsPage < commentTotalPages;

  const stageValue = project?.current_stage as Stage | null | undefined;
  const statusValue = project?.stage_status as StageStatus | null | undefined;
  const stageLabel = stageValue
    ? messages.stageLabels[stageValue] ?? stageValue
    : "--";
  const statusLabel = statusValue
    ? messages.stageStatuses[statusValue] ?? statusValue
    : "--";
  const statusVariant = statusValue
    ? STATUS_VARIANTS[statusValue] ?? "warning"
    : "warning";

  const loadDetail = useCallback(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchProjectDetail(projectId)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setProject(response);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getProjectErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [projectId, messages]);

  useEffect(() => loadDetail(), [loadDetail]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    if (!project) {
      return;
    }
    setEditDraft({
      title: project.title,
      description: project.description ?? "",
      current_stage: (project.current_stage as Stage) ?? "problem",
      stage_status: (project.stage_status as StageStatus) ?? "in_progress",
    });
  }, [project]);

  useEffect(() => {
    if (activeTab !== "reports") {
      return;
    }
    let isActive = true;
    setIsReportsLoading(true);
    setReportsError(null);
    fetchProjectReports(projectId)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setReports(response.reports ?? []);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setReportsError(getProjectErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsReportsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [activeTab, projectId, messages]);

  useEffect(() => {
    if (activeTab !== "comments") {
      return;
    }
    setCommentsPage(1);
  }, [activeTab, projectId]);

  useEffect(() => {
    if (activeTab !== "comments") {
      return;
    }
    let isActive = true;
    setIsCommentsLoading(true);
    setCommentsError(null);
    fetchProjectComments(projectId, commentsPage)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setComments(response.comments ?? []);
        setCommentsTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setCommentsError(getProjectErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsCommentsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [activeTab, projectId, commentsPage, messages]);

  const stageOptions = useMemo(
    () => [
      { value: "problem", label: messages.stageLabels.problem },
      { value: "market", label: messages.stageLabels.market },
      { value: "tech", label: messages.stageLabels.tech },
      { value: "report", label: messages.stageLabels.report },
    ] satisfies Array<{ value: Stage; label: string }>,
    [messages]
  );

  const statusOptions = useMemo(
    () => [
      { value: "in_progress", label: messages.stageStatuses.in_progress },
      {
        value: "awaiting_confirm",
        label: messages.stageStatuses.awaiting_confirm,
      },
      { value: "passed", label: messages.stageStatuses.passed },
    ] satisfies Array<{ value: StageStatus; label: string }>,
    [messages]
  );

  const handleOpenEdit = () => {
    if (!project) {
      return;
    }
    setEditError(null);
    setIsEditOpen(true);
  };

  const handleCloseEdit = () => {
    if (isSaving) {
      return;
    }
    setIsEditOpen(false);
  };

  const handleEditSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!project) {
      return;
    }
    setEditError(null);
    setIsSaving(true);
    try {
      const updated = await updateProject(project.id, {
        title: editDraft.title,
        description: editDraft.description,
        current_stage: editDraft.current_stage,
        stage_status: editDraft.stage_status,
      });
      setProject(updated);
      setToastMessage(messages.toasts.projectUpdated);
      setIsEditOpen(false);
    } catch (error) {
      setEditError(getProjectErrorMessage(error, messages));
    } finally {
      setIsSaving(false);
    }
  };

  const handleCommentSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!commentDraft.trim()) {
      setCommentFormError(messages.comments.emptyError);
      return;
    }
    setCommentFormError(null);
    setIsSubmittingComment(true);
    try {
      await createProjectComment(projectId, { content: commentDraft.trim() });
      setCommentDraft("");
      setToastMessage(messages.toasts.commentPosted);
      setCommentsPage(1);
      if (activeTab === "comments") {
        const response = await fetchProjectComments(projectId, 1);
        setComments(response.comments ?? []);
        setCommentsTotal(response.total ?? 0);
      }
    } catch (error) {
      setCommentFormError(getProjectErrorMessage(error, messages));
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleDeleteComment = async () => {
    if (!commentToDelete) {
      return;
    }
    setIsDeletingComment(true);
    try {
      await deleteProjectComment(projectId, commentToDelete.id);
      setToastMessage(messages.toasts.commentDeleted);
      const response = await fetchProjectComments(projectId, commentsPage);
      setComments(response.comments ?? []);
      setCommentsTotal(response.total ?? 0);
    } catch (error) {
      setCommentsError(getProjectErrorMessage(error, messages));
    } finally {
      setIsDeletingComment(false);
      setCommentToDelete(null);
    }
  };

  const reportCountLabel = useMemo(
    () =>
      interpolate(messages.reports.countLabel, {
        count: reports.length.toLocaleString(intlLocale),
      }),
    [intlLocale, messages, reports.length]
  );

  return (
    <>
      <ProjectDetailSurface
        locale={locale}
        intlLocale={intlLocale}
        messages={messages}
        unknownOwnerLabel={appMessages.adminProjects.table.unknownOwner}
        project={project}
        isLoading={isLoading}
        loadError={loadError}
        activeTab={activeTab}
        stageLabel={stageLabel}
        statusLabel={statusLabel}
        statusVariant={statusVariant}
        reports={reports}
        reportsError={reportsError}
        isReportsLoading={isReportsLoading}
        reportCountLabel={reportCountLabel}
        comments={comments}
        commentsTotal={commentsTotal}
        commentsPage={commentsPage}
        commentsError={commentsError}
        isCommentsLoading={isCommentsLoading}
        commentDraft={commentDraft}
        isSubmittingComment={isSubmittingComment}
        commentFormError={commentFormError}
        commentPageStart={commentPageStart}
        commentPageEnd={commentPageEnd}
        commentTotalPages={commentTotalPages}
        canCommentBack={canCommentBack}
        canCommentForward={canCommentForward}
        toastMessage={toastMessage}
        onOpenEdit={handleOpenEdit}
        onTabChange={setActiveTab}
        onCommentDraftChange={setCommentDraft}
        onCommentSubmit={handleCommentSubmit}
        onRequestDeleteComment={setCommentToDelete}
        onPreviousCommentsPage={() => setCommentsPage(Math.max(commentsPage - 1, 1))}
        onNextCommentsPage={() => setCommentsPage(commentsPage + 1)}
      />

      {isEditOpen ? (
        <EditProjectModal
          messages={messages}
          editDraft={editDraft}
          stageOptions={stageOptions}
          statusOptions={statusOptions}
          editError={editError}
          isSaving={isSaving}
          onClose={handleCloseEdit}
          onSubmit={handleEditSubmit}
          onDraftChange={setEditDraft}
        />
      ) : null}

      {commentToDelete ? (
        <DeleteProjectCommentModal
          messages={messages}
          isDeletingComment={isDeletingComment}
          onClose={() => setCommentToDelete(null)}
          onConfirm={handleDeleteComment}
        />
      ) : null}
    </>
  );
}
