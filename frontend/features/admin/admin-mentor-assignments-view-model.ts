import type { useAppMessages } from "@/lib/i18n/provider";

export type AssignmentStatus = "pending" | "active" | "revoked";
export type AssignmentStatusFilter = AssignmentStatus | "all";
export type OrgRole = "owner" | "admin" | "mentor" | "student";
export type MemberStatus = "active" | "invited" | "removed";

export type MemberUser = {
  id: string | null;
  display_name: string | null;
  email: string | null;
};

export type OrgMember = {
  id: string;
  org_role: OrgRole;
  status: MemberStatus;
  user: MemberUser | null;
};

export type OrgMembersResponse = {
  members: OrgMember[];
  total: number;
  limit: number;
  offset: number;
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

export type CohortMemberItem = {
  user_id: string;
  display_name: string | null;
  email: string | null;
  status: "active" | "removed";
  role_in_cohort: "student" | "mentor";
};

export type CohortDetailResponse = {
  items: CohortMemberItem[];
  total: number;
  page: number;
  limit: number;
};

export type AssignmentUser = {
  id: string;
  display_name: string | null;
  email: string | null;
};

export type AssignmentCohort = {
  id: string;
  name: string;
};

export type MentorAssignment = {
  id: string;
  status: AssignmentStatus;
  can_view_messages: boolean;
  can_view_facts: boolean;
  can_comment: boolean;
  created_at: string;
  updated_at: string;
  mentor: AssignmentUser;
  student: AssignmentUser;
  cohort: AssignmentCohort | null;
};

export type MentorAssignmentsResponse = {
  assignments: MentorAssignment[];
  total: number;
  page: number;
  limit: number;
};

export type MemberOption = {
  id: string;
  label: string;
};

export type AssignmentFlags = {
  can_view_messages: boolean;
  can_view_facts: boolean;
  can_comment: boolean;
};

export type CohortOption = {
  id: string;
  label: string;
};

export type StatusFilterOption = {
  value: AssignmentStatusFilter;
  label: string;
};

export type AdminMentorAssignmentsMessages = ReturnType<
  typeof useAppMessages
>["adminMentorAssignments"];

export const DEFAULT_MENTOR_ASSIGNMENTS_LIMIT = 20;

export const ASSIGNMENT_STATUS_VARIANTS: Record<
  AssignmentStatus,
  "success" | "warning" | "danger"
> = {
  active: "success",
  pending: "warning",
  revoked: "danger",
};

export const resolveMentorAssignmentIntlLocale = (locale: string): string =>
  locale.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";

export const interpolateMentorAssignmentMessage = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export const resolveMentorAssignmentInitials = (value: string): string => {
  const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, " ").trim();
  if (!cleaned) {
    return "IS";
  }
  const parts = cleaned.split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "IS";
};

export const buildMentorAssignmentMemberLabel = (
  displayName: string | null,
  email: string | null,
  unknownMemberLabel: string
): string => {
  const trimmedName = displayName?.trim() ?? "";
  const trimmedEmail = email?.trim() ?? "";
  if (trimmedName && trimmedEmail) {
    return `${trimmedName} (${trimmedEmail})`;
  }
  return trimmedName || trimmedEmail || unknownMemberLabel;
};

export const buildAssignmentsQuery = (
  page: number,
  statusFilter: AssignmentStatusFilter,
  cohortId: string,
  query: string
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_MENTOR_ASSIGNMENTS_LIMIT));
  searchParams.set("status", statusFilter);
  if (cohortId) {
    searchParams.set("cohort_id", cohortId);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return searchParams.toString();
};

export const toMemberOptions = (
  members: OrgMember[],
  unknownMemberLabel: string
): MemberOption[] =>
  members
    .map((member) => {
      const user = member.user;
      if (!user?.id) {
        return null;
      }
      return {
        id: user.id,
        label: buildMentorAssignmentMemberLabel(
          user.display_name,
          user.email,
          unknownMemberLabel
        ),
      };
    })
    .filter((option): option is MemberOption => Boolean(option));

export const toCohortMemberOptions = (
  members: CohortMemberItem[],
  unknownMemberLabel: string
): MemberOption[] =>
  members
    .map((member) => ({
      id: member.user_id,
      label: buildMentorAssignmentMemberLabel(
        member.display_name,
        member.email,
        unknownMemberLabel
      ),
    }))
    .filter((option) => option.id);

export const ensureMentorAssignmentOption = (
  options: MemberOption[],
  user: AssignmentUser | null,
  unknownMemberLabel: string
): MemberOption[] => {
  if (!user?.id) {
    return options;
  }
  if (options.some((option) => option.id === user.id)) {
    return options;
  }
  return [
    {
      id: user.id,
      label: buildMentorAssignmentMemberLabel(
        user.display_name,
        user.email,
        unknownMemberLabel
      ),
    },
    ...options,
  ];
};
