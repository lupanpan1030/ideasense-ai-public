export type DetailTab = "members" | "mentors" | "projects";

export type MemberStatusFilter = "active" | "removed" | "all";

export type CohortSummary = {
  id: string;
  name: string;
  description: string | null;
  start_at: string | null;
  end_at: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  students_count: number;
  mentors_count: number;
  projects_count: number;
};

export type CohortMemberItem = {
  membership_id: string;
  user_id: string;
  display_name: string | null;
  email: string | null;
  status: "active" | "removed";
  joined_at: string;
  role_in_cohort: "student" | "mentor";
};

export type CohortProjectItem = {
  id: string;
  title: string | null;
  owner_name: string | null;
  owner_email: string | null;
  current_stage: string | null;
  stage_status: string | null;
  is_archived: boolean;
};

export type CohortDetailResponse = {
  cohort: CohortSummary;
  list_type: DetailTab;
  items: Array<CohortMemberItem | CohortProjectItem>;
  total: number;
  page: number;
  limit: number;
};

export type OrgMember = {
  id: string;
  org_role: string;
  status: "active" | "invited" | "removed";
  created_at: string;
  user: {
    id: string;
    display_name: string | null;
    email: string | null;
  } | null;
};

export type OrgMembersResponse = {
  members: OrgMember[];
  total: number;
  limit: number;
  offset: number;
};

export type CohortMembersAddResponse = {
  added: number;
  updated: number;
  restored: number;
};
