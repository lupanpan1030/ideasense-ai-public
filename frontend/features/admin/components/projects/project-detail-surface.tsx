import type { FormEventHandler } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button, buttonClassNames } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { buildLocalePath, type AppLocale } from "@/lib/i18n/config";
import type { useAppMessages } from "@/lib/i18n/provider";

import type {
  DetailTab,
  ProjectCommentItem,
  ProjectDetailResponse,
  ProjectReportItem,
  ReportStatus,
} from "./project-detail-types";

type AdminProjectDetailMessages = ReturnType<
  typeof useAppMessages
>["adminProjectDetail"];

type ProjectDetailSurfaceProps = {
  locale: AppLocale;
  intlLocale: string;
  messages: AdminProjectDetailMessages;
  unknownOwnerLabel: string;
  project: ProjectDetailResponse | null;
  isLoading: boolean;
  loadError: string | null;
  activeTab: DetailTab;
  stageLabel: string;
  statusLabel: string;
  statusVariant: "warning" | "info" | "success";
  reports: ProjectReportItem[];
  reportsError: string | null;
  isReportsLoading: boolean;
  reportCountLabel: string;
  comments: ProjectCommentItem[];
  commentsTotal: number;
  commentsPage: number;
  commentsError: string | null;
  isCommentsLoading: boolean;
  commentDraft: string;
  isSubmittingComment: boolean;
  commentFormError: string | null;
  commentPageStart: number;
  commentPageEnd: number;
  commentTotalPages: number;
  canCommentBack: boolean;
  canCommentForward: boolean;
  toastMessage: string | null;
  onOpenEdit: () => void;
  onTabChange: (tab: DetailTab) => void;
  onCommentDraftChange: (value: string) => void;
  onCommentSubmit: FormEventHandler<HTMLFormElement>;
  onRequestDeleteComment: (comment: ProjectCommentItem) => void;
  onPreviousCommentsPage: () => void;
  onNextCommentsPage: () => void;
};

const REPORT_STATUS_VARIANTS: Record<
  ReportStatus,
  "warning" | "success" | "default"
> = {
  draft: "warning",
  final: "success",
  archived: "default",
};

export const resolveIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

const resolveInitials = (value: string): string => {
  const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, " ").trim();
  if (!cleaned) {
    return "IS";
  }
  const parts = cleaned.split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "IS";
};

const formatDate = (value: string, locale: AppLocale): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(resolveIntlLocale(locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
};

const formatDateTime = (value: string, locale: AppLocale): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(resolveIntlLocale(locale), {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
};

export const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export function ProjectDetailSurface({
  locale,
  intlLocale,
  messages,
  unknownOwnerLabel,
  project,
  isLoading,
  loadError,
  activeTab,
  stageLabel,
  statusLabel,
  statusVariant,
  reports,
  reportsError,
  isReportsLoading,
  reportCountLabel,
  comments,
  commentsTotal,
  commentsPage,
  commentsError,
  isCommentsLoading,
  commentDraft,
  isSubmittingComment,
  commentFormError,
  commentPageStart,
  commentPageEnd,
  commentTotalPages,
  canCommentBack,
  canCommentForward,
  toastMessage,
  onOpenEdit,
  onTabChange,
  onCommentDraftChange,
  onCommentSubmit,
  onRequestDeleteComment,
  onPreviousCommentsPage,
  onNextCommentsPage,
}: ProjectDetailSurfaceProps) {
  const ownerLabel = project
    ? project.owner.display_name || project.owner.email || unknownOwnerLabel
    : "--";
  const ownerEmail = project?.owner.email || null;
  const ownerInitials = resolveInitials(ownerLabel);

  return (
    <div className="page">
      <div className="page-header">
        <div className="stack-sm">
          <p className="eyebrow">{messages.page.eyebrow}</p>
          <div className="admin-project-detail__headline">
            <h1 className="page-title">
              {project?.title || messages.page.fallbackTitle}
            </h1>
            <Badge variant="info">{stageLabel}</Badge>
            <Badge variant={statusVariant}>{statusLabel}</Badge>
            {project?.is_archived ? (
              <Badge variant="warning">{messages.page.archived}</Badge>
            ) : null}
          </div>
          <p className="page-subtitle">
            {project?.description || messages.page.fallbackDescription}
          </p>
          {project ? (
            <div className="admin-project-detail__meta">
              <div className="admin-member__identity">
                <div className="admin-member__avatar">{ownerInitials}</div>
                <div className="stack-sm">
                  <span className="admin-member__name">{ownerLabel}</span>
                  {ownerEmail ? (
                    <span className="admin-member__email">{ownerEmail}</span>
                  ) : null}
                </div>
              </div>
              <div className="admin-project-detail__meta-item">
                <span className="text-muted">{messages.page.cohortLabel}</span>
                <strong>{project.cohort?.name || messages.page.global}</strong>
              </div>
              <div className="admin-project-detail__meta-item">
                <span className="text-muted">{messages.page.updatedLabel}</span>
                <strong>{formatDate(project.updated_at, locale)}</strong>
              </div>
            </div>
          ) : null}
        </div>
        <div className="admin-project-detail__header-actions">
          <Link
            className={buttonClassNames({ variant: "secondary", size: "sm" })}
            href={buildLocalePath(locale, "/admin/projects")}
          >
            {messages.page.backToProjects}
          </Link>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={onOpenEdit}
            disabled={!project || isLoading}
          >
            {messages.page.editProject}
          </Button>
        </div>
      </div>

      {loadError ? (
        <div className="alert" role="alert">
          <span>{loadError}</span>
        </div>
      ) : null}

      <Card className="admin-project-detail">
        <CardHeader className="admin-project-detail__tabs">
          <div
            className="admin-tabs"
            role="tablist"
            aria-label={messages.tabs.ariaLabel}
          >
            {(["summary", "reports", "comments"] as DetailTab[]).map((tab) => (
              <button
                key={tab}
                type="button"
                className={[
                  "admin-tab",
                  activeTab === tab ? "admin-tab--active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => onTabChange(tab)}
                role="tab"
                aria-selected={activeTab === tab}
              >
                {tab === "summary"
                  ? messages.tabs.summary
                  : tab === "reports"
                    ? messages.tabs.reports
                    : messages.tabs.comments}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="stack">
          {isLoading ? (
            <div className="admin-project-detail__empty">
              {messages.states.loadingProject}
            </div>
          ) : null}

          {!isLoading && activeTab === "summary" ? (
            <div className="admin-project-summary">
              <div className="admin-project-summary__row">
                <span className="text-muted">{messages.summary.stage}</span>
                <strong>{stageLabel}</strong>
              </div>
              <div className="admin-project-summary__row">
                <span className="text-muted">{messages.summary.status}</span>
                <strong>{statusLabel}</strong>
              </div>
              <div className="admin-project-summary__row">
                <span className="text-muted">{messages.summary.created}</span>
                <strong>{project ? formatDate(project.created_at, locale) : "--"}</strong>
              </div>
              <div className="admin-project-summary__row">
                <span className="text-muted">{messages.summary.updated}</span>
                <strong>{project ? formatDate(project.updated_at, locale) : "--"}</strong>
              </div>
            </div>
          ) : null}

          {!isLoading && activeTab === "reports" ? (
            <div className="admin-report-timeline">
              <div className="admin-report-timeline__header">
                <span className="text-muted">{reportCountLabel}</span>
              </div>
              {isReportsLoading ? (
                <div className="admin-project-detail__empty">
                  {messages.states.loadingReports}
                </div>
              ) : reportsError ? (
                <div className="alert" role="alert">
                  <span>{reportsError}</span>
                </div>
              ) : reports.length === 0 ? (
                <div className="admin-project-detail__empty">
                  {messages.states.noReports}
                </div>
              ) : (
                reports.map((report) => (
                  <div key={report.id} className="admin-report-item">
                    <div className="admin-report-item__marker" aria-hidden="true" />
                    <div className="admin-report-item__body">
                      <div className="admin-report-item__header">
                        <div className="admin-report-item__meta">
                          <strong>
                            {interpolate(messages.reports.reportVersion, {
                              version: report.report_version,
                            })}
                          </strong>
                          <span className="text-muted">
                            {formatDateTime(report.created_at, locale)}
                          </span>
                        </div>
                        <Badge variant={REPORT_STATUS_VARIANTS[report.status]}>
                          {messages.reportStatuses[report.status]}
                        </Badge>
                      </div>
                      {report.content_markdown ? (
                        <pre className="admin-report__content">
                          {report.content_markdown}
                        </pre>
                      ) : (
                        <p className="text-muted">{messages.states.noReportContent}</p>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : null}

          {!isLoading && activeTab === "comments" ? (
            <div className="admin-project-comments">
              <form
                className="admin-project-comment__composer"
                onSubmit={onCommentSubmit}
              >
                <div className="field">
                  <label className="field__label" htmlFor="project-comment">
                    {messages.comments.addComment}
                  </label>
                  <textarea
                    id="project-comment"
                    className="textarea"
                    rows={4}
                    placeholder={messages.comments.placeholder}
                    value={commentDraft}
                    onChange={(event) => onCommentDraftChange(event.target.value)}
                    disabled={isSubmittingComment}
                    required
                  />
                  <span className="field__hint">
                    {messages.comments.visibilityHint}
                  </span>
                </div>
                {commentFormError ? (
                  <div className="alert" role="alert">
                    <span>{commentFormError}</span>
                  </div>
                ) : null}
                <div className="admin-project-comment__actions">
                  <Button type="submit" disabled={isSubmittingComment}>
                    {isSubmittingComment
                      ? messages.comments.posting
                      : messages.comments.postComment}
                  </Button>
                </div>
              </form>

              {commentsError ? (
                <div className="alert" role="alert">
                  <span>{commentsError}</span>
                </div>
              ) : null}

              {isCommentsLoading ? (
                <div className="admin-project-detail__empty">
                  {messages.states.loadingComments}
                </div>
              ) : comments.length === 0 ? (
                <div className="admin-project-detail__empty">
                  {messages.states.noComments}
                </div>
              ) : (
                <div className="admin-project-comment__list">
                  {comments.map((comment) => {
                    const authorLabel =
                      comment.author.display_name ||
                      comment.author.email ||
                      messages.comments.unknownAuthor;
                    const authorInitials = resolveInitials(authorLabel);
                    return (
                      <div key={comment.id} className="admin-project-comment">
                        <div className="admin-project-comment__header">
                          <div className="admin-member__identity">
                            <div className="admin-member__avatar">
                              {authorInitials}
                            </div>
                            <div className="stack-sm">
                              <span className="admin-member__name">
                                {authorLabel}
                              </span>
                              {comment.author.email ? (
                                <span className="admin-member__email">
                                  {comment.author.email}
                                </span>
                              ) : null}
                            </div>
                          </div>
                          <div className="admin-project-comment__meta">
                            <span className="text-muted">
                              {formatDateTime(comment.created_at, locale)}
                            </span>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="admin-project-comment__delete"
                              onClick={() => onRequestDeleteComment(comment)}
                              aria-label={messages.comments.deleteAriaLabel}
                            >
                              <svg
                                viewBox="0 0 24 24"
                                aria-hidden="true"
                                focusable="false"
                              >
                                <path
                                  d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9z"
                                  fill="currentColor"
                                />
                              </svg>
                            </Button>
                          </div>
                        </div>
                        <div className="admin-project-comment__body">
                          {comment.content}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}
        </CardContent>
        {activeTab === "comments" && !isCommentsLoading ? (
          <CardFooter className="admin-project-comments__footer">
            <span className="text-muted">
              {interpolate(messages.commentsPagination.showing, {
                start: commentPageStart,
                end: commentPageEnd,
                total: commentsTotal.toLocaleString(intlLocale),
              })}
            </span>
            <div className="admin-project-comments__pagination">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={onPreviousCommentsPage}
                disabled={!canCommentBack}
              >
                {messages.commentsPagination.previous}
              </Button>
              <span className="text-muted">
                {interpolate(messages.commentsPagination.page, {
                  current: commentsPage,
                  total: commentTotalPages,
                })}
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={onNextCommentsPage}
                disabled={!canCommentForward}
              >
                {messages.commentsPagination.next}
              </Button>
            </div>
          </CardFooter>
        ) : null}
      </Card>

      {toastMessage ? (
        <div className="admin-toast" role="status" aria-live="polite">
          <span className="admin-toast__title">{toastMessage}</span>
        </div>
      ) : null}
    </div>
  );
}
