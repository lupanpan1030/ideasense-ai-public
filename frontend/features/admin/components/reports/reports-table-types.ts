export type ReportStatus = "draft" | "final" | "archived";

export type ConfirmedFilter = "all" | "confirmed" | "unconfirmed";

export type ReportOwner = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

export type ReportCohort = {
  id: string;
  name: string;
  is_archived: boolean;
};

export type ReportProject = {
  id: string;
  title: string;
  current_stage: string | null;
  stage_status: string | null;
  is_archived: boolean;
  owner: ReportOwner;
  cohort: ReportCohort | null;
};

export type ReportSummary = {
  id: string;
  report_version: number;
  status: ReportStatus;
  confirmed: boolean;
  created_at: string;
  updated_at: string;
  project: ReportProject;
};

export type ReportsResponse = {
  reports: ReportSummary[];
  total: number;
  page: number;
  limit: number;
};

export type CohortSummary = {
  id: string;
  name: string;
  is_archived: boolean;
};

export type CohortsResponse = {
  cohorts: CohortSummary[];
  total: number;
  page: number;
  limit: number;
};

export type UpdatedRange = "all" | "7" | "30" | "90";
