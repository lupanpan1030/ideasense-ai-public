"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError, apiClient } from "@/lib/api/client";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import {
  buildAssignmentsQuery,
  DEFAULT_MENTOR_ASSIGNMENTS_LIMIT,
  ensureMentorAssignmentOption,
  resolveMentorAssignmentIntlLocale,
  toCohortMemberOptions,
  toMemberOptions,
  type AdminMentorAssignmentsMessages,
  type AssignmentStatusFilter,
  type CohortDetailResponse,
  type CohortsResponse,
  type CohortSummary,
  type MemberOption,
  type MentorAssignment,
  type MentorAssignmentsResponse,
  type OrgMembersResponse,
  type OrgRole,
} from "@/features/admin/admin-mentor-assignments-view-model";
import { MentorAssignmentsSurface } from "./mentor-assignments-panels";

const getAssignmentsErrorMessageWithLocale = (
  error: unknown,
  messages: AdminMentorAssignmentsMessages
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

const getAssignmentActionErrorMessage = (
  error: unknown,
  messages: AdminMentorAssignmentsMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return messages.errors.updateNoAccess;
    }
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

const fetchAssignments = async (
  page: number,
  statusFilter: AssignmentStatusFilter,
  cohortId: string,
  query: string
): Promise<MentorAssignmentsResponse> => {
  const queryString = buildAssignmentsQuery(page, statusFilter, cohortId, query);
  const url = queryString
    ? `/admin-api/mentor-assignments?${queryString}`
    : "/admin-api/mentor-assignments";
  return apiClient.fetchJson<MentorAssignmentsResponse>(url);
};

const fetchCohorts = async (): Promise<CohortsResponse> => {
  const query = new URLSearchParams({
    page: "1",
    limit: "100",
    status: "all",
  });
  return apiClient.fetchJson<CohortsResponse>(`/admin-api/cohorts?${query}`);
};

const fetchOrgMembers = async (
  roles: OrgRole[]
): Promise<OrgMembersResponse> => {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", "100");
  searchParams.set("offset", "0");
  searchParams.set("status", "active");
  if (roles.length > 0) {
    searchParams.set("roles", roles.join(","));
  }
  return apiClient.fetchJson<OrgMembersResponse>(
    `/admin-api/org/members?${searchParams.toString()}`
  );
};

const fetchCohortMembers = async (
  cohortId: string,
  tab: "members" | "mentors"
): Promise<CohortDetailResponse> => {
  const searchParams = new URLSearchParams();
  searchParams.set("tab", tab);
  searchParams.set("status", "active");
  searchParams.set("page", "1");
  searchParams.set("limit", "100");
  return apiClient.fetchJson<CohortDetailResponse>(
    `/admin-api/cohorts/${cohortId}?${searchParams.toString()}`
  );
};

const createAssignment = async (payload: {
  mentor_user_id: string;
  student_user_id: string;
  cohort_id?: string | null;
  can_view_messages: boolean;
  can_view_facts: boolean;
  can_comment: boolean;
}): Promise<MentorAssignment> =>
  apiClient.postJson<MentorAssignment>("/admin-api/mentor-assignments", payload);

const updateAssignment = async (
  assignmentId: string,
  payload: {
    status?: "active" | "revoked";
    can_view_messages?: boolean;
    can_view_facts?: boolean;
    can_comment?: boolean;
  }
): Promise<MentorAssignment> =>
  apiClient.postJson<MentorAssignment>(
    `/admin-api/mentor-assignments/${assignmentId}`,
    payload,
    { method: "PATCH" }
  );

export function MentorAssignmentsTable() {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminMentorAssignments;
  const archivedCohortLabel = appMessages.adminCohorts.table.archived;
  const intlLocale = resolveMentorAssignmentIntlLocale(locale);
  const [assignments, setAssignments] = useState<MentorAssignment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<AssignmentStatusFilter>(
    "active"
  );
  const [cohortFilter, setCohortFilter] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [cohortError, setCohortError] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "restore" | "edit">(
    "create"
  );
  const [editingAssignment, setEditingAssignment] =
    useState<MentorAssignment | null>(null);
  const [selectedCohortId, setSelectedCohortId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [mentorId, setMentorId] = useState("");
  const [flags, setFlags] = useState({
    can_view_messages: false,
    can_view_facts: false,
    can_comment: true,
  });
  const [memberOptions, setMemberOptions] = useState<{
    students: MemberOption[];
    mentors: MemberOption[];
  }>({ students: [], mentors: [] });
  const [memberOptionsLoading, setMemberOptionsLoading] = useState(false);
  const [memberOptionsError, setMemberOptionsError] = useState<string | null>(
    null
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [assignmentToRevoke, setAssignmentToRevoke] =
    useState<MentorAssignment | null>(null);
  const [isRevoking, setIsRevoking] = useState(false);

  const cohortOptions = useMemo(
    () =>
      cohorts.map((cohort) => ({
        id: cohort.id,
        label: cohort.is_archived
          ? `${cohort.name} (${archivedCohortLabel})`
          : cohort.name,
      })),
    [cohorts, archivedCohortLabel]
  );

  const statusFilterOptions = useMemo(
    () => [
      { value: "active", label: messages.filters.statusOptions.active },
      { value: "revoked", label: messages.filters.statusOptions.revoked },
      { value: "pending", label: messages.filters.statusOptions.pending },
      { value: "all", label: messages.filters.statusOptions.all },
    ] satisfies Array<{ value: AssignmentStatusFilter; label: string }>,
    [messages]
  );

  const totalPages = Math.max(
    1,
    Math.ceil(total / DEFAULT_MENTOR_ASSIGNMENTS_LIMIT)
  );
  const pageStart =
    total === 0 ? 0 : (page - 1) * DEFAULT_MENTOR_ASSIGNMENTS_LIMIT + 1;
  const pageEnd = Math.min(total, page * DEFAULT_MENTOR_ASSIGNMENTS_LIMIT);
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setPage(1);
  }, [query, statusFilter, cohortFilter]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchAssignments(page, statusFilter, cohortFilter, debouncedQuery)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setAssignments(response.assignments ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getAssignmentsErrorMessageWithLocale(error, messages));
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
  }, [page, statusFilter, cohortFilter, debouncedQuery, refreshToken, messages]);

  useEffect(() => {
    if (total === 0) {
      if (page !== 1) {
        setPage(1);
      }
      return;
    }
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, total, totalPages]);

  useEffect(() => {
    let isActive = true;
    setCohortError(null);
    fetchCohorts()
      .then((response) => {
        if (!isActive) {
          return;
        }
        setCohorts(response.cohorts ?? []);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setCohortError(getAssignmentsErrorMessageWithLocale(error, messages));
      });
    return () => {
      isActive = false;
    };
  }, [messages]);

  useEffect(() => {
    if (!isModalOpen) {
      return;
    }
    let isActive = true;
    setMemberOptionsLoading(true);
    setMemberOptionsError(null);

    const loadOptions = async () => {
      if (selectedCohortId) {
        const [studentsResponse, mentorsResponse] = await Promise.all([
          fetchCohortMembers(selectedCohortId, "members"),
          fetchCohortMembers(selectedCohortId, "mentors"),
        ]);
        return {
          students: toCohortMemberOptions(
            studentsResponse.items ?? [],
            messages.table.unknownMember
          ),
          mentors: toCohortMemberOptions(
            mentorsResponse.items ?? [],
            messages.table.unknownMember
          ),
        };
      }
      const [studentsResponse, mentorsResponse] = await Promise.all([
        fetchOrgMembers(["student"]),
        fetchOrgMembers(["mentor", "admin", "owner"]),
      ]);
      return {
        students: toMemberOptions(
          studentsResponse.members ?? [],
          messages.table.unknownMember
        ),
        mentors: toMemberOptions(
          mentorsResponse.members ?? [],
          messages.table.unknownMember
        ),
      };
    };

    loadOptions()
      .then((options) => {
        if (!isActive) {
          return;
        }
        let students = options.students;
        let mentors = options.mentors;
        if (editingAssignment) {
          students = ensureMentorAssignmentOption(
            students,
            editingAssignment.student,
            messages.table.unknownMember
          );
          mentors = ensureMentorAssignmentOption(
            mentors,
            editingAssignment.mentor,
            messages.table.unknownMember
          );
        }
        setMemberOptions({ students, mentors });
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setMemberOptionsError(getAssignmentsErrorMessageWithLocale(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setMemberOptionsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [isModalOpen, selectedCohortId, editingAssignment, messages]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  const openCreateModal = () => {
    setModalMode("create");
    setEditingAssignment(null);
    setSelectedCohortId("");
    setStudentId("");
    setMentorId("");
    setFlags({
      can_view_messages: false,
      can_view_facts: false,
      can_comment: true,
    });
    setMemberOptionsError(null);
    setFormError(null);
    setIsModalOpen(true);
  };

  const openRestoreModal = (assignment: MentorAssignment) => {
    setModalMode("restore");
    setEditingAssignment(assignment);
    setSelectedCohortId(assignment.cohort?.id ?? "");
    setStudentId(assignment.student?.id ?? "");
    setMentorId(assignment.mentor?.id ?? "");
    setFlags({
      can_view_messages: assignment.can_view_messages,
      can_view_facts: assignment.can_view_facts,
      can_comment: assignment.can_comment,
    });
    setMemberOptionsError(null);
    setFormError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (assignment: MentorAssignment) => {
    setModalMode("edit");
    setEditingAssignment(assignment);
    setSelectedCohortId(assignment.cohort?.id ?? "");
    setStudentId(assignment.student?.id ?? "");
    setMentorId(assignment.mentor?.id ?? "");
    setFlags({
      can_view_messages: assignment.can_view_messages,
      can_view_facts: assignment.can_view_facts,
      can_comment: assignment.can_comment,
    });
    setMemberOptionsError(null);
    setFormError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (isSubmitting) {
      return;
    }
    setFormError(null);
    setIsModalOpen(false);
  };

  const handleMessagesToggle = (checked: boolean) => {
    setFlags((prev) => ({
      ...prev,
      can_view_messages: checked,
      can_view_facts: checked ? true : prev.can_view_facts,
    }));
  };

  const handleFactsToggle = (checked: boolean) => {
    setFlags((prev) => ({
      ...prev,
      can_view_facts: checked,
    }));
  };

  const handleCommentToggle = (checked: boolean) => {
    setFlags((prev) => ({
      ...prev,
      can_comment: checked,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setActionError(null);

    if (modalMode === "create") {
      if (!studentId || !mentorId) {
        setFormError(messages.errors.selectStudentAndMentor);
        return;
      }
      if (studentId === mentorId) {
        setFormError(messages.errors.mentorStudentDifferent);
        return;
      }
    } else if (!editingAssignment) {
      setFormError(messages.errors.assignmentUnavailable);
      return;
    }

    const normalizedFlags = flags.can_view_messages
      ? { ...flags, can_view_facts: true }
      : flags;

    setIsSubmitting(true);
    try {
      if (modalMode === "restore" && editingAssignment) {
        await updateAssignment(editingAssignment.id, {
          status: "active",
          can_view_messages: normalizedFlags.can_view_messages,
          can_view_facts: normalizedFlags.can_view_facts,
          can_comment: normalizedFlags.can_comment,
        });
        setToastMessage(messages.toasts.restored);
      } else if (modalMode === "edit" && editingAssignment) {
        await updateAssignment(editingAssignment.id, {
          can_view_messages: normalizedFlags.can_view_messages,
          can_view_facts: normalizedFlags.can_view_facts,
          can_comment: normalizedFlags.can_comment,
        });
        setToastMessage(messages.toasts.updated);
      } else {
        await createAssignment({
          mentor_user_id: mentorId,
          student_user_id: studentId,
          cohort_id: selectedCohortId || null,
          can_view_messages: normalizedFlags.can_view_messages,
          can_view_facts: normalizedFlags.can_view_facts,
          can_comment: normalizedFlags.can_comment,
        });
        setToastMessage(messages.toasts.created);
      }
      setIsModalOpen(false);
      setRefreshToken((prev) => prev + 1);
    } catch (error) {
      setFormError(getAssignmentActionErrorMessage(error, messages));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async () => {
    if (!assignmentToRevoke) {
      return;
    }
    setIsRevoking(true);
    setActionError(null);
    try {
      await updateAssignment(assignmentToRevoke.id, { status: "revoked" });
      setToastMessage(messages.toasts.revoked);
      setRefreshToken((prev) => prev + 1);
    } catch (error) {
      setActionError(getAssignmentActionErrorMessage(error, messages));
    } finally {
      setIsRevoking(false);
      setAssignmentToRevoke(null);
    }
  };

  const handleCohortChange = (value: string) => {
    setSelectedCohortId(value);
    if (modalMode === "create") {
      setStudentId("");
      setMentorId("");
    }
  };

  const factsLocked = flags.can_view_messages;
  const isLockedMode = modalMode !== "create";

  return (
    <MentorAssignmentsSurface
      messages={messages}
      intlLocale={intlLocale}
      assignments={assignments}
      total={total}
      query={query}
      statusFilter={statusFilter}
      statusFilterOptions={statusFilterOptions}
      cohortFilter={cohortFilter}
      cohortOptions={cohortOptions}
      isLoading={isLoading}
      loadError={loadError}
      cohortError={cohortError}
      actionError={actionError}
      pageStart={pageStart}
      pageEnd={pageEnd}
      page={page}
      totalPages={totalPages}
      canGoBack={canGoBack}
      canGoForward={canGoForward}
      isModalOpen={isModalOpen}
      modalMode={modalMode}
      selectedCohortId={selectedCohortId}
      studentId={studentId}
      mentorId={mentorId}
      flags={flags}
      memberOptions={memberOptions}
      memberOptionsLoading={memberOptionsLoading}
      memberOptionsError={memberOptionsError}
      formError={formError}
      isSubmitting={isSubmitting}
      factsLocked={factsLocked}
      isLockedMode={isLockedMode}
      assignmentToRevoke={assignmentToRevoke}
      isRevoking={isRevoking}
      toastMessage={toastMessage}
      onQueryChange={setQuery}
      onStatusFilterChange={setStatusFilter}
      onCohortFilterChange={setCohortFilter}
      onCreateAssignment={openCreateModal}
      onPreviousPage={() => setPage(Math.max(page - 1, 1))}
      onNextPage={() => setPage(page + 1)}
      onEditAssignment={openEditModal}
      onRestoreAssignment={openRestoreModal}
      onRequestRevoke={setAssignmentToRevoke}
      onCloseModal={closeModal}
      onSubmit={handleSubmit}
      onSelectedCohortChange={handleCohortChange}
      onStudentIdChange={setStudentId}
      onMentorIdChange={setMentorId}
      onMessagesToggle={handleMessagesToggle}
      onFactsToggle={handleFactsToggle}
      onCommentToggle={handleCommentToggle}
      onCloseRevoke={() => setAssignmentToRevoke(null)}
      onConfirmRevoke={handleRevoke}
    />
  );
}
