"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, apiClient } from "@/lib/api/client";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import {
  buildMembersQuery,
  DEFAULT_MEMBERS_LIMIT,
  MEMBER_ROLE_FILTER_VALUES,
  MEMBER_ROLE_VALUES,
  type AdminMembersMessages,
  type MemberRoleFilter,
  type MembersResponse,
  type MutableOrgRole,
  type OrgMember,
} from "@/features/admin/admin-members-view-model";
import { RemoveMemberModal } from "@/features/admin/components/org/member-modals";
import { MembersTableSurface } from "@/features/admin/components/org/members-table-surface";

const getMembersErrorMessage = (
  error: unknown,
  messages: AdminMembersMessages
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

const getMemberActionErrorMessage = (
  error: unknown,
  messages: AdminMembersMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return error.message.toLowerCase().includes("owner")
        ? messages.errors.ownerImmutable
        : messages.errors.noAccess;
    }
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

const fetchMembers = async (
  offset: number,
  roleFilter: MemberRoleFilter,
  query: string
): Promise<MembersResponse> => {
  const queryString = buildMembersQuery(offset, roleFilter, query);
  const url = queryString
    ? `/admin-api/org/members?${queryString}`
    : "/admin-api/org/members";
  return apiClient.fetchJson<MembersResponse>(url);
};

const updateMemberRole = async (
  membershipId: string,
  role: MutableOrgRole
): Promise<OrgMember> =>
  apiClient.postJson<OrgMember>(
    `/admin-api/org/members/${membershipId}`,
    { role },
    { method: "PATCH" }
  );

const removeMember = async (membershipId: string): Promise<void> => {
  await apiClient.fetchJson(`/admin-api/org/members/${membershipId}`, {
    method: "DELETE",
  });
};

export function MembersTable() {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminMembers;
  const roleLabels = appMessages.adminShell.roles;
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<MemberRoleFilter>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingRoles, setPendingRoles] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [memberToRemove, setMemberToRemove] = useState<OrgMember | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setOffset(0);
  }, [query, roleFilter]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchMembers(offset, roleFilter, debouncedQuery)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setMembers(response.members ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getMembersErrorMessage(error, messages));
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
  }, [offset, roleFilter, debouncedQuery, messages]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    if (offset === 0 || total === 0) {
      return;
    }
    if (offset >= total) {
      const lastPageOffset =
        Math.max(0, Math.floor((total - 1) / DEFAULT_MEMBERS_LIMIT)) *
        DEFAULT_MEMBERS_LIMIT;
      if (lastPageOffset !== offset) {
        setOffset(lastPageOffset);
      }
    }
  }, [offset, total]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / DEFAULT_MEMBERS_LIMIT)),
    [total]
  );
  const currentPage = useMemo(
    () => Math.min(totalPages, Math.floor(offset / DEFAULT_MEMBERS_LIMIT) + 1),
    [offset, totalPages]
  );
  const canGoBack = offset > 0;
  const canGoForward = offset + DEFAULT_MEMBERS_LIMIT < total;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + DEFAULT_MEMBERS_LIMIT, total);
  const removeTargetName = memberToRemove
    ? memberToRemove.user?.display_name ||
      memberToRemove.user?.email ||
      messages.table.removedMember
    : messages.table.removedMember;
  const roleFilterOptions = MEMBER_ROLE_FILTER_VALUES.map((value) => ({
    value,
    label: messages.filters.roleOptions[value],
  }));
  const roleOptions = MEMBER_ROLE_VALUES.map((value) => ({
    value,
    label: roleLabels[value] ?? value,
  }));

  const handleRoleChange = async (
    member: OrgMember,
    nextRole: MutableOrgRole
  ) => {
    if (member.org_role === nextRole) {
      return;
    }
    setActionError(null);
    setPendingRoles((prev) => ({ ...prev, [member.id]: true }));
    setMembers((prev) =>
      prev.map((item) =>
        item.id === member.id ? { ...item, org_role: nextRole } : item
      )
    );

    try {
      await updateMemberRole(member.id, nextRole);
      setToastMessage(messages.toasts.roleUpdated);
    } catch (error) {
      setMembers((prev) =>
        prev.map((item) =>
          item.id === member.id ? { ...item, org_role: member.org_role } : item
        )
      );
      setActionError(getMemberActionErrorMessage(error, messages));
    } finally {
      setPendingRoles((prev) => {
        const next = { ...prev };
        delete next[member.id];
        return next;
      });
    }
  };

  const handleRemove = async () => {
    if (!memberToRemove) {
      return;
    }
    setIsRemoving(true);
    setActionError(null);
    try {
      await removeMember(memberToRemove.id);
      setMembers((prev) =>
        prev.map((item) =>
          item.id === memberToRemove.id
            ? { ...item, status: "removed" }
            : item
        )
      );
      setToastMessage(messages.toasts.memberRemoved);
    } catch (error) {
      setActionError(getMemberActionErrorMessage(error, messages));
    } finally {
      setIsRemoving(false);
      setMemberToRemove(null);
    }
  };

  return (
    <>
      <MembersTableSurface
        actionError={actionError}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        currentPage={currentPage}
        isLoading={isLoading}
        loadError={loadError}
        locale={locale}
        members={members}
        messages={messages}
        offset={offset}
        onOffsetChange={setOffset}
        onQueryChange={setQuery}
        onRemoveRequest={setMemberToRemove}
        onRoleChange={handleRoleChange}
        onRoleFilterChange={setRoleFilter}
        pageEnd={pageEnd}
        pageStart={pageStart}
        pendingRoles={pendingRoles}
        query={query}
        roleFilter={roleFilter}
        roleFilterOptions={roleFilterOptions}
        roleOptions={roleOptions}
        toastMessage={toastMessage}
        total={total}
        totalPages={totalPages}
      />
      <RemoveMemberModal
        isRemoving={isRemoving}
        member={memberToRemove}
        messages={messages}
        onClose={() => setMemberToRemove(null)}
        onConfirm={handleRemove}
        removeTargetName={removeTargetName}
      />
    </>
  );
}
