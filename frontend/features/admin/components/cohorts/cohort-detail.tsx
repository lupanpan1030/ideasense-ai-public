"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useParams } from "next/navigation";
import { ApiError, apiClient } from "@/lib/api/client";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";

import {
  AddCohortMembersModal,
  RemoveCohortMemberModal,
} from "./cohort-detail-dialogs";
import {
  CohortDetailSurface,
  interpolate,
  resolveIntlLocale,
} from "./cohort-detail-surface";
import type {
  CohortDetailResponse,
  CohortMemberItem,
  CohortMembersAddResponse,
  CohortProjectItem,
  CohortSummary,
  DetailTab,
  MemberStatusFilter,
  OrgMember,
  OrgMembersResponse,
} from "./cohort-detail-types";

type CohortDetailProps = {
  cohortId: string;
};

const DEFAULT_LIMIT = 20;
const ORG_MEMBERS_LIMIT = 20;

const resolveParam = (
  value: string | string[] | undefined
): string | undefined => {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
};

const buildDetailQuery = (
  tab: DetailTab,
  page: number,
  statusFilter: MemberStatusFilter,
  query: string
): string => {
  const searchParams = new URLSearchParams();
  searchParams.set("tab", tab);
  searchParams.set("page", String(page));
  searchParams.set("limit", String(DEFAULT_LIMIT));
  if (tab !== "projects" && statusFilter !== "active") {
    searchParams.set("status", statusFilter);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return searchParams.toString();
};

const fetchCohortDetail = async (
  cohortId: string,
  tab: DetailTab,
  page: number,
  statusFilter: MemberStatusFilter,
  query: string
): Promise<CohortDetailResponse> => {
  const queryString = buildDetailQuery(tab, page, statusFilter, query);
  const url = queryString
    ? `/admin-api/cohorts/${cohortId}?${queryString}`
    : `/admin-api/cohorts/${cohortId}`;
  return apiClient.fetchJson<CohortDetailResponse>(url);
};

const fetchOrgMembers = async (
  page: number,
  query: string,
  cohortId: string,
  roles: string
): Promise<OrgMembersResponse> => {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(ORG_MEMBERS_LIMIT));
  searchParams.set("offset", String((page - 1) * ORG_MEMBERS_LIMIT));
  searchParams.set("status", "active");
  searchParams.set("exclude_cohort_id", cohortId);
  if (roles) {
    searchParams.set("roles", roles);
  }
  if (query) {
    searchParams.set("q", query);
  }
  return apiClient.fetchJson<OrgMembersResponse>(
    `/admin-api/org/members?${searchParams.toString()}`
  );
};

const addCohortMembers = async (
  cohortId: string,
  role: "student" | "mentor",
  userIds: string[]
): Promise<CohortMembersAddResponse> =>
  apiClient.postJson<CohortMembersAddResponse>(
    `/admin-api/cohorts/${cohortId}/members`,
    { role_in_cohort: role, user_ids: userIds }
  );

const removeCohortMember = async (
  cohortId: string,
  membershipId: string
): Promise<void> => {
  await apiClient.fetchJson(
    `/admin-api/cohorts/${cohortId}/members/${membershipId}`,
    { method: "DELETE" }
  );
};

const updateCohortArchive = async (
  cohortId: string,
  isArchived: boolean
): Promise<CohortSummary> =>
  apiClient.postJson<CohortSummary>(
    `/admin-api/cohorts/${cohortId}`,
    { is_archived: isArchived },
    { method: "PATCH" }
  );

const getDetailErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminCohortDetail"]
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

const getActionErrorMessage = (
  error: unknown,
  messages: ReturnType<typeof useAppMessages>["adminCohortDetail"]
): string => {
  if (error instanceof ApiError) {
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

export function CohortDetail({ cohortId }: CohortDetailProps) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminCohortDetail;
  const timelineMessages = appMessages.adminShared.timeline;
  const intlLocale = resolveIntlLocale(locale);
  const routeParams = useParams();
  const resolvedCohortId = useMemo(() => {
    return cohortId || resolveParam(routeParams?.cohortId);
  }, [cohortId, routeParams]);
  const [cohort, setCohort] = useState<CohortSummary | null>(null);
  const [items, setItems] = useState<Array<CohortMemberItem | CohortProjectItem>>(
    []
  );
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<DetailTab>("members");
  const [statusFilter, setStatusFilter] =
    useState<MemberStatusFilter>("active");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isArchiving, setIsArchiving] = useState(false);

  const [memberToRemove, setMemberToRemove] = useState<CohortMemberItem | null>(
    null
  );
  const [isRemoving, setIsRemoving] = useState(false);

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [availableMembers, setAvailableMembers] = useState<OrgMember[]>([]);
  const [availableTotal, setAvailableTotal] = useState(0);
  const [availablePage, setAvailablePage] = useState(1);
  const [memberQuery, setMemberQuery] = useState("");
  const [debouncedMemberQuery, setDebouncedMemberQuery] = useState("");
  const [isMembersLoading, setIsMembersLoading] = useState(false);
  const [memberLoadError, setMemberLoadError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Record<string, boolean>>({});
  const [selectedMembers, setSelectedMembers] = useState<
    Record<string, { id: string; name: string; email: string }>
  >({});
  const [memberActionError, setMemberActionError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const isMemberTab = tab === "members" || tab === "mentors";
  const tabLabel =
    tab === "members"
      ? messages.tabs.members
      : tab === "mentors"
        ? messages.tabs.mentors
        : messages.tabs.projects;
  const addLabel =
    tab === "members" ? messages.filters.addStudents : messages.filters.addMentors;
  const roleForAdd = tab === "members" ? "student" : "mentor";
  const availableRoleFilter =
    tab === "members" ? "student" : "mentor,admin,owner";
  const searchPlaceholder =
    tab === "projects"
      ? messages.filters.searchProjectsPlaceholder
      : tab === "mentors"
        ? messages.filters.searchMentorsPlaceholder
        : messages.filters.searchStudentsPlaceholder;

  const statusFilterOptions = useMemo(
    () => [
      { value: "active", label: messages.filters.statusOptions.active },
      { value: "removed", label: messages.filters.statusOptions.removed },
      { value: "all", label: messages.filters.statusOptions.all },
    ] satisfies Array<{ value: MemberStatusFilter; label: string }>,
    [messages]
  );

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setPage(1);
  }, [tab, statusFilter, debouncedQuery]);

  useEffect(() => {
    setItems([]);
    setTotal(0);
  }, [tab]);

  useEffect(() => {
    let isActive = true;
    if (!resolvedCohortId) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setLoadError(null);
    fetchCohortDetail(
      resolvedCohortId,
      tab,
      page,
      statusFilter,
      debouncedQuery
    )
      .then((response) => {
        if (!isActive) {
          return;
        }
        setCohort(response.cohort);
        setItems(response.items ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getDetailErrorMessage(error, messages));
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
  }, [resolvedCohortId, tab, page, statusFilter, debouncedQuery, messages]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    if (total === 0) {
      return;
    }
    const totalPages = Math.max(1, Math.ceil(total / DEFAULT_LIMIT));
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [total, page]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedMemberQuery(memberQuery.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [memberQuery]);

  useEffect(() => {
    if (!isAddOpen) {
      return;
    }
    setAvailablePage(1);
  }, [debouncedMemberQuery, isAddOpen]);

  useEffect(() => {
    if (!isAddOpen) {
      return;
    }
    setSelection({});
  }, [availablePage, debouncedMemberQuery, isAddOpen]);

  useEffect(() => {
    if (!isAddOpen) {
      return;
    }
    let isActive = true;
    if (!resolvedCohortId) {
      return;
    }
    setIsMembersLoading(true);
    setMemberLoadError(null);
    fetchOrgMembers(
      availablePage,
      debouncedMemberQuery,
      resolvedCohortId,
      availableRoleFilter
    )
      .then((response) => {
        if (!isActive) {
          return;
        }
        setAvailableMembers(response.members ?? []);
        setAvailableTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setMemberLoadError(getDetailErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsMembersLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [
    isAddOpen,
    availablePage,
    debouncedMemberQuery,
    resolvedCohortId,
    availableRoleFilter,
    messages,
  ]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / DEFAULT_LIMIT)),
    [total]
  );
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;
  const pageStart = total === 0 ? 0 : (page - 1) * DEFAULT_LIMIT + 1;
  const pageEnd = Math.min(page * DEFAULT_LIMIT, total);

  const availableTotalPages = useMemo(
    () => Math.max(1, Math.ceil(availableTotal / ORG_MEMBERS_LIMIT)),
    [availableTotal]
  );
  const canGoBackAvailable = availablePage > 1;
  const canGoForwardAvailable = availablePage < availableTotalPages;
  const hasSelection = Object.values(selection).some(Boolean);
  const hasSelectedMembers = Object.keys(selectedMembers).length > 0;

  const handleRemoveMember = async () => {
    if (!memberToRemove) {
      return;
    }
    setIsRemoving(true);
    setActionError(null);
    try {
      if (!resolvedCohortId) {
        return;
      }
      await removeCohortMember(
        resolvedCohortId,
        memberToRemove.membership_id
      );
      setToastMessage(messages.toasts.memberRemoved);
      const response = await fetchCohortDetail(
        resolvedCohortId,
        tab,
        page,
        statusFilter,
        debouncedQuery
      );
      setCohort(response.cohort);
      setItems(response.items ?? []);
      setTotal(response.total ?? 0);
    } catch (error) {
      setActionError(getActionErrorMessage(error, messages));
    } finally {
      setIsRemoving(false);
      setMemberToRemove(null);
    }
  };

  const handleArchiveToggle = async () => {
    if (!cohort || isArchiving) {
      return;
    }
    setIsArchiving(true);
    setActionError(null);
    try {
      const updated = await updateCohortArchive(cohort.id, !cohort.is_archived);
      setCohort(updated);
      setToastMessage(
        updated.is_archived
          ? messages.toasts.cohortArchived
          : messages.toasts.cohortUnarchived
      );
    } catch (error) {
      setActionError(getActionErrorMessage(error, messages));
    } finally {
      setIsArchiving(false);
    }
  };

  const handleAddSelected = () => {
    setMemberActionError(null);
    const availableMap = availableMembers.reduce<Record<string, OrgMember>>(
      (acc, member) => {
        const userId = member.user?.id;
        if (userId) {
          acc[userId] = member;
        }
        return acc;
      },
      {}
    );

    const nextSelected = { ...selectedMembers };
    Object.entries(selection).forEach(([userId, checked]) => {
      if (!checked || nextSelected[userId]) {
        return;
      }
      const member = availableMap[userId];
      const displayName =
        member?.user?.display_name ||
        member?.user?.email ||
        messages.addModal.unknownMember;
      const email = member?.user?.email || messages.addModal.noEmail;
      nextSelected[userId] = { id: userId, name: displayName, email };
    });

    setSelectedMembers(nextSelected);
    setSelection({});
  };

  const handleRemoveSelected = (userId: string) => {
    setMemberActionError(null);
    setSelectedMembers((prev) => {
      const next = { ...prev };
      delete next[userId];
      return next;
    });
  };

  const handleAddMembers = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMemberActionError(null);

    const userIds = Object.keys(selectedMembers);
    if (userIds.length === 0) {
      setMemberActionError(messages.errors.selectAtLeastOne);
      return;
    }

    setIsAdding(true);
    try {
      if (!resolvedCohortId) {
        return;
      }
      const response = await addCohortMembers(
        resolvedCohortId,
        roleForAdd,
        userIds
      );
      const messageParts = [];
      if (response.added) {
        messageParts.push(
          interpolate(messages.toasts.added, { count: response.added })
        );
      }
      if (response.restored) {
        messageParts.push(
          interpolate(messages.toasts.restored, { count: response.restored })
        );
      }
      if (response.updated) {
        messageParts.push(
          interpolate(messages.toasts.updated, { count: response.updated })
        );
      }
      setToastMessage(
        messageParts.length > 0
          ? messageParts.join(", ")
          : messages.toasts.membersUpdated
      );
      setIsAddOpen(false);
      setSelectedMembers({});
      setSelection({});
      const detail = await fetchCohortDetail(
        resolvedCohortId,
        tab,
        page,
        statusFilter,
        debouncedQuery
      );
      setCohort(detail.cohort);
      setItems(detail.items ?? []);
      setTotal(detail.total ?? 0);
    } catch (error) {
      setMemberActionError(getActionErrorMessage(error, messages));
    } finally {
      setIsAdding(false);
    }
  };

  const handleOpenAdd = () => {
    setMemberActionError(null);
    setMemberQuery("");
    setDebouncedMemberQuery("");
    setSelection({});
    setSelectedMembers({});
    setIsAddOpen(true);
  };

  const archiveLabel = cohort?.is_archived
    ? messages.projectTable.archived
    : messages.memberTable.active;
  const archiveVariant = cohort?.is_archived ? "warning" : "success";

  return (
    <>
      <CohortDetailSurface
        locale={locale}
        messages={messages}
        timelineMessages={timelineMessages}
        intlLocale={intlLocale}
        cohort={cohort}
        archiveLabel={archiveLabel}
        archiveVariant={archiveVariant}
        isArchiving={isArchiving}
        tab={tab}
        tabLabel={tabLabel}
        query={query}
        searchPlaceholder={searchPlaceholder}
        statusFilter={statusFilter}
        statusFilterOptions={statusFilterOptions}
        isMemberTab={isMemberTab}
        total={total}
        addLabel={addLabel}
        items={items}
        isLoading={isLoading}
        loadError={loadError}
        actionError={actionError}
        pageStart={pageStart}
        pageEnd={pageEnd}
        page={page}
        totalPages={totalPages}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        toastMessage={toastMessage}
        onArchiveToggle={handleArchiveToggle}
        onTabChange={setTab}
        onQueryChange={setQuery}
        onStatusFilterChange={setStatusFilter}
        onOpenAdd={handleOpenAdd}
        onPreviousPage={() => setPage(Math.max(page - 1, 1))}
        onNextPage={() => setPage(page + 1)}
        onRequestRemoveMember={setMemberToRemove}
      />

      {memberToRemove ? (
        <RemoveCohortMemberModal
          messages={messages}
          memberToRemove={memberToRemove}
          isRemoving={isRemoving}
          onClose={() => setMemberToRemove(null)}
          onConfirm={handleRemoveMember}
        />
      ) : null}

      {isAddOpen ? (
        <AddCohortMembersModal
          messages={messages}
          tab={tab === "members" ? "members" : "mentors"}
          memberQuery={memberQuery}
          memberLoadError={memberLoadError}
          isMembersLoading={isMembersLoading}
          availableMembers={availableMembers}
          selectedMembers={selectedMembers}
          selection={selection}
          hasSelection={hasSelection}
          hasSelectedMembers={hasSelectedMembers}
          memberActionError={memberActionError}
          isAdding={isAdding}
          availablePage={availablePage}
          availableTotalPages={availableTotalPages}
          canGoBackAvailable={canGoBackAvailable}
          canGoForwardAvailable={canGoForwardAvailable}
          onClose={() => setIsAddOpen(false)}
          onSubmit={handleAddMembers}
          onMemberQueryChange={setMemberQuery}
          onSelectionChange={(userId, checked) =>
            setSelection((prev) => ({
              ...prev,
              [userId]: checked,
            }))
          }
          onAddSelected={handleAddSelected}
          onAvailablePreviousPage={() =>
            setAvailablePage(Math.max(availablePage - 1, 1))
          }
          onAvailableNextPage={() => setAvailablePage(availablePage + 1)}
          onRemoveSelected={handleRemoveSelected}
        />
      ) : null}
    </>
  );
}
