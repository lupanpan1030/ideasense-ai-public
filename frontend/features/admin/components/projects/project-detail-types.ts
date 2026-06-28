export type Stage = "problem" | "market" | "tech" | "report";

export type StageStatus = "in_progress" | "awaiting_confirm" | "passed";

export type ReportStatus = "draft" | "final" | "archived";

export type ProjectOwner = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

export type ProjectCohort = {
  id: string;
  name: string;
  is_archived: boolean;
};

export type ProjectDetailResponse = {
  id: string;
  title: string;
  description: string | null;
  current_stage: string | null;
  stage_status: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  owner: ProjectOwner;
  cohort: ProjectCohort | null;
};

export type ProjectReportItem = {
  id: string;
  report_version: number;
  status: ReportStatus;
  created_at: string;
  updated_at: string;
  confirmed: boolean;
  content_markdown: string | null;
};

export type ProjectReportsResponse = {
  reports: ProjectReportItem[];
};

export type ProjectCommentAuthor = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

export type ProjectCommentItem = {
  id: string;
  content: string;
  visibility: string;
  created_at: string;
  author: ProjectCommentAuthor;
};

export type ProjectCommentsResponse = {
  comments: ProjectCommentItem[];
  total: number;
  page: number;
  limit: number;
};

export type DetailTab = "summary" | "reports" | "comments";
